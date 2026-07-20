
// ============ GLOBAL STATE ============
let accounts = [];
let targets = [];
let botSettings = {};
let currentTab = 'tab1';
let logInterval = null;
let statusInterval = null;
let currentAccountId = 0;

// ============ INIT ============
document.addEventListener('DOMContentLoaded', () => {
    loadAccounts();
    loadBotSettings();
    setupTabs();
    setupEventListeners();
    startStatusPolling();
});

// ============ TABS ============
function setupTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');
            currentTab = tab.dataset.tab;

            const botNum = parseInt(currentTab.replace('tab', ''));
            if (botNum >= 1 && botNum <= 4) {
                loadBotSettingsForTab(botNum);
            }

            // Hedef hesaplar sekmesine gecince hesaplari doldur
            if (currentTab === 'tab5') {
                updateTargetAccountSelect();
            }
        });
    });
}

// ============ ACCOUNTS ============
async function loadAccounts() {
    try {
        const res = await fetch('/api/accounts');
        const data = await res.json();
        if (data.ok) {
            accounts = data.accounts;
            updateAccountSelects();
            renderAccountsList();
            // Hedef hesaplar sekmesini de guncelle
            updateTargetAccountSelect();
        }
    } catch (e) {
        console.error('Hesaplar yuklenemedi:', e);
    }
}

function updateAccountSelects() {
    const selects = ['b1-account', 'b2-account', 'b3-account', 'b4-account', 'db-account'];
    selects.forEach(id => {
        const sel = document.getElementById(id);
        if (!sel) return;
        const currentVal = sel.value;
        sel.innerHTML = '<option value="">Hesap secin...</option>' +
            accounts.map(a => `<option value="${a.id}" ${a.id == currentVal ? 'selected' : ''}>${a.name} (@${a.username})</option>`).join('');
    });
}

// ===== YENI: Hedef hesaplar sekmesindeki dropdown'u guncelle =====
function updateTargetAccountSelect() {
    const sel = document.getElementById('target-account-select');
    if (!sel) return;

    if (accounts.length === 0) {
        sel.innerHTML = '<option value="">Once hesap ekleyin...</option>';
        return;
    }

    const currentVal = sel.value;
    sel.innerHTML = '<option value="">Hesap secin...</option>' +
        accounts.map(a => `<option value="${a.id}" ${a.id == currentVal ? 'selected' : ''}>${a.name} (@${a.username})</option>`).join('');

    // Eger hesap seciliyse hedefleri de yukle
    if (sel.value) {
        loadTargets(parseInt(sel.value));
    }
}

function renderAccountsList() {
    const container = document.getElementById('accounts-list');
    if (!container) return;

    if (accounts.length === 0) {
        container.innerHTML = '<div style="color:#888;padding:20px;text-align:center;">Henuz hesap eklenmemis...</div>';
        return;
    }

    container.innerHTML = accounts.map(acc => `
        <div class="account-card">
            <div class="account-avatar">${acc.name.charAt(0).toUpperCase()}</div>
            <div class="account-info">
                <div class="account-name">${acc.name}</div>
                <div class="account-username">@${acc.username}</div>
                <span class="account-status ${acc.is_active ? 'active' : 'inactive'}">${acc.is_active ? 'Aktif' : 'Pasif'}</span>
            </div>
            <div class="account-actions">
                <button class="btn btn-secondary" onclick="toggleAccount(${acc.id}, ${acc.is_active ? 0 : 1})" style="padding:6px 12px;font-size:0.75rem;">
                    ${acc.is_active ? 'Pasif Yap' : 'Aktif Yap'}
                </button>
                <button class="btn btn-danger" onclick="deleteAccount(${acc.id})" style="padding:6px 12px;font-size:0.75rem;">Sil</button>
            </div>
        </div>
    `).join('');
}

async function toggleAccount(id, isActive) {
    try {
        const res = await fetch(`/api/accounts/${id}/toggle`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({is_active: isActive})
        });
        const data = await res.json();
        if (data.ok) {
            showToast(data.message, 'success');
            loadAccounts();
        }
    } catch (e) {
        showToast('Hata: ' + e.message, 'error');
    }
}

async function deleteAccount(id) {
    if (!confirm('Hesabi silmek istediginize emin misiniz?')) return;
    try {
        const res = await fetch(`/api/accounts/${id}`, {method: 'DELETE'});
        const data = await res.json();
        if (data.ok) {
            showToast(data.message, 'success');
            loadAccounts();
        }
    } catch (e) {
        showToast('Hata: ' + e.message, 'error');
    }
}

