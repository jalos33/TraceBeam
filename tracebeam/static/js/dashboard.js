/* === TraceBeam Dashboard JS === */
const API = '/api';

// --- Health check ---
async function checkHealth() {
    try {
        const r = await fetch(API + '/health');
        const d = await r.json();
        const dot = document.getElementById('health-dot');
        const txt = document.getElementById('health-text');
        if (d.status === 'healthy') {
            dot.className = 'dot healthy';
            txt.textContent = 'Connected';
        } else {
            dot.className = 'dot unhealthy';
            txt.textContent = 'API Error';
        }
    } catch {
        document.getElementById('health-dot').className = 'dot unhealthy';
        document.getElementById('health-text').textContent = 'Offline';
    }
}
checkHealth();
setInterval(checkHealth, 30000);

// --- Helpers ---
function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
}

function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
}

// --- LAN Monitor (PingPlotter-style) ---
const LAT_GOOD = 50, LAT_WARN = 150;   // ms latency-quality thresholds
let monWindow = '1h';
let monPaused = false;
let monTimer = null;
let detailId = null;
let detailTarget = null;
let detailChart = null;
const monRows = {};                    // id -> latest summary row

function fmt(v, unit) {
    if (v == null || isNaN(v)) return '—';
    return (Math.round(v * 100) / 100) + (unit || '');
}
function latClass(v) { if (v == null) return 'bad'; if (v < LAT_GOOD) return 'good'; if (v < LAT_WARN) return 'warn'; return 'bad'; }
function lossClass(p) { if (p == null) return ''; if (p <= 0) return 'good'; if (p < 2) return 'warn'; return 'bad'; }
function mosClass(m) { if (m == null) return 'bad'; if (m >= 4) return 'good'; if (m >= 3) return 'warn'; return 'bad'; }
function statusOf(row) {
    if (!row.count) return 'gray';
    if (row.loss_pct >= 50 || row.cur == null) return 'bad';
    if (row.loss_pct > 0 || (row.avg != null && row.avg >= LAT_WARN)) return 'warn';
    return 'good';
}

// --- Target CRUD ---
async function addTarget() {
    const name = document.getElementById('mon-name').value.trim();
    const address = document.getElementById('mon-address').value.trim();
    const protocol = document.getElementById('mon-protocol').value;
    if (!address) { document.getElementById('mon-address').focus(); return; }
    try {
        const r = await fetch(API + '/monitor/targets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name || null, address, protocol }),
        });
        const d = await r.json();
        if (d.success) {
            document.getElementById('mon-name').value = '';
            document.getElementById('mon-address').value = '';
            loadSummary();
        } else {
            alert('Could not add target: ' + (d.detail || 'Unknown error'));
        }
    } catch (e) {
        alert('Error adding target: ' + e.message);
    }
}

async function deleteTarget(id, name, ev) {
    if (ev) ev.stopPropagation();
    if (!confirm('Remove target "' + name + '" and its history?')) return;
    try {
        await fetch(API + '/monitor/targets/' + id, { method: 'DELETE' });
        if (detailId === id) closeDetail();
        loadSummary();
    } catch (e) {
        alert('Delete failed: ' + e.message);
    }
}

// --- Summary view ---
async function loadSummary() {
    try {
        const r = await fetch(API + '/monitor/summary?window=' + monWindow);
        const d = await r.json();
        renderSummary(d.targets || []);
        document.getElementById('mon-updated').textContent = 'Updated ' + new Date().toLocaleTimeString();
    } catch (e) {
        console.error('summary error', e);
    }
}

