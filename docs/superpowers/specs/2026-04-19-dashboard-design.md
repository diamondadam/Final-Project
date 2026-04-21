# Rail Track Digital Twin — Live Dashboard Design Spec

**Date:** 2026-04-19  
**Stack:** Node.js (Express) + Vanilla JS + Chart.js (CDN)  
**Backend:** FastAPI at `localhost:8000` (existing, untouched)

---

## 1. Architecture

```
dashboard/                    ← self-contained, delete to revert
  server.js                   ← Express, serves public/, port 3000
  package.json                ← single dependency: express
  public/
    index.html                ← shell: sidebar, alert banner, 4-panel grid
    style.css                 ← charcoal theme, sidebar hover, panel layout
    ws.js                     ← WebSocket connection + auto-reconnect
    state.js                  ← shared TwinState store, 30-tick rolling history
    charts.js                 ← Chart.js line graph (velocity, accel, MPC speed)
    segments.js               ← segment classification panel renderer
    orders.js                 ← work order panel: fetch, material select, complete
```

**Data flow:**
- Express serves static files only — no proxy, no WebSocket logic server-side
- Browser opens `ws://localhost:8000/ws` directly (native WebSocket API)
- `ws.js` dispatches a custom `twinstate` DOM event on each tick; all other modules listen for it
- `orders.js` polls `GET http://localhost:8000/work-orders` every 5 seconds and on every `twinstate` event
- `POST http://localhost:8000/work-orders/{id}/complete` fired when user clicks Mark Complete
- FastAPI backend and `data/` directory are never modified

---

## 2. Visual Design

| Token | Value | Used for |
|---|---|---|
| Background | `#111827` | App background |
| Panel surface | `#1f2937` | All 4 panel backgrounds |
| Sidebar | `#1a2332` | Sidebar background |
| Border | `#374151` | Panel borders, dividers |
| Cream | `#FDFBD4` | Panel headings, acceleration line, labels |
| Sky Blue | `#87CEEB` | Velocity line, coordinate readouts |
| Soft Green | `#ADEBB3` | Healthy state, complete button |
| Amber | `#f59e0b` | Degraded state, MPC speed line |
| Red | `#FF1A1A` | Damaged state, critical alerts |
| Muted text | `#6b7280` | Secondary labels, axis text |

---

## 3. Layout

Full-viewport 2×2 CSS grid (no scrolling). All panels use `flex:1` internally so content scales to fill available height regardless of data count.

```
┌─────────┬──────────────────────────────────────────┐
│         │  Alert Banner (persistent, full width)    │
│Sidebar  ├──────────────────┬───────────────────────┤
│(icon,   │  Live Feed       │  Track Segment        │
│hover-   │  UE5 placeholder │  Classification       │
│expand)  │  LAT/LONG/SEG    ├───────────────────────┤
│         │  readouts        │  Maintenance          │
│         ├──────────────────┤  Order List           │
│         │  Real-Time       │                       │
│         │  Telemetry       │                       │
└─────────┴──────────────────┴───────────────────────┘
```

---

## 4. Panel Specifications

### 4a. Alert Banner
- Full-width strip above the 4 panels, always visible
- Source: `state.alert` (string from WebSocket)
- Damaged/degraded: dark red background `#1f1515`, red border, pulsing dot, `#FF1A1A` text
- Clear: dark green background, `#ADEBB3` text, static dot
- Right side: `TICK #{state.tick} · {state.timestamp}` in muted monospace

### 4b. Live Feed (top-left)
- Main area: dark placeholder `#0d1117` with centered UE5 play icon — teammate replaces `<div>` with `<iframe>` or `<video>` when UE stream is ready
- Bottom strip: three equal cells separated by vertical dividers
  - **LAT** — `16px` monospace, `#87CEEB`
  - **LONG** — `16px` monospace, `#87CEEB`
  - **ACTIVE SEGMENT** — `16px` monospace, color matches segment state (`#ADEBB3` / `#f59e0b` / `#FF1A1A`)
- Source: `state.train_segment` (index → segment state color lookup)
- LAT/LONG: static CMU Pittsburgh coords for now; swap for live GPS when available

### 4c. Track Segment Classification (top-right)
- One row per segment; rows share panel height equally via `flex:1` — 4 segments fill the panel, 6 segments shrink proportionally
- Each row: `SEG N` label → horizontal bar (color = MAP state, width = `max(belief) * 100%`) → confidence percentage
- Active segment (train position = `state.train_segment`) highlighted with tinted row background and `▶` suffix on ID
- Bar colors: `#ADEBB3` Healthy · `#f59e0b` Degraded · `#FF1A1A` Damaged
- Label text inside bar: "Healthy" / "Degraded" / "Damaged"
- Source: `state.segments[i].map_state_name`, `max(state.segments[i].belief)`
- Legend: `11px` text, `10px` dots — Healthy · Degraded · Damaged + "▶ = train position" right-aligned

