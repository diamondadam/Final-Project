# Rail Track Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained `dashboard/` folder with an Express server + vanilla JS frontend that streams live rail track health data from the FastAPI backend WebSocket and displays it in a 4-panel dark-theme dashboard.

**Architecture:** Express on port 3000 serves static files from `public/`. The browser connects directly to `ws://localhost:8000/ws` and `http://localhost:8000` (FastAPI). Modules communicate via a shared `store` object in `state.js` and DOM CustomEvents dispatched by `ws.js`. No build step, no framework, Chart.js loaded from CDN.

**Tech Stack:** Node.js 18+, Express 4, Vanilla JS (ES modules via `<script type="module">`), Chart.js 4 (CDN), native WebSocket API, native `fetch`

---

## File Map

| File | Responsibility |
|---|---|
| `dashboard/server.js` | Express app — serves `public/` on port 3000 |
| `dashboard/package.json` | Single dep: express |
| `dashboard/public/index.html` | App shell: sidebar, alert banner, 4-panel grid, loads all scripts |
| `dashboard/public/style.css` | All styles: tokens, layout, sidebar hover, panels, components |
| `dashboard/public/state.js` | Shared store: `latest` TwinState, 30-tick `history`, `workOrders` cache |
| `dashboard/public/ws.js` | WebSocket connection, auto-reconnect, dispatches `twinstate` CustomEvent |
| `dashboard/public/segments.js` | Renders track segment classification panel on each `twinstate` event |
| `dashboard/public/charts.js` | Chart.js line chart for telemetry, updates on each `twinstate` event |
| `dashboard/public/orders.js` | Fetches `/work-orders`, renders order list, handles Mark Complete |
| `dashboard/tests/state.test.js` | Unit tests for state.js pure logic |

---

## Task 1: Project Scaffold

**Files:**
- Create: `dashboard/package.json`
- Create: `dashboard/server.js`
- Create: `dashboard/public/` (empty dir placeholder)
- Create: `dashboard/tests/` (empty dir placeholder)

- [ ] **Step 1: Create `dashboard/package.json`**

```json
{
  "name": "rail-twin-dashboard",
  "version": "1.0.0",
  "type": "commonjs",
  "scripts": {
    "start": "node server.js",
    "test": "node --test tests/state.test.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  }
}
```

- [ ] **Step 2: Create `dashboard/server.js`**

```js
const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.static(path.join(__dirname, 'public')));

app.listen(PORT, () => {
  console.log(`Dashboard running at http://localhost:${PORT}`);
  console.log(`Requires FastAPI backend at http://localhost:8000`);
});
```

- [ ] **Step 3: Install dependencies**

Run from `dashboard/`:
```bash
npm install
```
Expected: `node_modules/` created, no errors.

- [ ] **Step 4: Verify server starts**

```bash
npm start
```
Expected output:
```
Dashboard running at http://localhost:3000
Requires FastAPI backend at http://localhost:8000
```
Stop with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add dashboard/package.json dashboard/server.js
git commit -m "feat(dashboard): add Express scaffold"
```

---

## Task 2: State Store

**Files:**
- Create: `dashboard/public/state.js`
- Create: `dashboard/tests/state.test.js`

- [ ] **Step 1: Write failing tests**

Create `dashboard/tests/state.test.js`:

```js
const { test } = require('node:test');
const assert = require('node:assert/strict');

// state.js uses ES module exports — load via dynamic import
let store, pushHistory, deriveAcceleration;

test('setup', async () => {
  const mod = await import('../public/state.js');
  store = mod.store;
  pushHistory = mod.pushHistory;
  deriveAcceleration = mod.deriveAcceleration;
});

test('store initialises with empty state', () => {
  assert.equal(store.latest, null);
  assert.deepEqual(store.history, []);
  assert.deepEqual(store.workOrders, []);
});

test('pushHistory caps at 30 entries', () => {
  for (let i = 0; i < 35; i++) {
    pushHistory({ commanded_speed_fps: i, tick: i });
  }
  assert.equal(store.history.length, 30);
  assert.equal(store.history[29].tick, 34); // most recent last
});

test('deriveAcceleration returns 0 when history has fewer than 2 entries', () => {
  store.history = [{ commanded_speed_fps: 1.5 }];
  assert.equal(deriveAcceleration(), 0);
});

test('deriveAcceleration computes delta between last two ticks', () => {
  store.history = [
    { commanded_speed_fps: 1.0 },
    { commanded_speed_fps: 1.6 },
  ];
  // (1.6 - 1.0) / 1.0 tick = 0.6 fps²
  assert.ok(Math.abs(deriveAcceleration() - 0.6) < 0.001);
});

test('deriveAcceleration rounds to 2 decimal places', () => {
  store.history = [
    { commanded_speed_fps: 1.0 },
    { commanded_speed_fps: 1.333 },
  ];
  assert.equal(deriveAcceleration(), 0.33);
});
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd dashboard && npm test
```
Expected: error — `Cannot find module '../public/state.js'`

- [ ] **Step 3: Create `dashboard/public/state.js`**

