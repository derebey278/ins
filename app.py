"""Instagram Bot Paneli - Ana Flask Uygulaması"""
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
    db_get_daily_stats
)
from bot_runner import bot_runner, get_log_file, read_pid

app = Flask(__name__)

init_db()


def _pid_exists(pid):
    """psutil olmadan PID kontrolü"""
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
    """Çalışan bot'ları tespit et"""
    running = {}
    for bot_num in [1, 2, 3, 4]:
        pid = read_pid(bot_num)
        if pid and _pid_exists(pid):
            running[bot_num] = {"pid": pid, "running": True}
        else:
            running[bot_num] = {"pid": None, "running": False}
    return jsonify({"ok": True, "running": running})


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
            {
                "username": row[0],
                "target_account": row[1],
                "status": row[2],
                "result": row[3],
                "followed_at": row[4]
            } for row in history
        ],
        "stats": stats,
        "daily_stats": [
            {"date": row[0], "approved": row[1], "rejected": row[2]} for row in daily
        ]
    })


@app.route('/api/reset_failed', methods=['POST'])
def reset_failed():
    bot_id = int(request.args.get('bot', 4))
    account_id = int(request.args.get('account', 0))
    if not account_id:
        return jsonify({"ok": False, "message": "Hesap secilmedi"})
    db_mark_all_pending(account_id)
    return jsonify({"ok": True, "message": "Basarisiz kullanicilar tekrar siraya alindi"})


@app.route('/api/clear_history', methods=['POST'])
def clear_history():
    bot_id = int(request.args.get('bot', 4))
    account_id = int(request.args.get('account', 0))
    if not account_id:
        return jsonify({"ok": False, "message": "Hesap secilmedi"})
    db_clear_history(account_id)
    return jsonify({"ok": True, "message": "Gecmis temizlendi"})


@app.route('/api/start', methods=['POST', 'GET'])
def start_bot():
    bot_num = int(request.args.get('bot', 1))

    data = {}
    if request.method == 'POST':
        try:
            data = request.get_json(force=True, silent=True) or {}
        except:
            data = {}

    if not data:
        data = {
            'account_id': request.args.get('account_id', ''),
            'target': request.args.get('target', ''),
            'targets': request.args.getlist('targets') or [request.args.get('target', '')],
            'max_per_target': request.args.get('max_per_target', '50'),
            'loop_delay': request.args.get('loop_delay', '60'),
            'batch_size': request.args.get('batch_size', '50'),
            'delay': request.args.get('delay', '5'),
            'break_after': request.args.get('break_after', '400'),
            'break_duration': request.args.get('break_duration', '100'),
            'mode': request.args.get('mode', 'collect_loop')
        }

    account_id = 0
    try:
        account_id = int(data.get('account_id', 0))
    except:
        account_id = 0

    if not account_id:
        return jsonify({"ok": False, "message": "Hesap secilmedi"})

    print("[DEBUG] Bot " + str(bot_num) + " baslatiliyor, account_id=" + str(account_id))

    account = db_get_account(account_id)
    if not account:
        print("[DEBUG] Hesap bulunamadi: " + str(account_id))
        return jsonify({"ok": False, "message": "Hesap bulunamadi"})
    print("[DEBUG] Hesap bulundu: " + account[2])

    username = account[2]
    password = account[3]

    ok, message = bot_runner.start(bot_num, account_id, username, password, data)
    return jsonify({"ok": ok, "message": message})


@app.route('/api/stop', methods=['GET', 'POST'])
def stop_bot():
    bot_num = int(request.args.get('bot', 1))
    bot_runner.stop(bot_num)
    return jsonify({"ok": True, "message": "Bot " + str(bot_num) + " durduruldu"})


@app.route('/api/stream', methods=['GET'])
def stream():
    bot_num = int(request.args.get('bot', 1))
    account_id = int(request.args.get('account', 0))
    reconnect = request.args.get('reconnect', 'false') == 'true'

    def generate():
        log_file = get_log_file(bot_num)

        max_wait = MAX_WAIT_STREAM
        waited = 0
        while waited < max_wait:
            if bot_runner.is_running(bot_num):
                break
            time.sleep(0.5)
            waited += 0.5
            yield "data: " + json.dumps({"type":"log","msg":"Bot baslatiliyor...","level":"info"}) + "\n\n"

        if not bot_runner.is_running(bot_num):
            yield "data: " + json.dumps({"type":"log","msg":"Bot calismiyor veya baslatilamadi","level":"error"}) + "\n\n"
            return

        if not os.path.exists(log_file):
            yield "data: " + json.dumps({"type":"log","msg":"Log dosyasi bulunamadi","level":"error"}) + "\n\n"
            return

        if reconnect:
            tail_lines = bot_runner.get_log_tail(bot_num, 50)
            for line in tail_lines:
                line = line.strip()
                if line:
                    yield "data: " + json.dumps({"type":"log","msg":"[RECONNECT] " + line,"level":"info"}) + "\n\n"
            yield "data: " + json.dumps({"type":"log","msg":"--- Yeniden baglanildi, canli log ---","level":"success"}) + "\n\n"

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                f.seek(0, 2)

                while bot_runner.is_running(bot_num):
                    line = f.readline()
                    if line:
                        line = line.strip()
                        if line:
                            msg = line
                            level = 'info'

                            if 'ERROR' in line or 'hata' in line.lower() or 'basarisiz' in line.lower() or 'ONAYSIZ' in line:
                                level = 'error'
                            elif '✅' in line or 'ONAYLI' in line or 'Basarili' in line:
                                level = 'success'

                            if 'YENI' in line and 'Kaynak' in line:
                                parts = line.split(': ')
                                if len(parts) > 1:
                                    username = parts[1].split(' ')[0].strip()
                                    yield "data: " + json.dumps({"type":"follower","name":username}) + "\n\n"

                            if 'ONAYLI' in line:
                                parts = line.split(': ')
                                if len(parts) > 1:
                                    username = parts[1].split(' ')[0].strip()
                                    yield "data: " + json.dumps({"type":"status","name":username,"status":"done"}) + "\n\n"

                            if 'ONAYSIZ' in line:
                                parts = line.split(': ')
                                if len(parts) > 1:
                                    username = parts[1].split(' ')[0].strip()
                                    yield "data: " + json.dumps({"type":"status","name":username,"status":"fail"}) + "\n\n"

                            yield "data: " + json.dumps({"type":"log","msg":msg,"level":level}) + "\n\n"
                    else:
                        time.sleep(0.5)

                yield "data: " + json.dumps({"type":"done","msg":"Bot durduruldu"}) + "\n\n"
        except Exception as e:
            yield "data: " + json.dumps({"type":"log","msg":"Stream hatasi: " + str(e),"level":"error"}) + "\n\n"

    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    print("="*60)
    print("INSTAGRAM BOT PANELI")
    print("="*60)
    print("Panel aciliyor: http://127.0.0.1:" + str(FLASK_PORT))
    print("Telefondan erisim: http://<telefon-ip>:" + str(FLASK_PORT))
    print("="*60)
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, threaded=FLASK_THREADED)
