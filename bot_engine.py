"""Instagram Bot Engine - Selenium ile Instagram otomasyonu"""
import os
import re
import time
import random
import logging
import subprocess
import sqlite3
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementClickInterceptedException, StaleElementReferenceException,
    WebDriverException
)

from config import DB_PATH, CHROMIUM_PATHS, CHROMEDRIVER_PATHS

logger = logging.getLogger(__name__)


class InstagramBot:
    """Instagram otomasyon botu"""

    def __init__(self, username, password, account_id=0):
        self.username = username
        self.password = password
        self.account_id = account_id
        self.driver = None
        self.wait = None
        self.wait_short = None
        self.running = True
        self.consecutive_errors = 0

    def setup_driver(self, profile_dir=None):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-default-apps")
        options.add_argument("--no-first-run")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        options.add_argument("--disable-site-isolation-trials")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=BlockInsecurePrivateNetworkRequests")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Linux; Android 14; SM-S918B) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"
        )
        # ===== Bellek optimizasyonu =====
        options.add_argument("--js-flags=--max-old-space-size=512")
        options.add_argument("--memory-model=low")
        options.add_argument("--max_discard_memory_in_percentage=10")

        profile_used = False
        if profile_dir:
            try:
                lock_file = os.path.join(profile_dir, 'SingletonLock')
                if os.path.exists(lock_file):
                    try:
                        os.remove(lock_file)
                    except:
                        pass

                options.add_argument(f"--user-data-dir={profile_dir}")
                logger.info(f"Chrome profili: {profile_dir}")
                profile_used = True
            except Exception as e:
                logger.warning(f"Profil ayarlanamadi: {e}, profilsiz devam ediliyor...")

        chromium_found = False
        for path in CHROMIUM_PATHS:
            if os.path.exists(path):
                options.binary_location = path
                logger.info(f"Chromium bulundu: {path}")
                chromium_found = True
                break
        if not chromium_found:
            raise FileNotFoundError("Chromium bulunamadi. 'pkg install chromium -y' ile kurun.")

        chromedriver_path = None
        for path in CHROMEDRIVER_PATHS:
            if os.path.exists(path):
                chromedriver_path = path
                logger.info(f"ChromeDriver bulundu: {path}")
                break
        if not chromedriver_path:
            self._install_chromedriver()
            chromedriver_path = "/data/data/com.termux/files/usr/bin/chromedriver"

        try:
            from selenium.webdriver.chrome.service import Service
            service = Service(executable_path=chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            logger.error(f"Service ile baslatilamadi: {e}")
            if profile_used:
                logger.info("Profilsiz deneniyor...")
                options = webdriver.ChromeOptions()
                options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_argument(
                    "--user-agent=Mozilla/5.0 (Linux; Android 14; SM-S918B) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"
                )
                for path in CHROMIUM_PATHS:
                    if os.path.exists(path):
                        options.binary_location = path
                        break
            try:
                self.driver = webdriver.Chrome(options=options)
            except Exception as e2:
                logger.error(f"Profilsiz de baslatilamadi: {e2}")
                raise

        self.wait = WebDriverWait(self.driver, 30)
        self.wait_short = WebDriverWait(self.driver, 10)
        self._anti_detection()
        logger.info("Driver baslatildi (Termux/Android)")

    def _anti_detection(self):
        scripts = [
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
            "Object.defineProperty(navigator, 'languages', {get: () => ['tr-TR', 'tr', 'en-US', 'en']})",
            "Object.defineProperty(navigator, 'platform', {get: () => 'Linux armv8l'})",
        ]
        for script in scripts:
            try:
                self.driver.execute_script(script)
            except:
                pass

    def _install_chromedriver(self):
        try:
            logger.info("ChromeDriver kurulumu deneniyor...")
            result = subprocess.run(
                ["pkg", "install", "chromium", "-y"],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                logger.info("Chromium kurulumu tamamlandi")
            else:
                logger.error(f"Kurulum hatasi: {result.stderr}")
        except Exception as e:
            logger.error(f"Otomatik kurulum basarisiz: {e}")

    def stop(self):
        self.running = False
        logger.info("Bot durdurma sinyali alindi...")

    def _check_driver_alive(self):
        """Driver hala calisiyor mu kontrol et"""
        try:
            self.driver.title
            return True
        except:
            return False

    def _restart_driver(self, profile_dir=None):
        """Driver'i yeniden baslat"""
        logger.warning("Driver yeniden baslatiliyor...")
        try:
            self.close()
        except:
            pass
        time.sleep(3)
        self.setup_driver(profile_dir)
        if self.login():
            logger.info("Driver yeniden baslatildi ve giris yapildi")
            return True
        return False

    def _dismiss_save_login_popup(self):
        logger.info("'Save login info' popup kontrolu...")
        try:
            js_code = (
                'var elements = document.querySelectorAll("button, div[role=\'button\']"); '
                'for (var i = 0; i < elements.length; i++) { '
                'var text = (elements[i].innerText || elements[i].textContent || "").toLowerCase(); '
                'if (text.includes("not now") || text.includes("simdi degil") || text.includes("simdi değil")) '
                '{ elements[i].click(); return "clicked: " + text; } } return "not found";'
            )
            js_result = self.driver.execute_script(js_code)
            if "clicked" in str(js_result):
                logger.info(f"Popup JS ile kapatildi: {js_result}")
                time.sleep(2)
                return True
        except:
            pass
        logger.info("Popup bulunamadi veya zaten kapali")
        return False

    def _dismiss_notifications(self):
        for i in range(3):
            try:
                not_now_xpath = (
                    '//button[contains(text(), "Simdi Degil") or '
                    'contains(text(), "Not Now") or contains(text(), "Not now")]'
                )
                not_now_btn = self.driver.find_element(By.XPATH, not_now_xpath)
                not_now_btn.click()
                logger.info(f"Bildirim popup'i kapatildi ({i+1})")
                time.sleep(2)
            except:
                pass

    def login(self):
        try:
            logger.info("Instagram login sayfasi yukleniyor...")
            self.driver.get("https://www.instagram.com/accounts/login/")
            time.sleep(random.uniform(10, 15))

            try:
                cookie_xpath = (
                    '//*[contains(text(), "Tum Cerezleri Kabul Et") or '
                    'contains(text(), "Accept All") or contains(text(), "Allow All") or '
                    'contains(text(), "Allow all cookies") or '
                    'contains(text(), "Allow essential and optional cookies")]'
                )
                cookie_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, cookie_xpath)))
                cookie_btn.click()
                logger.info("Cerezler kabul edildi")
                time.sleep(3)
            except:
                logger.info("Cerez butonu bulunamadi veya gerekli degil")

            logger.info("Giris alanlari araniyor...")
            username_input = self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
            password_input = self.driver.find_element(By.NAME, "password")
            logger.info("Giris alanlari bulundu")

            logger.info("Kullanici adi giriliyor...")
            username_input.click()
            time.sleep(0.5)
            for char in self.username:
                username_input.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            time.sleep(random.uniform(1, 2))

            logger.info("Sifre giriliyor...")
            password_input.click()
            time.sleep(0.5)
            for char in self.password:
                password_input.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            time.sleep(random.uniform(1, 2))

            login_btn = self._find_login_button()

            if login_btn:
                self.wait.until(EC.element_to_be_clickable(login_btn))
                login_btn.click()
                logger.info("Giris butonuna tiklandi")
            else:
                logger.warning("Buton bulunamadi, JavaScript ile tiklama deneniyor...")
                if not self._js_login_click():
                    return False

            time.sleep(random.uniform(10, 15))
            self._dismiss_save_login_popup()
            self._dismiss_notifications()

            current_url = self.driver.current_url
            if "login" in current_url or "accounts" in current_url:
                self._log_login_error()
                logger.error(f"Giris basarisiz - hala login sayfasinda (URL: {current_url})")
                return False
            else:
                logger.info(f"Giris basarili! (URL: {current_url})")
                return True

        except Exception as e:
            logger.error(f"Giris hatasi: {e}")
            return False

    def _find_login_button(self):
        selectors = [
            '//div[@role="button" and contains(., "Log in")]',
            '//div[contains(text(), "Log in")]',
        ]
        for xpath in selectors:
            try:
                btn = self.driver.find_element(By.XPATH, xpath)
                logger.info(f"Giris butonu bulundu: {xpath}")
                return btn
            except:
                pass

        try:
            form = self.driver.find_element(By.TAG_NAME, "form")
            div_buttons = form.find_elements(By.XPATH, './/div[@role="button"]')
            for btn in div_buttons:
                if "log in" in btn.text.lower():
                    logger.info("Giris butonu bulundu: form icindeki div role=button")
                    return btn
        except:
            pass
        return None

    def _js_login_click(self):
        try:
            js_code = (
                'var elements = document.querySelectorAll("div[role=\'button\']"); '
                'for (var i = 0; i < elements.length; i++) { '
                'if (elements[i].innerText.includes("Log in")) '
                '{ elements[i].click(); return "clicked: " + elements[i].innerText; } } return "not found";'
            )
            js_result = self.driver.execute_script(js_code)
            logger.info(f"JavaScript sonucu: {js_result}")
            time.sleep(random.uniform(10, 15))
            if "login" not in self.driver.current_url:
                logger.info("Giris basarili gorunuyor (JS click)")
                self._dismiss_save_login_popup()
                return True
        except Exception as e:
            logger.error(f"JS tiklama hatasi: {e}")
        return False

    def _log_login_error(self):
        try:
            error_msg = self.driver.find_element(
                By.XPATH,
                '//*[contains(text(), "incorrect") or contains(text(), "yanlis") or '
                'contains(text(), "wrong") or contains(@id, "error") or contains(@class, "error")]'
            )
            logger.error(f"Giris hatasi mesaji: {error_msg.text}")
        except:
            pass

    # ============ DATABASE HELPERS ============

    def _db_add_follower(self, username, source_account, bot_id):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute("SELECT id FROM followers WHERE username = ? AND account_id = ?", (username, self.account_id))
            existing = c.fetchone()
            if existing:
                conn.close()
                return False

            c.execute(
                "INSERT INTO followers (username, source_account, bot_id, account_id, status, approval, created_at) "
                "VALUES (?, ?, ?, ?, 'pending', 'pending', ?)",
                (username, source_account, bot_id, self.account_id, datetime.now().isoformat())
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            logger.error(f"DB Hata: {e}")
            return False
        finally:
            conn.close()

    def _db_update_status(self, username, status):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE followers SET status = ?, followed_at = ? WHERE username = ? AND account_id = ?",
            (status, datetime.now().isoformat(), username, self.account_id)
        )
        conn.commit()
        conn.close()

    def _db_update_approval(self, username, approval):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE followers SET approval = ?, followed_at = ? WHERE username = ? AND account_id = ?",
            (approval, datetime.now().isoformat(), username, self.account_id)
        )
        conn.commit()
        conn.close()

    def _db_add_history(self, username, target_account, bot_id, status, result):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO follow_history (username, target_account, bot_id, account_id, status, result, followed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username, target_account, bot_id, self.account_id, status, result, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def _db_get_pending_for_follow(self, batch_size=50):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT f.username, f.source_account FROM followers f
            LEFT JOIN failed_retry_control fr ON f.username = fr.username AND f.account_id = fr.account_id
            WHERE f.account_id = ? AND f.status = 'pending' AND f.approval = 'pending'
            AND (fr.can_retry = 1 OR fr.can_retry IS NULL)
            ORDER BY f.created_at ASC LIMIT ?
        """, (self.account_id, batch_size))
        rows = c.fetchall()
        conn.close()
        return rows

    def _db_increment_daily_stat(self, stat_type):
        today = datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("SELECT id FROM daily_stats WHERE account_id = ? AND date = ?", (self.account_id, today))
        existing = c.fetchone()

        if existing:
            if stat_type == 'approved':
                c.execute("UPDATE daily_stats SET approved_count = approved_count + 1 WHERE account_id = ? AND date = ?",
                          (self.account_id, today))
            elif stat_type == 'rejected':
                c.execute("UPDATE daily_stats SET rejected_count = rejected_count + 1 WHERE account_id = ? AND date = ?",
                          (self.account_id, today))
        else:
            if stat_type == 'approved':
                c.execute("INSERT INTO daily_stats (account_id, date, approved_count, rejected_count) VALUES (?, ?, 1, 0)",
                          (self.account_id, today))
            elif stat_type == 'rejected':
                c.execute("INSERT INTO daily_stats (account_id, date, approved_count, rejected_count) VALUES (?, ?, 0, 1)",
                          (self.account_id, today))

        conn.commit()
        conn.close()

    def _db_record_failure(self, username):
        from database import db_record_failure
        db_record_failure(username, self.account_id)

    # ============ GET FOLLOWERS ============

    def get_followers(self, target_username, max_followers=50, bot_id=1, source_account=""):
        try:
            logger.info(f"@{target_username} profiline gidiliyor...")
            self.driver.get(f"https://www.instagram.com/{target_username}/")
            time.sleep(random.uniform(8, 12))

            try:
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "header")))
            except:
                logger.warning("Header bulunamadi, devam ediliyor...")

            followers_link = self._find_followers_link()
            if not followers_link:
                logger.error(f"@{target_username} icin takipciler linki bulunamadi")
                return 0

            followers_link.click()
            logger.info("Takipciler popup'i acildi")
            time.sleep(random.uniform(5, 8))

            collected = 0
            last_height = 0
            same_height_count = 0
            scroll_attempts = 0
            max_scroll_attempts = max_followers // 5 + 10

            while collected < max_followers and scroll_attempts < max_scroll_attempts and self.running:
                scroll_attempts += 1
                users = self._extract_usernames_from_dialog()

                for user in users:
                    if not self.running:
                        break
                    if collected >= max_followers:
                        break
                    if self._db_add_follower(user, source_account or target_username, bot_id):
                        collected += 1
                        if collected % 10 == 0:
                            logger.info(f"Toplandi: {collected}/{max_followers}")

                self.driver.execute_script(
                    'var d = document.querySelector("div[role=\'dialog\'] div._aano, '
                    'div[role=\'dialog\'] ._aano, div[role=\'dialog\'] > div > div"); '
                    'if(d) d.scrollTop = d.scrollHeight;'
                )
                time.sleep(random.uniform(2, 4))

                new_height = self.driver.execute_script(
                    'var d = document.querySelector("div[role=\'dialog\'] div._aano, '
                    'div[role=\'dialog\'] ._aano, div[role=\'dialog\'] > div > div"); '
                    'return d ? d.scrollTop : 0;'
                )

                if new_height == last_height:
                    same_height_count += 1
                    if same_height_count >= 3:
                        logger.info("Scroll sonuna gelindi")
                        break
                else:
                    same_height_count = 0
                last_height = new_height

            logger.info(f"@{target_username} icin {collected} kullanici toplandi")
            return collected

        except Exception as e:
            logger.error(f"Takipci toplama hatasi ({target_username}): {e}")
            return 0

    def _find_followers_link(self):
        selectors = [
            '//a[contains(@href, "/followers/")]',
            '//span[contains(text(), "takipci") or contains(text(), "followers")]/parent::a',
            '//*[contains(text(), "takipci") or contains(text(), "followers")]',
        ]
        for xpath in selectors:
            try:
                elem = self.driver.find_element(By.XPATH, xpath)
                if elem.tag_name == 'a':
                    return elem
                parent = elem.find_element(By.XPATH, '..')
                if parent.tag_name == 'a':
                    return parent
                return elem
            except:
                pass

        try:
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                href = link.get_attribute("href") or ""
                if "/followers" in href:
                    return link
        except:
            pass
        return None

    def _extract_usernames_from_dialog(self):
        usernames = set()
        try:
            dialog = self.driver.find_element(
                By.XPATH,
                '//div[@role="dialog"]//div[contains(@class, "_aano") or contains(@class, "xyi19xy")]'
            )
            links = dialog.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href") or ""
                if "/" in href and "/p/" not in href and "/reel/" not in href:
                    username = href.rstrip("/").split("/")[-1]
                    if username and len(username) > 1 and username not in ["explore", "accounts", "direct"]:
                        usernames.add(username)
        except:
            pass

        if not usernames:
            try:
                spans = self.driver.find_elements(
                    By.XPATH,
                    '//div[@role="dialog"]//span[contains(@class, "_ap3a")]'
                )
                for span in spans:
                    text = span.text.strip()
                    if text and " " not in text and len(text) > 1:
                        usernames.add(text)
            except:
                pass
        return list(usernames)

    # ============ COLLECT FOLLOWERS LOOP ============

    def collect_followers_loop(self, targets, max_per_target=50, bot_id=1, loop_delay=60):
        logger.info(f"\n{'='*60}")
        logger.info("SUREKLI DONGU MODU BASLADI")
        logger.info(f"Hedefler: {targets}")
        logger.info("Durdurmak icin Ctrl+C veya panelden durdur")
        logger.info(f"{'='*60}\n")

        cycle = 0
        while self.running:
            cycle += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"DONGU #{cycle}")
            logger.info(f"{'='*60}")

            for target in targets:
                if not self.running:
                    break

                logger.info(f"\n>>> HEDEF: @{target}")
                try:
                    self.get_followers(
                        target_username=target,
                        max_followers=max_per_target,
                        bot_id=bot_id,
                        source_account=target
                    )
                except Exception as e:
                    logger.error(f"Hata ({target}): {e}")

                if not self.running:
                    break
                wait = random.uniform(10, 20)
                logger.info(f"Bekleniyor... {wait:.1f}s")
                time.sleep(wait)

            if self.running:
                logger.info(f"\n>>> DONGU #{cycle} TAMAMLANDI. {loop_delay}s sonra tekrar baslayacak...")
                logger.info(f"{'='*60}\n")

                for _ in range(loop_delay):
                    if not self.running:
                        break
                    time.sleep(1)

        logger.info("\n>>> SUREKLI DONGU DURDURULDU <<<\n")

    # ============ FOLLOW USER - GELISTIRILMIS BUTON BULMA ============

    def follow_user(self, target_username, source_account="", bot_id=4):
        try:
            logger.info(f"{target_username} profiline gidiliyor...")
            self.driver.get(f"https://www.instagram.com/{target_username}/")
            time.sleep(random.uniform(10, 15))

            # ===== SAYFA YUKLENMESINI BEKLE =====
            try:
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "header")))
            except:
                logger.warning("Header bulunamadi, devam ediliyor...")

            # Ekstra bekleme - sayfanin tam yuklenmesi icin
            time.sleep(random.uniform(3, 5))

            # ===== ZATEN TAKIP EDILIYOR MU KONTROL ET =====
            already_following = self._check_already_following(target_username)
            if already_following:
                self._db_update_status(target_username, 'followed')
                self._db_update_approval(target_username, 'approved')
                self._db_add_history(target_username, source_account, bot_id, 'followed', 'already_following')
                self._db_increment_daily_stat('approved')
                logger.info(f"ONAYLI: {target_username} (Zaten takip ediliyor)")
                self.consecutive_errors = 0
                return "already_following"

            # ===== TAKIP BUTONUNU BUL =====
            follow_button = self._find_follow_button()

            if not follow_button:
                logger.info("Takip butonu bulunamadi, JavaScript deneniyor...")
                if self._js_follow_click(target_username, source_account, bot_id):
                    self.consecutive_errors = 0
                    return True
                else:
                    # ===== HESAP GIZLI MI KONTROL ET =====
                    is_private = self._check_private_account()
                    if is_private:
                        self._db_update_status(target_username, 'failed')
                        self._db_update_approval(target_username, 'rejected')
                        self._db_add_history(target_username, source_account, bot_id, 'failed', 'private_account')
                        self._db_increment_daily_stat('rejected')
                        self._db_record_failure(target_username)
                        logger.info(f"ONAYSIZ: {target_username} (Gizli hesap)")
                        self.consecutive_errors += 1
                        return False

                    self._db_update_status(target_username, 'failed')
                    self._db_update_approval(target_username, 'rejected')
                    self._db_add_history(target_username, source_account, bot_id, 'failed', 'button_not_found')
                    self._db_increment_daily_stat('rejected')
                    self._db_record_failure(target_username)
                    logger.info(f"ONAYSIZ: {target_username} (Buton bulunamadi)")
                    self.consecutive_errors += 1
                    return False

            if follow_button:
                try:
                    follow_button.click()
                    logger.info(f"{target_username} takip edildi!")
                except ElementClickInterceptedException:
                    logger.warning("Normal tiklama engellendi, JS ile tiklaniyor...")
                    self.driver.execute_script("arguments[0].click();", follow_button)
                    logger.info(f"{target_username} takip edildi (JS fallback)!")

                self._db_update_status(target_username, 'followed')
                self._db_update_approval(target_username, 'approved')
                self._db_add_history(target_username, source_account, bot_id, 'followed', 'success')
                self._db_increment_daily_stat('approved')
                logger.info(f"ONAYLI: {target_username} (Basariyla takip edildi)")
                self.consecutive_errors = 0
                time.sleep(random.uniform(4, 7))
                return True

            self._db_update_status(target_username, 'failed')
            self._db_update_approval(target_username, 'rejected')
            self._db_add_history(target_username, source_account, bot_id, 'failed', 'unknown')
            self._db_increment_daily_stat('rejected')
            self._db_record_failure(target_username)
            logger.info(f"ONAYSIZ: {target_username} (Bilinmeyen hata)")
            self.consecutive_errors += 1
            return False

        except WebDriverException as e:
            logger.error(f"WebDriver hatasi ({target_username}): {e}")
            self.consecutive_errors += 1
            # Driver olmus olabilir, yeniden baslatmayi dene
            if not self._check_driver_alive():
                logger.warning("Driver olmus gorunuyor, yeniden baslatiliyor...")
                return "restart_needed"
            return False
        except Exception as e:
            logger.error(f"{target_username} takip hatasi: {e}")
            self._db_update_status(target_username, 'failed')
            self._db_update_approval(target_username, 'rejected')
            self._db_add_history(target_username, source_account, bot_id, 'failed', 'exception')
            self._db_increment_daily_stat('rejected')
            self._db_record_failure(target_username)
            logger.info(f"ONAYSIZ: {target_username} (Hata: {e})")
            self.consecutive_errors += 1
            return False

    def _check_already_following(self, target_username):
        check_selectors = [
            '//button[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "following") '
            'or contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "takiptesin") '
            'or contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "requested") '
            'or contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "istek gonderildi")]',
            '//div[@role="button" and (contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "following") '
            'or contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "takiptesin"))]',
        ]
        for xpath in check_selectors:
            try:
                btn = self.driver.find_element(By.XPATH, xpath)
                logger.info(f"{target_username} zaten takip ediliyor! (Buton: '{btn.text}')")
                return True
            except:
                pass
        return False

    def _check_private_account(self):
        """Hesap gizli mi kontrol et"""
        try:
            private_indicators = [
                '//*[contains(text(), "This Account is Private") or contains(text(), "Bu Hesap Gizli")]',
                '//*[contains(text(), "Private Account") or contains(text(), "Gizli Hesap")]',
                '//span[contains(text(), "Follow to see their photos and videos")]',
            ]
            for xpath in private_indicators:
                try:
                    elem = self.driver.find_element(By.XPATH, xpath)
                    if elem.is_displayed():
                        logger.info(f"Gizli hesap tespit edildi: {elem.text}")
                        return True
                except:
                    pass
            return False
        except:
            return False

    def _find_follow_button(self):
        # ===== 1. Standart seciciler =====
        selectors = [
            '//button[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "follow") '
            'and not(contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "following")) '
            'and not(contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "followed")) '
            'and not(contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "unfollow"))]',
            '//div[@role="button" and contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "follow") '
            'and not(contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "following"))]',
            '//*[@aria-label="Follow" or @aria-label="Takip Et" or @aria-label="follow"]',
        ]
        for xpath in selectors:
            try:
                btn = self.wait_short.until(EC.presence_of_element_located((By.XPATH, xpath)))
                logger.info(f"Takip butonu bulundu: {xpath}")
                return btn
            except:
                pass

        # ===== 2. Genel arama - tum butonlar =====
        try:
            all_elements = self.driver.find_elements(
                By.XPATH,
                '//*[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "follow") '
                'and not(contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "following")) '
                'and not(contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "followed"))]'
            )
            for elem in all_elements:
                if elem.is_displayed() and elem.is_enabled() and elem.tag_name in ['button', 'div']:
                    logger.info(f"Takip butonu bulundu (genel arama): tag={elem.tag_name}, text='{elem.text[:50]}'")
                    return elem
        except:
            pass

        # ===== 3. Header ici arama =====
        try:
            header = self.driver.find_element(By.TAG_NAME, "header")
            buttons = header.find_elements(By.XPATH, './/button | .//div[@role="button"]')
            for btn in buttons:
                text = btn.text.lower()
                if 'follow' in text and 'following' not in text and 'unfollow' not in text:
                    logger.info(f"Takip butonu bulundu (header): text='{btn.text[:50]}'")
                    return btn
        except:
            pass

        return None

    def _js_follow_click(self, target_username, source_account, bot_id):
        try:
            # ===== 1. Standart JS tiklama =====
            js_code = (
                'var elements = document.querySelectorAll("button, div[role=\'button\']"); '
                'for (var i = 0; i < elements.length; i++) { '
                'var text = (elements[i].innerText || elements[i].textContent || "").toLowerCase(); '
                'if ((text.includes("follow") || text.includes("takip et")) '
                '&& !text.includes("following") && !text.includes("followed") && !text.includes("unfollow")) '
                '{ elements[i].click(); return "clicked: " + text; } } return "not found";'
            )
            js_result = self.driver.execute_script(js_code)
            logger.info(f"JavaScript sonucu: {js_result}")
            if "clicked" in str(js_result):
                self._db_update_status(target_username, 'followed')
                self._db_update_approval(target_username, 'approved')
                self._db_add_history(target_username, source_account, bot_id, 'followed', 'success')
                self._db_increment_daily_stat('approved')
                logger.info(f"ONAYLI: {target_username} (JS ile takip edildi)")
                time.sleep(random.uniform(4, 7))
                return True

            # ===== 2. Header ici JS arama =====
            js_code2 = (
                'var header = document.querySelector("header"); '
                'if (header) { '
                'var buttons = header.querySelectorAll("button, div[role=\'button\']"); '
                'for (var i = 0; i < buttons.length; i++) { '
                'var text = (buttons[i].innerText || buttons[i].textContent || "").toLowerCase(); '
                'if (text.includes("follow") && !text.includes("following") && !text.includes("unfollow")) '
                '{ buttons[i].click(); return "header-clicked: " + text; } } } '
                'return "header-not-found";'
            )
            js_result2 = self.driver.execute_script(js_code2)
            logger.info(f"Header JS sonucu: {js_result2}")
            if "clicked" in str(js_result2):
                self._db_update_status(target_username, 'followed')
                self._db_update_approval(target_username, 'approved')
                self._db_add_history(target_username, source_account, bot_id, 'followed', 'success')
                self._db_increment_daily_stat('approved')
                logger.info(f"ONAYLI: {target_username} (Header JS ile takip edildi)")
                time.sleep(random.uniform(4, 7))
                return True

        except Exception as e:
            logger.error(f"JS takip hatasi: {e}")
        return False

    # ============ FOLLOW LOOP - GELISTIRILMIS ============

    def follow_loop(self, batch_size=50, delay=5, break_after=400, break_duration=100,
                    session_limit=1000, bot_id=4, source_account=""):
        logger.info(f"\n{'='*60}")
        logger.info("TAKIP ETME DONGUSU BASLADI")
        logger.info("Durdurmak icin Ctrl+C veya panelden durdur")
        logger.info(f"{'='*60}\n")

        total_processed = 0
        successful = 0
        failed = 0
        already_following = 0
        cycle = 0
        profile_dir = None  # Yeniden baslatma icin profil

        while self.running:
            cycle += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"TAKIP DONGUSU #{cycle}")
            logger.info(f"{'='*60}")

            # Driver hala calisiyor mu kontrol et
            if not self._check_driver_alive():
                logger.warning("Driver calismiyor, yeniden baslatiliyor...")
                if not self._restart_driver(profile_dir):
                    logger.error("Driver yeniden baslatilamadi, dongu durduruluyor...")
                    break

            pending = self._db_get_pending_for_follow(batch_size)
            if not pending:
                logger.info("Bekleyen kullanici kalmadi. 30 saniye sonra tekrar kontrol edilecek...")
                for _ in range(30):
                    if not self.running:
                        break
                    time.sleep(1)
                continue

            logger.info(f"{len(pending)} bekleyen kullanici bulundu, takip ediliyor...")

            for username, src in pending:
                if not self.running:
                    break

                # Cok fazla ardışik hata varsa mola ver
                if self.consecutive_errors >= 5:
                    logger.warning(f"{self.consecutive_errors} ardisik hata, 60 saniye mola...")
                    for _ in range(60):
                        if not self.running:
                            break
                        time.sleep(1)
                    self.consecutive_errors = 0
                    # Driver'i yeniden baslat
                    if not self._check_driver_alive():
                        self._restart_driver(profile_dir)

                logger.info(f"\n{'='*50}")
                logger.info(f"Takip {total_processed+1}: {username}")
                logger.info(f"{'='*50}")

                user_source = src if src else source_account
                result = self.follow_user(username, user_source, bot_id)

                if result == "restart_needed":
                    logger.warning("Driver yeniden baslatma gerekiyor...")
                    if not self._restart_driver(profile_dir):
                        logger.error("Yeniden baslatma basarisiz, dongu durduruluyor...")
                        self.running = False
                        break
                    # Bu kullaniciyi tekrar dene
                    result = self.follow_user(username, user_source, bot_id)

                if result is True:
                    successful += 1
                elif result == "already_following":
                    already_following += 1
                else:
                    failed += 1

                total_processed += 1

                # Mola kontrolu
                if total_processed % break_after == 0 and self.running:
                    logger.info(f"\n{'='*50}")
                    logger.info(f"MOLA: {break_duration} saniye bekleniyor...")
                    logger.info(f"{'='*50}")
                    for _ in range(break_duration):
                        if not self.running:
                            break
                        time.sleep(1)
                    # Moladan sonra driver kontrolu
                    if not self._check_driver_alive():
                        self._restart_driver(profile_dir)

                if self.running:
                    wait_time = random.uniform(delay, delay + 10)
                    logger.info(f"Rate limit korumasi: {wait_time:.1f}s bekleniyor...")
                    time.sleep(wait_time)

            logger.info(f"\n>>> DONGU #{cycle} TAMAMLANDI. Tekrar baslayacak...")

        logger.info(f"\n{'='*60}")
        logger.info("TAKIP ISLEMI OZETI")
        logger.info(f"{'='*60}")
        logger.info(f"Basarili (Onayli): {successful}")
        logger.info(f"Zaten Takip Edilen: {already_following}")
        logger.info(f"Basarisiz (Onaysiz): {failed}")
        logger.info(f"Toplam Islenen: {total_processed}")
        logger.info(f"{'='*60}")

        return successful, already_following, failed, total_processed

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Tarayici kapatildi")
            except:
                pass
