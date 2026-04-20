from abc import ABC, abstractmethod

import numpy as np


class BaseSensorSimulator(ABC):
    """
    Common interface for all sensor simulators.
    DigitalTwin is typed against this — swap CSV ↔ Synthetic without touching
    the orchestrator.
    """

    @abstractmethod
    def get_reading(self, segment_id: int, true_state: int) -> np.ndarray:
        """
        Return one feature vector for the given segment and health state.

        Parameters
        ----------
        segment_id  : index of the track segment being observed (0-based)
        true_state  : ground-truth health label (0=Healthy, 1=Degraded, 2=Damaged)

        Returns
        -------
        np.ndarray of shape (N_SEGMENTS * features_per_segment,) — same shape the
        classifier expects from extract_run_features().
        """

    @abstractmethod
    def set_track_config(self, config: list[int]) -> None:
        """Update ground-truth health state per segment (0/1/2 per index)."""