// ============ TARGET ACCOUNTS ============
async function loadTargets(accountId) {
    if (!accountId) return;
    try {
        const res = await fetch(`/api/targets?account=${accountId}`);
        const data = await res.json();
        if (data.ok) {
            targets = data.targets;
            renderTargetsList();
            updateTargetsTextarea();
        }
    } catch (e) {
        console.error('Hedefler yuklenemedi:', e);
    }
}

function renderTargetsList() {
    const container = document.getElementById('targets-list');
    if (!container) return;

    const accountId = parseInt(document.getElementById('target-account-select')?.value || 0);
    if (!accountId) {
        container.innerHTML = '<div style="color:#888;padding:20px;text-align:center;">Once hesap secin...</div>';
        return;
    }

    if (targets.length === 0) {
        container.innerHTML = '<div style="color:#888;padding:20px;text-align:center;">Henuz hedef eklenmemis...</div>';
        return;
    }

    container.innerHTML = targets.map(t => `
        <div class="target-item ${t.is_active ? '' : 'inactive'}">
            <span class="target-name">@${t.username}</span>
            <div class="target-actions">
                <button class="btn btn-secondary" onclick="toggleTarget(${t.id}, ${t.is_active ? 0 : 1})" style="padding:4px 10px;font-size:0.7rem;">
                    ${t.is_active ? 'Pasif' : 'Aktif'}
                </button>
                <button class="btn btn-danger" onclick="deleteTarget(${t.id})" style="padding:4px 10px;font-size:0.7rem;">Sil</button>
            </div>
        </div>
    `).join('');
}

function updateTargetsTextarea() {
    const activeTargets = targets.filter(t => t.is_active).map(t => t.username).join('\n');
    ['b1-target', 'b2-targets', 'b3-target'].forEach(id => {
        const el = document.getElementById(id);
        if (el && activeTargets) {
            el.value = activeTargets;
        }
    });
}

async function addTarget() {
    const accountId = parseInt(document.getElementById('target-account-select')?.value || 0);
    const username = document.getElementById('new-target')?.value.trim().replace('@', '') || '';

    if (!accountId) {
        showToast('Once hesap secin!', 'error');
        return;
    }
    if (!username) {
        showToast('Kullanici adi girin!', 'error');
        return;
    }

    try {
        const res = await fetch('/api/targets', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({account_id: accountId, username: username})
        });
        const data = await res.json();
        if (data.ok) {
            showToast(data.message, 'success');
            document.getElementById('new-target').value = '';
            loadTargets(accountId);
        } else {
            showToast(data.message, 'error');
        }
    } catch (e) {
        showToast('Hata: ' + e.message, 'error');
    }
}

async function deleteTarget(targetId) {
    if (!confirm('Hedefi silmek istediginize emin misiniz?')) return;
    try {
        const res = await fetch(`/api/targets/${targetId}`, {method: 'DELETE'});
        const data = await res.json();
        if (data.ok) {
            showToast(data.message, 'success');
            const accountId = parseInt(document.getElementById('target-account-select')?.value || 0);
            loadTargets(accountId);
        }
    } catch (e) {
        showToast('Hata: ' + e.message, 'error');
    }
}

async function toggleTarget(targetId, isActive) {
    try {
        const res = await fetch(`/api/targets/${targetId}/toggle`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({is_active: isActive})
        });
        const data = await res.json();
        if (data.ok) {
            showToast(data.message, 'success');
            const accountId = parseInt(document.getElementById('target-account-select')?.value || 0);
            loadTargets(accountId);
        }
    } catch (e) {
        showToast('Hata: ' + e.message, 'error');
    }
}

// ============ BOT SETTINGS ============
async function loadBotSettings() {
    try {
        const res = await fetch('/api/bot-settings');
        const data = await res.json();
        if (data.ok && data.settings) {
            botSettings = data.settings;
        }
    } catch (e) {
        console.error('Ayarlar yuklenemedi:', e);
    }
}

