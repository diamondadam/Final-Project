from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import joblib
import numpy as np

# Project root on path so classifier / controller / sensors import cleanly
_ROOT = str(Path(__file__).parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from controller.bayesian import BayesianSegmentTracker  # noqa: E402
from controller.mpc import PyomoMPCController           # noqa: E402
from sensors.base import BaseSensorSimulator            # noqa: E402
from digital_twin_v2.state import TwinState, SegmentState  # noqa: E402

if TYPE_CHECKING:
    from integrations.work_orders import WorkOrderClient

_CLASSIFIER_DIR = Path(__file__).parent.parent / "classifier"
_MODEL_PATH = _CLASSIFIER_DIR / "output" / "model_knn.joblib"

V_MAX_FPS = 3.0
V_MIN_FPS = 0.5
MPC_HORIZON = 3


class DigitalTwin:
    """
    OODA loop orchestrator for the rail track digital twin.

    Uses the pre-trained KNN pipeline from classifier/output/model_knn.joblib.
    The sklearn Pipeline bundles StandardScaler + KNN so no separate scaler
    is needed — pass raw feature vectors directly to predict_proba().

    Wires together:
      - BaseSensorSimulator  (CSV replay or synthetic)
      - KNN classifier pipeline (pre-trained, loaded from disk)
      - BayesianSegmentTracker  (one per segment)
      - PyomoMPCController
      - WorkOrderClient  (optional — fires on MAP state transition to Degraded/Damaged)
    """

    def __init__(
        self,
        track_config: list[int],
        simulator: BaseSensorSimulator,
        model_path: Path | str = _MODEL_PATH,
        work_order_client: "WorkOrderClient | None" = None,
        v_max: float = V_MAX_FPS,
        v_min: float = V_MIN_FPS,
        mpc_horizon: int = MPC_HORIZON,
    ) -> None:
        self.track_config = list(track_config)
        self.n_segments = len(track_config)
        self.simulator = simulator
        self.simulator.set_track_config(track_config)
        self._work_order_client = work_order_client

        print(f"DigitalTwin: loading KNN model from {model_path}")
        self._model = joblib.load(model_path)   # sklearn Pipeline (scaler + KNN)

        self.trackers: list[BayesianSegmentTracker] = [
            BayesianSegmentTracker() for _ in range(self.n_segments)
        ]
        self.mpc = PyomoMPCController(v_max, v_min, mpc_horizon)

        self._tick = 0
        self._current_seg = 0
        self._state: TwinState | None = None
        self._prev_map_states: list[int | None] = [None] * self.n_segments

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def step(self) -> TwinState:
        """Advance one OODA tick — observe one segment, update beliefs, emit state."""
        seg = self._current_seg
        true_state = self.track_config[seg]

        # OBSERVE
        feat_vec = self.simulator.get_reading(seg, true_state)

        # ORIENT — Pipeline handles scaling internally
        likelihood = self._model.predict_proba(feat_vec.reshape(1, -1))[0]

        # DECIDE
        self.trackers[seg].update(likelihood)
        speed, alert = self.mpc.compute_speed(self.trackers, seg)

        # ACT
        self._tick += 1
        segments = [
            SegmentState.build(
                segment_id=i,
                true_state=self.track_config[i],
                belief=self.trackers[i].belief.tolist(),
                map_state=self.trackers[i].map_state(),
                entropy=self.trackers[i].entropy(),
            )
            for i in range(self.n_segments)
        ]
        self._state = TwinState.build(
            tick=self._tick,
            train_segment=seg,
            commanded_speed_fps=speed,
            alert=alert,
            segments=segments,
        )

        await self._maybe_submit_work_order(seg, segments[seg])
        self._current_seg = (self._current_seg + 1) % self.n_segments
        return self._state

    def apply_human_correction(self, segment_id: int, confirmed_state: int) -> None:
        """HITL override: collapse belief to near-certain around confirmed_state."""
        self.trackers[segment_id].human_correction(confirmed_state)
        self._prev_map_states[segment_id] = confirmed_state

    def get_state(self) -> TwinState | None:
        """Return the most recent TwinState without advancing the simulation."""
        return self._state

    def reset(self) -> None:
        """Reset all Bayesian trackers to uniform priors and restart tick counter."""
        for tracker in self.trackers:
            tracker.reset()
        self._tick = 0
        self._current_seg = 0
        self._state = None
        self._prev_map_states = [None] * self.n_segments

    # ------------------------------------------------------------------
    # Work order helper
    # ------------------------------------------------------------------

    async def _maybe_submit_work_order(
        self, seg: int, seg_state: SegmentState
    ) -> None:
        if self._work_order_client is None:
            return

        current_map = seg_state.map_state
        prev_map = self._prev_map_states[seg]

        if current_map in (1, 2) and current_map != prev_map:
            from integrations.work_orders import WorkOrderPayload
            payload = WorkOrderPayload(
                segment_id=seg,
                severity="DAMAGED" if current_map == 2 else "DEGRADED",
                belief=seg_state.belief,
                confidence=max(seg_state.belief),
                commanded_speed_fps=self._state.commanded_speed_fps,
                alert_message=self._state.alert,
            )
            try:
                await self._work_order_client.submit(payload)
            except Exception as exc:
                print(f"  [WARN] Work order submission failed for seg {seg}: {exc}")

        self._prev_map_states[seg] = current_map
