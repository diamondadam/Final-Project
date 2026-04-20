# Analytics & Maintenance Pages — Design Spec

**Date:** 2026-04-20
**Project:** Rail Track Digital Twin (CMU Final Project)
**Status:** Approved

---

## Overview

Add two new pages to the existing React dashboard:

1. **Analytics** (`/analytics`) — deeper train telemetry and MPC controller performance, split equally into two labeled sections with six total panels.
2. **Maintenance** (`/maintenance`) — a single hub replacing `/work-orders` that combines work order management, HITL segment overrides, and a repair history log.

The existing `/work-orders` route will be replaced by `/maintenance`. The NavBar gains two new links: **Analytics** and **Maintenance** (Work Orders link is removed).

---

## Page 1: Analytics (`/analytics`)

### Layout

Option B: **Featured + Companion** layout, repeated for each section.

Each section has:
- One wide featured panel on the left (richer chart, taller)
- Two stacked companion panels on the right (equal height, narrower)

All data is sourced from the existing Zustand store (`twinStore`). The store already buffers the last 60 ticks of speed + timestamp. History buffers for the additional series (alert state, train position, per-segment belief snapshots) will be added to the store.

### Section 1 — Train Telemetry

**Featured: Speed + Alert Band Chart**
- X-axis: tick number (last 60 ticks)
- Y-axis: speed in fps (0–3.5)
- Line: `commanded_speed_fps` (emerald, stroke-width 2)
- Background bands: colored by alert state per tick — green for CLEAR, amber for WARNING, red for DANGER
- Reference dashed line at `v_max = 3.0 fps`
- Recharts `ComposedChart` with `ReferenceArea` per alert-state run + `Line`

**Companion 1: Alert State Breakdown**
- Three stat tiles side by side: CLEAR / WARNING / DANGER
- Each shows the percentage of buffered ticks spent in that state
- Colors: emerald / amber / red with matching background tint
- Updates live on every tick

**Companion 2: Train Position Timeline**
- Step chart: X = tick, Y = segment index (0–N)
- Line: `train_segment` per tick (indigo/violet)
- Y-axis labels: seg0, seg1, … segN
- Makes it easy to correlate which segment caused an alert

### Section 2 — MPC Controller Performance

**Featured: Commanded vs. v_safe Target Speed**
- X-axis: tick number (last 60 ticks)
- Two lines:
  - `v_safe` target (amber dashed) — computed from the MAP state of the current segment each tick: Healthy → 3.0, Degraded → 1.8, Damaged → 0.9
  - `commanded_speed_fps` (emerald solid) — actual MPC output after rate-limiting QP
- The gap between lines visualises the smoothing effect of the QP solver's rate constraint
- Legend inline

**Companion 1: Segment Health Heatmap**
- Grid: rows = segments, columns = last N ticks (up to 60)
- Each cell colored by `map_state`: green (Healthy), amber (Degraded), red (Damaged)
- Row labels: seg0 … segN
- Built with a CSS grid of divs (not Recharts) for pixel-precise coloring
- Updates each tick by appending a new column and dropping the oldest

**Companion 2: Belief Convergence (per segment)**
- Small multiples: one mini bar chart per segment
- Each mini shows current `belief[0]` (H), `belief[1]` (D), `belief[2]` (X) as vertical bars
- Colors: emerald / amber / red
- Bars animate height transitions each tick (Tailwind `transition-all duration-500`)
- Segment label above each mini

### Store Changes

Add to `twinStore`:
```ts
alertHistory: Array<{ tick: number; alert: string }>          // last 60
positionHistory: Array<{ tick: number; segment: number }>     // last 60
segmentBeliefHistory: Array<{                                  // last 60, all segments
  tick: number
  beliefs: Array<[number, number, number]>
}>
```

The existing `tickHistory` (speed + timestamp) already covers Sections 1 featured and Section 2 featured. The three new arrays are populated in the same `setState` reducer, capped at 60 entries.

### No Backend Changes Required

All analytics data is derivable from the existing WebSocket stream. `v_safe` is computed in the frontend: `V_SAFE = { 0: 3.0, 1: 1.8, 2: 0.9 }[map_state_of_current_segment]`.

---

## Page 2: Maintenance (`/maintenance`)

### Layout

Three vertical regions on one scrollable page:

1. **Action bar** (top) — page title, summary stats, Reset All Beliefs button
2. **Main grid** (two columns) — Work Orders list (left, wider) + Segment Override panel (right)
3. **Repair History log** (full width, below)

### Action Bar

- Left: "Maintenance" heading + subtitle "Work orders · segment overrides · repair log"
- Right: two inline stats ("N open WOs", "N repairs") + **Reset All Beliefs** button
- Reset All calls `POST /reset`, then `refreshWorkOrders()` and clears `repairLog` in store
- Stats derived from store: `workOrders.filter(w => w.status === 'OPEN').length` and `repairLog.length`

### Work Orders List (left column)

Replaces the existing `WorkOrderPanel`. Functionally identical but with one addition:
- Completing a work order appends an entry to the local `repairLog` in the store before calling `POST /work-orders/{id}/complete`
- Open orders appear first (red/amber dot), completed orders below a divider at 50% opacity

### Segment Override Panel (right column, HITL)

- One control card per segment (2-column sub-grid)
- Each card shows: segment ID, current `map_state_name` (colored), and three buttons: **H** / **D** / **X**
- Active state button is outlined/highlighted
- Clicking a button calls `POST /correction { segment_id, state }` and appends to `repairLog`
- State data comes from `twinStore.state.segments`

