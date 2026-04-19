import sys
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from .base import BaseSensorSimulator

if TYPE_CHECKING:
    from simulation import DataPool

# Ensure digital_twin/ is importable when fitting from a live DataPool
sys.path.insert(0, str(Path(__file__).parent.parent / "digital_twin"))


class SyntheticSensorSimulator(BaseSensorSimulator):
    """
    Generates feature vectors from per-class Gaussian models.

    Parameters are fit from real DataPool statistics (per-class mean and
    per-feature standard deviation). Sampling is independent per feature
    (diagonal covariance), which is stable even with few training runs.

    Use this for:
    - edge-case / stress testing (noise_scale > 1.0 amplifies variance)
    - running without the data/ directory (load pre-saved .npz parameters)
    - scenarios with no matching real runs (e.g. mixed-severity segments)
    """

    _N_CLASSES = 3

    def __init__(
        self,
        means: dict[int, np.ndarray],
        stds: dict[int, np.ndarray],
        noise_scale: float = 1.0,
        seed: int = 42,
    ) -> None:
        self._means = means          # {state_label: (n_features,) array}
        self._stds = stds            # {state_label: (n_features,) array}
        self._noise_scale = noise_scale
        self._rng = np.random.default_rng(seed)
        self._track_config: list[int] = []

    # ------------------------------------------------------------------
    # BaseSensorSimulator interface
    # ------------------------------------------------------------------

    def get_reading(self, segment_id: int, true_state: int) -> np.ndarray:
        """Sample from the per-class Gaussian model for this health state."""
        mean = self._means[true_state]
        std = self._stds[true_state] * self._noise_scale
        return self._rng.normal(mean, std).astype(np.float32)

    def set_track_config(self, config: list[int]) -> None:
        self._track_config = list(config)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def fit_from_data_pool(
        cls,
        pool: "DataPool",
        noise_scale: float = 1.0,
        seed: int = 42,
    ) -> "SyntheticSensorSimulator":
        """
        Fit class-conditional Gaussian parameters from a loaded DataPool.

        Called once at startup when data/ is available. Use save() afterward
        to persist parameters so the simulator can be loaded without data/.
        """
        X, y = pool.all_features_and_labels()
        means: dict[int, np.ndarray] = {}
        stds: dict[int, np.ndarray] = {}

        for state in range(cls._N_CLASSES):
            mask = y == state
            if not mask.any():
                raise ValueError(
                    f"DataPool has no samples for state {state}. "
                    "Cannot fit SyntheticSensorSimulator."
                )
            means[state] = X[mask].mean(axis=0)
            # Small floor prevents zero-std features from collapsing to a point
            stds[state] = X[mask].std(axis=0) + 1e-8

        return cls(means=means, stds=stds, noise_scale=noise_scale, seed=seed)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: "Path | str") -> None:
        """Persist fitted parameters to a .npz file."""
        path = Path(path)
        np.savez(
            path,
            **{f"means_{s}": self._means[s] for s in range(self._N_CLASSES)},
            **{f"stds_{s}": self._stds[s] for s in range(self._N_CLASSES)},
        )
        print(f"SyntheticSensorSimulator parameters saved -> {path}")

    @classmethod
    def load(
        cls,
        path: "Path | str",
        noise_scale: float = 1.0,
        seed: int = 42,
    ) -> "SyntheticSensorSimulator":
        """Load pre-saved parameters without requiring the data/ directory."""
        path = Path(path)
        data = np.load(path)
        means = {s: data[f"means_{s}"] for s in range(cls._N_CLASSES)}
        stds = {s: data[f"stds_{s}"] for s in range(cls._N_CLASSES)}
        return cls(means=means, stds=stds, noise_scale=noise_scale, seed=seed)
