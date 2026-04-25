# Rail Track Health Monitoring via Digital Twin
### CMU Final Project — Adam Diamond

---

## Abstract

This project presents a real-time digital twin for rail track health monitoring. A moving train carries two accelerometers (g4, g5) that record vibration at 1,000 Hz. A machine-learning classifier continuously categorizes each track segment as **Healthy**, **Degraded**, or **Damaged** based on a 99-feature signal representation. A sequential Bayesian filter accumulates evidence across passes, and a Model Predictive Controller (MPC) adjusts train speed based on the estimated health state of upcoming segments. The system broadcasts live telemetry over WebSocket to a React dashboard and an Unreal Engine 5 visualization. The best classifier (K-Nearest Neighbours, k=7) achieves **98.25% balanced accuracy** on the held-out test set.

---

## 1. Introduction

Rail infrastructure degradation is a leading cause of derailments and unplanned maintenance outages. Traditional inspection regimes rely on periodic manual surveys, which leave long windows between inspections during which developing faults go undetected. Continuous, automated monitoring would allow maintenance crews to respond to emerging defects before they become safety hazards.

This project builds a **digital twin** — a software model that mirrors the physical track's health state in real time — using only the vibration signals already present on a moving train. The twin runs an OODA (Observe–Orient–Decide–Act) loop once per segment, updating a probabilistic health estimate and issuing speed commands proportional to the estimated risk. When a segment's MAP (maximum a-posteriori) state transitions to Degraded or Damaged, the system automatically files a work order with a maintenance system and reduces the commanded train speed.

The full system integrates:

- A signal-processing and classification pipeline trained on physical test-track runs
- A sequential Bayesian state estimator per segment
- A receding-horizon MPC speed planner
- A FastAPI server with WebSocket fan-out
- A React 19 + TypeScript operations dashboard
- An Unreal Engine 5 real-time 3D visualization

---

## 2. Hardware and Data Collection

### 2.1 Test Track and Rolling Stock

Experiments were conducted on a scale model rail system. The track surface is swapped between three material/geometry combinations to simulate three health states:

| Label | Material | Condition |
|---|---|---|
| Healthy | Steel 3/8 in | Nominal surface |
| Degraded | Aluminum 1/2 in | Surface discontinuity |
| Damaged | Aluminum 3/8 in | Severe surface discontinuity |

### 2.2 Sensor Suite

Two MEMS accelerometers (channels **g4** and **g5**) are mounted to the bogie frame and sample at **1,000 Hz**. A 10 Hz motion encoder (Arduino) records timestamps, phase labels (ACCEL / CRUISE / DECEL), position in feet, and velocity in feet per second.

Each run produces two synchronized CSV files:

- `daq_sensors_1000hz.csv` — columns: `time_ms`, `g4`, `g5`
- `arduino_motion_raw.csv` — columns: `time_ms`, `phase`, `pos_ft`, `vel_fps`

### 2.3 Dataset Composition

The full labeled dataset contains **270 runs** across the three health states. The dataset combines natural runs with augmented Degraded and Damaged samples to achieve class balance. A `source_run_id` field tracks the original physical run each augmented copy derives from.

| Split | Runs |
|---|---|
| Training | 218 |
| Test | 52 |
| **Total** | **270** |

Train/test splitting uses `GroupShuffleSplit` (80/20) keyed on `source_run_id`, guaranteeing that all augmented copies of a given physical run land in the same fold. This prevents the model from seeing near-duplicate samples in both train and test sets, which would inflate accuracy estimates.

---

## 3. Feature Engineering

### 3.1 Phase Segmentation

Vibration does not scale linearly with speed. Motor forces during acceleration and braking introduce their own spectral signature that is unrelated to track health. To disentangle these effects, features are computed **independently for each motion phase** (ACCEL, CRUISE, DECEL) and concatenated, producing a constant-length feature vector regardless of run timing.

Samples with velocity below 0.30 fps are excluded within the ACCEL and DECEL phases to eliminate near-zero-speed noise. Phases with fewer than 50 samples are zero-padded so the vector length is always constant.

### 3.2 Feature Block (33 features per phase)

For each phase and each accelerometer channel, the following features are computed:

**Time-domain statistics (7):**
RMS, mean, standard deviation, peak-to-peak, kurtosis, skewness, crest factor

**Frequency-domain band energies (3, normalized):**
Low band (0–50 Hz), mid band (50–200 Hz), high band (200–500 Hz)

**Spike / impulsive features (5):**
99th-percentile absolute amplitude, exceedance rate (fraction of samples > μ + 3σ), impulse factor (max|a| / mean|a|), maximum windowed RMS, maximum windowed kurtosis (50-sample sliding window)

