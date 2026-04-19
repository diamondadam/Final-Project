import sys
from pathlib import Path

import numpy as np

from .base import BaseSensorSimulator

_ROOT = str(Path(__file__).parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


class CSVSensorSimulator(BaseSensorSimulator):
    """
    Replays real accelerometer runs from the classifier's processed dataset.

    Uses classifier.train_classifiers.load_dataset() to load 33-feature vectors
    extracted via the classifier module pipeline (no Kalman, no spatial binning).
    Feature vectors are pooled by health class; get_reading() samples randomly
    from the matching pool on each call.

    Use this for realistic fidelity testing and the final demo.
    """

    def __init__(self, seed: int = 42) -> None:
        # Lazy import: avoids pulling in sklearn/matplotlib at package import time
        from classifier.train_classifiers import load_dataset  # noqa: PLC0415
        from digital_twin_v2.constants import LABEL_TO_INT    # noqa: PLC0415

        print("CSVSensorSimulator: loading dataset via classifier pipeline...")
        X, y_str, _ = load_dataset()

        self._pool: dict[int, list[np.ndarray]] = {0: [], 1: [], 2: []}
        for feat, label_str in zip(X, y_str):
            state = LABEL_TO_INT.get(label_str)
            if state is not None:
                self._pool[state].append(feat.astype(np.float32))

        for state, vecs in self._pool.items():
            print(f"  Class {state}: {len(vecs)} runs loaded")

        self._rng = np.random.default_rng(seed)
        self._track_config: list[int] = []

    # ------------------------------------------------------------------
    # BaseSensorSimulator interface
    # ------------------------------------------------------------------

    def get_reading(self, segment_id: int, true_state: int) -> np.ndarray:
        """Sample a random real-run feature vector for this health state."""
        pool = self._pool[true_state]
        idx = int(self._rng.integers(len(pool)))
        return pool[idx]

    def set_track_config(self, config: list[int]) -> None:
        self._track_config = list(config)
