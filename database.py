"""SQLite veritabanı işlemleri"""
import sqlite3
from datetime import datetime
from config import DB_PATH


def init_db():
    """Veritabanını ve tabloları oluştur"""
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

    # Takipçiler tablosu - UNIQUE(username, account_id) ile tekrar eklenmesin
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

    # Takip geçmişi tablosu
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

    # İstatistikler tablosu - günlük takip sayıları
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

    conn.commit()
    conn.close()


# ============ HESAP İŞLEMLERİ ============

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
    conn.commit()
    conn.close()


def db_toggle_account(account_id, is_active):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE accounts SET is_active = ? WHERE id = ?", (is_active, account_id))
    conn.commit()
    conn.close()


# ============ TAKİPÇİ İŞLEMLERİ (TEKRAR EKLENMESİN) ============

def db_add_follower(username, source_account, bot_id, account_id):
    """Kullanıcı adı bir kez eklensin, tekrar eklenmesin"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        # Önce bu kullanıcı adı bu hesapta var mı kontrol et
        c.execute("SELECT id FROM followers WHERE username = ? AND account_id = ?", (username, account_id))
        existing = c.fetchone()
        if existing:
            conn.close()
            return False  # Zaten var, ekleme

        c.execute(
            "INSERT INTO followers (username, source_account, bot_id, account_id, status, approval, created_at) "
            "VALUES (?, ?, ?, ?, 'pending', 'pending', ?)",
            (username, source_account, bot_id, account_id, datetime.now().isoformat())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # UNIQUE constraint - zaten var
    except Exception as e:
        print(f"DB Hata: {e}")
        return False
    finally:
        conn.close()


def db_follower_exists(username, account_id):
    """Kullanıcı adı veritabanında var mı kontrol et"""
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
    """Takip edilecek bekleyen kullanıcıları getir (approval = pending)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT username, source_account FROM followers WHERE account_id = ? "
        "AND status = 'pending' AND approval = 'pending' ORDER BY created_at ASC LIMIT ?",
        (account_id, limit)
    )
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
    """Onay durumunu güncelle: approved / rejected"""
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
    """Genel istatistikler"""
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
    """Başarısız olanları tekrar sıraya al"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE followers SET status = 'pending', approval = 'pending' WHERE account_id = ? AND status = 'failed'",
        (account_id,)
    )
    conn.commit()
    conn.close()


def db_clear_history(account_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM follow_history WHERE account_id = ?", (account_id,))
    conn.commit()
    conn.close()


# ============ GÜNLÜK İSTATİSTİKLER ============

def db_increment_daily_stat(account_id, stat_type):
    """Günlük istatistiği artır: approved veya rejected"""
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id FROM daily_stats WHERE account_id = ? AND date = ?", (account_id, today))
    existing = c.fetchone()

    if existing:
        if stat_type == 'approved':
            c.execute("UPDATE daily_stats SET approved_count = approved_count + 1 WHERE account_id = ? AND date = ?",
                      (account_id, today))
        else:
            c.execute("UPDATE daily_stats SET rejected_count = rejected_count + 1 WHERE account_id = ? AND date = ?",
                      (account_id, today))
    else:
        if stat_type == 'approved':
            c.execute("INSERT INTO daily_stats (account_id, date, approved_count, rejected_count) VALUES (?, ?, 1, 0)",
                      (account_id, today))
        else:
            c.execute("INSERT INTO daily_stats (account_id, date, approved_count, rejected_count) VALUES (?, ?, 0, 1)",
                      (account_id, today))

    conn.commit()
    conn.close()


def db_get_daily_stats(account_id, days=7):
    """Son N günlük istatistikleri getir"""
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