```js
// Shared mutable store — imported by all panel modules
export const store = {
  latest: null,       // most recent TwinState from WebSocket
  history: [],        // last 30 TwinStates (oldest → newest)
  workOrders: [],     // cached from GET /work-orders
};

// Append state to history, cap at 30
export function pushHistory(state) {
  store.history.push(state);
  if (store.history.length > 30) store.history.shift();
}

// Compute acceleration fps² from last two history entries (1 tick = 1s)
export function deriveAcceleration() {
  const h = store.history;
  if (h.length < 2) return 0;
  const delta = h[h.length - 1].commanded_speed_fps - h[h.length - 2].commanded_speed_fps;
  return Math.round(delta * 100) / 100;
}

// 3-tick rolling average of commanded_speed_fps
export function deriveMpcSmoothed() {
  const h = store.history;
  const window = h.slice(-3);
  if (window.length === 0) return 0;
  const avg = window.reduce((s, t) => s + t.commanded_speed_fps, 0) / window.length;
  return Math.round(avg * 100) / 100;
}
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd dashboard && npm test
```
Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add dashboard/public/state.js dashboard/tests/state.test.js
git commit -m "feat(dashboard): add state store with history and derived metrics"
```

---

## Task 3: HTML Shell + CSS

**Files:**
- Create: `dashboard/public/index.html`
- Create: `dashboard/public/style.css`

- [ ] **Step 1: Create `dashboard/public/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rail Track Digital Twin</title>
  <link rel="stylesheet" href="style.css">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
  <div class="app">

    <!-- Sidebar -->
    <nav class="sidebar" id="sidebar">
      <div class="sidebar-logo">
        <span class="logo-short">RT</span>
        <span class="logo-long">RAIL TWIN</span>
      </div>
      <a class="nav-item active" href="#"><span class="nav-icon">⬡</span><span class="nav-label">Live HUD</span></a>
      <a class="nav-item" href="#"><span class="nav-icon">⟁</span><span class="nav-label">Analytics</span></a>
      <a class="nav-item" href="#"><span class="nav-icon">⚙</span><span class="nav-label">Maintenance</span></a>
      <div class="sidebar-footer">
        <div class="ws-indicator" id="ws-indicator">
          <span class="ws-dot" id="ws-dot"></span>
          <span class="ws-label" id="ws-label">Connecting…</span>
        </div>
        <a class="nav-item nav-bottom" href="#" id="export-btn">
          <span class="nav-icon">↗</span><span class="nav-label">Export Report</span>
        </a>
      </div>
    </nav>

    <!-- Main -->
    <div class="main">

      <!-- Alert Banner -->
      <div class="alert-banner" id="alert-banner">
        <span class="alert-dot" id="alert-dot"></span>
        <span class="alert-text" id="alert-text">Waiting for data…</span>
        <span class="alert-tick" id="alert-tick"></span>
      </div>

      <!-- 4-Panel Grid -->
      <div class="panels">

        <!-- P1: Live Feed -->
        <div class="panel" id="panel-feed">
          <div class="panel-header">
            <span class="panel-title">▶ LIVE FEED — UE5</span>
            <span class="panel-badge badge-live">● LIVE</span>
          </div>
          <div class="feed-body">
            <div class="live-placeholder">
              <div class="play-icon">▶</div>
              <span class="placeholder-label">UNREAL ENGINE FEED</span>
              <span class="placeholder-sub">Connect UE5 stream URL here</span>
            </div>
            <div class="coord-row">
              <div class="coord-cell">
                <div class="coord-label">LAT</div>
                <div class="coord-value" id="coord-lat">—</div>
              </div>
              <div class="coord-cell">
                <div class="coord-label">LONG</div>
                <div class="coord-value" id="coord-long">—</div>
              </div>
              <div class="coord-cell">
                <div class="coord-label">ACTIVE SEGMENT</div>
                <div class="coord-value" id="coord-seg">—</div>
              </div>
            </div>
          </div>
        </div>

        <!-- P2: Segment Classification -->
        <div class="panel" id="panel-segments">
          <div class="panel-header">
            <span class="panel-title">TRACK SEGMENT CLASSIFICATION</span>
            <span class="panel-badge badge-red" id="seg-badge">—</span>
          </div>
          <div class="seg-body">
            <div class="seg-list" id="seg-list">
              <!-- Populated by segments.js -->
            </div>
            <div class="seg-legend">
              <div class="leg"><div class="leg-dot" style="background:#ADEBB3;"></div><span style="color:#ADEBB3;">Healthy</span></div>
              <div class="leg"><div class="leg-dot" style="background:#f59e0b;"></div><span style="color:#f59e0b;">Degraded</span></div>
              <div class="leg"><div class="leg-dot" style="background:#FF1A1A;"></div><span style="color:#FF1A1A;">Damaged</span></div>
              <span class="train-pos-note">▶ = train position</span>
            </div>
          </div>
        </div>

        <!-- P3: Telemetry -->
        <div class="panel" id="panel-telemetry">
          <div class="panel-header">
            <span class="panel-title">REAL-TIME TELEMETRY</span>
            <div class="chart-legend">
              <div class="c-leg"><div class="c-line" style="background:#87CEEB;"></div><span style="color:#87CEEB;">Velocity</span></div>
              <div class="c-leg"><div class="c-line c-dashed" style="border-color:#FDFBD4;"></div><span style="color:#FDFBD4;">Accel</span></div>
              <div class="c-leg"><div class="c-line" style="background:#f59e0b;"></div><span style="color:#f59e0b;">MPC Speed</span></div>
            </div>
          </div>
          <div class="telem-body">
            <div class="chart-outer">
              <canvas id="telem-chart"></canvas>
            </div>
            <div class="readouts">
              <div class="readout">
                <div><span class="readout-val" id="rv-velocity" style="color:#87CEEB;">—</span><span class="readout-unit"> fps</span></div>
                <div class="readout-lbl">VELOCITY</div>
              </div>
              <div class="readout">
                <div><span class="readout-val" id="rv-accel" style="color:#FDFBD4;">—</span><span class="readout-unit"> fps²</span></div>
                <div class="readout-lbl">ACCELERATION</div>
              </div>
              <div class="readout">
                <div><span class="readout-val" id="rv-mpc" style="color:#f59e0b;">—</span><span class="readout-unit"> fps</span></div>
                <div class="readout-lbl">MPC SPEED</div>
              </div>
            </div>
          </div>
        </div>

        <!-- P4: Maintenance Orders -->
        <div class="panel" id="panel-orders">
          <div class="panel-header">
            <span class="panel-title">MAINTENANCE ORDER LIST</span>
            <span class="panel-badge badge-red" id="orders-badge">—</span>
          </div>
          <div class="orders-body">
            <div class="orders-list" id="orders-list">
              <!-- Populated by orders.js -->
            </div>
            <div class="orders-footer">
              Auto-sorted by damage confidence · Marking complete repairs segment in simulation
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>

  <script type="module" src="state.js"></script>
  <script type="module" src="ws.js"></script>
  <script type="module" src="segments.js"></script>
  <script type="module" src="charts.js"></script>
  <script type="module" src="orders.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `dashboard/public/style.css`**

