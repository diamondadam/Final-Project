# Digital Twin Architecture

Rail track health monitoring system. A moving train reads accelerometer data,
classifies track health per segment, and exposes live state to an Unreal Engine
visualization via WebSocket.

---

## Module Map

```
data/                          ← raw CSV sensor runs (read-only, do not modify)
sensors/                       ← sensor simulators (NEW)
  base.py                      ← BaseSensorSimulator — abstract interface both simulators implement
  csv_simulator.py             ← CSVSensorSimulator — replays real CSV runs via DataPool
  synthetic_simulator.py       ← SyntheticSensorSimulator — generates parametric synthetic readings
  __init__.py                  ← exports BaseSensorSimulator, CSVSensorSimulator, SyntheticSensorSimulator
classifier/                    ← classification pipeline (EXISTING, minimal changes)
  train_classifiers.py
  uncertainty.py
  __init__.py
controller/                    ← Bayesian tracker + MPC speed planner (NEW, extracted from simulation.py)
  bayesian.py                  ← BayesianSegmentTracker
  mpc.py                       ← PyomoMPCController
  __init__.py
digital_twin/                  ← OODA orchestrator + authoritative state (REFACTORED)
  orchestrator.py              ← DigitalTwin — drives the OODA loop each tick
  state.py                     ← TwinState dataclass, the canonical state object
  track_health_classifier.py   ← existing (shared helpers imported by everything)
  simulation.py                ← existing (keep for standalone demo / batch runs)
  __init__.py
api/                           ← FastAPI server (NEW)
  app.py                       ← FastAPI application, lifespan startup
  websocket.py                 ← WebSocketManager — fan-out to all Unreal clients
  models.py                    ← Pydantic schemas (request + response)
  __init__.py
```

---

## Data Flow

```
                 ┌──────────────────────────────────────────────────────────┐
                 │                     OODA Loop (tick)                     │
                 │                                                          │
   data/         │  sensors/               classifier/     controller/      │
   TrainRuns/ ──►│  CSVSensorSimulator ──► KalmanFilter ──► BayesianSegmentTracker │
   (CSV files)   │        OR              + feature    ──► PyomoMPCController     │
   parameters ──►│  SyntheticSimulator     extraction       │                     │
                 │  (BaseSensorSimulator)     │             │                     │
                 │      │                    │             │                     │
                 │      └────────────────────┴─────────────┘                    │
                 │                           │                                   │
                 │                    digital_twin/                              │
                 │                    DigitalTwin.step()                         │
                 │                    → TwinState                               │
                 └──────────────────────────────────┬───────────────────────────┘
                                                │
                                           api/app.py
                                        (FastAPI server)
                                                │
                                    WebSocket broadcast
                                                │
                                        Unreal Engine
                                    (visualization client)
```

---

## Module Responsibilities

### `sensors/base.py` — BaseSensorSimulator

Abstract base class both simulators implement. `DigitalTwin` is typed against this
interface — swap implementations without touching the orchestrator.

```python
class BaseSensorSimulator(ABC):
    @abstractmethod
    def get_reading(self, segment_id: int, true_state: int) -> np.ndarray:
        """Return one feature vector for the given segment and health state."""

    @abstractmethod
    def set_track_config(self, config: list[int]) -> None:
        """Update the ground-truth health state per segment."""
```

---

### `sensors/csv_simulator.py` — CSVSensorSimulator

Wraps `DataPool` from `digital_twin/simulation.py`. Draws feature vectors directly
from real recorded runs so sensor noise and run-to-run variability are authentic.
Use this for realistic fidelity testing and final demo.

```python
class CSVSensorSimulator(BaseSensorSimulator):
    def get_reading(self, segment_id: int, true_state: int) -> np.ndarray:
        """Sample a random real run feature vector for this health state."""
```

---

### `sensors/synthetic_simulator.py` — SyntheticSensorSimulator

Generates feature vectors from parametric Gaussian models fit to the real dataset
statistics (per-class mean and covariance of each feature). Use this for:
- testing scenarios with no matching real runs (e.g. partially damaged segments)
- stress-testing the controller with edge-case inputs
- running the system without the `data/` directory present

