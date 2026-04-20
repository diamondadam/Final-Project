# Pyomo-Based MPC Speed Controller — Design Spec

**Date:** 2026-04-16  
**File to modify:** `classifier/simulation.py`  
**Scope:** Replace the heuristic `MPCSpeedController` with a proper Pyomo QP-based `PyomoMPCController`. No other files change in substance.

---

## 1. Objective Function

```
minimize  sum_{t=0}^{H-1} (speed[t] - v_safe[t])^2

where H = MPC_HORIZON = 3  (look-ahead segments)
```

Only `speed[0]` (the command for the current segment) is applied after solving. The rest are discarded and the problem is re-solved at the next segment (receding-horizon convention).

---

## 2. Target Safe Speed

`v_safe[t]` is derived from the MAP (maximum a-posteriori) state of the look-ahead segment at position `(current_seg + t) % n_segments`:

| MAP State | v_safe        |
|-----------|---------------|
| Healthy   | `V_MAX`       |
| Degraded  | `0.6 * V_MAX` |
| Damaged   | `0.3 * V_MAX` |

With `V_MAX = 3.0 fps`: Healthy → 3.0, Degraded → 1.8, Damaged → 0.9.

---

## 3. Constraints

```
V_MIN  ≤ speed[t]              ≤ V_MAX     for all t in 0..H-1
       |speed[t+1] - speed[t]| ≤ 1.0 fps  for all t in 0..H-2
```

`V_MIN = 0.5 fps`, `V_MAX = 3.0 fps`, `delta_v_max = 1.0 fps`.

---

## 4. Solver

**Pyomo + IPOPT.** The objective is nonlinear (quadratic) and IPOPT handles it cleanly without linearization. The problem is tiny (3 variables, ~8 constraints) so solve time is negligible.

Install:
```bash
pip install pyomo
conda install -c conda-forge ipopt   # or: pip install idaes-pse then idaes get-extensions
```

---

## 5. Class Design

```python
class PyomoMPCController:
    def __init__(self, v_max: float, v_min: float, horizon: int, delta_v_max: float = 1.0):
        ...

    def _build_and_solve(self, v_safe: list[float]) -> list[float]:
        """Build Pyomo ConcreteModel, solve with IPOPT, return speed trajectory."""
        ...

    def compute_speed(
        self,
        trackers: list[BayesianSegmentTracker],
        current_seg: int,
    ) -> tuple[float, str]:
        """
        Same external interface as the old MPCSpeedController.
        1. Derive v_safe[t] from MAP state of each look-ahead segment.
        2. Build + solve Pyomo model.
        3. Return (speed[0], alert_string).
        """
        ...

# Backward-compatibility alias for visualization_3d.py
MPCSpeedController = PyomoMPCController
```

---

## 6. Alert String Logic

Unchanged from the current implementation — based solely on the MAP state of `current_seg`:

| MAP State | Alert string                                          |
|-----------|-------------------------------------------------------|
| Healthy   | `"CLEAR"`                                             |
| Degraded  | `"WARNING – Degraded track. Proceed with caution."`   |
| Damaged   | `"DANGER  – Damaged track detected. Speed reduced. Whistle!"` |

---

## 7. Integration Points

| Location | Change |
|---|---|
| `simulation.py` — `Simulation.__init__` | `self.mpc = PyomoMPCController(V_MAX_FPS, V_MIN_FPS, MPC_HORIZON)` |
| `simulation.py` — old `MPCSpeedController` class | Deleted, replaced by `PyomoMPCController` + alias |
| `visualization_3d.py` | No change — imports `MPCSpeedController` which resolves to the alias |
| `track_health_classifier.py` | No change |

---

## 8. Out of Scope

- ARMAX forecasting integration
- Human-in-the-loop retraining
- Pyomo fallback to heuristic on solver failure (fail loudly with a clear error instead)
