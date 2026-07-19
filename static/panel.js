(function() {
  var activeBot = null;
  var eventSource = null;
  var runningBots = new Set();
  var currentAccountId = null;
  var isReconnecting = false;

  // ============ SEKME YÖNETİMİ ============

  function switchTab(tabId) {
    var tabs = document.querySelectorAll('.tab');
    var contents = document.querySelectorAll('.tab-content');
    for(var i = 0; i < tabs.length; i++) tabs[i].classList.remove('active');
    for(var i = 0; i < contents.length; i++) contents[i].classList.remove('active');
    var clickedTab = document.querySelector('.tab[data-tab="' + tabId + '"]');
    if(clickedTab) clickedTab.classList.add('active');
    var target = document.getElementById(tabId);
    if(target) target.classList.add('active');
    if(tabId === 'tab5') loadHistory();
    if(tabId === 'tab6') loadAccounts();
  }

  var tabElements = document.querySelectorAll('.tab');
  for(var i = 0; i < tabElements.length; i++) {
    tabElements[i].addEventListener('click', function() {
      var tabId = this.getAttribute('data-tab');
      if(tabId) switchTab(tabId);
    });
  }

  // ============ UI YARDIMCILARI ============

  function showToast(msg, type) {
    type = type || 'success';
    var toast = document.getElementById('toast');
    if(!toast) return;
    toast.textContent = msg;
    toast.className = 'toast toast-' + type + ' show';
    setTimeout(function() { toast.classList.remove('show'); }, 3000);
  }

  function addLog(msg, type) {
    type = type || 'info';
    var area = document.getElementById('log-area');
    if(!area) return;
    var now = new Date().toTimeString().split(' ')[0];
    var entry = document.createElement('div');
    entry.className = 'log-entry';
    var cls = type === 'success' ? 'log-success' : type === 'error' ? 'log-error' : 'log-info';
    entry.innerHTML = '<span class="log-time">[' + now + ']</span> <span class="' + cls + '">' + msg + '</span>';
    area.appendChild(entry);
    area.scrollTop = area.scrollHeight;
  }

  function updateStats(s, f, p, t) {
    var elA = document.getElementById('stat-approved');
    var elR = document.getElementById('stat-rejected');
    var elP = document.getElementById('stat-pending');
    var elT = document.getElementById('stat-total');
    var elPct = document.getElementById('progress-percent');
    var elBar = document.getElementById('progress-bar');
    if(elA) elA.textContent = s;
    if(elR) elR.textContent = f;
    if(elP) elP.textContent = p;
    if(elT) elT.textContent = t;
    var pct = t > 0 ? Math.round(((s + f) / t) * 100) : 0;
    if(elPct) elPct.textContent = pct + '%';
    if(elBar) elBar.style.width = pct + '%';
  }

  function addFollower(name) {
    var grid = document.getElementById('followers-grid');
    if(!grid || document.getElementById('f-' + name)) return;
    var item = document.createElement('div');
    item.className = 'follower-item';
    item.id = 'f-' + name;
    item.innerHTML = '<span class="follower-status status-waiting"></span><span class="follower-name">@' + name + '</span>';
    item.addEventListener('click', function() { window.open('https://instagram.com/' + name, '_blank'); });
    grid.appendChild(item);
  }

  function setFollowerStatus(name, status) {
    var item = document.getElementById('f-' + name);
    if(item) {
      var statusEl = item.querySelector('.follower-status');
      if(statusEl) statusEl.className = 'follower-status status-' + status;
    }
  }

  // ============ ÇALIŞAN BOT KONTROLÜ (SAYFA YÜKLENDİĞİNDE) ============

  function checkRunningBots() {
    fetch('/api/status').then(function(res) { return res.json(); }).then(function(data) {
      if(!data.ok) return;

      var anyRunning = false;
      for(var botNum in data.running) {
        if(data.running[botNum].running) {
          anyRunning = true;
          var pid = data.running[botNum].pid;
          runningBots.add(botNum + '-reconnect');
          addLog('Bot ' + botNum + ' zaten calisiyor (PID: ' + pid + '). Yeniden baglaniliyor...', 'info');
        }
      }

      if(anyRunning) {
        updateRunningBots();
        // İlk çalışan bot'a reconnect
        for(var botNum in data.running) {
          if(data.running[botNum].running) {
            reconnectStream(parseInt(botNum));
            break;
          }
        }
      }
    }).catch(function(e) { console.error('Status check error:', e); });
  }

  function reconnectStream(botNum) {
    if(eventSource) { eventSource.close(); eventSource = null; }
    isReconnecting = true;

    activeBot = botNum;
    document.getElementById('current-user').textContent = '@Bot ' + botNum + ' (Yeniden Baglanildi)';
    document.getElementById('bot-status').textContent = 'Calisiyor...';

    eventSource = new EventSource('/api/stream?bot=' + botNum + '&reconnect=true');

    eventSource.onopen = function() { 
      addLog('Yeniden baglanti basarili!', 'success');
      isReconnecting = false;
    };

    eventSource.onmessage = function(e) {
      try {
        var d = JSON.parse(e.data);
        if(d.type === 'log') addLog(d.msg, d.level);
        if(d.type === 'follower') addFollower(d.name);
        if(d.type === 'status') setFollowerStatus(d.name, d.status);
        if(d.type === 'done') { addLog('Bot durduruldu!', 'info'); stopBot(botNum); }
      } catch(err) { console.error('SSE parse error:', err); }
    };

    eventSource.onerror = function(e) {
      if(!isReconnecting) {
        addLog('Baglanti koptu, 5sn sonra yeniden denenecek...', 'error');
        setTimeout(function() {
          reconnectStream(botNum);
        }, 5000);
      }
    };
  }

  // ============ HESAP YÖNETİMİ ============

  function loadAccounts() {
    fetch('/api/accounts').then(function(res) { return res.json(); }).then(function(data) {
      var selects = ['b1-account', 'b2-account', 'b3-account', 'b4-account', 'db-account'];
      for(var i = 0; i < selects.length; i++) {
        var sel = document.getElementById(selects[i]);
        if(!sel) continue;
        sel.innerHTML = '';
        if(!data.accounts || data.accounts.length === 0) {
          var opt = document.createElement('option');
          opt.value = '';
          opt.textContent = 'Hesap ekleyin...';
          sel.appendChild(opt);
        } else {
          for(var j = 0; j < data.accounts.length; j++) {
            var acc = data.accounts[j];
            var opt = document.createElement('option');
            opt.value = acc.id;
            opt.textContent = acc.name + ' (@' + acc.username + ')';
            sel.appendChild(opt);
          }
        }
      }
      renderAccountsList(data.accounts || []);
    }).catch(function(e) { showToast('Hesaplar yuklenemedi', 'error'); });
  }

  function renderAccountsList(accounts) {
    var container = document.getElementById('accounts-list');
    if(!container) return;
    if(!accounts || accounts.length === 0) {
      container.innerHTML = '<div style="color:#888;padding:20px;text-align:center;">Henuez hesap eklenmemis...</div>';
      return;
    }
    container.innerHTML = '';
    for(var i = 0; i < accounts.length; i++) {
      var acc = accounts[i];
      var card = document.createElement('div');
      card.className = 'account-card';
      card.innerHTML = '<div class="account-avatar">U</div>' +
        '<div class="account-info"><div class="account-name">' + acc.name + '</div>' +
        '<div class="account-username">@' + acc.username + '</div>' +
        '<span class="account-status ' + (acc.is_active ? 'active' : 'inactive') + '">' + (acc.is_active ? 'Aktif' : 'Pasif') + '</span></div>' +
        '<div class="account-actions">' +
        '<button class="btn btn-secondary btn-toggle" data-id="' + acc.id + '" data-active="' + acc.is_active + '" style="padding:6px 12px;font-size:0.75rem;">' + (acc.is_active ? 'Pasif Yap' : 'Aktif Yap') + '</button>' +
        '<button class="btn btn-danger btn-delete" data-id="' + acc.id + '" style="padding:6px 12px;font-size:0.75rem;">Sil</button></div>';
      container.appendChild(card);
    }
    var toggleBtns = container.querySelectorAll('.btn-toggle');
    for(var i = 0; i < toggleBtns.length; i++) {
      toggleBtns[i].addEventListener('click', function() {
        var id = parseInt(this.getAttribute('data-id'));
        var active = parseInt(this.getAttribute('data-active'));
        toggleAccount(id, active ? 0 : 1);
      });
    }
    var deleteBtns = container.querySelectorAll('.btn-delete');
    for(var i = 0; i < deleteBtns.length; i++) {
      deleteBtns[i].addEventListener('click', function() {
        var id = parseInt(this.getAttribute('data-id'));
        deleteAccount(id);
      });
    }
  }

  function addAccount() {
    var name = document.getElementById('acc-name').value.trim();
    var username = document.getElementById('acc-username').value.trim();
    var password = document.getElementById('acc-password').value;
    if(!name || !username || !password) { showToast('Tum alanlari doldurun!', 'error'); return; }
    fetch('/api/accounts', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({name:name, username:username, password:password})
    }).then(function(res) { return res.json(); }).then(function(result) {
      showToast(result.message, result.ok ? 'success' : 'error');
      if(result.ok) {
        document.getElementById('acc-name').value = '';
        document.getElementById('acc-username').value = '';
        document.getElementById('acc-password').value = '';
        loadAccounts();
      }
    }).catch(function(e) { showToast('Hata: ' + e.message, 'error'); });
  }

  function deleteAccount(id) {
    if(!confirm('Hesabi silmek istediginize emin misiniz?')) return;
    fetch('/api/accounts/' + id, {method: 'DELETE'}).then(function(res) { return res.json(); }).then(function(result) {
      showToast(result.message, result.ok ? 'success' : 'error');
      loadAccounts();
    }).catch(function(e) { showToast('Hata: ' + e.message, 'error'); });
  }

  function toggleAccount(id, is_active) {
    fetch('/api/accounts/' + id + '/toggle', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({is_active: is_active})
    }).then(function(res) { return res.json(); }).then(function(result) {
      showToast(result.message, result.ok ? 'success' : 'error');
      loadAccounts();
    }).catch(function(e) { showToast('Hata: ' + e.message, 'error'); });
  }

  // ============ VERİTABANI İŞLEMLERİ ============

  function loadHistory() {
    var accountId = document.getElementById('db-account');
    if(!accountId) return;
    accountId = accountId.value;
    if(!accountId) return;
    fetch('/api/history?bot=4&account=' + accountId).then(function(res) { return res.json(); }).then(function(data) {
      var grid = document.getElementById('history-grid');
      if(!grid) return;
      if(!data.history || data.history.length === 0) {
        grid.innerHTML = '<div style="color:#888;font-size:0.85rem;padding:20px;text-align:center;">Henuez takip islemi yok...</div>';
      } else {
        grid.innerHTML = '';
        for(var i = 0; i < data.history.length; i++) {
          var h = data.history[i];
          var item = document.createElement('a');
          item.className = 'history-item ' + h.status;
          item.href = 'https://instagram.com/' + h.username;
          item.target = '_blank';
          item.innerHTML = '<div class="history-username">@' + h.username + '</div>' +
            '<div class="history-target">Hedef: ' + h.target_account + '</div>' +
            '<span class="history-result ' + (h.result === 'success' ? 'success' : h.result === 'fail' ? 'fail' : 'pending') + '">' + (h.result === 'success' ? 'Takip Edildi' : h.result === 'fail' ? 'Basarisiz' : 'Bekliyor') + '</span>' +
            '<div class="history-time">' + new Date(h.followed_at).toLocaleString('tr-TR') + '</div>';
          grid.appendChild(item);
        }
      }
      var stats = data.stats || {};
      var elP = document.getElementById('db-pending');
      var elF = document.getElementById('db-followed');
      var elFa = document.getElementById('db-failed');
      var elT = document.getElementById('db-total');
      var elA = document.getElementById('db-approved');
      var elR = document.getElementById('db-rejected');
      if(elP) elP.textContent = stats.pending || 0;
      if(elF) elF.textContent = stats.followed || 0;
      if(elFa) elFa.textContent = stats.failed || 0;
      if(elT) elT.textContent = stats.total || 0;
      if(elA) elA.textContent = stats.approved || 0;
      if(elR) elR.textContent = stats.rejected || 0;

      var dailyContainer = document.getElementById('daily-stats');
      if(dailyContainer && data.daily_stats) {
        if(data.daily_stats.length === 0) {
          dailyContainer.innerHTML = '<div style="color:#888;font-size:0.85rem;padding:10px;text-align:center;grid-column:1/-1;">Henuez veri yok...</div>';
        } else {
          dailyContainer.innerHTML = '';
          for(var j = 0; j < data.daily_stats.length; j++) {
            var ds = data.daily_stats[j];
            var dsItem = document.createElement('div');
            dsItem.className = 'daily-stat-item';
            dsItem.innerHTML = '<div class="daily-stat-date">' + ds.date + '</div>' +
              '<div class="daily-stat-approved">✅ ' + ds.approved + '</div>' +
              '<div class="daily-stat-rejected">❌ ' + ds.rejected + '</div>';
            dailyContainer.appendChild(dsItem);
          }
        }
      }
    }).catch(function(e) { console.error('loadHistory error:', e); });
  }

  function resetFailed() {
    var accountId = document.getElementById('db-account');
    accountId = accountId ? (accountId.value || currentAccountId) : currentAccountId;
    if(!accountId) { showToast('Lutfen bir hesap secin!', 'error'); return; }
    fetch('/api/reset_failed?bot=4&account=' + accountId, {method: 'POST'}).then(function(res) { return res.json(); }).then(function(result) {
      showToast(result.message, result.ok ? 'success' : 'error');
      addLog('Basarisiz kullanicilar tekrar siraya alindi', 'info');
      loadHistory();
    }).catch(function(e) { showToast('Hata: ' + e.message, 'error'); });
  }

  function clearHistory() {
    var accountId = document.getElementById('db-account');
    accountId = accountId ? (accountId.value || currentAccountId) : currentAccountId;
    if(!accountId) { showToast('Lutfen bir hesap secin!', 'error'); return; }
    if(!confirm('Gecmisi temizlemek istediginize emin misiniz?')) return;
    fetch('/api/clear_history?bot=4&account=' + accountId, {method: 'POST'}).then(function(res) { return res.json(); }).then(function(result) {
      showToast(result.message, result.ok ? 'success' : 'error');
      loadHistory();
    }).catch(function(e) { showToast('Hata: ' + e.message, 'error'); });
  }

  // ============ BOT YÖNETİMİ ============

  function updateRunningBots() {
    var container = document.getElementById('running-bots');
    if(!container) return;
    container.innerHTML = '';
    runningBots.forEach(function(key) {
      var parts = key.split('-');
      var botNum = parts[0];
      var label = parts[1] === 'reconnect' ? '(Yeniden Baglandi)' : '(Hesap #' + parts[1] + ')';
      var tag = document.createElement('div');
      tag.className = 'running-bot-tag';
      tag.innerHTML = 'Bot ' + botNum + ' ' + label + ' <button class="stop-btn">X</button>';
      tag.querySelector('.stop-btn').addEventListener('click', function() {
        stopBot(parseInt(botNum));
      });
      container.appendChild(tag);
    });
  }

  function startBot(botNum) {
    var accountSelect = document.getElementById('b' + botNum + '-account');
    if(!accountSelect) { showToast('Hesap secim alani bulunamadi!', 'error'); return; }
    var accountId = accountSelect.value;
    if(!accountId) { showToast('Lutfen bir hesap secin!', 'error'); return; }

    currentAccountId = accountId;
    var key = botNum + '-' + accountId;
    runningBots.add(key);
    updateRunningBots();

    activeBot = botNum;
    document.getElementById('current-user').textContent = '@Bot ' + botNum + ' (Hesap #' + accountId + ')';
    document.getElementById('bot-status').textContent = 'Calisiyor...';
    addLog('Bot ' + botNum + ' baslatiliyor...', 'info');

    var data = {};
    if(botNum === 1) {
      data = {
        bot: 1, account_id: accountId,
        targets: [document.getElementById('b1-target').value],
        max_per_target: document.getElementById('b1-max').value,
        loop_delay: document.getElementById('b1-delay').value,
        mode: 'collect_loop'
      };
    } else if(botNum === 2) {
      var targetsText = document.getElementById('b2-targets').value;
      var targets = targetsText.split('\n').map(function(t) { return t.trim(); }).filter(function(t) { return t; });
      data = {
        bot: 2, account_id: accountId,
        targets: targets,
        max_per_target: document.getElementById('b2-per-target').value,
        loop_delay: document.getElementById('b2-delay').value,
        mode: 'collect_loop'
      };
    } else if(botNum === 3) {
      data = {
        bot: 3, account_id: accountId,
        targets: [document.getElementById('b3-target').value],
        max_per_target: document.getElementById('b3-max').value,
        loop_delay: document.getElementById('b3-delay').value,
        mode: 'collect_loop'
      };
    } else if(botNum === 4) {
      data = {
        bot: 4, account_id: accountId,
        batch_size: document.getElementById('b4-batch').value,
        delay: document.getElementById('b4-delay').value,
        break_after: document.getElementById('b4-break').value,
        break_duration: document.getElementById('b4-break-duration').value,
        mode: 'follow_loop'
      };
    }

    fetch('/api/start?bot=' + botNum, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(data)
    }).then(function(startRes) { return startRes.json(); }).then(function(startResult) {
      if(!startResult.ok) {
        showToast(startResult.message, 'error');
        addLog('Bot baslatma basarisiz: ' + startResult.message, 'error');
        runningBots.delete(key);
        updateRunningBots();
        document.getElementById('bot-status').textContent = 'Bekliyor';
        return;
      }
      showToast(startResult.message, 'success');
      addLog('Bot baslatildi, loglar baglaniyor...', 'success');

      if(eventSource) { eventSource.close(); eventSource = null; }
      eventSource = new EventSource('/api/stream?bot=' + botNum + '&account=' + accountId);

      eventSource.onopen = function() { addLog('Canli baglanti acildi', 'success'); };
      eventSource.onmessage = function(e) {
        try {
          var d = JSON.parse(e.data);
          if(d.type === 'log') addLog(d.msg, d.level);
          if(d.type === 'follower') addFollower(d.name);
          if(d.type === 'status') setFollowerStatus(d.name, d.status);
          if(d.type === 'done') { addLog('Bot tamamlandi!', 'success'); stopBot(botNum); }
        } catch(err) { console.error('SSE parse error:', err); }
      };
      eventSource.onerror = function(e) {
        if(!isReconnecting) {
          addLog('Baglanti koptu, yeniden baglaniliyor...', 'error');
          setTimeout(function() {
            reconnectStream(botNum);
          }, 3000);
        }
      };
    }).catch(function(e) {
      showToast('Baglanti hatasi: ' + e.message, 'error');
      addLog('Baglanti hatasi: ' + e.message, 'error');
      runningBots.delete(key);
      updateRunningBots();
      document.getElementById('bot-status').textContent = 'Hata';
    });
  }

  function stopBot(botNum) {
    document.getElementById('bot-status').textContent = 'Durduruldu';
    var dot = document.querySelector('.status-dot');
    if(dot) dot.style.background = '#ff4757';
    addLog('Bot ' + botNum + ' durduruldu', 'error');
    if(eventSource) { eventSource.close(); eventSource = null; }
    runningBots.forEach(function(key) { if(key.startsWith(botNum + '-')) runningBots.delete(key); });
    updateRunningBots();
    fetch('/api/stop?bot=' + botNum).catch(function(e) { console.error('stopBot error:', e); });
  }

  // ============ EVENT LISTENERS ============

  document.getElementById('btn-start-1').addEventListener('click', function() { startBot(1); });
  document.getElementById('btn-stop-1').addEventListener('click', function() { stopBot(1); });
  document.getElementById('btn-start-2').addEventListener('click', function() { startBot(2); });
  document.getElementById('btn-stop-2').addEventListener('click', function() { stopBot(2); });
  document.getElementById('btn-start-3').addEventListener('click', function() { startBot(3); });
  document.getElementById('btn-stop-3').addEventListener('click', function() { stopBot(3); });
  document.getElementById('btn-start-4').addEventListener('click', function() { startBot(4); });
  document.getElementById('btn-stop-4').addEventListener('click', function() { stopBot(4); });
  document.getElementById('btn-add-account').addEventListener('click', addAccount);
  document.getElementById('btn-reset-failed').addEventListener('click', resetFailed);
  document.getElementById('btn-clear-history').addEventListener('click', clearHistory);

  // ============ BAŞLANGIÇ - ÇALIŞAN BOT KONTROLÜ ============

  addLog('Panel hazir. Calisan botlar kontrol ediliyor...', 'info');
  loadAccounts();

  // Sayfa yüklendiğinde çalışan bot'ları kontrol et
  setTimeout(function() {
    checkRunningBots();
  }, 1000);

  setInterval(function() {
    var tab5 = document.getElementById('tab5');
    if(tab5 && tab5.classList.contains('active')) {
      loadHistory();
    }
  }, 5000);

})();
