"""Instagram Bot Paneli - Ana Flask Uygulamasi"""
from flask import Flask, request, jsonify, Response, render_template
import json
import os
import time
import signal

from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, FLASK_THREADED, MAX_WAIT_STREAM, PID_DIR
from database import (
    init_db, db_add_account, db_get_accounts, db_get_account,
    db_delete_account, db_toggle_account, db_get_follow_history,
    db_get_stats, db_mark_all_pending, db_clear_history,
    db_get_daily_stats,
    # YENI FONKSIYONLAR
    db_add_target, db_get_targets, db_delete_target, db_toggle_target,
    db_save_bot_settings, db_get_bot_settings, db_get_all_bot_settings,
    db_get_failed_list, db_allow_retry
)
from bot_runner import bot_runner, get_log_file, read_pid

app = Flask(__name__)

init_db()


def _pid_exists(pid):
    """psutil olmadan PID kontrolu"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


@app.route('/')
def index():
    return render_template('panel.html')


@app.route('/api/status')
def get_status():
    """Calisan bot'lari tespit et"""
    running = {}
    for bot_num in [1, 2, 3, 4]:
        pid = read_pid(bot_num)
        if pid and _pid_exists(pid):
            running[bot_num] = {"pid": pid, "running": True}
        else:
            running[bot_num] = {"pid": None, "running": False}
    return jsonify({"ok": True, "running": running})


# ============ HESAP ISLEMLERI ============

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    accounts = db_get_accounts()
    return jsonify({
        "ok": True,
        "accounts": [
            {"id": row[0], "name": row[1], "username": row[2], "is_active": bool(row[3])}
            for row in accounts
        ]
    })