function renderSummary(rows) {
    const body = document.getElementById('mon-summary-body');
    if (!rows.length) {
        body.innerHTML = '<tr><td colspan="14" class="empty">No targets yet — add one above to start monitoring.</td></tr>';
        return;
    }
    body.innerHTML = '';
    rows.forEach(row => {
        monRows[row.id] = row;
        const tr = el('tr', 'mon-row');
        tr.onclick = () => openDetail(row.id);
        tr.innerHTML = `
            <td class="c-status"><span class="sdot ${statusOf(row)}"></span></td>
            <td class="c-name">${esc(row.name)}</td>
            <td class="c-ip"><code>${esc(row.host)}</code></td>
            <td class="c-num ${latClass(row.cur)}">${fmt(row.cur)}</td>
            <td class="c-num ${latClass(row.avg)}">${fmt(row.avg)}</td>
            <td class="c-num">${fmt(row.min)}</td>
            <td class="c-num">${fmt(row.max)}</td>
            <td class="c-num">${fmt(row.jitter)}</td>
            <td class="c-num ${lossClass(row.loss_pct)}">${fmt(row.loss_pct)}</td>
            <td class="c-num ${mosClass(row.mos)}">${row.mos == null ? '—' : row.mos.toFixed(2)}</td>
            <td class="c-num muted">${row.count || 0}</td>
            <td class="c-num ${row.err ? 'bad' : 'muted'}">${row.err || 0}</td>
            <td class="c-spark"><canvas class="spark" width="180" height="34"></canvas></td>
            <td class="c-act"><button class="icon-btn" title="Remove" onclick="deleteTarget(${row.id}, '${esc(row.name)}', event)">✕</button></td>`;
        body.appendChild(tr);
        drawSparkline(tr.querySelector('canvas.spark'), row.series || []);
    });
    renderStrips(rows);
}

// Stacked per-target timeline strips (like PingPlotter's "All Targets" lower panel).
function renderStrips(rows) {
    const wrap = document.getElementById('mon-strips');
    if (!wrap) return;
    // (Re)build the strip cards only when the set of targets changes; otherwise
    // just redraw the canvases in place so it stays smooth.
    const key = rows.map(r => r.id).join(',');
    if (wrap.dataset.key !== key) {
        wrap.dataset.key = key;
        wrap.innerHTML = '';
        rows.forEach(row => {
            const card = el('div', 'strip-card');
            card.dataset.id = row.id;
            card.onclick = () => openDetail(row.id);
            card.innerHTML = `
                <div class="strip-head">
                    <span class="strip-name">${esc(row.name)}</span>
                    <span class="strip-host">${esc(row.host)}</span>
                    <span class="strip-win">${monWindow}</span>
                </div>
                <canvas class="strip-canvas" height="120"></canvas>`;
            wrap.appendChild(card);
        });
    }
    rows.forEach(row => {
        const card = wrap.querySelector('.strip-card[data-id="' + row.id + '"]');
        if (!card) return;
        card.querySelector('.strip-win').textContent = monWindow;
        drawStrip(card.querySelector('canvas.strip-canvas'), row.series || []);
    });
}