```css
/* ── Design tokens ── */
:root {
  --bg:         #111827;
  --surface:    #1f2937;
  --sidebar-bg: #1a2332;
  --border:     #374151;
  --border-dim: #2d3748;
  --cream:      #FDFBD4;
  --blue:       #87CEEB;
  --green:      #ADEBB3;
  --amber:      #f59e0b;
  --red:        #FF1A1A;
  --muted:      #6b7280;
  --muted-dim:  #4b5563;
  --text:       #e5e7eb;
}

/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; overflow: hidden; }
body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; font-size: 13px; }
a { text-decoration: none; }

/* ── App shell ── */
.app { display: flex; height: 100vh; }

/* ── Sidebar ── */
.sidebar {
  width: 44px;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  padding: 10px 0; gap: 2px;
  transition: width 0.22s ease;
  overflow: hidden; white-space: nowrap;
  flex-shrink: 0;
}
.sidebar:hover { width: 150px; }

.sidebar-logo {
  color: var(--cream); font-size: 9px; font-weight: 700;
  letter-spacing: 2px; padding: 0 12px; margin-bottom: 10px; width: 100%;
}
.logo-short { display: inline; }
.logo-long  { display: none; }
.sidebar:hover .logo-short { display: none; }
.sidebar:hover .logo-long  { display: inline; }

.nav-item {
  width: 100%; padding: 8px 12px;
  display: flex; align-items: center; gap: 10px;
  color: var(--muted); font-size: 10px; cursor: pointer;
  border-radius: 3px; transition: background 0.15s, color 0.15s;
}
.nav-item:hover, .nav-item.active { background: var(--border-dim); color: var(--cream); }
.nav-icon  { font-size: 14px; min-width: 20px; text-align: center; flex-shrink: 0; }
.nav-label { opacity: 0; transition: opacity 0.15s; }
.sidebar:hover .nav-label { opacity: 1; }

.sidebar-footer { margin-top: auto; display: flex; flex-direction: column; gap: 2px; }
.ws-indicator { display: flex; align-items: center; gap: 8px; padding: 6px 12px; }
.ws-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--amber); flex-shrink: 0; }
.ws-dot.connected    { background: var(--green); }
.ws-dot.reconnecting { background: var(--amber); animation: pulse 1.2s infinite; }
.ws-dot.disconnected { background: var(--red); }
.ws-label { font-size: 9px; color: var(--muted); opacity: 0; transition: opacity 0.15s; }
.sidebar:hover .ws-label { opacity: 1; }

/* ── Main area ── */
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }

/* ── Alert banner ── */
.alert-banner {
  display: flex; align-items: center; gap: 10px;
  padding: 7px 16px; border-bottom: 1px solid var(--border);
  background: var(--surface); flex-shrink: 0;
  font-size: 11px; transition: background 0.3s, border-color 0.3s;
}
.alert-banner.state-damaged  { background: #1f1515; border-color: #FF1A1A44; }
.alert-banner.state-degraded { background: #1f1a0f; border-color: #f59e0b44; }
.alert-banner.state-clear    { background: #141f14; border-color: #ADEBB344; }

.alert-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; background: var(--muted); }
.alert-banner.state-damaged  .alert-dot { background: var(--red);   animation: pulse 1.4s infinite; }
.alert-banner.state-degraded .alert-dot { background: var(--amber); animation: pulse 2s infinite; }
.alert-banner.state-clear    .alert-dot { background: var(--green); animation: none; }

.alert-text { flex: 1; font-weight: 600; color: var(--muted); }
.alert-banner.state-damaged  .alert-text { color: var(--red); }
.alert-banner.state-degraded .alert-text { color: var(--amber); }
.alert-banner.state-clear    .alert-text { color: var(--green); }

.alert-stale .alert-text::after { content: ' [STALE]'; color: var(--amber); font-size: 9px; }
.alert-tick { color: var(--muted-dim); font-size: 9px; font-family: monospace; white-space: nowrap; }

/* ── 4-Panel grid ── */
.panels {
  flex: 1; display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 8px; padding: 8px;
  overflow: hidden; min-height: 0;
}

/* ── Panel base ── */
.panel {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 6px; display: flex; flex-direction: column;
  overflow: hidden; min-height: 0;
}
.panel-header {
  padding: 7px 11px; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
  flex-shrink: 0;
}
.panel-title { color: var(--cream); font-size: 8px; letter-spacing: 2px; font-weight: 600; }
.panel-badge { font-size: 7px; padding: 2px 7px; border-radius: 10px; }
.badge-live { background: #87CEEB22; color: var(--blue);  border: 1px solid #87CEEB44; }
.badge-red  { background: #FF1A1A22; color: var(--red);   border: 1px solid #FF1A1A44; }
.badge-amber{ background: #f59e0b22; color: var(--amber); border: 1px solid #f59e0b44; }
.badge-muted{ background: #37415144; color: var(--muted); border: 1px solid #374151; }

/* ── P1: Live Feed ── */
.feed-body { flex: 1; display: flex; flex-direction: column; padding: 10px; gap: 8px; min-height: 0; }
.live-placeholder {
  flex: 1; background: #0d1117; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  flex-direction: column; gap: 6px; border: 1px dashed var(--border-dim);
}
.play-icon       { font-size: 28px; color: var(--cream); opacity: 0.3; }
.placeholder-label { color: var(--muted); font-size: 9px; letter-spacing: 1px; }
.placeholder-sub   { color: var(--muted-dim); font-size: 8px; }

.coord-row { display: flex; border-top: 1px solid var(--border); flex-shrink: 0; }
.coord-cell { flex: 1; padding: 7px 10px; border-right: 1px solid var(--border); }
.coord-cell:last-child { border-right: none; }
.coord-label { font-size: 8px; color: var(--muted); letter-spacing: 1px; margin-bottom: 2px; }
.coord-value { font-size: 16px; font-weight: 700; font-family: monospace; color: var(--blue); line-height: 1; }
.coord-value.seg-healthy  { color: var(--green); }
.coord-value.seg-degraded { color: var(--amber); }
.coord-value.seg-damaged  { color: var(--red);   }

/* ── P2: Segments ── */
.seg-body { flex: 1; display: flex; flex-direction: column; padding: 8px 11px 8px; min-height: 0; }
.seg-list { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.seg-row {
  flex: 1; display: flex; align-items: center; gap: 8px;
  border-bottom: 1px solid #111827; min-height: 0; padding: 3px 0;
}
.seg-row:last-child { border-bottom: none; }
.seg-row.active { background: rgba(255,26,26,0.06); border-radius: 4px; padding: 3px 6px; border: 1px solid #FF1A1A22; border-bottom: 1px solid #FF1A1A22; }
.seg-row.active-healthy  { background: rgba(173,235,179,0.06); border: 1px solid #ADEBB322; border-bottom: 1px solid #ADEBB322; }
.seg-row.active-degraded { background: rgba(245,158,11,0.06);  border: 1px solid #f59e0b22; border-bottom: 1px solid #f59e0b22; }

.seg-id { color: var(--muted); font-size: 9px; font-family: monospace; width: 42px; flex-shrink: 0; }
.seg-bar-wrap { flex: 1; background: #111827; border-radius: 3px; overflow: hidden; height: 55%; min-height: 12px; max-height: 28px; }
.seg-bar { height: 100%; border-radius: 3px; display: flex; align-items: center; padding: 0 8px; transition: width 0.4s ease; }
.seg-bar-label { font-size: 9px; font-weight: 600; white-space: nowrap; }
.seg-pct { font-size: 11px; font-weight: 700; font-family: monospace; width: 36px; text-align: right; flex-shrink: 0; }

.seg-legend { display: flex; gap: 14px; padding-top: 7px; border-top: 1px solid var(--border); flex-shrink: 0; margin-top: 5px; align-items: center; }
.leg { display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 500; }
.leg-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.train-pos-note { margin-left: auto; color: var(--muted-dim); font-size: 8px; font-style: italic; }

/* ── P3: Telemetry ── */
.telem-body { flex: 1; display: flex; flex-direction: column; padding: 8px 11px 8px; min-height: 0; gap: 6px; }
.chart-legend { display: flex; gap: 12px; }
.c-leg { font-size: 8px; display: flex; align-items: center; gap: 5px; }
.c-line { width: 18px; height: 2px; border-radius: 1px; }
.c-dashed { height: 0; border-top: 2px dashed; background: transparent !important; }

.chart-outer { flex: 1; position: relative; min-height: 0; }
.chart-outer canvas { position: absolute; top: 0; left: 0; width: 100% !important; height: 100% !important; }

.readouts { display: flex; border-top: 1px solid var(--border); flex-shrink: 0; }
.readout { flex: 1; text-align: center; padding: 6px 4px; border-right: 1px solid var(--border); }
.readout:last-child { border-right: none; }
.readout-val  { font-size: 18px; font-weight: 700; font-family: monospace; line-height: 1; }
.readout-unit { font-size: 9px; color: var(--muted); }
.readout-lbl  { font-size: 7px; color: var(--muted); letter-spacing: 1px; margin-top: 2px; }

/* ── P4: Orders ── */
.orders-body { flex: 1; display: flex; flex-direction: column; padding: 8px 11px 8px; min-height: 0; }
.orders-list { flex: 1; display: flex; flex-direction: column; gap: 6px; min-height: 0; }

.order-item {
  flex: 1; display: flex; align-items: center; gap: 10px;
  border-radius: 5px; padding: 0 12px; border: 1px solid transparent; min-height: 0;
  transition: border-color 0.2s;
}
.order-item.damaged  { background: #1f1515; border-color: #FF1A1A44; }
.order-item.degraded { background: #1f1a0f; border-color: #f59e0b44; }
.order-item.ok       { background: #141f14; border-color: #ADEBB344; opacity: 0.65; }
.order-item.error    { border-color: var(--red) !important; animation: flash-red 0.4s ease; }

@keyframes flash-red { 0%,100%{ border-color: #FF1A1A44; } 50%{ border-color: var(--red); } }

.order-rank { font-size: 18px; font-weight: 700; flex-shrink: 0; }
.order-info { flex: 1; min-width: 0; }
.order-name { font-size: 12px; color: var(--text); font-weight: 600; }
.order-sub  { font-size: 9px; color: var(--muted); margin-top: 3px; }
.order-actions { display: flex; flex-direction: column; gap: 5px; align-items: flex-end; flex-shrink: 0; }

.mat-select {
  background: var(--border-dim); color: var(--cream);
  border: 1px solid #4b5563; font-size: 9px;
  border-radius: 3px; padding: 4px 7px; cursor: pointer;
}
.complete-btn {
  background: #ADEBB322; color: var(--green);
  border: 1px solid #ADEBB355; font-size: 9px;
  border-radius: 3px; padding: 5px 12px; cursor: pointer; white-space: nowrap;
  transition: background 0.15s;
}
.complete-btn:hover    { background: #ADEBB344; }
.complete-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.orders-footer { font-size: 8px; color: var(--muted-dim); padding-top: 5px; border-top: 1px solid var(--border-dim); flex-shrink: 0; margin-top: 4px; }

/* ── Shared animations ── */
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
```