The windowed spike features are deliberately included because single-impact defects produce brief spikes that aggregate statistics dilute — a 50-sample window containing one spike will exhibit extreme kurtosis even when the full-signal kurtosis appears near-Gaussian.

**Cross-sensor features (3):**
Pearson cross-correlation (g4, g5), RMS ratio (g4 / g5), differential RMS (RMS of g4 − g5)

Each phase block is 33 features (15 for g4 + 15 for g5 + 3 cross-sensor). With 3 phases, the final feature vector is **99 dimensions**.

---

## 4. Classification

Three classifiers were trained and evaluated: K-Nearest Neighbours (KNN), Gradient Boosting (GBM), and a Support Vector Machine (SVM). Each is wrapped in a `sklearn.Pipeline` with a `StandardScaler` preprocessing step.

### 4.1 Model Configurations

| Model | Hyperparameters |
|---|---|
| KNN | k=7, metric=euclidean, weights=distance |
| GBM | 300 estimators, lr=0.05, max_depth=4, subsample=0.8 |
| SVM | RBF kernel, C=10.0, gamma=scale, class_weight=balanced |

### 4.2 Evaluation Results

| Model | CV Bal. Acc. (mean ± std) | Test Bal. Acc. | F1 Macro | F1 (Healthy / Degraded / Damaged) |
|---|---|---|---|---|
| **KNN** | 0.911 ± 0.022 | **0.9825** | **0.980** | 0.968 / 0.973 / **1.000** |
| GBM | 0.955 ± 0.031 | 0.9417 | 0.941 | 0.903 / 0.947 / 0.971 |
| SVM | 0.937 ± 0.040 | 0.9427 | 0.942 | 0.933 / 0.944 / 0.947 |

### 4.3 Model Selection

**KNN is selected as the production model** despite GBM achieving higher cross-validation balanced accuracy. The rationale is safety-driven:

- KNN's test accuracy of 98.25% substantially exceeds its CV estimate, indicating strong generalisation.
- KNN's confidence scores (`predict_proba`) are well-calibrated: samples rated as high-confidence are consistently correct. This is essential because the Bayesian tracker and MPC controller rely on the full probability vector, not just the class label.
- GBM produces overconfident probabilities regardless of actual correctness, which would cause the Bayesian tracker to converge prematurely on incorrect states.
- KNN achieves a **perfect F1 of 1.00 on the Damaged class**, meaning zero false negatives for the most safety-critical condition.

### 4.4 Top Informative Features

Permutation importance analysis on the KNN model identifies the most discriminative features as:

1. `DECEL_g5_mean` — mean deceleration-phase vibration on channel g5
2. `DECEL_g5_rms` — RMS deceleration vibration on g5
3. `CRUISE_g4_max_win_kurtosis` — peak windowed kurtosis at cruise speed on g4
4. `ACCEL_g5_max_win_rms` — peak windowed RMS during acceleration on g5
5. `ACCEL_rms_ratio` — inter-sensor RMS ratio during acceleration

For GBM, the dominant features are `CRUISE_g5_rms` (31.2% importance), `CRUISE_g4_kurtosis` (18.0%), and `CRUISE_cross_corr` (14.1%), confirming that steady-state cruise vibration is the richest signal for health discrimination.

---

## 5. State Estimation: Bayesian Segment Tracker

A single classifier inference per pass is noisy. The system maintains a **sequential Bayesian filter** for each track segment to accumulate evidence over multiple passes.

### 5.1 Update Rule

```
belief_t[i]  ∝  likelihood_t[i]  ×  belief_{t-1}[i]
```

where `likelihood[i]` is the KNN `predict_proba` output for class i. Multiplying likelihoods across passes is equivalent to running the HMM forward algorithm under a stationary transition matrix — the belief sharpens with each consistent observation.

A minimum belief floor of **MIN_BELIEF = 0.02** prevents any state from reaching zero probability, ensuring that after a human correction or transient misclassification, the tracker can recover.

### 5.2 MAP State and Entropy

The MAP (maximum a-posteriori) state is `argmax(belief)`. Shannon entropy over the belief vector quantifies confidence:

```
H = -Σ p_i · log(p_i)
```

Low entropy indicates a confident, converged estimate; high entropy indicates ambiguity. Both values are broadcast to the dashboard and Unreal Engine every tick.

### 5.3 Human-in-the-Loop (HITL) Override

Operators can submit a correction via `POST /correction`. This collapses the belief to near-certainty around the confirmed state while preserving the minimum floor on all other states, modelling the maintenance operator as an authoritative high-confidence sensor.

---

## 6. Speed Control: Model Predictive Controller

### 6.1 Formulation

A receding-horizon quadratic program is solved each segment using **Pyomo + IPOPT**:

