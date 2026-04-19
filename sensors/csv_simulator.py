import random
import sys
from pathlib import Path

import numpy as np

from .base import BaseSensorSimulator

_DIGITAL_TWIN_DIR = str(Path(__file__).parent.parent / "digital_twin")


class CSVSensorSimulator(BaseSensorSimulator):
    """
    Replays real accelerometer runs from the dataset.

    Draws feature vectors from DataPool — the same pool used by simulation.py —
    so sensor noise and run-to-run variability are authentic. Every call to
    get_reading() returns a randomly sampled run for the requested health state.

    Use this for realistic fidelity testing and the final demo.
    """

    def __init__(self, seed: int = 42) -> None:
        # Lazy import: simulation.py pulls in pyomo at module level, so we defer
        # until instantiation rather than paying the import cost (and requiring
        # pyomo to be installed) just from importing the sensors package.
        if _DIGITAL_TWIN_DIR not in sys.path:
            sys.path.insert(0, _DIGITAL_TWIN_DIR)
        from simulation import DataPool  # noqa: PLC0415

        print("CSVSensorSimulator: loading DataPool from CSV files...")
        self._pool = DataPool()
        self._rng = random.Random(seed)
        self._track_config: list[int] = []

    # ------------------------------------------------------------------
    # BaseSensorSimulator interface
    # ------------------------------------------------------------------

    def get_reading(self, segment_id: int, true_state: int) -> np.ndarray:
        """Sample a random real-run feature vector for this health state."""
        return self._pool.sample(true_state, self._rng)

    def set_track_config(self, config: list[int]) -> None:
        self._track_config = list(config)
