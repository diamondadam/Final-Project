# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CMU final project: a **digital twin** for rail track health monitoring. Vibration signals from two accelerometers (g4, g5) on a moving train are classified into Healthy / Degraded / Damaged track states, then streamed in real time to an Unreal Engine visualization via WebSocket.

## Running the Code

All commands are run from the repo root unless noted.

```bash
# 1. Train classifiers (required before running the API — outputs model_knn.joblib)
python classifier/train_classifiers.py

# 2. Start the FastAPI server (primary entry point for the live digital twin)
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

# 3. Start the React dashboard (cd frontend first)
cd frontend && npm install && npm run dev   # dev server at http://localhost:5173
cd frontend && npm run build               # production build
cd frontend && npm run lint                # ESLint
cd frontend && npm run test                # Vitest (run once)
cd frontend && npm run test:watch          # Vitest (watch mode)
cd frontend && npx vitest run src/store/twinStore.test.ts          # single test file
cd frontend && npx vitest run src/components/analytics/utils.test.ts

# Legacy dashboard (Express static server, no install needed)
node dashboard/server.js                   # serves dashboard/public/ at http://localhost:3000

# Standalone batch scripts (legacy / demo only)
python classifier/track_health_classifier.py   # old Random Forest pipeline
python classifier/simulation.py                # OODA loop batch run
python classifier/visualization_3d.py          # 3D animated GIF (slow)
python classifier/diagnose_frequencies.py      # PSD + ANOVA frequency analysis
python week10example/train_stop_decision.py    # safety-stop decision demo
```

**Install Python dependencies:**

```bash
pip install -r requirements.txt
pip install joblib   # missing from requirements.txt — needed by the classifier
```

**API environment variables:**

| Variable | Default | Purpose |
|---|---|---|
| `TRACK_CONFIG` | `"0,1,2,1,0"` | Comma-separated health states per segment |
| `SIMULATOR_TYPE` | `"csv"` | `"csv"` (real runs) or `"synthetic"` (parametric Gaussian) |
| `TICK_INTERVAL_S` | `"1.0"` | Seconds between OODA ticks |
| `WORK_ORDER_API_URL` | unset | External maintenance API base URL (omit to disable) |
| `WORK_ORDER_API_KEY` | unset | Bearer token for work order API |

## Architecture

> **Read [ARCHITECTURE.md](ARCHITECTURE.md) before making structural changes.** It is the canonical reference for module responsibilities, data flow, WebSocket contract, and design decisions.

### Module Map

```
data/TrainRuns/          ← read-only raw CSV sensor runs
classifier/
  train_classifiers.py   ← trains KNN + GBM pipelines, writes classifier/output/
  uncertainty.py         ← Monte Carlo uncertainty propagation via delta method
  output/
    model_knn.joblib     ← sklearn Pipeline (StandardScaler + KNN) — used by live twin
    model_gbm.joblib     ← sklearn Pipeline (StandardScaler + GBM)
sensors/
  base.py                ← BaseSensorSimulator abstract interface
  csv_simulator.py       ← replays real CSV runs via DataPool
  synthetic_simulator.py ← parametric Gaussian readings (no data/ required)
controller/
  bayesian.py            ← BayesianSegmentTracker (one per segment)
  mpc.py                 ← PyomoMPCController (receding-horizon QP via IPOPT)
digital_twin_v2/
  orchestrator.py        ← DigitalTwin — drives the OODA loop each tick
  state.py               ← TwinState / SegmentState dataclasses
  constants.py           ← CLASS_NAMES = ["Healthy", "Degraded", "Damaged"]
api/
  app.py                 ← FastAPI server, lifespan startup, REST + WS endpoints
  websocket.py           ← WebSocketManager — fan-out to all Unreal clients
  models.py              ← Pydantic request/response schemas
integrations/
  work_orders.py         ← WorkOrderClient + WorkOrderStore (in-memory)
frontend/                ← React 19 + TypeScript + Vite + Tailwind v4 + Recharts dashboard
  src/
    types.ts             ← shared TypeScript interfaces (TwinState, WorkOrder, CLASS_COLORS)
    store/twinStore.ts   ← Zustand store; holds live state, tick/alert/position/belief history (last 60), work orders, repairLog
    hooks/useTwinWebSocket.ts ← connects ws://<host>/ws, auto-reconnects every 2 s
    components/
      NavBar.tsx          ← top-level navigation bar
      TrackDashboard.tsx, SegmentCard.tsx, AlertBanner.tsx, TrackConfigurator.tsx, WorkOrderPanel.tsx
      analytics/          ← SpeedAlertChart, AlertBreakdown, PositionTimeline, CommandedVsTargetChart, HealthHeatmap, BeliefConvergence + utils.ts
      maintenance/        ← WorkOrderList, SegmentOverridePanel, RepairHistoryLog
    pages/
      AnalyticsPage.tsx, MaintenancePage.tsx, WorkOrdersPage.tsx
  vite.config.ts         ← proxies /api → http://localhost:8000, /ws → ws://localhost:8000
dashboard/               ← legacy Express static server (dashboard/public/); superseded by frontend/
```

