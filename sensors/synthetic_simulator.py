import sys
from pathlib import Path

import numpy as np

from .base import BaseSensorSimulator

_ROOT = str(Path(__file__).parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_N_CLASSES = 3


class SyntheticSensorSimulator(BaseSensorSimulator):
    """
    Generates 33-feature vectors from per-class Gaussian models.

    Parameters are fit from the classifier module's processed dataset statistics
    (per-class mean and per-feature standard deviation). Sampling is independent
    per feature (diagonal covariance), which is stable even with few training runs.

    Use this for:
    - edge-case / stress testing (noise_scale > 1.0 amplifies variance)
    - running without the classifier/processed/ directory (load pre-saved .npz)
    - scenarios with no matching real runs (e.g. mixed-severity segments)
    """

    def __init__(
        self,
        means: dict[int, np.ndarray],
        stds: dict[int, np.ndarray],
        noise_scale: float = 1.0,
        seed: int = 42,
    ) -> None:
        self._means = means
        self._stds = stds
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
    def fit_from_dataset(
        cls,
        noise_scale: float = 1.0,
        seed: int = 42,
    ) -> "SyntheticSensorSimulator":
        """
        Fit class-conditional Gaussian parameters from the classifier dataset.

        Calls classifier.train_classifiers.load_dataset() internally.
        Use save() afterward to persist parameters for offline use.
        """
        from classifier.train_classifiers import load_dataset  # noqa: PLC0415
        from digital_twin_v2.constants import LABEL_TO_INT     # noqa: PLC0415

        X, y_str, _ = load_dataset()
        means: dict[int, np.ndarray] = {}
        stds: dict[int, np.ndarray] = {}

        for state in range(_N_CLASSES):
            label_str = list(LABEL_TO_INT.keys())[state]
            mask = y_str == label_str
            if not mask.any():
                raise ValueError(
                    f"Dataset has no samples for class '{label_str}'. "
                    "Cannot fit SyntheticSensorSimulator."
                )
            means[state] = X[mask].mean(axis=0)
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
            **{f"means_{s}": self._means[s] for s in range(_N_CLASSES)},
            **{f"stds_{s}": self._stds[s] for s in range(_N_CLASSES)},
        )
        print(f"SyntheticSensorSimulator parameters saved -> {path}")

    @classmethod
    def load(
        cls,
        path: "Path | str",
        noise_scale: float = 1.0,
        seed: int = 42,
    ) -> "SyntheticSensorSimulator":
        """Load pre-saved parameters without requiring the classifier/processed/ directory."""
        path = Path(path)
        data = np.load(path)
        means = {s: data[f"means_{s}"] for s in range(_N_CLASSES)}
        stds = {s: data[f"stds_{s}"] for s in range(_N_CLASSES)}
        return cls(means=means, stds=stds, noise_scale=noise_scale, seed=seed)