- [ ] **Step 3: Start server and open browser**

```bash
cd dashboard && npm start
```
Open `http://localhost:3000`. Expected: page loads with dark charcoal background, sidebar icons visible, 4 empty panel boxes, no JS errors in console.

- [ ] **Step 4: Commit**

```bash
git add dashboard/public/index.html dashboard/public/style.css
git commit -m "feat(dashboard): add HTML shell and CSS design system"
```

---

## Task 4: WebSocket Module

**Files:**
- Create: `dashboard/public/ws.js`

- [ ] **Step 1: Create `dashboard/public/ws.js`**

```js
import { store, pushHistory } from './state.js';

const WS_URL = 'ws://localhost:8000/ws';
const MAX_BACKOFF_MS = 30_000;

let ws = null;
let retryDelay = 1000;
let retryTimer = null;

function setIndicator(status, label) {
  const dot   = document.getElementById('ws-dot');
  const lbl   = document.getElementById('ws-label');
  dot.className = `ws-dot ${status}`;
  lbl.textContent = label;
}

function connect() {
  setIndicator('reconnecting', 'Connecting…');
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    retryDelay = 1000;
    setIndicator('connected', 'Connected');
  };

  ws.onmessage = (event) => {
    let state;
    try { state = JSON.parse(event.data); } catch { return; }
    store.latest = state;
    pushHistory(state);
    document.dispatchEvent(new CustomEvent('twinstate', { detail: state }));
  };

  ws.onclose = () => {
    setIndicator('reconnecting', `Retry in ${Math.round(retryDelay / 1000)}s…`);
    scheduleReconnect();
  };

  ws.onerror = () => {
    ws.close();
  };
}

function scheduleReconnect() {
  clearTimeout(retryTimer);
  retryTimer = setTimeout(() => {
    retryDelay = Math.min(retryDelay * 2, MAX_BACKOFF_MS);
    connect();
  }, retryDelay);
}

// Export report: download latest TwinState as JSON
document.getElementById('export-btn').addEventListener('click', (e) => {
  e.preventDefault();
  if (!store.latest) return;
  const blob = new Blob([JSON.stringify(store.latest, null, 2)], { type: 'application/json' });
  const a = Object.assign(document.createElement('a'), {
    href: URL.createObjectURL(blob),
    download: `twin-state-tick-${store.latest.tick}.json`,
  });
  a.click();
});

connect();
```

