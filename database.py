"""SQLite veritabani islemleri"""
import sqlite3
from datetime import datetime
from config import DB_PATH


def init_db():
    """Veritabanini ve tablolari olustur"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Hesaplar tablosu
    c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Takipciler tablosu
    c.execute("""
        CREATE TABLE IF NOT EXISTS followers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            source_account TEXT NOT NULL,
            bot_id INTEGER NOT NULL,
            account_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            approval TEXT DEFAULT 'pending',
            followed_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, account_id)
        )
    """)

    # Takip gecmisi tablosu
    c.execute("""
        CREATE TABLE IF NOT EXISTS follow_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            target_account TEXT NOT NULL,
            bot_id INTEGER NOT NULL,
            account_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            result TEXT,
            followed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Istatistikler tablosu
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            approved_count INTEGER DEFAULT 0,
            rejected_count INTEGER DEFAULT 0,
            UNIQUE(account_id, date)
        )
    """)

    # ===== YENI: HEDEF HESAPLAR TABLOSU =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS target_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(account_id, username)
        )
    """)

    # ===== YENI: BOT AYARLARI TABLOSU =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL UNIQUE,
            account_id INTEGER,
            settings_json TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ===== YENI: BASARISIZ TAKIP TEKRAR KONTROLU =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS failed_retry_control (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            account_id INTEGER NOT NULL,
            fail_count INTEGER DEFAULT 1,
            last_failed_at TEXT,
            can_retry INTEGER DEFAULT 0,
            UNIQUE(username, account_id)
        )
    """)

    conn.commit()
    conn.close()


# ============ HESAP ISLEMLERI ============

def db_add_account(name, username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO accounts (name, username, password, is_active) VALUES (?, ?, ?, 1)",
                  (name, username, password))
        conn.commit()
        return c.lastrowid
    except Exception as e:
        print(f"DB Hata: {e}")
        return None
    finally:
        conn.close()


def db_get_accounts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, username, is_active FROM accounts ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def db_get_account(account_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, username, password, is_active FROM accounts WHERE id = ?", (account_id,))
    row = c.fetchone()
    conn.close()
    return row


def db_delete_account(account_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    c.execute("DELETE FROM followers WHERE account_id = ?", (account_id,))
    c.execute("DELETE FROM follow_history WHERE account_id = ?", (account_id,))
    c.execute("DELETE FROM daily_stats WHERE account_id = ?", (account_id,))
    c.execute("DELETE FROM target_accounts WHERE account_id = ?", (account_id,))
    c.execute("DELETE FROM bot_settings WHERE account_id = ?", (account_id,))
    c.execute("DELETE FROM failed_retry_control WHERE account_id = ?", (account_id,))
    conn.commit()
    conn.close()


def db_toggle_account(account_id, is_active):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE accounts SET is_active = ? WHERE id = ?", (is_active, account_id))
    conn.commit()
    conn.close()


# ============ HEDEF HESAP ISLEMLERI ============

def db_add_target(account_id, username):
    """Hedef hesap ekle"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO target_accounts (account_id, username) VALUES (?, ?)",
                  (account_id, username))
        conn.commit()
        return c.lastrowid
    except Exception as e:
        print(f"DB Hata: {e}")
        return None
    finally:
        conn.close()


