import shutil
from pathlib import Path

import numpy as np
from pyomo.environ import (
    ConcreteModel, Var, Objective, Constraint, SolverFactory, minimize,
)

from .bayesian import BayesianSegmentTracker


class PyomoMPCController:
    """
    Receding-horizon speed controller using Pyomo + IPOPT.

    Solves a QP each segment:
        minimize  sum_{t=0}^{H-1}  (speed[t] - v_safe[t])^2

    where v_safe[t] is derived from the MAP health state of the look-ahead segment:
        Healthy  (0) -> v_max
        Degraded (1) -> 0.6 * v_max
        Damaged  (2) -> 0.3 * v_max

    Constraints:
        v_min  <= speed[t]               <= v_max        for all t
               |speed[t+1] - speed[t]|  <= delta_v_max  for all t in 0..H-2

    Only speed[0] is applied each tick (receding horizon).
    """

    V_SAFE_MULT: dict[int, float] = {0: 1.0, 1: 0.6, 2: 0.3}

    def __init__(
        self,
        v_max: float,
        v_min: float,
        horizon: int,
        delta_v_max: float = 1.0,
    ) -> None:
        self.v_max = v_max
        self.v_min = v_min
        self.horizon = horizon
        self.delta_v_max = delta_v_max
        self._solver = self._find_ipopt()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------


    def compute_speed(
        self,
        trackers: list[BayesianSegmentTracker],
        current_seg: int,
    ) -> tuple[float, str]:
        """
        Compute commanded speed for current_seg via receding-horizon MPC.

        Returns
        -------
        (commanded_speed_fps, alert_string)
        """
        n_segs = len(trackers)
        v_safe = [
            self.v_max * self.V_SAFE_MULT[
                trackers[(current_seg + t) % n_segs].map_state()
            ]
            for t in range(self.horizon)
        ]

        speeds = self._build_and_solve(v_safe)
        commanded = float(np.clip(round(speeds[0], 3), self.v_min, self.v_max))

        map_state = trackers[current_seg].map_state()
        if map_state == 2:
            alert = "DANGER \u2013 Damaged track detected. Speed reduced. Whistle!"
        elif map_state == 1:
            alert = "WARNING \u2013 Degraded track. Proceed with caution."
        else:
            alert = "CLEAR"

        return commanded, alert

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_and_solve(self, v_safe: list[float]) -> list[float]:
        H = len(v_safe)
        m = ConcreteModel()
        m.speed = Var(range(H), bounds=(self.v_min, self.v_max))
        m.obj = Objective(
            expr=sum((m.speed[t] - v_safe[t]) ** 2 for t in range(H)),
            sense=minimize,
        )
        m.accel_up = Constraint(
            range(H - 1),
            rule=lambda m, t: m.speed[t + 1] - m.speed[t] <= self.delta_v_max,
        )
        m.accel_dn = Constraint(
            range(H - 1),
            rule=lambda m, t: m.speed[t] - m.speed[t + 1] <= self.delta_v_max,
        )
        self._solver.solve(m, tee=False)
        return [float(m.speed[t].value) for t in range(H)]

    @staticmethod
    def _find_ipopt() -> SolverFactory:

        """Return a ready IPOPT SolverFactory, checking PATH then IDAES install."""
        if shutil.which("ipopt"):
            return SolverFactory("ipopt")
        idaes_ipopt = (
            Path.home() / "AppData" / "Local" / "idaes" / "bin" / "ipopt.exe"
        )
        if idaes_ipopt.exists():
            return SolverFactory("ipopt", executable=str(idaes_ipopt))
        raise RuntimeError(
            "IPOPT not found on PATH or in IDAES install location. "
            "Install via: idaes get-extensions"
        )