```python
class SyntheticSensorSimulator(BaseSensorSimulator):
    def __init__(self, noise_scale: float = 1.0, seed: int = 42): ...
    # noise_scale > 1.0 amplifies variance — useful for robustness testing

    def get_reading(self, segment_id: int, true_state: int) -> np.ndarray:
        """Sample from the per-class Gaussian model for this health state."""

    @classmethod
    def fit_from_data_pool(cls, pool: DataPool, **kwargs) -> "SyntheticSensorSimulator":
        """Fit class-conditional Gaussian parameters from a loaded DataPool."""
```

The class-conditional Gaussians are fit once at construction time from `DataPool`
statistics (or from a pre-saved `.npz` parameter file if `data/` is unavailable).

---

### `controller/bayesian.py` — BayesianSegmentTracker

Extracted verbatim from `digital_twin/simulation.py`. One tracker instance per
track segment. Key methods:

```python
def update(self, likelihood: np.ndarray) -> None   # multiply + renormalise
def map_state(self) -> int                          # argmax of belief
def entropy(self) -> float                          # confidence measure
def human_correction(self, true_state: int) -> None # HITL override
```

---

### `controller/mpc.py` — PyomoMPCController

Extracted verbatim from `digital_twin/simulation.py`. Receding-horizon QP over
`MPC_HORIZON` look-ahead segments solved via Pyomo + IPOPT.

```python
def compute_speed(
    self,
    trackers: list[BayesianSegmentTracker],
    current_seg: int,
) -> tuple[float, str]:   # (commanded_fps, alert_string)
```

---

### `digital_twin/state.py` — TwinState

The single authoritative state object. Produced each OODA tick. Serialised to
JSON for WebSocket broadcast.

```python
@dataclass
class SegmentState:
    id: int
    true_state: int                # ground truth (from track config)
    belief: list[float]            # [P(Healthy), P(Degraded), P(Damaged)]
    map_state: int                 # argmax(belief)
    map_state_name: str
    entropy: float

@dataclass
class TwinState:
    tick: int
    timestamp: str                 # ISO-8601
    train_segment: int             # which segment the train is currently on
    commanded_speed_fps: float
    alert: str
    segments: list[SegmentState]
```

---

### `digital_twin/orchestrator.py` — DigitalTwin

Owns the OODA loop. Composes `SensorSimulator`, classifier, `BayesianSegmentTracker`
instances, and `PyomoMPCController`. Produces a `TwinState` on every `step()` call.

```python
class DigitalTwin:
    def __init__(self, track_config: list[int], seed: int = 42): ...

    async def step(self) -> TwinState:
        """Advance one OODA tick (one segment observation). Returns new state."""

    def apply_human_correction(self, segment_id: int, confirmed_state: int) -> None:
        """HITL override: collapse belief to near-certain around confirmed_state."""

    def get_state(self) -> TwinState:
        """Return the most recent TwinState without advancing the simulation."""

    def reset(self) -> None:
        """Reset all Bayesian trackers to uniform priors."""
```

Internally `step()` does:
1. **Observe** — `SensorSimulator.get_reading(current_seg, true_state)`
2. **Orient** — Kalman filter → feature extraction → `clf.predict_proba()`
3. **Decide** — `BayesianSegmentTracker.update(proba)` → `MPCController.compute_speed()`
4. **Act** — advance `train_segment` counter, emit `TwinState`

---

### `api/app.py` — FastAPI Application

```
GET  /health          → {"status": "ok"}
GET  /state           → TwinState (latest snapshot, JSON)
POST /correction      → body: {"segment_id": int, "state": int}  → apply HITL override
POST /reset           → reset all segment beliefs
WS   /ws              → WebSocket stream; server pushes TwinState JSON each tick
```

The `/ws` endpoint is the primary channel for Unreal Engine. The server runs the
OODA loop on a configurable tick interval (default 1 s) and broadcasts `TwinState`
to every connected WebSocket client.

---

### `api/websocket.py` — WebSocketManager

```python
class WebSocketManager:
    async def connect(self, ws: WebSocket) -> None
    async def disconnect(self, ws: WebSocket) -> None
    async def broadcast(self, state: TwinState) -> None
```