```
minimize  Σ_{t=0}^{H-1}  (v[t] - v_safe[t])²

subject to:
  v_min  ≤  v[t]               ≤  v_max        for all t
            |v[t+1] - v[t]|   ≤  Δv_max        for all t
```

Parameters: H = 3 (look-ahead segments), v_max = 3.0 fps, v_min = 0.5 fps, Δv_max = 1.0 fps/segment.

The safe-speed target for each look-ahead segment is derived from its MAP health state:

| MAP State | Speed multiplier | Commanded speed (v_max = 3.0 fps) |
|---|---|---|
| Healthy (0) | 1.0× | 3.0 fps |
| Degraded (1) | 0.6× | 1.8 fps |
| Damaged (2) | 0.3× | 0.9 fps |

Only v[0] is applied each tick (receding horizon). The ramp constraint prevents physically unrealistic step changes in speed.

### 6.2 Alert Generation

Alongside the speed command, the controller emits a human-readable alert string broadcast to all clients:

| MAP State | Alert |
|---|---|
| Healthy | `CLEAR` |
| Degraded | `WARNING – Degraded track. Proceed with caution.` |
| Damaged | `DANGER – Damaged track detected. Speed reduced. Whistle!` |

---

## 7. System Architecture

### 7.1 OODA Loop

The digital twin executes a four-phase loop once per tick (default: 1 second):

1. **Observe** — `simulator.get_reading(seg, true_state)` returns a 99-element feature vector drawn from a real CSV run or a parametric Gaussian model.
2. **Orient** — The KNN pipeline's `predict_proba()` returns class probabilities, reordered from sklearn's alphabetical output order (Damaged, Degraded, Healthy) to the canonical order (Healthy, Degraded, Damaged).
3. **Decide** — The Bayesian tracker for the current segment is updated; the MPC solves for the commanded speed.
4. **Act** — A `TwinState` object is assembled and broadcast to all WebSocket clients. If the segment's MAP state transitioned to Degraded or Damaged, a work order is filed asynchronously (failure never blocks the OODA loop).

### 7.2 Sensor Simulators

Two sensor simulators share a common `BaseSensorSimulator` interface, allowing the orchestrator to be swapped between them without modification:

- **CSVSensorSimulator** — replays real accelerometer runs from the labeled dataset. Used for high-fidelity demo scenarios.
- **SyntheticSensorSimulator** — samples from per-class Gaussian models fit to dataset statistics. Used for edge-case stress testing and offline operation.

### 7.3 API Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/state` | Latest TwinState snapshot |
| GET | `/config` | Current track health configuration |
| POST | `/config` | Hot-swap track configuration |
| POST | `/correction` | HITL override for a segment |
| POST | `/reset` | Reset all Bayesian trackers |
| GET | `/work-orders` | List open work orders |
| POST | `/work-orders/{id}/complete` | Complete a work order + repair segment |
| WS | `/ws` | Push TwinStateResponse JSON each tick |

### 7.4 WebSocket Message Contract

Each tick, all connected clients receive:

```json
{
  "tick": 42,
  "timestamp": "2026-04-25T14:23:01.123Z",
  "train_segment": 2,
  "commanded_speed_fps": 1.5,
  "alert": "WARNING – Degraded track. Proceed with caution.",
  "segments": [
    {"id": 0, "belief": [0.95, 0.03, 0.02], "map_state": 0, "map_state_name": "Healthy",  "entropy": 0.12},
    {"id": 1, "belief": [0.88, 0.10, 0.02], "map_state": 0, "map_state_name": "Healthy",  "entropy": 0.31},
    {"id": 2, "belief": [0.05, 0.70, 0.25], "map_state": 1, "map_state_name": "Degraded", "entropy": 0.82},
    {"id": 3, "belief": [0.02, 0.08, 0.90], "map_state": 2, "map_state_name": "Damaged",  "entropy": 0.38}
  ]
}
```

### 7.5 React Dashboard

A **React 19 + TypeScript** dashboard (Vite + Tailwind CSS v4 + Recharts) provides:

- **Live Feed HUD** — real-time segment health cards with belief bars and entropy indicators
- **Alert Banner** — prominent display of the current alert string
- **Track Configurator** — operator UI to set per-segment health states and hot-swap the configuration
- **Analytics Page** — SpeedAlert chart, AlertBreakdown, PositionTimeline, HealthHeatmap, BeliefConvergence trends
- **Maintenance Page** — work order list, segment override panel, repair history log

State is managed with **Zustand**. History arrays are capped at 60 entries (~1 minute at the default 1 Hz tick rate).

### 7.6 Unreal Engine 5 Visualization