- [ ] **Step 2: Verify in browser**

With FastAPI running (`uvicorn api.app:app --port 8000`), open `http://localhost:3000`. Expected:
- Sidebar WS dot turns green
- `ws-label` reads "Connected"
- Browser console shows no errors
- `store.latest` is populated (check: `import('./state.js').then(m => console.log(m.store.latest))` in console)

Without FastAPI running, expected: dot stays amber, label shows "Retry in Xs…"

- [ ] **Step 3: Commit**

```bash
git add dashboard/public/ws.js
git commit -m "feat(dashboard): add WebSocket module with auto-reconnect"
```

---

## Task 5: Alert Banner

**Files:**
- Modify: `dashboard/public/ws.js` (add alert banner update logic after `connect()` call)

- [ ] **Step 1: Add alert banner updater to `ws.js`**

Add this function and event listener before the `connect()` call at the bottom of `ws.js`:

```js
function updateAlertBanner(state) {
  const banner = document.getElementById('alert-banner');
  const text   = document.getElementById('alert-text');
  const tick   = document.getElementById('alert-tick');

  const alert = (state.alert || '').toUpperCase();
  banner.className = 'alert-banner';

  if (alert.startsWith('DANGER'))  banner.classList.add('state-damaged');
  else if (alert.startsWith('WARNING')) banner.classList.add('state-degraded');
  else banner.classList.add('state-clear');

  text.textContent = state.alert || 'All clear.';
  tick.textContent = `TICK #${state.tick} · ${new Date(state.timestamp).toLocaleTimeString()}`;
}

