"""Ayarlar ve sabitler"""
import os

# Veritabani
DB_PATH = 'bot_data.db'

# Flask
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = False
FLASK_THREADED = True

# Bot process yonetimi
MAX_WAIT_STREAM = 30
PID_DIR = 'pids'
os.makedirs(PID_DIR, exist_ok=True)

# ===== Her bot icin ayri Chrome profili =====
PROFILE_DIR = 'chrome_profiles'
os.makedirs(PROFILE_DIR, exist_ok=True)

def get_profile_dir(bot_num):
    profile = os.path.join(PROFILE_DIR, f'bot_{bot_num}')
    os.makedirs(profile, exist_ok=True)
    # Termux'ta profil dizini icin gerekli izinler
    try:
        os.chmod(profile, 0o755)
    except:
        pass
    return profile

# Instagram ayarlari
CHROMIUM_PATHS = [
    "/data/data/com.termux/files/usr/bin/chromium",
    "/data/data/com.termux/files/usr/bin/chromium-browser",
    "/data/data/com.termux/files/usr/lib/chromium/chromium",
]

CHROMEDRIVER_PATHS = [
    "/data/data/com.termux/files/usr/bin/chromedriver",
    "/data/data/com.termux/files/usr/lib/chromium/chromedriver",
]

# Bot dosya sablonlari
BOT_FILE_TEMPLATE = 'bot{bot_num}_run.py'