function formatSeriesTime(iso) {
    const dt = new Date(iso);
    const secs = monWindow.endsWith('m') || monWindow === '1h';
    return dt.toLocaleTimeString([], secs ? { hour: '2-digit', minute: '2-digit' } : { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function drawStrip(canvas, series) {
    const ctx = canvas.getContext('2d');
    // Match backing store to displayed width for crisp full-width rendering.
    const cssW = canvas.clientWidth || canvas.parentElement.clientWidth || 800;
    if (canvas.width !== cssW) canvas.width = cssW;
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    const AXIS_H = 14;   // bottom strip reserved for x-axis time labels
    const plotH = H - AXIS_H;

    const rtts = series.map(p => p.rtt).filter(v => v != null);
    const max = rtts.length ? Math.max(Math.max(...rtts) * 1.1, LAT_WARN * 1.2) : LAT_WARN * 1.2;
    const yFor = v => plotH - 4 - (v / max) * (plotH - 8);

    // latency quality zones (subtle)
    const zones = [[0, LAT_GOOD, 'rgba(34,197,94,0.10)'], [LAT_GOOD, LAT_WARN, 'rgba(245,158,11,0.10)'], [LAT_WARN, max, 'rgba(239,68,68,0.10)']];
    zones.forEach(([lo, hi, c]) => {
        if (hi <= lo) return;
        const yt = yFor(Math.min(hi, max)), yb = yFor(lo);
        ctx.fillStyle = c; ctx.fillRect(0, yt, W, yb - yt);
    });

    if (!series.length) return;
    const n = series.length, bw = W / n;

    // red packet-loss bands
    series.forEach((p, i) => {
        if (p.loss > 0) {
            ctx.fillStyle = 'rgba(239,68,68,' + (0.22 + 0.6 * Math.min(1, p.loss)) + ')';
            ctx.fillRect(i * bw, 0, Math.max(1, bw + 0.5), plotH);
        }
    });

    // latency line
    ctx.beginPath();
    let started = false;
    series.forEach((p, i) => {
        if (p.rtt == null) { started = false; return; }
        const x = i * bw + bw / 2, y = yFor(p.rtt);
        if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1.2;
    ctx.stroke();

    // y-axis labels: top = max latency, bottom = 0
    ctx.fillStyle = 'rgba(148,163,184,0.9)';
    ctx.font = '10px -apple-system, sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText(Math.round(max) + ' ms', 4, 3);
    ctx.textBaseline = 'alphabetic';
    ctx.fillText('0 ms', 4, plotH - 3);

    // x-axis labels: a few evenly-spaced timestamps below the plot
    const tickCount = Math.min(series.length, W < 500 ? 3 : 5);
    if (tickCount >= 2) {
        ctx.textBaseline = 'top';
        for (let i = 0; i < tickCount; i++) {
            const idx = Math.round(i * (series.length - 1) / (tickCount - 1));
            const p = series[idx];
            if (!p || !p.t) continue;
            const x = idx * bw + bw / 2;
            ctx.textAlign = i === 0 ? 'left' : (i === tickCount - 1 ? 'right' : 'center');
            ctx.fillText(formatSeriesTime(p.t), Math.min(Math.max(x, 2), W - 2), plotH + 2);
        }
    }
}

function drawSparkline(canvas, series) {
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    if (!series.length) return;
    const rtts = series.map(p => p.rtt).filter(v => v != null);
    const max = rtts.length ? Math.max(...rtts) : 1;
    const n = series.length;
    const bw = W / n;

    // Red packet-loss bands
    series.forEach((p, i) => {
        if (p.loss > 0) {
            ctx.fillStyle = 'rgba(239,68,68,' + (0.25 + 0.55 * Math.min(1, p.loss)) + ')';
            ctx.fillRect(i * bw, 0, Math.max(1, bw), H);
        }
    });

    // Latency line
    ctx.beginPath();
    let started = false;
    series.forEach((p, i) => {
        if (p.rtt == null) { started = false; return; }
        const x = i * bw + bw / 2;
        const y = H - 3 - (p.rtt / (max || 1)) * (H - 6);
        if (!started) { ctx.moveTo(x, y); started = true; }
        else ctx.lineTo(x, y);
    });
    const avg = rtts.length ? rtts.reduce((a, b) => a + b, 0) / rtts.length : null;
    ctx.strokeStyle = avg == null ? '#64748b' : (avg < LAT_GOOD ? '#22c55e' : avg < LAT_WARN ? '#f59e0b' : '#ef4444');
    ctx.lineWidth = 1.5;
    ctx.stroke();
}

// --- Detail view ---
function openDetail(id) {
    detailId = id;
    detailTarget = monRows[id] || null;
    document.getElementById('monitor-summary').style.display = 'none';
    document.getElementById('monitor-detail').style.display = 'block';
    document.getElementById('detail-name').textContent = detailTarget ? detailTarget.name : 'Target';
    document.getElementById('detail-host').textContent = detailTarget ? detailTarget.host : '';
    document.getElementById('detail-hops-body').innerHTML = '<tr><td colspan="11" class="empty">Loading…</td></tr>';
    scheduleMonitor();   // detail view polls faster
    loadDetail();
}

function closeDetail() {
    detailId = null;
    detailTarget = null;
    if (detailChart) { detailChart.destroy(); detailChart = null; }
    detailChartKey = null;
    document.getElementById('monitor-detail').style.display = 'none';
    document.getElementById('monitor-summary').style.display = 'block';
    scheduleMonitor();
    loadSummary();
}

async function loadDetail() {
    if (detailId == null) return;
    const id = detailId;
    try {
        const [hopsR, seriesR] = await Promise.all([
            fetch(API + '/monitor/targets/' + id + '/hops'),
            fetch(API + '/monitor/targets/' + id + '/series?window=' + monWindow),
        ]);
        const hopsD = await hopsR.json();
        const seriesD = await seriesR.json();
        if (detailId !== id) return;   // user navigated away
        renderHops(hopsD.hops || [], hopsD.permission_denied);
        document.getElementById('detail-mtr-ts').textContent =
            hopsD.run_ts ? 'Hops: ' + new Date(hopsD.run_ts).toLocaleTimeString() : '';
        renderTimeline(seriesD);
    } catch (e) {
        console.error('detail error', e);
    }
}

function renderHops(hops, permissionDenied) {
    const body = document.getElementById('detail-hops-body');
    if (!hops.length) {
        body.innerHTML = permissionDenied
            ? '<tr><td colspan="11" class="empty error">Hop data needs elevated privileges on this OS — see README "Permissions".</td></tr>'
            : '<tr><td colspan="11" class="empty">No hop data yet — runs every ~45s.</td></tr>';
        return;
    }
    const scaleMax = Math.max(1, ...hops.map(h => h.worst_ms || 0));
    body.innerHTML = '';
    hops.forEach(h => {
        const st = h.host === '???' ? 'gray' : (h.loss_pct >= 50 ? 'bad' : h.loss_pct > 0 ? 'warn' : 'good');
        const best = h.best_ms || 0, worst = h.worst_ms || 0, avg = h.avg_ms || 0;
        const left = (best / scaleMax) * 100;
        const width = Math.max(2, ((worst - best) / scaleMax) * 100);
        const avgPos = (avg / scaleMax) * 100;
        const barColor = latClass(h.avg_ms);
        const tr = el('tr');
        tr.innerHTML = `
            <td class="c-status"><span class="sdot ${st}"></span></td>
            <td class="c-num">${h.hop_no}</td>
            <td class="c-ip"><code>${esc(h.host)}</code></td>
            <td class="c-name">${esc(h.name)}</td>
            <td class="c-num ${lossClass(h.loss_pct)}">${fmt(h.loss_pct)}</td>
            <td class="c-num muted">${h.sent || 0}</td>
            <td class="c-num">${fmt(h.last_ms)}</td>
            <td class="c-num ${latClass(h.avg_ms)}">${fmt(h.avg_ms)}</td>
            <td class="c-num">${fmt(h.best_ms)}</td>
            <td class="c-num">${fmt(h.worst_ms)}</td>
            <td class="c-graph">
                <div class="hopbar">
                    <div class="hopbar-range ${barColor}" style="left:${left}%;width:${width}%"></div>
                    <div class="hopbar-avg" style="left:${avgPos}%"></div>
                </div>
            </td>`;
        body.appendChild(tr);
    });
}

// Chart.js inline plugins: latency quality zones + red packet-loss bands.
const zonesPlugin = {
    id: 'zones',
    beforeDatasetsDraw(chart) {
        const { ctx, chartArea: area, scales: { y } } = chart;
        if (!area || !y) return;
        const bands = [
            [0, LAT_GOOD, 'rgba(34,197,94,0.08)'],
            [LAT_GOOD, LAT_WARN, 'rgba(245,158,11,0.08)'],
            [LAT_WARN, y.max, 'rgba(239,68,68,0.09)'],
        ];
        ctx.save();
        bands.forEach(([lo, hi, color]) => {
            if (hi <= lo) return;
            const yTop = y.getPixelForValue(Math.min(hi, y.max));
            const yBot = y.getPixelForValue(Math.max(lo, y.min));
            ctx.fillStyle = color;
            ctx.fillRect(area.left, yTop, area.right - area.left, yBot - yTop);
        });
        ctx.restore();
    },
};
const lossBandsPlugin = {
    id: 'lossBands',
    beforeDatasetsDraw(chart) {
        const { ctx, chartArea: area, scales: { x } } = chart;
        const loss = chart.$lossSeries || [];
        if (!area || !x || !loss.length) return;
        const bw = (area.right - area.left) / loss.length;
        ctx.save();
        loss.forEach((v, i) => {
            if (v > 0) {
                ctx.fillStyle = 'rgba(239,68,68,' + (0.2 + 0.55 * Math.min(1, v)) + ')';
                ctx.fillRect(area.left + i * bw, area.top, Math.max(1, bw), area.bottom - area.top);
            }
        });
        ctx.restore();
    },
};

let detailChartKey = null;   // identifies target+window the chart is built for

function renderTimeline(data) {
    const series = data.series || [];
    const canvas = document.getElementById('detail-chart');
    if (!canvas) return;
    const labels = series.map(p => formatSeriesTime(p.t));
    const rtt = series.map(p => p.rtt);
    const lossArr = series.map(p => p.loss || 0);
    const key = detailId + '|' + monWindow;

    // Fast path: same target+window -> update the existing chart's data in place
    // (no destroy/recreate), which keeps the timeline smooth on every poll.
    if (detailChart && detailChartKey === key) {
        detailChart.data.labels = labels;
        detailChart.data.datasets[0].data = rtt;
        detailChart.$lossSeries = lossArr;
        detailChart.update('none');
        return;
    }

    if (detailChart) { detailChart.destroy(); detailChart = null; }
    detailChartKey = key;
    detailChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Latency (ms)',
                data: rtt,
                borderColor: '#e2e8f0',
                borderWidth: 1.3,
                pointRadius: 0,
                spanGaps: false,
                tension: 0.2,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            interaction: { intersect: false, mode: 'index' },
            scales: {
                x: { ticks: { color: '#94a3b8', maxTicksLimit: 12, maxRotation: 0 }, grid: { color: 'rgba(148,163,184,0.08)' } },
                y: { beginAtZero: true, ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.08)' }, title: { display: true, text: 'Latency (ms)', color: '#94a3b8' } },
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#0f172a', titleColor: '#e2e8f0', bodyColor: '#cbd5e1', borderColor: '#334155', borderWidth: 1,
                    callbacks: {
                        afterBody: (items) => {
                            const i = items[0].dataIndex;
                            const l = lossArr[i];
                            return l > 0 ? 'Packet loss: ' + Math.round(l * 100) + '%' : 'No loss';
                        },
                    },
                },
            },
        },
        plugins: [zonesPlugin, lossBandsPlugin],
    });
    detailChart.$lossSeries = lossArr;
    detailChart.update('none');
}

// --- Monitor controls / polling ---
// Short windows refresh live; long windows barely change per tick, so poll
// them less often to keep SQLite reads light.
const SHORT_WINDOWS = new Set(['5m', '15m', '30m', '1h']);
function pollInterval() {
    if (detailId != null) return 2000;               // detail view: live-feel refresh
    return SHORT_WINDOWS.has(monWindow) ? 5000 : 20000;
}

function onWindowChange() {
    monWindow = document.getElementById('mon-window').value;
    scheduleMonitor();
    if (detailId != null) loadDetail(); else loadSummary();
}
function togglePause() {
    monPaused = !monPaused;
    document.getElementById('mon-pause').textContent = monPaused ? '▶ Resume' : '⏸ Pause';
}
function monitorTick() {
    if (monPaused) return;
    if (detailId != null) loadDetail(); else loadSummary();
}
function scheduleMonitor() {
    if (monTimer) clearInterval(monTimer);
    monTimer = setInterval(monitorTick, pollInterval());
}
function startMonitor() {
    loadSummary();
    scheduleMonitor();
    const addr = document.getElementById('mon-address');
    if (addr) addr.addEventListener('keydown', e => { if (e.key === 'Enter') addTarget(); });
}

// --- Init ---
startMonitor();
