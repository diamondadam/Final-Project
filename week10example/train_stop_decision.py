"""
Week 10 Assignment: Train Stop Decision Function
Digital Twin System - Safety Decision Making

Derived from analysis of 108 runs across Steel_3_8_in, Aluminum_1_2_in,
and Aluminum_3_8_in track configurations with varying loads.

Observed acceleration statistics (g4/g5 sensors, 4.3M samples):
  - Global mean:     ~0.026g
  - Global std:      ~0.031g
  - 99th percentile: ~0.126g
  - 99.9th percentile: ~0.168g
  - Observed maximum: ~0.244g (all conditions, all loads)
"""

import math
from collections import deque
from typing import Union


# ── Thresholds derived from empirical data ─────────────────────────────────────
# Hard peak stop: 25% safety margin above the observed absolute maximum (~0.244g)
PEAK_THRESHOLD_G   = 0.30

# Sustained vibration stop: RMS over a window well above normal cruise (~0.076g mean)
# Set at ~2× the 99.9th percentile to allow brief spikes but catch sustained exceedance
RMS_THRESHOLD_G    = 0.15

# Statistical anomaly: z-score relative to the run's own running statistics
# Conservative k=6 so a single transient doesn't falsely trigger
ZSCORE_THRESHOLD   = 6.0

# Minimum samples required before statistical checks become active
MIN_SAMPLES        = 50

# Rolling window length (samples). At 1000 Hz this is 100 ms.
WINDOW_SIZE        = 100

# Safety factor applied on top of all thresholds when uncertainty is flagged
SAFETY_MARGIN      = 0.90          # tighten thresholds by 10 % when uncertain


def should_stop_train(
    accel_series: list[float],
    *,
    window_size: int = WINDOW_SIZE,
    safety_margin: float = 1.0,
) -> dict:
    """
    Decide whether the train should stop based on acceleration measurements.

    Parameters
    ----------
    accel_series : list[float]
        Acceleration time-series in g-units (absolute or signed).
        Typically the g4 or g5 channel from daq_sensors_1000hz.csv,
        or the acc_fps2 column from arduino_motion_raw.csv converted to g.
        Only the most recent `window_size` samples need to be provided for
        real-time use; the full history is also accepted.
    window_size : int
        Number of samples in the analysis window (default 100 → 100 ms at 1 kHz).
    safety_margin : float
        Multiplier in (0, 1] that tightens all thresholds when uncertainty is
        present (e.g. sensor noise flagged upstream).  Pass SAFETY_MARGIN (0.90)
        when the caller has reason to be conservative.

    Returns
    -------
    dict with keys:
        "decision"   : "CONTINUE" | "STOP"
        "reason"     : human-readable explanation
        "peak_g"     : float  – peak absolute value in the window
        "rms_g"      : float  – RMS of the window
        "zscore"     : float  – z-score of the latest sample vs. run history
        "n_samples"  : int    – number of samples analysed
    """
    if not accel_series:
        return _result("CONTINUE", "No data received yet.", 0.0, 0.0, 0.0, 0)

    # Work with absolute values; signed direction is irrelevant for safety
    abs_series = [abs(x) for x in accel_series]
    n = len(abs_series)

    # Most-recent window for fast, real-time checks
    window = abs_series[-window_size:]

    # ── Compute window statistics ──────────────────────────────────────────────
    peak_g = max(window)
    rms_g  = math.sqrt(sum(x * x for x in window) / len(window))

    # ── Compute z-score against full run history ───────────────────────────────
    zscore = 0.0
    if n >= MIN_SAMPLES:
        mean = sum(abs_series) / n
        variance = sum((x - mean) ** 2 for x in abs_series) / n
        std = math.sqrt(variance) if variance > 0 else 1e-9
        zscore = (abs_series[-1] - mean) / std

    # ── Apply safety margin to thresholds ─────────────────────────────────────
    sm = max(0.01, min(1.0, safety_margin))   # clamp to (0, 1]
    eff_peak   = PEAK_THRESHOLD_G  * sm
    eff_rms    = RMS_THRESHOLD_G   * sm
    eff_zscore = ZSCORE_THRESHOLD / sm        # tighter margin → lower z-threshold

    # ── Decision logic ─────────────────────────────────────────────────────────
    # Check 1: instantaneous peak (hardest safety limit)
    if peak_g > eff_peak:
        return _result(
            "STOP",
            f"Peak acceleration {peak_g:.3f}g exceeds safety limit {eff_peak:.3f}g.",
            peak_g, rms_g, zscore, n,
        )

    # Check 2: sustained high vibration (catches gradual build-up)
    if rms_g > eff_rms:
        return _result(
            "STOP",
            f"Sustained RMS {rms_g:.3f}g exceeds limit {eff_rms:.3f}g "
            f"over {len(window)}-sample window.",
            peak_g, rms_g, zscore, n,
        )

    # Check 3: statistical anomaly relative to run baseline
    if n >= MIN_SAMPLES and zscore > eff_zscore:
        return _result(
            "STOP",
            f"Anomalous acceleration spike (z={zscore:.1f} > {eff_zscore:.1f}). "
            f"Current sample {abs_series[-1]:.3f}g is {zscore:.1f}σ above run mean.",
            peak_g, rms_g, zscore, n,
        )

    return _result("CONTINUE", "All checks passed.", peak_g, rms_g, zscore, n)