### 4d. Real-Time Telemetry (bottom-left)
- Chart.js line chart, type `line`, fills panel via `flex:1` container
- **X-axis:** last 30 ticks, labeled `−30s → now` (1 tick = 1 s), title: "Time (last 30 ticks · 1 tick = 1s)"
- **Y-axis:** 0.0 – 3.0 fps, labeled at 0.0 / 1.0 / 2.0 / 3.0, title: "fps" (rotated)
- Dashed vertical grid lines at 6s intervals; solid horizontal grid lines at each Y label
- Three lines sourced from WebSocket per tick (all derived from `commanded_speed_fps` — the only live speed value the backend streams):
  - **Velocity** `#87CEEB` solid — `commanded_speed_fps` raw value each tick
  - **Acceleration** `#FDFBD4` dashed — `(speed[t] - speed[t-1]) / 1.0` fps² (1 s tick interval)
  - **MPC Speed** `#f59e0b` solid — 3-tick rolling average of `commanded_speed_fps` (smoothed commanded speed, visually distinct from raw velocity)
- Below chart: three equal readout cells (VELOCITY · ACCELERATION · MPC SPEED) showing current values in large `18px` monospace

### 4e. Maintenance Order List (bottom-right)
- Rows share panel height equally via `flex:1` — content scales to fill box
- **Data source:** `GET /work-orders` polled every 5 s; belief confidence from live WebSocket
- **Sort order:** Damaged first (by confidence desc), then Degraded (by confidence desc), then Healthy/no-action row
- Each open work order row:
  - Rank badge (`#1`, `#2`, …) in state color
  - Segment name + state label
  - Confidence % + work order ID
  - Material dropdown: Steel 3/8" · Aluminum 1/2" · Aluminum 3/8"
  - "✓ Mark Complete" button → `POST /work-orders/{id}/complete` → repairs segment in simulation → row removed on next poll
- Healthy row (no open orders): muted, no dropdown, no button, reads "Monitoring active · No action required"
- Footer: "Auto-sorted by damage confidence · Marking complete repairs segment in simulation"

---

## 5. Sidebar

- Width: `44px` collapsed, `150px` expanded on hover (`transition: width 0.22s ease`)
- Icon-only when collapsed; icon + label when expanded
- Items: ⬡ Live HUD (active) · ⟁ Analytics · ⚙ Maintenance · ↗ Export Report
- Analytics and Maintenance: placeholder pages (empty panel with "Coming soon") — no backend calls
- Export Report: triggers `window.print()` or downloads a JSON snapshot of the last TwinState

---

## 6. WebSocket Handling (`ws.js`)

- Connects to `ws://localhost:8000/ws` on page load
- On message: parses JSON → stores in `state.js` → dispatches `new CustomEvent('twinstate', { detail: state })` on `document`
- Auto-reconnect: exponential backoff starting at 1 s, cap at 30 s
- Connection status indicator in sidebar footer: green dot (connected) / amber dot (reconnecting)

---

## 7. State Management (`state.js`)

```js
// Exported mutable store — all modules import this
export const store = {
  latest: null,          // most recent TwinState object
  history: [],           // last 30 TwinState objects (for chart)
  workOrders: [],        // cached from GET /work-orders
};
```

- `history` capped at 30 entries; oldest dropped when full
- No framework, no reactivity — modules pull from `store` on each `twinstate` event

---

## 8. Error Handling

- **WebSocket disconnected:** alert banner switches to amber "Reconnecting…" state; panels show last known data with a "STALE" watermark
- **Work order API failure:** console warning only; panel retains last successful fetch; no user-facing error (avoids alarm fatigue)
- **`/work-orders/{id}/complete` failure:** button re-enables, brief red border flash on the row
- **No data yet (startup):** panels show skeleton placeholders until first WebSocket message arrives

---

## 9. Running the Dashboard

```bash
# 1. Start FastAPI backend (required first)
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

# 2. Start dashboard
cd dashboard
npm install
npm start          # Express on http://localhost:3000
```

Unreal Engine teammate: replace the placeholder `<div class="live-placeholder">` in `index.html` with an `<iframe src="...">` or `<video>` tag pointing at the UE stream. No other files need to change.