### OODA Loop (one tick = one segment observation)

1. **Observe** — `simulator.get_reading(seg, true_state)` → 33-feature vector
2. **Orient** — `model_knn.predict_proba()` → class probabilities (reordered to `[Healthy, Degraded, Damaged]` since sklearn returns alphabetical order `[Damaged, Degraded, Healthy]`)
3. **Decide** — `BayesianSegmentTracker.update(proba)` → `PyomoMPCController.compute_speed()`
4. **Act** — emit `TwinState`, broadcast JSON to all WebSocket clients, fire work order on MAP state transition to Degraded/Damaged

### API Endpoints

```
GET  /health                          Liveness check
GET  /state                           Latest TwinState snapshot
GET  /config                          Current track config
POST /config                          Hot-swap track configuration
POST /correction  {segment_id, state} HITL override (collapses belief)
POST /reset                           Reset all Bayesian trackers
GET  /work-orders                     List all work orders (in-memory)
POST /work-orders/{id}/complete       Complete a work order + repair segment
WS   /ws                              Push TwinStateResponse JSON each tick
```

Unreal Engine connects to `ws://localhost:8000/ws`.

### Classifier Details

- **Active model:** KNN (`k=7, metric=euclidean, weights=distance`) — preferred for safety because confidence is well-calibrated (high-confidence predictions are always correct in evaluation). Test balanced accuracy: **0.964**.
- **Features:** 33 per run — 15 per channel (g4, g5) + 3 cross-sensor (`cross_corr`, `rms_ratio`, `diff_rms`). All computed from the CRUISE phase only.
- **Data:** 270 labeled runs (81 Healthy natural + 81 Degraded augmented + 81 Damaged augmented + 27 natural Degraded/Damaged). Train/test split uses `GroupShuffleSplit` by `source_run_id` to prevent augmented-copy leakage.
- **GBM** is also trained and saved but is overconfident — do not use its confidence scores for safety decisions.

### Data Layout

```
data/TrainRuns/
  Steel_3_8_in/          label "Healthy"
  Aluminum_1_2_in/       label "Degraded"
  Aluminum_3_8_in/       label "Damaged"
    <condition_dir>/<run_dir>/
      arduino_motion_raw.csv   ~10 Hz: time_ms, phase, pos_ft, vel_fps
      daq_sensors_1000hz.csv   1000 Hz: time_ms, g4, g5

classifier/processed/    ETL output (labeled, grouped by source_run_id)
```

Do not write to `data/`.

### Key Constants

| File | Constant | Default | Effect |
|---|---|---|---|
| `digital_twin_v2/orchestrator.py` | `V_MAX_FPS` | `3.0` | Max commanded speed |
| `digital_twin_v2/orchestrator.py` | `V_MIN_FPS` | `0.5` | Min commanded speed |
| `digital_twin_v2/orchestrator.py` | `MPC_HORIZON` | `3` | Look-ahead segments |
| `api/app.py` env | `TICK_INTERVAL_S` | `1.0` | Seconds per OODA tick |

### Work Order Logic

Work orders are created only on MAP state *transitions* to Degraded or Damaged (not every tick). Transitions back to Healthy do not auto-close. `POST /work-orders/{id}/complete` closes the order and calls `repair_segment()` — which sets `track_config[seg] = 0` and resets the tracker so the simulator stops returning degraded readings.

`WorkOrderStore` is in-memory; orders are lost on server restart. `WorkOrderClient` (external HTTP POST) is only instantiated when `WORK_ORDER_API_URL` is set.

### Frontend Architecture

The React dashboard (`frontend/`) connects to the FastAPI backend via Vite's dev proxy. In production, serve the Vite build behind the same origin as the API.

- **State management:** Zustand (`twinStore.ts`). All components read from the store — do not maintain local copies of `TwinState`. The store exposes: `setState`, `setConnected`, `setWorkOrders`, `addRepairLog`, `clearRepairLog`, `refreshWorkOrders`, `completeWorkOrder`, `applyCorrection`, `resetAll`.
- **History arrays** are capped at 60 entries: `tickHistory`, `alertHistory`, `positionHistory`, `segmentBeliefHistory`. `repairLog` is prepend-ordered (newest first), uncapped.
- **WebSocket:** `useTwinWebSocket` is mounted once at `App` level; it writes to the store on every tick. The `ws://` URL is derived from `window.location.host` so it works through the Vite proxy automatically.
- **REST calls** (`/api/work-orders`, `/api/work-orders/{id}/complete`, `/api/correction`, `/api/reset`) go through the `/api` proxy rewrite — call `/api/...` in the frontend, never `http://localhost:8000` directly.
- **Types:** `frontend/src/types.ts` mirrors `api/models.py` exactly. Keep them in sync when changing the API schema.
- **Note on ARCHITECTURE.md:** That file references `digital_twin/` but the live orchestrator lives in `digital_twin_v2/`. ARCHITECTURE.md is a design spec, not a map of the current file tree.
