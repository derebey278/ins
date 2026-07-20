"""Bot process yonetimi - PID takibi, detached mode, reconnect (psutil'siz)"""
import os
import time
import subprocess
import signal
from config import BOT_FILE_TEMPLATE, PID_DIR, get_profile_dir


def get_pid_file(bot_num):
    return os.path.join(PID_DIR, f"bot{bot_num}.pid")


def get_log_file(bot_num):
    return os.path.join(PID_DIR, f"bot{bot_num}.log")


def _pid_exists(pid):
    """psutil olmadan PID kontrolu"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def read_pid(bot_num):
    """PID dosyasindan process ID oku"""
    pid_file = get_pid_file(bot_num)
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
                if _pid_exists(pid):
                    return pid
                else:
                    os.remove(pid_file)
        except:
            pass
    return None


def write_pid(bot_num, pid):
    """PID dosyasina yaz"""
    pid_file = get_pid_file(bot_num)
    with open(pid_file, 'w') as f:
        f.write(str(pid))


def remove_pid(bot_num):
    """PID dosyasini sil"""
    pid_file = get_pid_file(bot_num)
    if os.path.exists(pid_file):
        os.remove(pid_file)


class BotRunner:
    """Bot process'lerini yonetir - detached mode, reconnect destekli"""

    def __init__(self):
        self.processes = {1: None, 2: None, 3: None, 4: None}
        self.log_files = {1: None, 2: None, 3: None, 4: None}
        self.profile_dirs = {}  # Bot numarasi -> profil dizini

    def is_running(self, bot_num):
        """Bot calisiyor mu? (PID dosyasi kontrolu)"""
        pid = read_pid(bot_num)
        if pid and _pid_exists(pid):
            return True
        return False

    def get_process(self, bot_num):
        """Calisan process'i getir (reconnect icin)"""
        pid = read_pid(bot_num)
        if pid and _pid_exists(pid):
            return pid
        return None

    def stop(self, bot_num):
        """Bot'u durdur"""
        pid = read_pid(bot_num)
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(2)
                if _pid_exists(pid):
                    os.kill(pid, signal.SIGKILL)
            except:
                pass

        self.processes[bot_num] = None
        remove_pid(bot_num)

        if self.log_files.get(bot_num):
            try:
                self.log_files[bot_num].close()
            except:
                pass
            self.log_files[bot_num] = None

        return True

    def start(self, bot_num, account_id, username, password, data):
        """Bot'u detached modda baslat"""
        self.stop(bot_num)

        mode = data.get('mode', 'collect')
        bot_file = BOT_FILE_TEMPLATE.format(bot_num=bot_num)
        log_file = get_log_file(bot_num)

        # Her bot icin ayri profil
        profile_dir = get_profile_dir(bot_num)
        self.profile_dirs[bot_num] = profile_dir

        bot_script = self._build_bot_script(account_id, username, password, bot_num, mode, data, profile_dir)

        with open(bot_file, 'w', encoding='utf-8') as f:
            f.write(bot_script)

        # Log dosyasini ac (append modunda)
        log_fh = open(log_file, 'a', encoding='utf-8')
        self.log_files[bot_num] = log_fh

        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'

        # DETACHED MODE: setsid ile yeni session olustur
        try:
            self.processes[bot_num] = subprocess.Popen(
                ['setsid', 'python', bot_file],
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                start_new_session=True,
                preexec_fn=os.setsid
            )
        except Exception as e:
            # setsid yoksa normal baslat
            self.processes[bot_num] = subprocess.Popen(
                ['python', bot_file],
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )

        time.sleep(2)

        if self.processes[bot_num] and self.processes[bot_num].poll() is None:
            write_pid(bot_num, self.processes[bot_num].pid)
            return True, "Bot " + str(bot_num) + " baslatildi (Hesap #" + str(account_id) + ")"
        else:
            return True, "Bot " + str(bot_num) + " baslatildi (Hesap #" + str(account_id) + ") - Detached"

    def get_stdout(self, bot_num):
        """Bot'un stdout'unu al - log dosyasindan oku"""
        log_file = get_log_file(bot_num)
        if os.path.exists(log_file):
            try:
                return open(log_file, 'r', encoding='utf-8')
            except:
                pass
        return None

    def get_log_tail(self, bot_num, lines=100):
        """Log dosyasinin son N satirini getir"""
        log_file = get_log_file(bot_num)
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    return all_lines[-lines:] if len(all_lines) > lines else all_lines
            except:
                pass
        return []

    def _build_bot_script(self, account_id, username, password, bot_num, mode, data, profile_dir):
        lines = []
        lines.append("from bot_engine import InstagramBot")
        lines.append("import logging")
        lines.append("import time")
        lines.append("import signal")
        lines.append("import sys")
        lines.append("import os")
        lines.append("")
        lines.append("logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')")
        lines.append("logger = logging.getLogger(__name__)")
        lines.append("")
        lines.append("ACCOUNT_ID = " + str(account_id))
        lines.append("YOUR_USERNAME = " + repr(username))
        lines.append("YOUR_PASSWORD = " + repr(password))
        lines.append("PROFILE_DIR = " + repr(profile_dir))
        lines.append("")
        lines.append("bot = InstagramBot(YOUR_USERNAME, YOUR_PASSWORD, ACCOUNT_ID)")
        lines.append("")
        lines.append("def signal_handler(sig, frame):")
        lines.append("    logger.info('Durdurma sinyali alindi...')")
        lines.append("    bot.stop()")
        lines.append("")
        lines.append("signal.signal(signal.SIGTERM, signal_handler)")
        lines.append("signal.signal(signal.SIGINT, signal_handler)")
        lines.append("")
        lines.append("try:")
        lines.append("    bot.setup_driver(profile_dir=PROFILE_DIR)")
        lines.append("    if bot.login():")

        if bot_num in [1, 2, 3]:
            # Hedefleri veritabanindan al
            lines.append("        from database import db_get_targets")
            lines.append("        targets = [t[1] for t in db_get_targets(ACCOUNT_ID) if t[2] == 1]")
            lines.append("        if not targets:")
            lines.append("            logger.error('Aktif hedef hesap bulunamadi! Veritabanindan ekleyin.')")
            lines.append("            sys.exit(1)")
            lines.append("        logger.info(f'Hedef hesaplar: {targets}')")

            max_per = int(data.get('max_per_target', 50))
            loop_delay = int(data.get('loop_delay', 60))

            lines.append("        bot.collect_followers_loop(")
            lines.append("            targets=targets,")
            lines.append("            max_per_target=" + str(max_per) + ",")
            lines.append("            bot_id=" + str(bot_num) + ",")
            lines.append("            loop_delay=" + str(loop_delay))
            lines.append("        )")

        elif bot_num == 4:
            batch = int(data.get('batch_size', 50))
            delay = int(data.get('delay', 5))
            break_after = int(data.get('break_after', 400))
            break_duration = int(data.get('break_duration', 100))
            source = data.get('source', '')

            lines.append("        bot.follow_loop(")
            lines.append("            batch_size=" + str(batch) + ",")
            lines.append("            delay=" + str(delay) + ",")
            lines.append("            break_after=" + str(break_after) + ",")
            lines.append("            break_duration=" + str(break_duration) + ",")
            lines.append("            bot_id=4,")
            lines.append("            source_account=" + repr(source))
            lines.append("        )")

        lines.append("    else:")
        lines.append("        logger.error('Giris basarisiz!')")
        lines.append("except KeyboardInterrupt:")
        lines.append("    logger.info('Kullanici tarafindan durduruldu.')")
        lines.append("except Exception as e:")
        lines.append("    logger.error(f'Beklenmeyen hata: {e}')")
        lines.append("finally:")
        lines.append("    bot.close()")

        return "\n".join(lines)


# Global instance
bot_runner = BotRunner()
