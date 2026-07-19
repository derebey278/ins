"""Ayarlar ve sabitler"""
import os

# Veritabanı
DB_PATH = 'bot_data.db'

# Flask
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = False
FLASK_THREADED = True

# Bot process yönetimi
MAX_WAIT_STREAM = 30
PID_DIR = 'pids'
os.makedirs(PID_DIR, exist_ok=True)

# Instagram ayarları
CHROMIUM_PATHS = [
    "/data/data/com.termux/files/usr/bin/chromium",
    "/data/data/com.termux/files/usr/bin/chromium-browser",
    "/data/data/com.termux/files/usr/lib/chromium/chromium",
]

CHROMEDRIVER_PATHS = [
    "/data/data/com.termux/files/usr/bin/chromedriver",
    "/data/data/com.termux/files/usr/lib/chromium/chromedriver",
]

# Bot dosya şablonları
BOT_FILE_TEMPLATE = 'bot{bot_num}_run.py'
