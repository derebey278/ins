from bot_engine import InstagramBot
import logging
import time
import signal
import sys
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ACCOUNT_ID = 1
YOUR_USERNAME = 'nusaybinemlak47'
YOUR_PASSWORD = 'ASLAN190547'
PROFILE_DIR = 'chrome_profiles/bot_3'

bot = InstagramBot(YOUR_USERNAME, YOUR_PASSWORD, ACCOUNT_ID)

def signal_handler(sig, frame):
    logger.info('Durdurma sinyali alindi...')
    bot.stop()

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

try:
    bot.setup_driver(profile_dir=PROFILE_DIR)
    if bot.login():
        from database import db_get_targets
        targets = [t[1] for t in db_get_targets(ACCOUNT_ID) if t[2] == 1]
        if not targets:
            logger.error('Aktif hedef hesap bulunamadi! Veritabanindan ekleyin.')
            sys.exit(1)
        logger.info(f'Hedef hesaplar: {targets}')
        bot.collect_followers_loop(
            targets=targets,
            max_per_target=50,
            bot_id=3,
            loop_delay=60
        )
    else:
        logger.error('Giris basarisiz!')
except KeyboardInterrupt:
    logger.info('Kullanici tarafindan durduruldu.')
except Exception as e:
    logger.error(f'Beklenmeyen hata: {e}')
finally:
    bot.close()