async function loadBotSettingsForTab(botNum) {
    const settings = botSettings[botNum];
    if (!settings) return;

    const accSel = document.getElementById(`b${botNum}-account`);
    if (accSel && settings.account_id) {
        accSel.value = settings.account_id;
        currentAccountId = settings.account_id;
        loadTargets(settings.account_id);
    }

    const s = settings.settings;
    if (!s) return;

    const mappings = {
        1: {target: 'b1-target', max: 'b1-max', delay: 'b1-delay'},
        2: {targets: 'b2-targets', 'per-target': 'b2-per-target', delay: 'b2-delay'},
        3: {target: 'b3-target', max: 'b3-max', delay: 'b3-delay'},
        4: {batch: 'b4-batch', delay: 'b4-delay', break: 'b4-break', 'break-duration': 'b4-break-duration'}
    };

    const map = mappings[botNum];
    if (!map) return;

    for (const [key, id] of Object.entries(map)) {
        const el = document.getElementById(id);
        if (el && s[key] !== undefined) {
            el.value = s[key];
        }
    }
}

async function saveCurrentBotSettings(botNum) {
    const accountId = parseInt(document.getElementById(`b${botNum}-account`)?.value || 0);
    if (!accountId) {
        showToast('Once hesap secin!', 'error');
        return;
    }

    const settings = {};
    const mappings = {
        1: {target: 'b1-target', max: 'b1-max', delay: 'b1-delay'},
        2: {targets: 'b2-targets', 'per-target': 'b2-per-target', delay: 'b2-delay'},
        3: {target: 'b3-target', max: 'b3-max', delay: 'b3-delay'},
        4: {batch: 'b4-batch', delay: 'b4-delay', break: 'b4-break', 'break-duration': 'b4-break-duration'}
    };

    const map = mappings[botNum];
    for (const [key, id] of Object.entries(map)) {
        const el = document.getElementById(id);
        if (el) {
            settings[key] = el.value;
        }
    }

    try {
        const res = await fetch(`/api/bot-settings/${botNum}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({account_id: accountId, settings: settings})
        });
        const data = await res.json();
        if (data.ok) {
            showToast('Ayarlar kaydedildi!', 'success');
            botSettings[botNum] = {account_id: accountId, settings: settings};
        }
    } catch (e) {
        showToast('Ayarlar kaydedilemedi: ' + e.message, 'error');
    }
}

// ============ BOT CONTROL ============
async function startBot(botNum) {
    const accountId = parseInt(document.getElementById(`b${botNum}-account`)?.value || 0);
    if (!accountId) {
        showToast('Lutfen hesap secin!', 'error');
        return;
    }

    currentAccountId = accountId;

    const data = {account_id: accountId, mode: botNum === 4 ? 'follow' : 'collect'};

    if (botNum === 1) {
        data.target = document.getElementById('b1-target')?.value.trim().replace('@', '') || '';
        data.max_per_target = parseInt(document.getElementById('b1-max')?.value || 50);
        data.loop_delay = parseInt(document.getElementById('b1-delay')?.value || 60);
    } else if (botNum === 2) {
        const targetsText = document.getElementById('b2-targets')?.value || '';
        data.targets = targetsText.split('\n').map(t => t.trim().replace('@', '')).filter(t => t);
        data.max_per_target = parseInt(document.getElementById('b2-per-target')?.value || 50);
        data.loop_delay = parseInt(document.getElementById('b2-delay')?.value || 60);
    } else if (botNum === 3) {
        data.target = document.getElementById('b3-target')?.value.trim().replace('@', '') || '';
        data.max_per_target = parseInt(document.getElementById('b3-max')?.value || 50);
        data.loop_delay = parseInt(document.getElementById('b3-delay')?.value || 60);
    } else if (botNum === 4) {
        data.batch_size = parseInt(document.getElementById('b4-batch')?.value || 50);
        data.delay = parseInt(document.getElementById('b4-delay')?.value || 5);
        data.break_after = parseInt(document.getElementById('b4-break')?.value || 400);
        data.break_duration = parseInt(document.getElementById('b4-break-duration')?.value || 100);
    }

    await saveCurrentBotSettings(botNum);

    try {
        const res = await fetch(`/api/start/${botNum}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        const result = await res.json();
        showToast(result.message, result.ok ? 'success' : 'error');
        if (result.ok) {
            startLogStreaming(botNum);
            updateCurrentUser(accountId);
        }
    } catch (e) {
        showToast('Baslatma hatasi: ' + e.message, 'error');
    }
}

async function stopBot(botNum) {
    try {
        const res = await fetch(`/api/stop/${botNum}`, {method: 'POST'});
        const data = await res.json();
        showToast(data.message, 'success');
        stopLogStreaming();
    } catch (e) {
        showToast('Durdurma hatasi: ' + e.message, 'error');
    }
}

// ============ LOG STREAMING ============
function startLogStreaming(botNum) {
    stopLogStreaming();
    const logArea = document.getElementById('log-area');
    if (!logArea) return;

    logArea.innerHTML = '';

    fetch(`/api/logs/${botNum}`)
        .then(r => r.json())
        .then(data => {
            if (data.ok && data.logs) {
                data.logs.forEach(line => appendLog(line));
            }
        });

    const evtSource = new EventSource(`/api/stream/${botNum}`);
    logInterval = evtSource;

    evtSource.onmessage = (e) => {
        appendLog(e.data);
    };

    evtSource.onerror = () => {
        evtSource.close();
    };
}

function stopLogStreaming() {
    if (logInterval) {
        logInterval.close();
        logInterval = null;
    }
}

function appendLog(line) {
    const logArea = document.getElementById('log-area');
    if (!logArea) return;

    const div = document.createElement('div');
    div.className = 'log-entry';

    const timestamp = new Date().toLocaleTimeString('tr-TR');
    let logClass = 'log-info';
    if (line.includes('ONAYLI') || line.includes('Basarili')) logClass = 'log-success';
    if (line.includes('ONAYSIZ') || line.includes('Hata') || line.includes('basarisiz')) logClass = 'log-error';

    div.innerHTML = `<span class="log-time">[${timestamp}]</span> <span class="${logClass}">${escapeHtml(line)}</span>`;
    logArea.appendChild(div);
    logArea.scrollTop = logArea.scrollHeight;

    while (logArea.children.length > 500) {
        logArea.removeChild(logArea.firstChild);
    }
}

// ============ STATUS POLLING ============
function startStatusPolling() {
    statusInterval = setInterval(async () => {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data.ok) {
                updateRunningBots(data.running);
            }
        } catch (e) {}
    }, 5000);
}

