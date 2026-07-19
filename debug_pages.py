"""Debug ve test sayfaları"""
from flask import Blueprint

debug_bp = Blueprint('debug', __name__)


@debug_bp.route('/debug')
def debug_page():
    return """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Debug</title></head>
<body style="background:#1a1a2e;color:#fff;padding:20px;font-family:sans-serif;">
<h2>Debug Panel</h2>
<div id="status" style="background:#000;padding:10px;border-radius:8px;margin:10px 0;">Yukleniyor...</div>
<button id="btn1" style="padding:10px 20px;margin:5px;">Test Buton 1</button>
<button id="btn2" style="padding:10px 20px;margin:5px;">API Test</button>
<button id="btn3" style="padding:10px 20px;margin:5px;">Hesap Ekle</button>
<div id="log" style="background:#000;padding:10px;border-radius:8px;margin:10px 0;font-family:monospace;font-size:12px;height:200px;overflow-y:auto;"></div>
<script>
(function() {
  var log = document.getElementById('log');
  var status = document.getElementById('status');

  function addLog(msg) {
    var div = document.createElement('div');
    div.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  document.getElementById('btn1').addEventListener('click', function() {
    addLog('BUTON 1 TIKLANDI - OK');
    status.textContent = 'Buton 1 calisiyor!';
    status.style.color = '#00d26a';
  });

  document.getElementById('btn2').addEventListener('click', function() {
    addLog('API testi baslatiliyor...');
    fetch('/api/accounts')
      .then(function(r) { 
        addLog('API yanit status: ' + r.status); 
        return r.json(); 
      })
      .then(function(d) { 
        addLog('API yanit: ' + JSON.stringify(d).substring(0,200)); 
        status.textContent = 'API calisiyor! Hesap sayisi: ' + (d.accounts ? d.accounts.length : 0);
        status.style.color = '#00d26a';
      })
      .catch(function(e) { 
        addLog('API HATASI: ' + e.message); 
        status.textContent = 'API hatasi: ' + e.message;
        status.style.color = '#ff4757';
      });
  });

  document.getElementById('btn3').addEventListener('click', function() {
    addLog('Hesap ekleme testi...');
    fetch('/api/accounts', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name: 'TestHesap', username: 'testuser123', password: 'testpass'})
    })
    .then(function(r) { return r.json(); })
    .then(function(d) { 
      addLog('Ekleme yanit: ' + JSON.stringify(d)); 
      status.textContent = d.ok ? 'Hesap eklendi!' : 'Ekleme basarisiz: ' + d.message;
      status.style.color = d.ok ? '#00d26a' : '#ff4757';
    })
    .catch(function(e) { 
      addLog('EKLEME HATASI: ' + e.message); 
      status.textContent = 'Hata: ' + e.message;
      status.style.color = '#ff4757';
    });
  });

  addLog('Debug paneli hazir');
  status.textContent = 'Hazir - Butonlara tiklayin';
})();
</script>
</body>
</html>"""


@debug_bp.route('/test')
def test_page():
    return """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Bot Test</title>
<style>
body { font-family: sans-serif; background: #1a1a2e; color: #fff; padding: 20px; }
.btn { padding: 10px 20px; margin: 5px; cursor: pointer; border-radius: 8px; border: none; }
.btn-primary { background: #e1306c; color: #fff; }
.btn-success { background: #00d26a; color: #fff; }
#log { background: #000; padding: 10px; border-radius: 8px; font-family: monospace; font-size: 12px; height: 200px; overflow-y: auto; margin-top: 20px; }
.log-entry { padding: 2px 0; }
.log-ok { color: #00d26a; }
.log-err { color: #ff4757; }
</style>
</head>
<body>
<h2>🧪 Bot Panel Test</h2>

<h3>1. API Testleri</h3>
<button class="btn btn-primary" id="test-accounts">Hesapları Getir</button>
<button class="btn btn-primary" id="test-add">Test Hesabı Ekle</button>
<button class="btn btn-primary" id="test-start">Bot Başlat (Test)</button>
<button class="btn btn-success" id="test-stop">Bot Durdur</button>

<h3>2. Sekme Testi</h3>
<div class="tabs">
  <button class="btn btn-primary tab-btn" data-tab="tab1">Tab 1</button>
  <button class="btn btn-primary tab-btn" data-tab="tab2">Tab 2</button>
</div>
<div id="tab1" style="display:block; padding:10px; background:rgba(255,255,255,0.1); margin-top:10px;">Tab 1 içeriği</div>
<div id="tab2" style="display:none; padding:10px; background:rgba(255,255,255,0.1); margin-top:10px;">Tab 2 içeriği</div>

<div id="log"></div>

<script>
(function() {
  function log(msg, type) {
    var div = document.getElementById('log');
    var entry = document.createElement('div');
    entry.className = 'log-entry ' + (type === 'ok' ? 'log-ok' : 'log-err');
    entry.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
    div.appendChild(entry);
    div.scrollTop = div.scrollHeight;
  }

  log('Test paneli hazır', 'ok');

  document.querySelectorAll('.tab-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var tabId = this.getAttribute('data-tab');
      document.getElementById('tab1').style.display = tabId === 'tab1' ? 'block' : 'none';
      document.getElementById('tab2').style.display = tabId === 'tab2' ? 'block' : 'none';
      log('Sekme değişti: ' + tabId, 'ok');
    });
  });

  document.getElementById('test-accounts').addEventListener('click', function() {
    log('Hesaplar getiriliyor...', 'ok');
    fetch('/api/accounts')
      .then(function(r) { return r.json(); })
      .then(function(d) { log('Hesaplar: ' + JSON.stringify(d), 'ok'); })
      .catch(function(e) { log('HATA: ' + e.message, 'err'); });
  });

  document.getElementById('test-add').addEventListener('click', function() {
    log('Test hesabı ekleniyor...', 'ok');
    fetch('/api/accounts', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name: 'Test', username: 'testuser', password: 'testpass'})
    })
    .then(function(r) { return r.json(); })
    .then(function(d) { log('Ekleme sonucu: ' + JSON.stringify(d), 'ok'); })
    .catch(function(e) { log('HATA: ' + e.message, 'err'); });
  });

  document.getElementById('test-start').addEventListener('click', function() {
    log('Bot başlatma isteği gönderiliyor...', 'ok');
    fetch('/api/start?bot=1', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({account_id: 1, target: 'test', max_follows: 1, mode: 'collect'})
    })
    .then(function(r) { return r.json(); })
    .then(function(d) { log('Başlatma sonucu: ' + JSON.stringify(d), d.ok ? 'ok' : 'err'); })
    .catch(function(e) { log('HATA: ' + e.message, 'err'); });
  });

  document.getElementById('test-stop').addEventListener('click', function() {
    log('Bot durdurma isteği...', 'ok');
    fetch('/api/stop?bot=1')
      .then(function(r) { return r.json(); })
      .then(function(d) { log('Durdurma sonucu: ' + JSON.stringify(d), 'ok'); })
      .catch(function(e) { log('HATA: ' + e.message, 'err'); });
  });

})();
</script>
</body>
</html>"""