document.addEventListener('twinstate', (e) => updateAlertBanner(e.detail));
```

- [ ] **Step 2: Verify in browser**

With FastAPI running, open `http://localhost:3000`. Expected:
- Banner text shows the backend `alert` string (e.g., "CLEAR" → green; "WARNING…" → amber; "DANGER…" → red)
- Tick number increments every second

- [ ] **Step 3: Commit**

```bash
git add dashboard/public/ws.js
git commit -m "feat(dashboard): wire alert banner to WebSocket state"
```

---

## Task 6: Live Feed Panel

**Files:**
- Modify: `dashboard/public/ws.js` (add feed panel updater)

- [ ] **Step 1: Add live feed updater to `ws.js`**

Add after the alert banner updater code:

```js
const SEG_STATE_CLASS = ['seg-healthy', 'seg-degraded', 'seg-damaged'];

function updateFeedPanel(state) {
  const segEl  = document.getElementById('coord-seg');
  const latEl  = document.getElementById('coord-lat');
  const longEl = document.getElementById('coord-long');

  // Static CMU Pittsburgh coords — swap for live GPS when available
  latEl.textContent  = '40.4427° N';
  longEl.textContent = '79.9432° W';

  const activeSeg = state.train_segment;
  const segState  = state.segments?.[activeSeg]?.map_state ?? 0;

  segEl.textContent = `SEG ${activeSeg}`;
  segEl.className   = `coord-value ${SEG_STATE_CLASS[segState]}`;
}

document.addEventListener('twinstate', (e) => updateFeedPanel(e.detail));
```

- [ ] **Step 2: Verify in browser**

Expected: "ACTIVE SEGMENT" cell shows "SEG N" in the correct state color (green/amber/red) matching the segment's MAP state.

- [ ] **Step 3: Commit**

```bash
git add dashboard/public/ws.js
git commit -m "feat(dashboard): wire live feed panel coords and active segment"
```

---

## Task 7: Segment Classification Panel

**Files:**
- Create: `dashboard/public/segments.js`

- [ ] **Step 1: Create `dashboard/public/segments.js`**

```js
import { store } from './state.js';

const STATE_COLORS = ['#ADEBB3', '#f59e0b', '#FF1A1A'];
const STATE_NAMES  = ['Healthy', 'Degraded', 'Damaged'];
const TEXT_COLORS  = ['#0d1117', '#0d1117', '#ffffff'];
const ACTIVE_CLASSES = ['active-healthy', 'active-degraded', 'active'];

function renderSegments(state) {
  const list   = document.getElementById('seg-list');
  const badge  = document.getElementById('seg-badge');
  const segs   = state.segments || [];
  const active = state.train_segment;

  // Badge: count damaged segments
  const damagedCount  = segs.filter(s => s.map_state === 2).length;
  const degradedCount = segs.filter(s => s.map_state === 1).length;

  if (damagedCount > 0) {
    badge.textContent = `${damagedCount} DAMAGED`;
    badge.className = 'panel-badge badge-red';
  } else if (degradedCount > 0) {
    badge.textContent = `${degradedCount} DEGRADED`;
    badge.className = 'panel-badge badge-amber';
  } else {
    badge.textContent = 'ALL CLEAR';
    badge.className = 'panel-badge badge-muted';
  }

  // Rows — rebuild DOM on each tick (panel is small, cost is negligible)
  list.innerHTML = '';
  segs.forEach(seg => {
    const isActive  = seg.id === active;
    const mapState  = seg.map_state;          // 0 | 1 | 2
    const pct       = Math.round(Math.max(...seg.belief) * 100);
    const color     = STATE_COLORS[mapState];
    const textColor = TEXT_COLORS[mapState];
    const label     = STATE_NAMES[mapState];

    const row = document.createElement('div');
    row.className = 'seg-row' + (isActive ? ` ${ACTIVE_CLASSES[mapState]}` : '');

    row.innerHTML = `
      <span class="seg-id">${isActive ? `SEG ${seg.id} ▶` : `SEG ${seg.id}`}</span>
      <div class="seg-bar-wrap">
        <div class="seg-bar" style="width:${pct}%;background:${color};">
          <span class="seg-bar-label" style="color:${textColor};">${label}</span>
        </div>
      </div>
      <span class="seg-pct" style="color:${color};">${pct}%</span>
    `;
    list.appendChild(row);
  });
}

document.addEventListener('twinstate', (e) => renderSegments(e.detail));
```

- [ ] **Step 2: Verify in browser**

Expected:
- All segment rows fill the panel height equally
- Active segment row has tinted background and `▶` suffix
- Bars animate width smoothly as beliefs update
- Badge updates to show count of damaged/degraded segments