def db_get_targets(account_id):
    """Aktif hedef hesaplari getir"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username, is_active FROM target_accounts WHERE account_id = ? ORDER BY created_at DESC",
              (account_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def db_delete_target(target_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM target_accounts WHERE id = ?", (target_id,))
    conn.commit()
    conn.close()


def db_toggle_target(target_id, is_active):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE target_accounts SET is_active = ? WHERE id = ?", (is_active, target_id))
    conn.commit()
    conn.close()


# ============ BOT AYARLARI ============

def db_save_bot_settings(bot_id, account_id, settings_dict):
    """Bot ayarlarini kaydet"""
    import json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        settings_json = json.dumps(settings_dict)
        c.execute("""
            INSERT INTO bot_settings (bot_id, account_id, settings_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(bot_id) DO UPDATE SET
                account_id=excluded.account_id,
                settings_json=excluded.settings_json,
                updated_at=excluded.updated_at
        """, (bot_id, account_id, settings_json, datetime.now().isoformat()))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Hata: {e}")
        return False
    finally:
        conn.close()


def db_get_bot_settings(bot_id):
    """Bot ayarlarini getir"""
    import json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT account_id, settings_json FROM bot_settings WHERE bot_id = ?", (bot_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"account_id": row[0], "settings": json.loads(row[1])}
    return None


def db_get_all_bot_settings():
    """Tum bot ayarlarini getir"""
    import json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT bot_id, account_id, settings_json FROM bot_settings")
    rows = c.fetchall()
    conn.close()
    result = {}
    for row in rows:
        result[row[0]] = {"account_id": row[1], "settings": json.loads(row[2])}
    return result


# ============ TAKIPCI ISLEMLERI ============

def db_add_follower(username, source_account, bot_id, account_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT id FROM followers WHERE username = ? AND account_id = ?", (username, account_id))
        existing = c.fetchone()
        if existing:
            conn.close()
            return False

        c.execute(
            "INSERT INTO followers (username, source_account, bot_id, account_id, status, approval, created_at) "
            "VALUES (?, ?, ?, ?, 'pending', 'pending', ?)",
            (username, source_account, bot_id, account_id, datetime.now().isoformat())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"DB Hata: {e}")
        return False
    finally:
        conn.close()


def db_follower_exists(username, account_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM followers WHERE username = ? AND account_id = ?", (username, account_id))
    exists = c.fetchone() is not None
    conn.close()
    return exists


def db_get_pending_followers(bot_id, account_id, limit=50):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT username, source_account FROM followers WHERE bot_id = ? AND account_id = ? "
        "AND status = 'pending' ORDER BY created_at ASC LIMIT ?",
        (bot_id, account_id, limit)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def db_get_pending_for_follow(account_id, limit=50):
    """Takip edilecek bekleyen kullanicilari getir (approval = pending VE can_retry = 1)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # ===== DEGISIKLIK: Sadece ilk kez basarisiz olanlari veya manuel izin verilenleri al =====
    c.execute("""
        SELECT f.username, f.source_account FROM followers f
        LEFT JOIN failed_retry_control fr ON f.username = fr.username AND f.account_id = fr.account_id
        WHERE f.account_id = ? AND f.status = 'pending' AND f.approval = 'pending'
        AND (fr.can_retry = 1 OR fr.can_retry IS NULL)
        ORDER BY f.created_at ASC LIMIT ?
    """, (account_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows


def db_update_follower_status(username, account_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE followers SET status = ?, followed_at = ? WHERE username = ? AND account_id = ?",
        (status, datetime.now().isoformat(), username, account_id)
    )
    conn.commit()
    conn.close()


def db_update_follower_approval(username, account_id, approval):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE followers SET approval = ?, followed_at = ? WHERE username = ? AND account_id = ?",
        (approval, datetime.now().isoformat(), username, account_id)
    )
    conn.commit()
    conn.close()


def db_add_follow_history(username, target_account, bot_id, account_id, status, result):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO follow_history (username, target_account, bot_id, account_id, status, result, followed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (username, target_account, bot_id, account_id, status, result, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def db_get_follow_history(bot_id, account_id, limit=25):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT username, target_account, status, result, followed_at FROM follow_history "
        "WHERE bot_id = ? AND account_id = ? ORDER BY followed_at DESC LIMIT ?",
        (bot_id, account_id, limit)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def db_get_stats(account_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM followers WHERE account_id = ? AND status = 'pending'", (account_id,))
    pending = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM followers WHERE account_id = ? AND status = 'followed'", (account_id,))
    followed = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM followers WHERE account_id = ? AND status = 'failed'", (account_id,))
    failed = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM followers WHERE account_id = ?", (account_id,))
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM followers WHERE account_id = ? AND approval = 'approved'", (account_id,))
    approved = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM followers WHERE account_id = ? AND approval = 'rejected'", (account_id,))
    rejected = c.fetchone()[0]

    conn.close()
    return {
        "pending": pending,
        "followed": followed,
        "failed": failed,
        "total": total,
        "approved": approved,
        "rejected": rejected
    }


def db_mark_all_pending(account_id):
    """Basarisiz olanlari tekrar siraya al - AMA sadece can_retry = 1 olanlari"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # ===== DEGISIKLIK: Sadece izin verilen basarisizlari tekrar dene =====
    c.execute("""
        UPDATE followers SET status = 'pending', approval = 'pending' 
        WHERE account_id = ? AND status = 'failed'
        AND username IN (
            SELECT username FROM failed_retry_control 
            WHERE account_id = ? AND can_retry = 1
        )
    """, (account_id, account_id))
    conn.commit()
    conn.close()


def db_clear_history(account_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM follow_history WHERE account_id = ?", (account_id,))
    conn.commit()
    conn.close()


# ============ BASARISIZ TAKIP KONTROLU ============

def db_record_failure(username, account_id):
    """Basarisiz takibi kaydet, ilk kez basarisizsa can_retry = 1"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT fail_count, can_retry FROM failed_retry_control WHERE username = ? AND account_id = ?",
                  (username, account_id))
        row = c.fetchone()

        if row:
            # Daha once basarisiz olmus
            new_count = row[0] + 1
            can_retry = 0  # Tekrar deneme izni yok
            c.execute("""
                UPDATE failed_retry_control 
                SET fail_count = ?, last_failed_at = ?, can_retry = ?
                WHERE username = ? AND account_id = ?
            """, (new_count, datetime.now().isoformat(), can_retry, username, account_id))
        else:
            # Ilk kez basarisiz - izin ver
            c.execute("""
                INSERT INTO failed_retry_control (username, account_id, fail_count, last_failed_at, can_retry)
                VALUES (?, ?, 1, ?, 1)
            """, (username, account_id, datetime.now().isoformat()))

        conn.commit()
    except Exception as e:
        print(f"DB Hata: {e}")
    finally:
        conn.close()


def db_allow_retry(username, account_id):
    """Manuel olarak tekrar deneme izni ver"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE failed_retry_control SET can_retry = 1 
        WHERE username = ? AND account_id = ?
    """, (username, account_id))
    conn.commit()
    conn.close()


def db_get_failed_list(account_id):
    """Basarisiz olanlarin listesini getir"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT fr.username, fr.fail_count, fr.can_retry, fr.last_failed_at
        FROM failed_retry_control fr
        WHERE fr.account_id = ?
        ORDER BY fr.fail_count DESC, fr.last_failed_at DESC
    """, (account_id,))
    rows = c.fetchall()
    conn.close()
    return rows


# ============ GUNLUK ISTATISTIKLER ============

def db_increment_daily_stat(account_id, stat_type):
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id FROM daily_stats WHERE account_id = ? AND date = ?", (account_id, today))
    existing = c.fetchone()

    if existing:
        if stat_type == 'approved':
            c.execute("UPDATE daily_stats SET approved_count = approved_count + 1 WHERE account_id = ? AND date = ?",
                      (account_id, today))
        elif stat_type == 'rejected':
            c.execute("UPDATE daily_stats SET rejected_count = rejected_count + 1 WHERE account_id = ? AND date = ?",
                      (account_id, today))
    else:
        if stat_type == 'approved':
            c.execute("INSERT INTO daily_stats (account_id, date, approved_count, rejected_count) VALUES (?, ?, 1, 0)",
                      (account_id, today))
        elif stat_type == 'rejected':
            c.execute("INSERT INTO daily_stats (account_id, date, approved_count, rejected_count) VALUES (?, ?, 0, 1)",
                      (account_id, today))

    conn.commit()
    conn.close()


def db_get_daily_stats(account_id, days=7):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT date, approved_count, rejected_count FROM daily_stats WHERE account_id = ? "
        "ORDER BY date DESC LIMIT ?",
        (account_id, days)
    )
    rows = c.fetchall()
    conn.close()
    return rows