function updateRunningBots(running) {
    const container = document.getElementById('running-bots');
    if (!container) return;

    const active = Object.entries(running).filter(([k, v]) => v.running);
    if (active.length === 0) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = active.map(([num, info]) => `
        <div class="running-bot-tag">
            Bot ${num} Calisiyor
            <button class="stop-btn" onclick="stopBot(${num})">×</button>
        </div>
    `).join('');
}

// ============ DATABASE STATS ============
async function loadStats() {
    const accountId = parseInt(document.getElementById('db-account')?.value || 0);
    if (!accountId) return;

    try {
        const res = await fetch(`/api/history?bot=4&account=${accountId}`);
        const data = await res.json();
        if (data.ok) {
            document.getElementById('db-pending').textContent = data.stats.pending;
            document.getElementById('db-followed').textContent = data.stats.followed;
            document.getElementById('db-failed').textContent = data.stats.failed;
            document.getElementById('db-total').textContent = data.stats.total;
            document.getElementById('db-approved').textContent = data.stats.approved;
            document.getElementById('db-rejected').textContent = data.stats.rejected;

            const total = data.stats.total || 1;
            const followed = data.stats.followed;
            const percent = Math.round((followed / total) * 100);
            document.getElementById('progress-percent').textContent = percent + '%';
            document.getElementById('progress-bar').style.width = percent + '%';

            const histGrid = document.getElementById('history-grid');
            if (data.history.length === 0) {
                histGrid.innerHTML = '<div style="color:#888;font-size:0.85rem;padding:20px;text-align:center;">Henuz takip islemi yok...</div>';
            } else {
                histGrid.innerHTML = data.history.map(h => `
                    <div class="history-item ${h.status}">
                        <div class="history-username">@${h.username}</div>
                        <div class="history-target">Kaynak: ${h.target}</div>
                        <span class="history-result ${h.status}">${h.result}</span>
                        <div class="history-time">${new Date(h.time).toLocaleString('tr-TR')}</div>
                    </div>
                `).join('');
            }

            const dailyContainer = document.getElementById('daily-stats');
            if (data.daily.length === 0) {
                dailyContainer.innerHTML = '<div style="color:#888;font-size:0.85rem;padding:10px;text-align:center;grid-column:1/-1;">Veri yok...</div>';
            } else {
                dailyContainer.innerHTML = data.daily.map(d => `
                    <div class="daily-stat-item">
                        <div class="daily-stat-date">${d.date}</div>
                        <div class="daily-stat-approved">${d.approved} OK</div>
                        <div class="daily-stat-rejected">${d.rejected} NO</div>
                    </div>
                `).join('');
            }
        }
    } catch (e) {
        console.error('Stats yuklenemedi:', e);
    }
}