### Repair History Log (full width)

- Chronological list of repair events, newest first
- Two event types:
  - **REPAIRED** (green badge) — from work order completion; shows segment and timestamp
  - **OVERRIDE** (indigo badge) — from HITL correction; shows segment, forced state, and timestamp
- `repairLog` lives in Zustand store (in-memory, cleared on page refresh / Reset All)
- Not persisted to backend (server has no history endpoint; work orders are already in-memory)

### Store Changes

Add to `twinStore`:
```ts
repairLog: Array<{
  timestamp: string
  type: 'REPAIRED' | 'OVERRIDE'
  segment_id: number
  detail: string         // e.g. "forced → Healthy" or "work order completed"
}>
```

### API Calls Used

| Action | Endpoint |
|---|---|
| Complete work order | `POST /api/work-orders/{id}/complete` |
| HITL segment override | `POST /api/correction { segment_id, state }` |
| Reset all beliefs | `POST /api/reset` |
| Refresh work orders | `GET /api/work-orders` |

All already implemented in `api/app.py`. No backend changes required.

---

## Navigation Changes

Update `NavBar.tsx`:
- Add **Analytics** link → `/analytics`
- Rename **Work Orders** link to **Maintenance** → `/maintenance`
- Open work order badge count stays on the Maintenance link

Update `App.tsx` routes:
```tsx
<Route path="/analytics"    element={<AnalyticsPage />} />
<Route path="/maintenance"  element={<MaintenancePage />} />
// remove: <Route path="/work-orders" ... />
```

---

## New Files

```
frontend/src/pages/AnalyticsPage.tsx
frontend/src/pages/MaintenancePage.tsx
frontend/src/components/analytics/
  SpeedAlertChart.tsx          ← featured, Section 1
  AlertBreakdown.tsx           ← companion, Section 1
  PositionTimeline.tsx         ← companion, Section 1
  CommandedVsTargetChart.tsx   ← featured, Section 2
  HealthHeatmap.tsx            ← companion, Section 2
  BeliefConvergence.tsx        ← companion, Section 2
frontend/src/components/maintenance/
  WorkOrderList.tsx            ← extracted + enhanced from WorkOrderPanel
  SegmentOverridePanel.tsx     ← new HITL controls
  RepairHistoryLog.tsx         ← new log component
```

`WorkOrderPanel.tsx` is replaced by `WorkOrderList.tsx` (same logic, imported by `MaintenancePage`).

---

## Color Scheme

All new components must use the existing dashboard palette exactly — no new colors introduced.

**Page & panel backgrounds**
- Page background: `bg-[#0f1117]`
- Panel background: `bg-white/[0.03]` (cards) or `bg-white/5` (active/hover)
- Panel border: `border-white/10`
- Active/highlighted border: `border-white/40`

**Text**
- Primary: `text-white`
- Secondary: `text-zinc-400`
- Muted / labels: `text-zinc-500`
- Section headers: `text-xs font-semibold tracking-widest text-zinc-500 uppercase`

**Health state colors** — use `CLASS_COLORS` from `frontend/src/types.ts`
| State | Tailwind text | Tailwind bg | Hex |
|---|---|---|---|
| Healthy | `text-emerald-400` | `bg-emerald-500` | `#10b981` |
| Degraded | `text-amber-400` | `bg-amber-500` | `#f59e0b` |
| Damaged | `text-red-400` | `bg-red-500` | `#ef4444` |

**Chart colors**
- Commanded speed line: `#34d399` (emerald-400)
- v_safe target line (dashed): `#f59e0b` (amber-400)
- Train position step line: `#818cf8` (indigo-400)
- Alert band fills (low opacity): `#10b98114` CLEAR, `#f59e0b14` WARNING, `#ef444414` DANGER
- Axis ticks & gridlines: `#52525b` (zinc-600)
- Chart tooltip: `background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8`
- Reference lines (dashed): `#3f3f46`

**Badges / tags**
- REPAIRED: `bg-emerald-500/20 text-emerald-400 ring-emerald-500/30`
- OVERRIDE: `bg-indigo-500/20 text-indigo-400 ring-indigo-500/30`
- DAMAGED work order: `bg-red-500/20 text-red-400 ring-red-500/30`
- DEGRADED work order: `bg-amber-500/20 text-amber-400 ring-amber-500/30`

**Buttons**
- Complete (work order): `bg-emerald-600 hover:bg-emerald-500 text-white`
- Reset All (destructive): `bg-red-500/20 text-red-400 ring-1 ring-red-500/30 hover:bg-red-500/30`
- H override button: `bg-emerald-500/20 text-emerald-400`
- D override button: `bg-amber-500/20 text-amber-400`
- X override button: `bg-red-500/20 text-red-400`
- Active override button adds `ring-1 ring-current`

---

## Constraints

- All chart data comes from the Zustand store — no new API endpoints
- `v_safe` target is computed client-side using `V_SAFE_MULT = { 0: 3.0, 1: 1.8, 2: 0.9 }`
- Health heatmap uses CSS grid divs, not Recharts (better cell-level color control)
- Belief convergence mini-charts use plain divs with Tailwind transitions (no Recharts overhead for 5 tiny bar charts)
- All new charts use `isAnimationActive={false}` on Recharts lines (consistent with existing Dashboard)
- `repairLog` is in-memory only — no backend persistence needed