- [ ] **Step 3: Commit**

```bash
git add dashboard/public/segments.js
git commit -m "feat(dashboard): add segment classification panel renderer"
```

---

## Task 8: Telemetry Chart

**Files:**
- Create: `dashboard/public/charts.js`

- [ ] **Step 1: Create `dashboard/public/charts.js`**

```js
import { store, deriveAcceleration, deriveMpcSmoothed } from './state.js';

const MAX_POINTS = 30;

// Build empty label array ["-30s", "-29s", ..., "now"]
function makeLabels() {
  return Array.from({ length: MAX_POINTS }, (_, i) => {
    const s = i - MAX_POINTS + 1;
    return s === 0 ? 'now' : `${s}s`;
  });
}

const ctx = document.getElementById('telem-chart').getContext('2d');

const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: makeLabels(),
    datasets: [
      {
        label: 'Velocity',
        data: Array(MAX_POINTS).fill(null),
        borderColor: '#87CEEB',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.3,
      },
      {
        label: 'Acceleration',
        data: Array(MAX_POINTS).fill(null),
        borderColor: '#FDFBD4',
        borderWidth: 1.5,
        borderDash: [5, 3],
        pointRadius: 0,
        tension: 0.3,
      },
      {
        label: 'MPC Speed',
        data: Array(MAX_POINTS).fill(null),
        borderColor: '#f59e0b',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.3,
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 0 },
    plugins: { legend: { display: false } },
    scales: {
      x: {
        ticks: { color: '#4b5563', font: { size: 9 }, maxRotation: 0 },
        grid:  { color: '#2d3748', drawBorder: false },
        title: {
          display: true,
          text: 'Time (last 30 ticks · 1 tick = 1s)',
          color: '#6b7280',
          font: { size: 8, style: 'italic' },
        },
      },
      y: {
        min: 0, max: 3.5,
        ticks: { color: '#4b5563', font: { size: 9 }, stepSize: 1 },
        grid:  { color: '#2d3748', drawBorder: false },
        title: {
          display: true,
          text: 'fps',
          color: '#6b7280',
          font: { size: 9 },
        },
      },
    },
  },
});

function updateChart(state) {
  const vel   = state.commanded_speed_fps;
  const accel = deriveAcceleration();
  const mpc   = deriveMpcSmoothed();

  // Shift data arrays: drop oldest, push newest
  const [velData, accelData, mpcData] = chart.data.datasets.map(d => d.data);
  velData.shift();   velData.push(vel);
  accelData.shift(); accelData.push(accel);
  mpcData.shift();   mpcData.push(mpc);

  chart.update('none'); // skip animation for live data

  // Update readout cells
  document.getElementById('rv-velocity').textContent = vel.toFixed(2);
  document.getElementById('rv-accel').textContent    = accel.toFixed(2);
  document.getElementById('rv-mpc').textContent      = mpc.toFixed(2);
}

document.addEventListener('twinstate', (e) => updateChart(e.detail));
```

- [ ] **Step 2: Verify in browser**

Expected:
- Chart fills the panel with correct Y-axis (0–3.5 fps), X-axis labels (−30s → now)
- Three lines animate as ticks arrive
- Readout cells below chart update each tick

- [ ] **Step 3: Commit**

```bash
git add dashboard/public/charts.js
git commit -m "feat(dashboard): add Chart.js telemetry panel"
```

---

## Task 9: Maintenance Order List

**Files:**
- Create: `dashboard/public/orders.js`

- [ ] **Step 1: Create `dashboard/public/orders.js`**