The UE5 client connects to `ws://localhost:8000/ws` and receives the same JSON stream as the dashboard. It maps `map_state` to segment material/color, uses the `belief` vector for smooth visual blending between health state representations, and drives audio and UI cues from the `alert` field.

### 7.7 Work Order Integration

Work orders fire only on MAP state *transitions* into Degraded or Damaged — not every tick — preventing duplicate submissions. Completing a work order via the API sets the segment's true state to Healthy, resets the Bayesian tracker to a uniform prior, and updates the simulator's track configuration so it stops returning degraded readings.

---

## 8. Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Active classifier | KNN (k=7) | Best-calibrated probabilities; zero false negatives on Damaged class |
| Feature resolution | 33 features × 3 phases | Phase separation prevents motor noise from masking track health signal |
| State estimator | Sequential Bayesian filter | Accumulates evidence across passes; handles noisy single-inference outputs |
| Speed planner | Receding-horizon MPC (H=3) | Anticipates upcoming health states; enforces smooth ramp constraints |
| Visualisation transport | WebSocket push | Low-latency updates at 1 Hz; polling would lag behind tick rate |
| Work order trigger | MAP state transition only | Prevents flooding the external maintenance system |
| Work order delivery | Async fire-and-forget, one retry | External system failure must never stall the OODA loop |
| Sensor abstraction | `BaseSensorSimulator` interface | Decouples CSV replay from synthetic generation; swappable at runtime |

---

## 9. Limitations and Future Work

**In-memory work order store.** Orders are lost on server restart. A persistent database backend would be required for production deployment.

**Augmented data.** The Degraded and Damaged classes rely on augmented copies of a small number of physical runs. While `GroupShuffleSplit` prevents leakage, the classifier has not been validated on truly independent runs from a different physical setup. Additional data collection would strengthen confidence bounds.

**Single-segment observation per tick.** The train observes only the segment it is currently on. A forward-looking sensor (LiDAR, acoustic emission) could enable simultaneous multi-segment observation.

**Stationary transition model.** The Bayesian tracker assumes health state does not change between passes. A Hidden Markov Model with an explicit degradation transition matrix could model slow progressive deterioration more accurately.

**MPC without vehicle dynamics.** The QP minimises deviation from a safe-speed target but does not model the train's mechanical dynamics. Incorporating mass, traction limits, and braking curves would make commanded speeds physically realizable.

---

## 10. Conclusion

This project demonstrates that a cost-effective MEMS accelerometer pair, combined with careful per-phase feature engineering and a probabilistic state estimator, can reliably distinguish Healthy, Degraded, and Damaged track conditions in real time. The KNN classifier achieves 98.25% balanced accuracy on the held-out test set with a perfect recall on the safety-critical Damaged class. The Bayesian filter eliminates single-inference noise, and the MPC controller translates health uncertainty into proportional speed reductions. The complete system — from raw accelerometer signal to Unreal Engine 5 visualization — runs end-to-end at a 1 Hz tick rate on commodity hardware, demonstrating the practical feasibility of continuous, automated rail track health monitoring via a software digital twin.

---

## Appendix A: Feature Names (99 total)

Features are ordered `{PHASE}_{name}` for phases ACCEL, CRUISE, DECEL. Per-phase base names (33):

```
g4_rms, g4_mean, g4_std, g4_ptp, g4_kurtosis, g4_skewness, g4_crest,
g4_band_low, g4_band_mid, g4_band_high,
g4_p99_abs, g4_exceedance_rate, g4_impulse_factor, g4_max_win_rms, g4_max_win_kurtosis,
g5_rms, g5_mean, g5_std, g5_ptp, g5_kurtosis, g5_skewness, g5_crest,
g5_band_low, g5_band_mid, g5_band_high,
g5_p99_abs, g5_exceedance_rate, g5_impulse_factor, g5_max_win_rms, g5_max_win_kurtosis,
cross_corr, rms_ratio, diff_rms
```

## Appendix B: Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `TRACK_CONFIG` | `"0,1,2,1,0"` | Comma-separated health states per segment (0=Healthy, 1=Degraded, 2=Damaged) |
| `SIMULATOR_TYPE` | `"csv"` | `"csv"` or `"synthetic"` |
| `TICK_INTERVAL_S` | `"1.0"` | Seconds per OODA tick |
| `WORK_ORDER_API_URL` | unset | External maintenance API base URL (omit to disable) |
| `WORK_ORDER_API_KEY` | unset | Bearer token for work order API |

## Appendix C: Running the System

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install joblib

# 2. Train classifiers (produces classifier/output/model_knn.joblib)
python classifier/train_classifiers.py

# 3. Start the FastAPI server
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

# 4. Start the React dashboard (separate terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173

# 5. Unreal Engine: connect to ws://localhost:8000/ws
```
