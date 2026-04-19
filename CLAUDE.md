# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CMU final project: a **digital twin** for rail track health monitoring. The core question is whether structural conditions under the track (Healthy / Degraded / Damaged) can be detected solely from vibration signals captured by two accelerometers on a moving train.

## Running the Code

All scripts are run from the repo root. Each writes its outputs to `classifier/output/`.

```bash
# Full classification pipeline (loads data, Kalman filter, Random Forest CV, plots)
python classifier/track_health_classifier.py

# OODA-loop simulation with Bayesian belief tracking + MPC speed control
python classifier/simulation.py

# 3D animated GIF of the simulation (slow — renders all frames)
python classifier/visualization_3d.py

# Frequency diagnostics: PSD plots and ANOVA discriminative-power analysis
python classifier/diagnose_frequencies.py

# Week 10 standalone safety-stop decision function demo
python week10example/train_stop_decision.py
```

Dependencies: `numpy`, `scipy`, `scikit-learn`, `matplotlib` (Agg backend), `Pillow` (for GIF output).

## Data Layout

```
data/TrainRuns/
  Steel_3_8_in/        → label 0 "Healthy"   (steel, highest stiffness)
  Aluminum_1_2_in/     → label 1 "Degraded"  (aluminum, 1/2-in thick)
  Aluminum_3_8_in/     → label 2 "Damaged"   (aluminum, 3/8-in thin)
    <condition_dir>/
      <run_dir>/
        arduino_motion_raw.csv    # ~10 Hz: time_ms, phase, pos_ft, vel_fps
        daq_sensors_1000hz.csv    # 1000 Hz: time_ms, g4, g5
```

## Architecture

> **Read [ARCHITECTURE.md](ARCHITECTURE.md) before making any structural changes.**
> It is the canonical reference for module responsibilities, data flow, WebSocket
> contract, and design decisions. CLAUDE.md contains run instructions and constants;
> ARCHITECTURE.md contains system design.

### Data pipeline (`track_health_classifier.py`)

1. **Phase filtering** — only `CRUISE` rows are used (constant-speed section). ACCEL/DECEL/REWIND are discarded because they introduce confounds unrelated to track structure.
2. **Timestamp alignment** — DAQ (1000 Hz) is aligned to arduino (10 Hz) using `bisect_left` nearest-neighbor lookup on `time_ms`.
3. **Kalman filter** (`KalmanFilter1D`) — applied independently to g4 and g5 to reduce sensor noise while preserving structural vibration.
4. **Position-segment feature extraction** — the cruise section is divided into `N_SEGMENTS=5` spatial bins. Features are computed per bin (not per time window), making them speed-invariant by design.
5. **Feature vector** — 5 segments × 20 features = **100 features per run**. Per segment: 8 stats for g4, 8 for g5 (rms, mean, std, peak, crest factor, kurtosis, skewness, speed-normalised rms), 3 cross-sensor (pearson_corr, rms_ratio, diff_rms), 1 kinematic (mean_vel).
6. **One row per run** — avoids data leakage in cross-validation.
7. **Classifier** — `RandomForestClassifier(n_estimators=300, class_weight="balanced")` with `StandardScaler`. Evaluated with `StratifiedGroupKFold(n_splits=5)`.

### Simulation (`simulation.py`)

Implements a full **OODA loop** per segment per pass over a configurable multi-segment track:

- **Observe** — sample a real feature vector from `DataPool` matching the segment's true health state.
- **Orient** — run the trained Random Forest to get soft class probabilities.
- **Decide** — `BayesianSegmentTracker` multiplies the new likelihood into the running belief (`posterior ∝ likelihood × prior`, with a `MIN_BELIEF=0.02` floor). `MPCSpeedController` uses a receding-horizon look-ahead (`MPC_HORIZON=3` segments) to compute commanded speed, penalising segments by their degradation risk.
- **Act** — speed command is recorded; in a physical system the train actuator would respond.

`human_correction()` collapses a segment's belief to near-certain around the operator-confirmed state, simulating the human-in-the-loop (HITL) override.

### Visualization (`visualization_3d.py`)

Renders a 3D animated GIF (`classifier/output/track_simulation_3d.gif`). Imports `DataPool`, `BayesianSegmentTracker`, and `MPCSpeedController` from `simulation.py` and re-runs the simulation to collect frame-level belief/speed data. Track segment colours are RGB-blended from the current belief vector (green=Healthy, orange=Degraded, red=Damaged).

### Safety stop (`week10example/train_stop_decision.py`)

Standalone module; not imported by the classifier or simulation. Contains `should_stop_train()` (batch) and `RealTimeStopMonitor` (streaming, O(1) memory via Welford's online algorithm). Thresholds derived empirically from the dataset: `PEAK_THRESHOLD_G=0.30`, `RMS_THRESHOLD_G=0.15`, `ZSCORE_THRESHOLD=6.0`.

## Key Constants (edit to change behaviour)

| Location | Constant | Default | Effect |
|---|---|---|---|
| `track_health_classifier.py` | `N_SEGMENTS` | 5 | Spatial bins per run |
| `simulation.py` | `TRACK_CONFIG` | `[0,0,1,2,1,0]` | True health state per segment |
| `simulation.py` | `N_PASSES` | 15 | Train passes to simulate |
| `simulation.py` | `MPC_HORIZON` | 3 | Look-ahead segments |
| `simulation.py` | `SPEED_PENALTY` | `{0:0.0, 1:0.45, 2:0.80}` | Speed reduction per state |
| `visualization_3d.py` | `N_VIS_PASSES` | 5 | Passes to animate |

## Known Issues

- `simulation.py` lines 26–29 contain a syntax error in the `labeled_data_example` dict literal (used only as a comment/illustration). The file still runs because the broken dict is defined at module level before any imports, but Python will raise a `SyntaxError` if the indentation is wrong. Verify this before running.