```js
import { store } from './state.js';

const API = 'http://localhost:8000';
const MATERIALS = ['Steel 3/8"', 'Aluminum 1/2"', 'Aluminum 3/8"'];

async function fetchOrders() {
  try {
    const res = await fetch(`${API}/work-orders`);
    if (!res.ok) return;
    const data = await res.json();
    store.workOrders = data.work_orders || [];
    renderOrders();
  } catch {
    // API unavailable — retain last known list silently
  }
}

function getSegmentBelief(segId) {
  if (!store.latest) return null;
  return store.latest.segments?.find(s => s.id === segId) ?? null;
}

function renderOrders() {
  const list  = document.getElementById('orders-list');
  const badge = document.getElementById('orders-badge');
  const orders = store.workOrders;

  // Only show OPEN orders; sort: damaged first (by confidence desc), then degraded
  const sorted = [...openOrders].sort((a, b) => {
    if (a.severity !== b.severity) return a.severity === 'DAMAGED' ? -1 : 1;
    return (b.confidence ?? 0) - (a.confidence ?? 0);
  });

  // Backend returns status as uppercase "OPEN" or "COMPLETED"
  const openOrders = orders.filter(o => o.status === 'OPEN');
  badge.textContent = openOrders.length > 0 ? `${openOrders.length} OPEN` : 'ALL CLEAR';
  badge.className   = openOrders.length > 0 ? 'panel-badge badge-red' : 'panel-badge badge-muted';

  list.innerHTML = '';

  if (openOrders.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'order-item ok';
    empty.style.justifyContent = 'center';
    empty.innerHTML = '<span style="color:#6b7280;font-size:11px;">No open work orders</span>';
    list.appendChild(empty);
    return;
  }

  sorted.forEach((order, idx) => {
    const liveSegData = getSegmentBelief(order.segment_id);
    const confidence  = liveSegData
      ? Math.round(Math.max(...liveSegData.belief) * 100)
      : Math.round((order.confidence ?? 0) * 100);
    const stateClass  = order.severity === 'DAMAGED' ? 'damaged' : 'degraded';
    const rankColor   = order.severity === 'DAMAGED' ? '#FF1A1A' : '#f59e0b';

    const item = document.createElement('div');
    item.className = `order-item ${stateClass}`;
    item.dataset.orderId = order.id;

    item.innerHTML = `
      <span class="order-rank" style="color:${rankColor};">#${idx + 1}</span>
      <div class="order-info">
        <div class="order-name">SEG ${order.segment_id} — ${order.severity[0] + order.severity.slice(1).toLowerCase()}</div>
        <div class="order-sub">Confidence ${confidence}% · ID: ${order.id}</div>
      </div>
      <div class="order-actions">
        <select class="mat-select">
          ${MATERIALS.map(m => `<option>${m}</option>`).join('')}
        </select>
        <button class="complete-btn" data-order-id="${order.id}">✓ Mark Complete</button>
      </div>
    `;

    item.querySelector('.complete-btn').addEventListener('click', () => completeOrder(order.id, item));
    list.appendChild(item);
  });
}

async function completeOrder(orderId, itemEl) {
  const btn = itemEl.querySelector('.complete-btn');
  btn.disabled = true;
  btn.textContent = 'Completing…';

  try {
    const res = await fetch(`${API}/work-orders/${orderId}/complete`, { method: 'POST' });
    if (!res.ok) throw new Error('API error');
    await fetchOrders(); // refresh list
  } catch {
    itemEl.classList.add('error');
    btn.disabled = false;
    btn.textContent = '✓ Mark Complete';
    setTimeout(() => itemEl.classList.remove('error'), 800);
  }
}

// Poll every 5s + refresh on each WebSocket tick
fetchOrders();
setInterval(fetchOrders, 5000);
document.addEventListener('twinstate', renderOrders);
```

- [ ] **Step 2: Verify in browser**

With FastAPI running, expected:
- Order list shows open work orders sorted by severity then confidence
- Each row has a material dropdown and Mark Complete button
- Clicking Mark Complete calls the API, row disappears on success
- On API error, button re-enables and row flashes red border

- [ ] **Step 3: Commit**

```bash
git add dashboard/public/orders.js
git commit -m "feat(dashboard): add maintenance order list with complete action"
```

---

## Task 10: Error Handling — Stale State

**Files:**
- Modify: `dashboard/public/ws.js` (add stale data detection)

- [ ] **Step 1: Add stale-state detection to `ws.js`**

Add this block after the `connect()` call at the bottom of `ws.js`:

```js
// Mark data as stale if no tick received for 10 seconds
let staleTimer = null;

function resetStaleTimer() {
  clearTimeout(staleTimer);
  const banner = document.getElementById('alert-banner');
  banner.classList.remove('alert-stale');
  staleTimer = setTimeout(() => {
    banner.classList.add('alert-stale');
  }, 10_000);
}

document.addEventListener('twinstate', resetStaleTimer);
```

- [ ] **Step 2: Verify stale behaviour**

Stop the FastAPI backend while the dashboard is open. Expected within ~10 s:
- Alert text gains "[STALE]" suffix (styled amber via `alert-stale` CSS class)
- WS indicator dot turns amber and shows "Retry in Xs…"
- Panels retain last known data

- [ ] **Step 3: Commit**

```bash
git add dashboard/public/ws.js
git commit -m "feat(dashboard): add stale-data detection and STALE banner label"
```

---

## Task 11: Final Integration Smoke Test

- [ ] **Step 1: Start FastAPI backend**

From repo root:
```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```
Expected output includes: `Starting OODA loop (tick interval: 1.0s …)`

- [ ] **Step 2: Start dashboard**

```bash
cd dashboard && npm start
```

- [ ] **Step 3: Open `http://localhost:3000` and verify all panels**

Check each of the following:

| Check | Expected |
|---|---|
| WS dot | Green "Connected" |
| Alert banner | Shows backend `alert` string, correct color |
| Live Feed | LAT/LONG populated, ACTIVE SEGMENT changes color with state |
| Segments | All segments render, fill panel, active segment highlighted |
| Telemetry chart | Three lines animate, X/Y axis labels visible, not clipped |
| Telemetry readouts | Velocity / Accel / MPC Speed update each tick |
| Order list | Shows work orders from `/work-orders` |
| Sidebar hover | Expands to 150px with labels on hover |
| Export button | Downloads JSON file of latest TwinState |

- [ ] **Step 4: Run unit tests**

```bash
cd dashboard && npm test
```
Expected: all 6 tests PASS.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat(dashboard): complete live rail track dashboard"
```

---

## Connecting the UE5 Stream (for teammate)

When the Unreal Engine stream is ready, open `dashboard/public/index.html` and replace:

```html
<div class="live-placeholder">
  <div class="play-icon">▶</div>
  <span class="placeholder-label">UNREAL ENGINE FEED</span>
  <span class="placeholder-sub">Connect UE5 stream URL here</span>
</div>
```

with:

```html
<iframe src="YOUR_UE5_STREAM_URL" style="flex:1;border:none;border-radius:4px;"></iframe>
```

No other files need to change.
