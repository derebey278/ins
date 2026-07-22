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
PROFILE_DIR = 'chrome_profiles/bot_4'

bot = InstagramBot(YOUR_USERNAME, YOUR_PASSWORD, ACCOUNT_ID)

def signal_handler(sig, frame):
    logger.info('Durdurma sinyali alindi...')
    bot.stop()

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

try:
    bot.setup_driver(profile_dir=PROFILE_DIR)
    if bot.login():
        bot.follow_loop(
            batch_size=100,
            delay=2,
            break_after=400,
            break_duration=100,
            bot_id=4,
            source_account=''
        )
    else:
        logger.error('Giris basarisiz!')
except KeyboardInterrupt:
    logger.info('Kullanici tarafindan durduruldu.')
except Exception as e:
    logger.error(f'Beklenmeyen hata: {e}')
finally:
    bot.close()