async function resetFailed() {
    const accountId = parseInt(document.getElementById('db-account')?.value || 0);
    if (!accountId) {
        showToast('Hesap secin!', 'error');
        return;
    }

    try {
        const res = await fetch('/api/reset-failed', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({account_id: accountId})
        });
        const data = await res.json();
        showToast(data.message, data.ok ? 'success' : 'error');
        if (data.ok) loadStats();
    } catch (e) {
        showToast('Hata: ' + e.message, 'error');
    }
}

async function clearHistory() {
    const accountId = parseInt(document.getElementById('db-account')?.value || 0);
    if (!accountId) {
        showToast('Hesap secin!', 'error');
        return;
    }

    if (!confirm('Gecmisi temizlemek istediginize emin misiniz?')) return;

    try {
        const res = await fetch('/api/clear-history', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({account_id: accountId})
        });
        const data = await res.json();
        showToast(data.message, 'success');
        if (data.ok) loadStats();
    } catch (e) {
        showToast('Hata: ' + e.message, 'error');
    }
}

// ============ EVENT LISTENERS ============
function setupEventListeners() {
    // Hesap ekle
    document.getElementById('btn-add-account')?.addEventListener('click', async () => {
        const name = document.getElementById('acc-name')?.value.trim();
        const username = document.getElementById('acc-username')?.value.trim().replace('@', '');
        const password = document.getElementById('acc-password')?.value;

        if (!name || !username || !password) {
            showToast('Tum alanlari doldurun!', 'error');
            return;
        }

        try {
            const res = await fetch('/api/accounts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, username, password})
            });
            const data = await res.json();
            showToast(data.message, data.ok ? 'success' : 'error');
            if (data.ok) {
                document.getElementById('acc-name').value = '';
                document.getElementById('acc-username').value = '';
                document.getElementById('acc-password').value = '';
                loadAccounts();
            }
        } catch (e) {
            showToast('Hata: ' + e.message, 'error');
        }
    });

    // Bot baslat/durdur
    document.getElementById('btn-start-1')?.addEventListener('click', () => startBot(1));
    document.getElementById('btn-stop-1')?.addEventListener('click', () => stopBot(1));
    document.getElementById('btn-start-2')?.addEventListener('click', () => startBot(2));
    document.getElementById('btn-stop-2')?.addEventListener('click', () => stopBot(2));
    document.getElementById('btn-start-3')?.addEventListener('click', () => startBot(3));
    document.getElementById('btn-stop-3')?.addEventListener('click', () => stopBot(3));
    document.getElementById('btn-start-4')?.addEventListener('click', () => startBot(4));
    document.getElementById('btn-stop-4')?.addEventListener('click', () => stopBot(4));

    // Veritabani islemleri
    document.getElementById('db-account')?.addEventListener('change', loadStats);
    document.getElementById('btn-reset-failed')?.addEventListener('click', resetFailed);
    document.getElementById('btn-clear-history')?.addEventListener('click', clearHistory);

    // Hesap secildiginde hedefleri yukle
    ['b1-account', 'b2-account', 'b3-account'].forEach(id => {
        document.getElementById(id)?.addEventListener('change', (e) => {
            const accId = parseInt(e.target.value);
            if (accId) {
                currentAccountId = accId;
                loadTargets(accId);
            }
        });
    });

    // Hedef hesaplar sekmesinde hesap secildiginde hedefleri yukle
    document.getElementById('target-account-select')?.addEventListener('change', (e) => {
        const accId = parseInt(e.target.value);
        if (accId) {
            loadTargets(accId);
        } else {
            document.getElementById('targets-list').innerHTML = '<div style="color:#888;padding:20px;text-align:center;">Once hesap secin...</div>';
        }
    });
}

// ============ UTILS ============
function updateCurrentUser(accountId) {
    const acc = accounts.find(a => a.id === accountId);
    if (acc) {
        document.getElementById('current-user').textContent = '@' + acc.username;
        document.getElementById('bot-status').textContent = 'Calisiyor...';
    }
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.className = 'toast show toast-' + type;
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