Maintains the set of active WebSocket connections. `broadcast()` serialises
`TwinState` → JSON and sends to all connected clients. Stale/closed connections
are pruned automatically.

---

### `api/models.py` — Pydantic Schemas

All JSON shapes are defined here. Unreal Engine reads these shapes.

```python
class SegmentStateResponse(BaseModel):
    id: int
    belief: list[float]          # length 3
    map_state: int               # 0=Healthy 1=Degraded 2=Damaged
    map_state_name: str
    entropy: float

class TwinStateResponse(BaseModel):
    tick: int
    timestamp: str
    train_segment: int
    commanded_speed_fps: float
    alert: str                   # "CLEAR" | "WARNING – ..." | "DANGER – ..."
    segments: list[SegmentStateResponse]

class CorrectionRequest(BaseModel):
    segment_id: int
    state: int                   # 0, 1, or 2
```

---

## WebSocket Message Contract (Unreal Engine)

Every message the server sends is a JSON object matching `TwinStateResponse`.
Unreal connects to `ws://<host>:8000/ws` and receives one message per OODA tick.

```json
{
  "tick": 42,
  "timestamp": "2026-04-19T14:23:01.123Z",
  "train_segment": 2,
  "commanded_speed_fps": 1.5,
  "alert": "WARNING – Degraded track. Proceed with caution.",
  "segments": [
    {"id": 0, "belief": [0.95, 0.03, 0.02], "map_state": 0, "map_state_name": "Healthy",  "entropy": 0.12},
    {"id": 1, "belief": [0.88, 0.10, 0.02], "map_state": 0, "map_state_name": "Healthy",  "entropy": 0.31},
    {"id": 2, "belief": [0.05, 0.70, 0.25], "map_state": 1, "map_state_name": "Degraded", "entropy": 0.82},
    {"id": 3, "belief": [0.02, 0.08, 0.90], "map_state": 2, "map_state_name": "Damaged",  "entropy": 0.38},
    {"id": 4, "belief": [0.80, 0.15, 0.05], "map_state": 0, "map_state_name": "Healthy",  "entropy": 0.45},
    {"id": 5, "belief": [0.93, 0.05, 0.02], "map_state": 0, "map_state_name": "Healthy",  "entropy": 0.18}
  ]
}
```

Unreal maps `map_state` → segment material/colour. `belief` drives blending weight
if a smooth health-gradient visual is desired. `alert` drives audio/UI cues.

---

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Visualisation transport | WebSocket (push) | Unreal needs low-latency real-time updates; polling would lag behind simulation ticks |
| Sensor data source | Two simulators behind a common `BaseSensorSimulator` interface | `CSVSensorSimulator` for fidelity (real noise); `SyntheticSensorSimulator` for edge cases and offline testing without `data/` |
| State serialisation | Pydantic + JSON | Self-documenting, easy to consume from Unreal Blueprint HTTP/WS nodes |
| OODA tick pacing | Server-side timer (asyncio) | Decouples visualisation frame rate from simulation tick rate |
| Classifier trained on startup | Full dataset retrain in `DigitalTwin.__init__` | Keeps model fresh; startup cost is ~2 s, acceptable |

---

## Dependencies (add to requirements.txt)

```
fastapi
uvicorn[standard]
websockets
pydantic>=2.0
# existing:
numpy scipy scikit-learn matplotlib Pillow pyomo
```

---

## Running the API Server

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

Unreal Engine WebSocket URL: `ws://localhost:8000/ws`

---

## What Does NOT Change

- `digital_twin/track_health_classifier.py` — shared helpers (`KalmanFilter1D`,
  `load_and_align`, `extract_run_features`, `feature_names`, `TRACK_LABELS`,
  `CLASS_NAMES`, `BASE_DIR`) are imported by everything. Do not move or rename exports.
- `digital_twin/simulation.py` — kept intact for standalone batch runs and for
  `visualization_3d.py` compatibility. `controller/` modules are extracted copies,
  not replacements.
- `data/` — read-only. Never write to the data directory.
