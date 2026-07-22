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

# ===== Instagram navigasyon ve footer linklerini filtrele =====
EXCLUDED_USERNAMES = {
    'explore', 'accounts', 'direct', 'reels', 'about', 'help',
    'privacy', 'terms', 'careers', 'press', 'api', 'jobs',
    'locations', 'popular', 'lite', 'home', 'messages',
    'notifications', 'profile', 'threads', 'more', 'inbox',
    'followers', 'following', 'tagged', 'login', 'emails',
    'directory', 'hashtags', 'locations', 'blog', 'p'
}

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

    # ============ DRIVER SETUP (ESKI CALISAN HALI) ============

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
            self.driver = webdriver.Chrome(options=options)

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
            except Exception as e:
                logger.warning(f"Anti-detection script hatasi: {e}")

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
        """Botu durdur"""
        self.running = False
        logger.info("Bot durdurma sinyali alindi...")

    def close(self):
        """Driveri kapat"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Tarayici kapatildi")
            except Exception as e:
                logger.warning(f"Tarayici kapatma hatasi: {e}")
        self.driver = None
        self.wait = None
        self.wait_short = None

    def _check_driver_alive(self):
        """Driverin calisip calismadigini kontrol et"""
        if self.driver is None:
            return False
        try:
            self.driver.current_url
            return True
        except Exception:
            return False

    def _restart_driver(self):
        """Driveri yeniden baslat"""
        logger.warning("Driver yeniden baslatiliyor...")
        self.close()
        time.sleep(3)
        self.setup_driver()
        if self.login():
            logger.info("Driver yeniden baslatildi ve giris yapildi")
            return True
        logger.error("Driver yeniden baslatildi ama giris basarisiz!")
        return False

    # ============ POPUP DISMISS ============

    def _dismiss_save_login_popup(self):
        logger.info("Save login info popup kontrolu...")
        try:
            js_code = (
                'var elements = document.querySelectorAll("button, div[role=\'button\']"); '
                'for (var i = 0; i < elements.length; i++) { '
                'var text = (elements[i].innerText || elements[i].textContent || "").toLowerCase(); '
                'if (text.includes("not now") || text.includes("simdi degil") || text.includes("simdi degil")) '
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
                logger.info(f"Bildirim popupi kapatildi ({i+1})")
                time.sleep(2)
            except:
                pass

    # ============ LOGIN ============

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
        """Kullanici adi bir kez eklensin, tekrar eklenmesin"""
        if not username or len(username) < 2 or len(username) > 30:
            return False
        if username.lower() in EXCLUDED_USERNAMES:
            return False
        if '?' in username or '=' in username or '/' in username or '&' in username:
            return False

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
        """Onay durumu: approved / rejected"""
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

    def _db_get_pending(self, bot_id, limit=50):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT username, source_account FROM followers WHERE bot_id = ? AND account_id = ? "
            "AND status = 'pending' ORDER BY created_at ASC LIMIT ?",
            (bot_id, self.account_id, limit)
        )
        rows = c.fetchall()
        conn.close()
        return rows

    def _db_get_pending_for_follow(self, limit=50):
        """Takip edilecek bekleyen kullanicilar"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT username, source_account FROM followers WHERE account_id = ? "
            "AND status = 'pending' AND approval = 'pending' ORDER BY created_at ASC LIMIT ?",
            (self.account_id, limit)
        )
        rows = c.fetchall()
        conn.close()
        return rows

    def _db_increment_daily_stat(self, stat_type):
        """Gunluk istatistigi artir"""
        today = datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("SELECT id FROM daily_stats WHERE account_id = ? AND date = ?", (self.account_id, today))
        existing = c.fetchone()

        if existing:
            if stat_type == 'approved':
                c.execute("UPDATE daily_stats SET approved_count = approved_count + 1 WHERE account_id = ? AND date = ?",
                          (self.account_id, today))
            else:
                c.execute("UPDATE daily_stats SET rejected_count = rejected_count + 1 WHERE account_id = ? AND date = ?",
                          (self.account_id, today))
        else:
            if stat_type == 'approved':
                c.execute("INSERT INTO daily_stats (account_id, date, approved_count, rejected_count) VALUES (?, ?, 1, 0)",
                          (self.account_id, today))
            else:
                c.execute("INSERT INTO daily_stats (account_id, date, approved_count, rejected_count) VALUES (?, ?, 0, 1)",
                          (self.account_id, today))

        conn.commit()
        conn.close()

    def _db_record_failure(self, username):
        """Basarisiz takip kaydet"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(
                "INSERT OR REPLACE INTO failed_retry_control (username, account_id, fail_count, last_failed_at, can_retry) "
                "VALUES (?, ?, COALESCE((SELECT fail_count + 1 FROM failed_retry_control WHERE username=? AND account_id=?), 1), ?, 0)",
                (username, self.account_id, username, self.account_id, datetime.now().isoformat())
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"Failure kayit hatasi: {e}")
        finally:
            conn.close()

    # ============ GET FOLLOWERS ============

    def get_followers(self, target_username, max_followers=50, bot_id=1, source_account=""):
        followers = []
        try:
            logger.info(f"{target_username} profiline gidiliyor (takipciler icin)...")
            self.driver.get(f"https://www.instagram.com/{target_username}/")
            time.sleep(random.uniform(10, 15))

            followers_btn = self._find_followers_button()
            if not followers_btn:
                logger.error("Takipciler butonu bulunamadi!")
                return followers

            self._click_followers_button(followers_btn)
            time.sleep(random.uniform(8, 12))

            current_url = self.driver.current_url
            logger.info(f"Takipciler tiklandiktan sonra URL: {current_url}")

            if "/followers/" in current_url:
                logger.info("Takipciler sayfasi yuklendi (URL yonlendirmesi)")
                return self._extract_followers_from_page(
                    target_username, max_followers, bot_id, source_account or target_username
                )

            return self._extract_followers_from_dialog(
                target_username, max_followers, bot_id, source_account or target_username
            )

        except Exception as e:
            logger.error(f"Takipcileri alma hatasi: {e}")
            return followers

    def _find_followers_button(self):
        selectors = [
            '//a[contains(@href, "/followers/")]',
            '//*[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "followers") '
            'or contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "takipci")]',
        ]
        for xpath in selectors:
            try:
                btn = self.driver.find_element(By.XPATH, xpath)
                logger.info(f"Takipciler butonu bulundu: {xpath}")
                return btn
            except:
                pass

        try:
            stats = self.driver.find_elements(By.XPATH, '//header//li | //header//span[contains(@class, "_ac2a")]')
            for stat in stats:
                text = stat.text.lower()
                if "follower" in text or "takipci" in text:
                    logger.info(f"Takipciler butonu bulundu (stat): text='{stat.text}'")
                    return stat
        except:
            pass
        return None

    def _click_followers_button(self, btn):
        try:
            btn.click()
            logger.info("Takipciler butonuna tiklandi")
        except:
            try:
                self.driver.execute_script("arguments[0].click();", btn)
                logger.info("Takipciler butonuna JS ile tiklandi")
            except Exception as e:
                logger.error(f"Takipciler butonuna tiklanamadi: {e}")
                raise

    def _extract_followers_from_dialog(self, target_username, max_followers, bot_id, source_account):
        followers = []
        scroll_count = 0
        max_scrolls = 500
        last_height = 0
        no_change_count = 0

        dialogs = self.driver.find_elements(By.XPATH, '//div[@role="dialog"]')
        if not dialogs:
            logger.warning("Dialog bulunamadi!")
            return followers

        scroll_container = None
        for dialog in dialogs:
            try:
                scroll_container = dialog.find_element(By.XPATH, './/div[contains(@class, "_aano")]')
                if scroll_container:
                    break
            except:
                pass

        if not scroll_container:
            scroll_container = dialogs[0]

        while len(followers) < max_followers and scroll_count < max_scrolls and self.running:
            try:
                links = scroll_container.find_elements(By.TAG_NAME, "a")
                found_new = False

                for link in links:
                    try:
                        username = self._extract_username_from_link(link, target_username)
                        if username and username not in followers:
                            if self._db_add_follower(username, source_account, bot_id):
                                followers.append(username)
                                found_new = True
                                logger.info(f"YENI: {username} (Kaynak: {source_account})")
                                if len(followers) >= max_followers:
                                    break
                    except StaleElementReferenceException:
                        continue
                    except Exception as e:
                        logger.debug(f"Link isleme hatasi: {e}")
                        continue

                if len(followers) >= max_followers:
                    break

                if len(followers) < max_followers:
                    try:
                        spans = scroll_container.find_elements(By.XPATH, './/span[@dir="auto"]')
                        for span in spans:
                            try:
                                username = self._extract_username_from_span(span, target_username)
                                if username and username not in followers:
                                    if self._db_add_follower(username, source_account, bot_id):
                                        followers.append(username)
                                        found_new = True
                                        logger.info(f"YENI (span): {username}")
                                        if len(followers) >= max_followers:
                                            break
                            except:
                                continue
                    except:
                        pass

                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
                time.sleep(random.uniform(2, 4))

                new_height = self.driver.execute_script("return arguments[0].scrollHeight", scroll_container)
                if new_height == last_height:
                    no_change_count += 1
                    if no_change_count >= 3:
                        logger.info("Scroll ilerlemesi durdu, cikiliyor...")
                        break
                else:
                    no_change_count = 0
                    last_height = new_height

                scroll_count += 1

            except Exception as e:
                logger.error(f"Dialog scroll hatasi: {e}")
                break

        try:
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            logger.info("Modal kapatildi")
            time.sleep(2)
        except:
            pass

        followers = list(dict.fromkeys(followers))
        logger.info(f"Toplam {len(followers)} yeni takipci bulundu ve kaydedildi")
        return followers[:max_followers]

    def _extract_followers_from_page(self, target_username, max_followers, bot_id, source_account):
        followers = []
        scroll_count = 0
        max_scrolls = 500
        last_height = 0
        no_change_count = 0

        while len(followers) < max_followers and scroll_count < max_scrolls and self.running:
            try:
                links = self.driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    try:
                        username = self._extract_username_from_link(link, target_username)
                        if username and username not in followers:
                            if self._db_add_follower(username, source_account, bot_id):
                                followers.append(username)
                                logger.info(f"YENI (page): {username}")
                            else:
                                logger.info(f"ATLA (page): {username} (Zaten DBde)")
                            if len(followers) >= max_followers:
                                break
                    except:
                        continue
            except:
                pass

            if len(followers) < max_followers and self.running:
                try:
                    spans = self.driver.find_elements(By.XPATH, '//span[@dir="auto"]')
                    for span in spans:
                        try:
                            username = self._extract_username_from_span(span, target_username)
                            if username and username not in followers:
                                if self._db_add_follower(username, source_account, bot_id):
                                    followers.append(username)
                                    logger.info(f"YENI (page span): {username}")
                                else:
                                    logger.info(f"ATLA (page span): {username} (Zaten DBde)")
                                if len(followers) >= max_followers:
                                    break
                        except:
                            continue
                except:
                    pass

            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                logger.info(f"Page scroll ({scroll_count + 1}/{max_scrolls})")
            except:
                pass

            time.sleep(random.uniform(3, 5))
            scroll_count += 1

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                no_change_count += 1
                if no_change_count >= 3:
                    logger.info("Page scroll ilerlemesi durdu, cikiliyor...")
                    break
            else:
                no_change_count = 0
                last_height = new_height

        followers = list(dict.fromkeys(followers))
        logger.info(f"Toplam {len(followers)} yeni takipci bulundu (sayfa)")
        return followers[:max_followers]

    def _extract_username_from_link(self, link_element, target_username):
        """Linkten kullanici adini cek - gelistirilmis filtreleme"""
        try:
            href = link_element.get_attribute("href") or ""
            if not href:
                return None

            if "?" in href or "=" in href or "&" in href:
                return None

            if "instagram.com" not in href:
                return None

            parts = [p for p in href.split("/") if p and p not in
                     ["https:", "http:", "www.instagram.com", "instagram.com"]]
            if not parts:
                return None
            username = parts[-1]

            if not username or len(username) < 2 or len(username) > 30:
                return None
            if username.lower() in EXCLUDED_USERNAMES:
                return None
            if username == target_username.lower():
                return None
            if "." in username and "/" not in username:
                return None
            if any(c in username for c in ["<", ">", "{", "}", "[", "]", "|", "\\", "^", "`"]):
                return None

            return username
        except Exception:
            return None

    def _extract_username_from_span(self, span_element, target_username):
        text = span_element.text.strip()
        if (text and " " not in text and text != target_username and
            len(text) > 2 and len(text) < 31 and
            (text.isalnum() or "_" in text or "." in text) and text[0].isalnum() and
            text.lower() not in EXCLUDED_USERNAMES):
            return text
        return None

    # ============ SUREKLI DONGU - TAKIPCI TOPLAMA ============

    def collect_followers_loop(self, targets, max_per_target=50, bot_id=1, loop_delay=60):
        """Surekli dongude takipci topla - durdurana kadar devam et"""
        logger.info(f"\n{"="*60}")
        logger.info("SUREKLI DONGU MODU BASLADI")
        logger.info(f"Hedefler: {targets}")
        logger.info("Durdurmak icin Ctrl+C veya panelden durdur")
        logger.info(f"{"="*60}\n")

        cycle = 0
        while self.running:
            cycle += 1
            logger.info(f"\n{"="*60}")
            logger.info(f"DONGU #{cycle}")
            logger.info(f"{"="*60}")

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
                logger.info(f"{"="*60}\n")

                for _ in range(loop_delay):
                    if not self.running:
                        break
                    time.sleep(1)

        logger.info("\n>>> SUREKLI DONGU DURDURULDU <<<\n")

    # ============ FOLLOW USER (ONAY SISTEMI) ============

    def follow_user(self, target_username, source_account="", bot_id=4):
        """Kullaniciyi takip et - onayli/onaysiz olarak kaydet"""
        if not self._check_driver_alive():
            logger.error("Driver calismiyor, yeniden baslatilacak...")
            return False, "driver_dead"

        try:
            logger.info(f"{target_username} profiline gidiliyor...")
            self.driver.get(f"https://www.instagram.com/{target_username}/")
            time.sleep(random.uniform(10, 15))

            try:
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "header")))
            except:
                logger.warning("Header bulunamadi, devam ediliyor...")

            already_following = self._check_already_following(target_username)
            if already_following:
                self._db_update_status(target_username, "followed")
                self._db_update_approval(target_username, "approved")
                self._db_add_history(target_username, source_account, bot_id, "followed", "already_following")
                self._db_increment_daily_stat("approved")
                logger.info(f"ONAYLI: {target_username} (Zaten takip ediliyor)")
                return True, "already_following"

            is_private = self._check_private_account()
            if is_private:
                logger.info(f"GIZLI HESAP: {target_username}")

            follow_button = self._find_follow_button()

            if not follow_button:
                logger.info("Takip butonu bulunamadi, JavaScript deneniyor...")
                if self._js_follow_click(target_username, source_account, bot_id):
                    return True, "success"
                else:
                    self._db_update_status(target_username, "failed")
                    self._db_update_approval(target_username, "rejected")
                    self._db_add_history(target_username, source_account, bot_id, "failed", "button_not_found")
                    self._db_increment_daily_stat("rejected")
                    self._db_record_failure(target_username)
                    logger.info(f"ONAYSIZ: {target_username} (Buton bulunamadi)")
                    return False, "button_not_found"

            if follow_button:
                try:
                    self.wait_short.until(EC.element_to_be_clickable(follow_button))
                    follow_button.click()
                    logger.info(f"{target_username} takip edildi!")
                except ElementClickInterceptedException:
                    logger.warning("Normal tiklama engellendi, JS ile tiklaniyor...")
                    self.driver.execute_script("arguments[0].click();", follow_button)
                    logger.info(f"{target_username} takip edildi (JS fallback)!")
                except Exception as e:
                    logger.warning(f"Normal tiklama basarisiz: {e}, JS deneniyor...")
                    self.driver.execute_script("arguments[0].click();", follow_button)
                    logger.info(f"{target_username} takip edildi (JS fallback)!")

                time.sleep(random.uniform(4, 7))

                following_now = self._check_already_following(target_username)
                if following_now:
                    self._db_update_status(target_username, "followed")
                    self._db_update_approval(target_username, "approved")
                    self._db_add_history(target_username, source_account, bot_id, "followed", "success")
                    self._db_increment_daily_stat("approved")
                    self.consecutive_errors = 0
                    logger.info(f"ONAYLI: {target_username} (Basariyla takip edildi)")
                    return True, "success"
                else:
                    logger.warning(f"Takip durumu dogrulanamadi: {target_username}")
                    self._db_update_status(target_username, "followed")
                    self._db_update_approval(target_username, "approved")
                    self._db_add_history(target_username, source_account, bot_id, "followed", "unverified")
                    self._db_increment_daily_stat("approved")
                    self.consecutive_errors = 0
                    return True, "unverified"

            self._db_update_status(target_username, "failed")
            self._db_update_approval(target_username, "rejected")
            self._db_add_history(target_username, source_account, bot_id, "failed", "unknown")
            self._db_increment_daily_stat("rejected")
            self._db_record_failure(target_username)
            logger.info(f"ONAYSIZ: {target_username} (Bilinmeyen hata)")
            return False, "unknown"

        except WebDriverException as e:
            logger.error(f"WebDriver hatasi: {e}")
            self.consecutive_errors += 1
            if self.consecutive_errors >= 3:
                logger.error("3 ardisik hata! Driver yeniden baslatiliyor...")
                self._restart_driver()
                self.consecutive_errors = 0
            return False, f"webdriver_error: {str(e)[:100]}"
        except Exception as e:
            logger.error(f"{target_username} takip hatasi: {e}")
            self.consecutive_errors += 1
            self._db_update_status(target_username, "failed")
            self._db_update_approval(target_username, "rejected")
            self._db_add_history(target_username, source_account, bot_id, "failed", str(e)[:200])
            self._db_increment_daily_stat("rejected")
            self._db_record_failure(target_username)
            logger.info(f"ONAYSIZ: {target_username} (Hata: {e})")
            return False, str(e)[:100]

    def _check_already_following(self, target_username):
        """Zaten takip ediliyor mu kontrol et - gelistirilmis"""
        try:
            following_selectors = [
                '//*[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "following")]',
                '//*[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "takiptesin")]',
                '//button[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "following")]',
                '//div[@role="button" and contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "following")]',
            ]
            for xpath in following_selectors:
                try:
                    elem = self.driver.find_element(By.XPATH, xpath)
                    if elem.is_displayed():
                        return True
                except:
                    pass

            try:
                header = self.driver.find_element(By.TAG_NAME, "header")
                buttons = header.find_elements(By.XPATH, './/button | .//div[@role="button"]')
                for btn in buttons:
                    text = (btn.text or "").lower()
                    if any(word in text for word in ["following", "takiptesin", "takip ediliyor", "requested", "istek gonderildi"]):
                        return True
            except:
                pass

            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                if "follow back" in page_text or "takip et" in page_text:
                    if "following" not in page_text and "takiptesin" not in page_text:
                        return False
            except:
                pass

            return False
        except Exception as e:
            logger.warning(f"Takip kontrol hatasi: {e}")
            return False

    def _check_private_account(self):
        """Gizli hesap mi kontrol et"""
        try:
            private_indicators = [
                '//*[contains(text(), "This Account is Private")]',
                '//*[contains(text(), "Bu hesap gizli")]',
                '//*[contains(text(), "Gizli Hesap")]',
            ]
            for xpath in private_indicators:
                try:
                    elem = self.driver.find_element(By.XPATH, xpath)
                    if elem.is_displayed():
                        return True
                except:
                    pass
            return False
        except:
            return False

    def _find_follow_button(self):
        """Takip butonunu bul - Instagram 2024/2025 yapisi uyumlu"""
        modern_selectors = [
            '//button[@type="button" and not(@disabled) and .//div[contains(text(), "Follow")]]',
            '//button[@type="button" and not(@disabled) and .//div[contains(text(), "Takip Et")]]',
            '//section//button[contains(@class, "_acan") and not(contains(@class, "_acat"))]',
            '//div[contains(@class, "x1i10hfl")]//button[not(@disabled)]',
            '//header//button[not(@disabled)]',
            '//button[.//span[contains(text(), "Follow") or contains(text(), "Takip Et")]]',
        ]
        for xpath in modern_selectors:
            try:
                btn = self.wait_short.until(EC.presence_of_element_located((By.XPATH, xpath)))
                if btn.is_displayed() and btn.is_enabled():
                    logger.info(f"Takip butonu bulundu (modern): {xpath}")
                    return btn
            except:
                pass

        standard_selectors = [
            '//button[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "follow") '
            'and not(contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "following")) '
            'and not(contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "followed")) '
            'and not(contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "unfollow"))]',
            '//div[@role="button" and contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "follow") '
            'and not(contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "following"))]',
            '//*[@aria-label="Follow" or @aria-label="Takip Et" or @aria-label="follow"]',
        ]
        for xpath in standard_selectors:
            try:
                btn = self.wait_short.until(EC.presence_of_element_located((By.XPATH, xpath)))
                if btn.is_displayed() and btn.is_enabled():
                    logger.info(f"Takip butonu bulundu: {xpath}")
                    return btn
            except:
                pass

        try:
            all_elements = self.driver.find_elements(
                By.XPATH,
                '//*[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "follow") '
                'and not(contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "following")) '
                'and not(contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "followed"))]'
            )
            for elem in all_elements:
                if elem.is_displayed() and elem.is_enabled() and elem.tag_name in ["button", "div"]:
                    logger.info(f"Takip butonu bulundu (genel arama): tag={elem.tag_name}, text='{elem.text[:50]}'")
                    return elem
        except:
            pass

        try:
            header = self.driver.find_element(By.TAG_NAME, "header")
            buttons = header.find_elements(By.XPATH, './/button | .//div[@role="button"]')
            for btn in buttons:
                text = (btn.text or "").lower()
                if "follow" in text and "following" not in text and "unfollow" not in text:
                    logger.info(f"Takip butonu bulundu (header): text='{btn.text[:50]}'")
                    return btn
        except:
            pass

        try:
            js_result = self.driver.execute_script('''
                var buttons = document.querySelectorAll('button, div[role="button"]');
                for (var i = 0; i < buttons.length; i++) {
                    var text = (buttons[i].innerText || buttons[i].textContent || "").toLowerCase();
                    if ((text.includes("follow") || text.includes("takip et")) 
                        && !text.includes("following") && !text.includes("takiptesin")
                        && buttons[i].offsetParent !== null) {
                        return "found: " + text;
                    }
                }
                return "not found";
            ''')
            if "found" in str(js_result):
                logger.info(f"JS ile takip butonu tespit edildi: {js_result}")
                try:
                    return self.driver.find_element(By.XPATH, '//button[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "follow")]')
                except:
                    pass
        except:
            pass

        return None

    def _js_follow_click(self, target_username, source_account, bot_id):
        """JavaScript ile takip butonuna tikla"""
        try:
            js_code = '''
                var buttons = document.querySelectorAll('button, div[role="button"]');
                for (var i = 0; i < buttons.length; i++) {
                    var text = (buttons[i].innerText || buttons[i].textContent || "").toLowerCase();
                    if ((text.includes("follow") || text.includes("takip et")) 
                        && !text.includes("following") && !text.includes("takiptesin")) {
                        buttons[i].click();
                        return "clicked: " + text;
                    }
                }
                return "not found";
            '''
            js_result = self.driver.execute_script(js_code)
            logger.info(f"JS takip sonucu: {js_result}")
            if "clicked" in str(js_result):
                time.sleep(random.uniform(3, 6))
                self._db_update_status(target_username, "followed")
                self._db_update_approval(target_username, "approved")
                self._db_add_history(target_username, source_account, bot_id, "followed", "success")
                self._db_increment_daily_stat("approved")
                self.consecutive_errors = 0
                logger.info(f"ONAYLI: {target_username} (JS ile takip edildi)")
                return True
        except Exception as e:
            logger.error(f"JS takip hatasi: {e}")
        return False

    # ============ SUREKLI DONGU - TAKIP ETME (BOT 4) ============

    def follow_loop(self, batch_size=50, delay=5, break_after=400, break_duration=100,
                    session_limit=1000, bot_id=4, source_account=""):
        """Surekli dongude veritabanindan takip et - durdurana kadar devam"""
        logger.info(f"\n{"="*60}")
        logger.info("TAKIP ETME DONGUSU BASLADI")
        logger.info("Durdurmak icin Ctrl+C veya panelden durdur")
        logger.info(f"{"="*60}\n")

        total_processed = 0
        successful = 0
        already_following = 0
        failed = 0
        cycle = 0

        while self.running:
            cycle += 1
            logger.info(f"\n{"="*60}")
            logger.info(f"TAKIP DONGUSU #{cycle}")
            logger.info(f"{"="*60}")

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

                logger.info(f"\n{"="*50}")
                logger.info(f"Takip {total_processed+1}: {username}")
                logger.info(f"{"="*50}")

                user_source = src if src else source_account
                result, msg = self.follow_user(username, user_source, bot_id)

                if msg == "success" or msg == "unverified":
                    successful += 1
                elif msg == "already_following":
                    already_following += 1
                else:
                    failed += 1

                total_processed += 1

                if total_processed % break_after == 0 and self.running:
                    logger.info(f"\n{"="*50}")
                    logger.info(f"MOLA: {break_duration} saniye bekleniyor...")
                    logger.info(f"{"="*50}")
                    for _ in range(break_duration):
                        if not self.running:
                            break
                        time.sleep(1)

                if self.running:
                    wait_time = random.uniform(delay, delay + 10)
                    logger.info(f"Rate limit korumasi: {wait_time:.1f}s bekleniyor...")
                    time.sleep(wait_time)

            logger.info(f"\n>>> DONGU #{cycle} TAMAMLANDI. Tekrar baslayacak...")

        logger.info(f"\n{"="*60}")
        logger.info("TAKIP ISLEMI OZETI")
        logger.info(f"{"="*60}")
        logger.info(f"Basarili (Onayli): {successful}")
        logger.info(f"Zaten Takip Edilen: {already_following}")
        logger.info(f"Basarisiz (Onaysiz): {failed}")
        logger.info(f"Toplam Islenen: {total_processed}")
        logger.info(f"{"="*60}")

        return successful, already_following, failed, total_processed
