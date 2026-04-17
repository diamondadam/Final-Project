"""
Unit tests for PyomoMPCController.

Run from repo root:
    pytest classifier/tests/test_pyomo_mpc.py -v
"""

import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

V_MAX = 3.0
V_MIN = 0.5
HORIZON = 3


class MockTracker:
    """
    Minimal stand-in for BayesianSegmentTracker.

    PyomoMPCController only calls .map_state() on each tracker, so this
    stub satisfies the full interface it needs. belief is set for
    completeness but is not read by the controller.
    """
    def __init__(self, map_state: int):
        self._map_state = map_state
        self.belief = np.zeros(3)
        self.belief[map_state] = 1.0

    def map_state(self) -> int:
        return self._map_state


# ---------------------------------------------------------------------------
# _build_and_solve tests (unit — no trackers needed)
# ---------------------------------------------------------------------------

def test_build_and_solve_all_healthy():
    """v_safe = V_MAX for all segments -> all speeds should converge to V_MAX."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON)
    v_safe = [V_MAX] * HORIZON
    speeds = ctrl._build_and_solve(v_safe)
    assert len(speeds) == HORIZON
    for s in speeds:
        assert abs(s - V_MAX) < 0.05

def test_build_and_solve_all_damaged():
    """v_safe = 0.3*V_MAX for all segments -> all speeds should be near 0.9 fps."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON)
    v_safe = [0.3 * V_MAX] * HORIZON
    speeds = ctrl._build_and_solve(v_safe)
    for s in speeds:
        assert abs(s - 0.3 * V_MAX) < 0.1

def test_build_and_solve_respects_speed_bounds():
    """All returned speeds must satisfy V_MIN <= speed <= V_MAX."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON)
    for v_safe_val in [V_MAX, 0.6 * V_MAX, 0.3 * V_MAX]:
        speeds = ctrl._build_and_solve([v_safe_val] * HORIZON)
        for s in speeds:
            assert V_MIN - 1e-6 <= s <= V_MAX + 1e-6

def test_build_and_solve_respects_acceleration_constraint():
    """Speed changes between consecutive steps must not exceed delta_v_max=1.0."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON, delta_v_max=1.0)
    # v_safe jumps abruptly -- solver must smooth the trajectory
    v_safe = [V_MAX, 0.3 * V_MAX, 0.3 * V_MAX]
    speeds = ctrl._build_and_solve(v_safe)
    for t in range(len(speeds) - 1):
        assert abs(speeds[t + 1] - speeds[t]) <= 1.0 + 1e-6

def test_build_and_solve_returns_horizon_length():
    """Output list length must equal horizon."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON)
    speeds = ctrl._build_and_solve([V_MAX] * HORIZON)
    assert len(speeds) == HORIZON

def test_build_and_solve_mixed_vsafe():
    """Mixed v_safe [V_MAX, 0.3*V_MAX, 0.6*V_MAX]: trajectory respects all constraints."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON, delta_v_max=1.0)
    v_safe = [V_MAX, 0.3 * V_MAX, 0.6 * V_MAX]
    speeds = ctrl._build_and_solve(v_safe)
    # Bounds hold
    for s in speeds:
        assert V_MIN - 1e-6 <= s <= V_MAX + 1e-6
    # Acceleration constraint holds
    for t in range(len(speeds) - 1):
        assert abs(speeds[t + 1] - speeds[t]) <= 1.0 + 1e-6
    # First step should be closer to V_MAX than to the damaged target
    assert speeds[0] > 0.5 * V_MAX


# ---------------------------------------------------------------------------
# compute_speed tests (integration -- uses MockTracker)
# ---------------------------------------------------------------------------

def test_compute_speed_healthy_returns_near_vmax():
    """All-Healthy look-ahead -> speed[0] near V_MAX, alert == 'CLEAR'."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON)
    trackers = [MockTracker(0)] * 6
    speed, alert = ctrl.compute_speed(trackers, current_seg=0)
    assert abs(speed - V_MAX) < 0.05
    assert alert == "CLEAR"

def test_compute_speed_damaged_returns_low_speed():
    """All-Damaged look-ahead -> speed[0] near 0.3*V_MAX=0.9, DANGER alert."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON)
    trackers = [MockTracker(2)] * 6
    speed, alert = ctrl.compute_speed(trackers, current_seg=0)
    assert abs(speed - 0.3 * V_MAX) < 0.1
    assert "DANGER" in alert