@app.route('/api/accounts', methods=['POST'])
def add_account():
    data = request.get_json()
    name = data.get('name', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not name or not username or not password:
        return jsonify({"ok": False, "message": "Tum alanlari doldurun!"})
    account_id = db_add_account(name, username, password)
    if account_id:
        return jsonify({"ok": True, "message": "Hesap eklendi", "id": account_id})
    return jsonify({"ok": False, "message": "Hesap eklenemedi"})


@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def delete_account_route(account_id):
    db_delete_account(account_id)
    return jsonify({"ok": True, "message": "Hesap silindi"})


@app.route('/api/accounts/<int:account_id>/toggle', methods=['POST'])
def toggle_account_route(account_id):
    data = request.get_json()
    is_active = data.get('is_active', 1)
    db_toggle_account(account_id, is_active)
    status = "aktif" if is_active else "pasif"
    return jsonify({"ok": True, "message": "Hesap " + status + " yapildi"})


# ============ HEDEF HESAP ISLEMLERI (YENI) ============

@app.route('/api/targets', methods=['GET'])
def get_targets():
    account_id = int(request.args.get('account', 0))
    if not account_id:
        return jsonify({"ok": False, "message": "Hesap secilmedi"})
    targets = db_get_targets(account_id)
    return jsonify({
        "ok": True,
        "targets": [
            {"id": row[0], "username": row[1], "is_active": bool(row[2])}
            for row in targets
        ]
    })


@app.route('/api/targets', methods=['POST'])
def add_target():
    data = request.get_json()
    account_id = data.get('account_id', 0)
    username = data.get('username', '').strip().replace('@', '')
    if not account_id or not username:
        return jsonify({"ok": False, "message": "Hesap ve kullanici adi gerekli!"})
    target_id = db_add_target(account_id, username)
    if target_id:
        return jsonify({"ok": True, "message": "Hedef eklendi", "id": target_id})
    return jsonify({"ok": False, "message": "Hedef zaten var veya eklenemedi"})


@app.route('/api/targets/<int:target_id>', methods=['DELETE'])
def delete_target_route(target_id):
    db_delete_target(target_id)
    return jsonify({"ok": True, "message": "Hedef silindi"})


@app.route('/api/targets/<int:target_id>/toggle', methods=['POST'])
def toggle_target_route(target_id):
    data = request.get_json()
    is_active = data.get('is_active', 1)
    db_toggle_target(target_id, is_active)
    return jsonify({"ok": True, "message": "Hedef guncellendi"})


# ============ BOT AYARLARI (YENI) ============

@app.route('/api/bot-settings/<int:bot_id>', methods=['GET'])
def get_bot_settings(bot_id):
    settings = db_get_bot_settings(bot_id)
    return jsonify({"ok": True, "settings": settings})


@app.route('/api/bot-settings/<int:bot_id>', methods=['POST'])
def save_bot_settings(bot_id):
    data = request.get_json()
    account_id = data.get('account_id', 0)
    settings = data.get('settings', {})
    if db_save_bot_settings(bot_id, account_id, settings):
        return jsonify({"ok": True, "message": "Ayarlar kaydedildi"})
    return jsonify({"ok": False, "message": "Ayarlar kaydedilemedi"})


@app.route('/api/bot-settings', methods=['GET'])
def get_all_bot_settings():
    settings = db_get_all_bot_settings()
    return jsonify({"ok": True, "settings": settings})


# ============ BASARISIZ TAKIP KONTROLU (YENI) ============

@app.route('/api/failed/<int:account_id>', methods=['GET'])
def get_failed_list(account_id):
    failed = db_get_failed_list(account_id)
    return jsonify({
        "ok": True,
        "failed": [
            {"username": row[0], "fail_count": row[1], "can_retry": bool(row[2]), "last_failed": row[3]}
            for row in failed
        ]
    })


@app.route('/api/failed/allow-retry', methods=['POST'])
def allow_retry():
    data = request.get_json()
    username = data.get('username', '')
    account_id = data.get('account_id', 0)
    if not username or not account_id:
        return jsonify({"ok": False, "message": "Kullanici adi ve hesap gerekli!"})
    db_allow_retry(username, account_id)
    return jsonify({"ok": True, "message": f"@{username} tekrar deneme izni verildi"})


# ============ BOT BASLATMA/DURDURMA ============

@app.route('/api/start/<int:bot_num>', methods=['POST'])
def start_bot(bot_num):
    data = request.get_json()
    account_id = int(data.get('account_id', 0))
    if not account_id:
        return jsonify({"ok": False, "message": "Hesap secilmedi!"})

    account = db_get_account(account_id)
    if not account:
        return jsonify({"ok": False, "message": "Hesap bulunamadi!"})

    username = account[2]
    password = account[3]

    # ===== YENI: Ayarlari kaydet =====
    db_save_bot_settings(bot_num, account_id, data)

    success, message = bot_runner.start(bot_num, account_id, username, password, data)
    return jsonify({"ok": success, "message": message})


@app.route('/api/stop/<int:bot_num>', methods=['POST'])
def stop_bot(bot_num):
    bot_runner.stop(bot_num)
    return jsonify({"ok": True, "message": f"Bot {bot_num} durduruldu"})


# ============ LOG STREAMING ============

@app.route('/api/logs/<int:bot_num>')
def get_logs(bot_num):
    lines = bot_runner.get_log_tail(bot_num, 200)
    return jsonify({"ok": True, "logs": lines})


@app.route('/api/stream/<int:bot_num>')
def stream_logs(bot_num):
    def generate():
        log_file = get_log_file(bot_num)
        if not os.path.exists(log_file):
            yield "data: Log dosyasi bulunamadi\n\n"
            return

        with open(log_file, 'r', encoding='utf-8') as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line}\n\n"
                else:
                    time.sleep(1)
                    pid = read_pid(bot_num)
                    if not pid or not _pid_exists(pid):
                        yield "data: [BOT DURDU]\n\n"
                        break

    return Response(generate(), mimetype='text/event-stream')


# ============ VERITABANI ISTATISTIKLERI ============

@app.route('/api/history')
def get_history():
    bot_id = int(request.args.get('bot', 4))
    account_id = int(request.args.get('account', 0))
    if not account_id:
        return jsonify({"ok": False, "message": "Hesap secilmedi"})
    history = db_get_follow_history(bot_id, account_id, 25)
    stats = db_get_stats(account_id)
    daily = db_get_daily_stats(account_id, 7)
    return jsonify({
        "ok": True,
        "history": [
            {"username": row[0], "target": row[1], "status": row[2], "result": row[3], "time": row[4]}
            for row in history
        ],
        "stats": stats,
        "daily": [
            {"date": row[0], "approved": row[1], "rejected": row[2]}
            for row in daily
        ]
    })


@app.route('/api/reset-failed', methods=['POST'])
def reset_failed():
    data = request.get_json()
    account_id = int(data.get('account_id', 0))
    if not account_id:
        return jsonify({"ok": False, "message": "Hesap secilmedi"})
    db_mark_all_pending(account_id)
    return jsonify({"ok": True, "message": "Izni olan basarisizlar tekrar siraya alindi"})


@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    data = request.get_json()
    account_id = int(data.get('account_id', 0))
    if not account_id:
        return jsonify({"ok": False, "message": "Hesap secilmedi"})
    db_clear_history(account_id)
    return jsonify({"ok": True, "message": "Gecmis temizlendi"})


if __name__ == '__main__':
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, threaded=FLASK_THREADED)
