import numpy as np


class BayesianSegmentTracker:
    """
    Maintains a posterior distribution over health states for one track segment.

    Update rule (sequential Bayesian filter):
        posterior[i]  ∝  likelihood[i]  *  prior[i]

    The likelihood is the soft probability vector from the Random Forest
    classifier, approximating P(observation | state=i). Multiplying likelihoods
    across passes is equivalent to running the HMM forward algorithm with a
    stationary transition matrix.

    MIN_BELIEF prevents any state from reaching zero probability, preserving
    the ability to recover from classification errors after a human correction.
    """

    MIN_BELIEF = 0.02
    N_CLASSES = 3

    def __init__(self) -> None:
        self.belief = np.ones(self.N_CLASSES, dtype=np.float64) / self.N_CLASSES

    def update(self, likelihood: np.ndarray) -> None:
        """Multiply current belief by likelihood vector and renormalise."""
        self.belief = self.belief * likelihood
        self.belief = np.clip(self.belief, self.MIN_BELIEF, None)
        self.belief /= self.belief.sum()

    def map_state(self) -> int:
        """Maximum a-posteriori state estimate."""
        return int(np.argmax(self.belief))

    def entropy(self) -> float:
        """Shannon entropy of current belief — low means confident."""
        p = self.belief
        return float(-np.sum(p * np.log(p + 1e-30)))

    def reset(self) -> None:
        self.belief = np.ones(self.N_CLASSES, dtype=np.float64) / self.N_CLASSES

    def human_correction(self, confirmed_state: int) -> None:
        """
        HITL override: collapse belief to near-certain around the operator-confirmed
        state, while keeping MIN_BELIEF on all others so no state is ruled out.
        """
        self.belief = np.full(self.N_CLASSES, self.MIN_BELIEF)
        self.belief[confirmed_state] = 1.0 - (self.N_CLASSES - 1) * self.MIN_BELIEF
        self.belief /= self.belief.sum()