# ── Streaming / real-time helper ───────────────────────────────────────────────

class RealTimeStopMonitor:
    """
    Lightweight stateful wrapper for real-time (sample-by-sample) use.

    Maintains an O(1)-memory sliding window and O(n) history deque so the
    caller never needs to manage state between samples.

    Example
    -------
    >>> monitor = RealTimeStopMonitor()
    >>> for sample in sensor_stream:
    ...     result = monitor.update(sample)
    ...     if result["decision"] == "STOP":
    ...         halt_train()
    ...         break
    """

    def __init__(
        self,
        window_size: int = WINDOW_SIZE,
        history_size: int = 10_000,
        safety_margin: float = 1.0,
    ):
        self._window   = deque(maxlen=window_size)
        self._history  = deque(maxlen=history_size)
        self._safety   = safety_margin
        # Running mean/variance via Welford's online algorithm
        self._n        = 0
        self._mean     = 0.0
        self._M2       = 0.0            # sum of squared deviations

    def update(self, accel_g: float) -> dict:
        """
        Ingest one new acceleration sample and return the current decision.

        Parameters
        ----------
        accel_g : float
            Latest acceleration reading in g-units (signed or absolute).

        Returns
        -------
        Same dict structure as `should_stop_train`.
        """
        val = abs(accel_g)
        self._window.append(val)
        self._history.append(val)

        # Welford's online mean/variance update
        self._n += 1
        delta = val - self._mean
        self._mean += delta / self._n
        self._M2   += delta * (val - self._mean)

        window_list = list(self._window)
        peak_g = max(window_list)
        rms_g  = math.sqrt(sum(x * x for x in window_list) / len(window_list))

        zscore = 0.0
        if self._n >= MIN_SAMPLES and self._M2 > 0:
            std = math.sqrt(self._M2 / self._n)
            zscore = (val - self._mean) / std

        sm = max(0.01, min(1.0, self._safety))
        eff_peak   = PEAK_THRESHOLD_G  * sm
        eff_rms    = RMS_THRESHOLD_G   * sm
        eff_zscore = ZSCORE_THRESHOLD / sm

        if peak_g > eff_peak:
            return _result(
                "STOP",
                f"Peak {peak_g:.3f}g > limit {eff_peak:.3f}g.",
                peak_g, rms_g, zscore, self._n,
            )
        if rms_g > eff_rms:
            return _result(
                "STOP",
                f"RMS {rms_g:.3f}g > limit {eff_rms:.3f}g.",
                peak_g, rms_g, zscore, self._n,
            )
        if self._n >= MIN_SAMPLES and zscore > eff_zscore:
            return _result(
                "STOP",
                f"Anomaly z={zscore:.1f} > {eff_zscore:.1f}.",
                peak_g, rms_g, zscore, self._n,
            )

        return _result("CONTINUE", "All checks passed.", peak_g, rms_g, zscore, self._n)


# ── Internal helper ────────────────────────────────────────────────────────────

def _result(decision, reason, peak_g, rms_g, zscore, n_samples):
    return {
        "decision":  decision,
        "reason":    reason,
        "peak_g":    round(peak_g, 6),
        "rms_g":     round(rms_g, 6),
        "zscore":    round(zscore, 3),
        "n_samples": n_samples,
    }


# ── Demo / validation ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import csv, os

    BASE = os.path.join(
        os.path.dirname(__file__),
        "2025-11-04 Final Project Train Runs",
    )

    print("=" * 70)
    print("Batch validation: should_stop_train() on all DAQ runs")
    print("=" * 70)

    for root, dirs, files in os.walk(BASE):
        for fname in files:
            if fname != "daq_sensors_1000hz.csv":
                continue

            path = os.path.join(root, fname)
            g4_vals = []
            with open(path, newline="") as fh:
                for row in csv.DictReader(fh):
                    try:
                        g4_vals.append(float(row["g4"]))
                    except (KeyError, ValueError):
                        pass

            if not g4_vals:
                continue

            result = should_stop_train(g4_vals)
            label  = os.path.relpath(root, BASE)
            flag   = "  <<< STOP" if result["decision"] == "STOP" else ""
            print(
                f"{label:<60}  "
                f"peak={result['peak_g']:.3f}g  "
                f"rms={result['rms_g']:.3f}g  "
                f"z={result['zscore']:5.1f}  "
                f"{result['decision']}{flag}"
            )

    print()
    print("=" * 70)
    print("Real-time monitor demo: injecting a synthetic spike")
    print("=" * 70)

    import random
    random.seed(42)
    normal = [random.gauss(0.026, 0.031) for _ in range(500)]
    spike  = normal + [0.35]                       # one dangerous spike

    monitor = RealTimeStopMonitor(safety_margin=SAFETY_MARGIN)
    for i, sample in enumerate(spike):
        r = monitor.update(sample)
        if r["decision"] == "STOP" or i == len(spike) - 1:
            print(f"  sample #{i+1:4d}  accel={sample:.4f}g  → {r['decision']}: {r['reason']}")
        if r["decision"] == "STOP":
            break
