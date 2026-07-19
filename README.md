# Instagram Bot Paneli

Modüler yapıya ayrılmış Instagram otomasyon botu.

## Proje Yapısı

```
instagram_bot/
├── app.py              # Flask ana uygulama (route'lar)
├── config.py           # Ayarlar ve sabitler
├── database.py         # SQLite veritabanı işlemleri
├── bot_engine.py       # Instagram bot sınıfı (Selenium)
├── bot_runner.py       # Bot process yönetimi
├── debug_pages.py      # Debug/test sayfaları
├── requirements.txt    # Python bağımlılıkları
├── templates/
│   └── panel.html      # Ana panel HTML
└── static/
    └── panel.js        # Panel JavaScript
```

## Dosya Sorumlulukları

| Dosya | Görev |
|-------|-------|
| `app.py` | Flask sunucusu, API route'ları, SSE stream |
| `config.py` | Veritabanı yolu, port, Chromium yolları |
| `database.py` | Tüm SQLite CRUD işlemleri |
| `bot_engine.py` | Selenium ile Instagram login, takipçi toplama, takip etme |
| `bot_runner.py` | Bot script oluşturma, subprocess yönetimi |
| `debug_pages.py` | `/debug` ve `/test` sayfaları |
| `templates/panel.html` | Ana yönetim paneli arayüzü |
| `static/panel.js` | Panel interaktivitesi, API çağrıları |

## Kurulum

```bash
pip install -r requirements.txt
pkg install chromium -y  # Termux için
```

## Çalıştırma

```bash
python app.py
```

Panel: http://127.0.0.1:5000

## Hata Ayıklama

Her dosya bağımsız, sorun hangi modüldeyse o dosyaya odaklan:
- **Giriş sorunu?** → `bot_engine.py` (login metodu)
- **Veritabanı hatası?** → `database.py`
- **Bot başlamıyor?** → `bot_runner.py`
- **Panel çalışmıyor?** → `app.py` veya `templates/panel.html`
- **Butonlar tepki vermiyor?** → `static/panel.js`