def test_compute_speed_degraded_returns_warning():
    """All-Degraded look-ahead -> WARNING alert."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON)
    trackers = [MockTracker(1)] * 6
    speed, alert = ctrl.compute_speed(trackers, current_seg=0)
    assert "WARNING" in alert

def test_compute_speed_always_within_bounds_forward():
    """speed[0] must satisfy V_MIN <= speed <= V_MAX for states [0, 1, 2]."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON)
    for state in [0, 1, 2]:
        trackers = [MockTracker(state)] * 6
        speed, _ = ctrl.compute_speed(trackers, current_seg=0)
        assert V_MIN - 1e-6 <= speed <= V_MAX + 1e-6

def test_compute_speed_always_within_bounds_reverse():
    """speed[0] must satisfy V_MIN <= speed <= V_MAX for states [2, 1, 0]."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON)
    for state in [2, 1, 0]:
        trackers = [MockTracker(state)] * 6
        speed, _ = ctrl.compute_speed(trackers, current_seg=0)
        assert V_MIN - 1e-6 <= speed <= V_MAX + 1e-6

def test_compute_speed_wraps_segment_index():
    """current_seg near end of track wraps look-ahead via modulo without error."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON)
    trackers = [MockTracker(0)] * 3   # only 3 segments, horizon=3 must wrap
    speed, _ = ctrl.compute_speed(trackers, current_seg=2)
    assert V_MIN - 1e-6 <= speed <= V_MAX + 1e-6

def test_compute_speed_lookahead_damage_reduces_speed():
    """Current seg Healthy but all look-ahead is Damaged -> speed < V_MAX despite CLEAR alert.

    This is the key MPC property: the controller anticipates upcoming damage
    and slows down proactively, even though the current segment is fine.
    """
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON)
    # seg 0 = Healthy, segs 1-5 = Damaged
    trackers = [MockTracker(0)] + [MockTracker(2)] * 5
    speed, alert = ctrl.compute_speed(trackers, current_seg=0)
    assert alert == "CLEAR"          # current seg is Healthy
    assert speed < V_MAX - 0.1       # look-ahead damage pulls speed down

def test_compute_speed_alternating_healthy_damaged():
    """Alternating [H, D, H, D, H, D] layout: speed at seg 0 is between damaged and healthy targets."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON)
    trackers = [MockTracker(s) for s in [0, 2, 0, 2, 0, 2]]
    speed, alert = ctrl.compute_speed(trackers, current_seg=0)
    assert alert == "CLEAR"
    # v_safe = [V_MAX, 0.3*V_MAX, V_MAX] -> speed[0] should be between 0.3*V_MAX and V_MAX
    assert 0.3 * V_MAX - 0.1 <= speed <= V_MAX + 1e-6

def test_compute_speed_current_damaged_lookahead_healthy():
    """Current seg Damaged, rest Healthy -> DANGER alert; speed near damaged target."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON)
    # seg 0 = Damaged, segs 1-5 = Healthy
    trackers = [MockTracker(2)] + [MockTracker(0)] * 5
    speed, alert = ctrl.compute_speed(trackers, current_seg=0)
    assert "DANGER" in alert
    # v_safe[0]=0.9, v_safe[1]=3.0, v_safe[2]=3.0 -> speed[0] near 0.9 but can start climbing
    assert speed < V_MAX * 0.7

def test_compute_speed_damaged_segment_slower_than_healthy():
    """Speed commanded at a Damaged segment is strictly lower than at a Healthy segment
    on the same track layout."""
    from simulation import PyomoMPCController
    ctrl = PyomoMPCController(V_MAX, V_MIN, HORIZON)
    # Layout: [H, H, D, H, H, H]
    trackers = [MockTracker(s) for s in [0, 0, 2, 0, 0, 0]]
    speed_healthy, _ = ctrl.compute_speed(trackers, current_seg=0)
    speed_damaged, _ = ctrl.compute_speed(trackers, current_seg=2)
    assert speed_damaged < speed_healthy


# ---------------------------------------------------------------------------
# Backward-compatibility alias
# ---------------------------------------------------------------------------

def test_mpc_speed_controller_is_alias():
    """MPCSpeedController must resolve to PyomoMPCController."""
    from simulation import MPCSpeedController, PyomoMPCController
    assert MPCSpeedController is PyomoMPCController
