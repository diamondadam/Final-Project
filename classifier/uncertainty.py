"""
Sensor-uncertainty-aware prediction via analytical delta-method propagation
plus Monte Carlo sampling at the feature level.

All sensor parameters are read from sensor_config.json — nothing is
hardcoded here.  Strategy:

  1. Load the raw CRUISE-phase signal arrays (g4, g5) once from disk.
  2. Compute the 33 nominal features from the clean signal.
  3. For each feature, derive a 1-σ analytical uncertainty (σ_feat) using
     the delta method: propagate the per-sample sensor noise σ_n through
     the feature formula.  This avoids the cross-correlation destruction
     that would occur if independent noise were added directly to the raw
     signal of each channel.
  4. Draw N_trials feature vectors by adding N(0, σ_feat²) noise to each
     feature independently, building an (N_trials × 33) matrix.
  5. Run the trained sklearn Pipeline on all rows at once and aggregate:
       - modal label  (most frequent predicted class across trials)
       - mean class probabilities across trials
       - confidence   (fraction of trials that agree on the modal label)
       - per-feature nominal value and ±σ (from analytical σ_feat)

Usage
-----
    from classifier.uncertainty import load_sensor_config, predict_with_uncertainty

    cfg   = load_sensor_config()
    model = classifier.load_model("knn")
    result = predict_with_uncertainty(model, daq_path, motion_path, cfg)
"""

import csv
import json
import os
from collections import Counter

import numpy as np

from .train_classifiers import (
    FEATURE_NAMES,
    WINDOW_MS,
    _cruise_window,
    _stats,
    _fft_band_energies,
    _spike_features,
)

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "sensor_config.json")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_sensor_config(path: str = _CONFIG_PATH) -> dict:
    """Load and return the sensor configuration dict from *path*."""
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Raw signal loader (CRUISE phase only)
# ---------------------------------------------------------------------------

def _load_cruise_signals(daq_path: str, motion_path: str) -> tuple[np.ndarray, np.ndarray]:
    """Return (g4, g5) numpy arrays covering only the CRUISE phase."""
    t_min, t_max = _cruise_window(motion_path)
    g4_vals, g5_vals = [], []
    with open(daq_path, newline="") as f:
        for row in csv.DictReader(f):
            t = int(row["time_ms"])
            if t_min <= t <= t_max:
                g4_vals.append(float(row["g4"]))
                g5_vals.append(float(row["g5"]))
    return np.asarray(g4_vals), np.asarray(g5_vals)


# ---------------------------------------------------------------------------
# Feature vector from raw arrays (no file I/O)
# ---------------------------------------------------------------------------

def _features_from_arrays(g4: np.ndarray, g5: np.ndarray) -> np.ndarray:
    """Compute the 33-element feature vector directly from signal arrays."""
    s4 = _stats(g4.tolist())
    s5 = _stats(g5.tolist())
    b4 = _fft_band_energies(g4.tolist())
    b5 = _fft_band_energies(g5.tolist())
    k4 = _spike_features(g4, window=WINDOW_MS)
    k5 = _spike_features(g5, window=WINDOW_MS)

    corr     = float(np.corrcoef(g4, g5)[0, 1]) if len(g4) > 1 else 0.0
    rms4     = s4["rms"] + 1e-12
    rms5     = s5["rms"] + 1e-12
    diff_rms = float(np.sqrt(np.mean((g4 - g5) ** 2))) if len(g4) else 0.0

    return np.asarray([
        s4["rms"], s4["mean"], s4["std"], s4["peak_to_peak"],
        s4["kurtosis"], s4["skewness"], s4["crest_factor"],
        b4["band_low"], b4["band_mid"], b4["band_high"],
        k4["p99_abs"], k4["exceedance_rate"], k4["impulse_factor"],
        k4["max_win_rms"], k4["max_win_kurtosis"],

        s5["rms"], s5["mean"], s5["std"], s5["peak_to_peak"],
        s5["kurtosis"], s5["skewness"], s5["crest_factor"],
        b5["band_low"], b5["band_mid"], b5["band_high"],
        k5["p99_abs"], k5["exceedance_rate"], k5["impulse_factor"],
        k5["max_win_rms"], k5["max_win_kurtosis"],

        corr,
        rms4 / rms5,
        diff_rms,
    ], dtype=float)


# ---------------------------------------------------------------------------
# Analytical delta-method uncertainty per feature
# ---------------------------------------------------------------------------

def compute_feature_sigmas(
    g4: np.ndarray,
    g5: np.ndarray,
    noise_sigma: float,
) -> np.ndarray:
    """
    Return a 1-D array of 1-σ analytical uncertainties for each of the 33
    features, derived by propagating per-sample sensor noise σ_n through
    each feature formula (delta method).

    Derivations used
    ----------------
    Let x be a length-N signal, ε_k ~ iid N(0, σ_n²).

    RMS          σ ≈ σ_n / √(2N)
                 (from ∂RMS/∂x_k = x_k/(N·RMS), summed in quadrature)
    mean         σ = σ_n / √N
    std          σ ≈ σ_n / √(2N)
    peak-to-peak σ ≈ σ_n · √2   (uncertainty in max plus uncertainty in min)
    kurtosis     σ ≈ √(24/N)    (asymptotic result for Gaussian signals)
    skewness     σ ≈ √(6/N)
    crest factor σ/CF ≈ √((σ_peak/peak)² + (σ_RMS/RMS)²)
    FFT band     σ ≈ σ_n · √(2·N_band) / (N · RMS)
                 (energy in band ≈ sum of N_band squared DFT bins, each ~ N(0,σ_n²/N))
    p99_abs      σ ≈ σ_n / (N · φ(Φ⁻¹(0.99)))  [order-statistic stderr]
                 ≈ σ_n / (N · 0.0267)
    exceedance   σ = √(p·(1-p)/N)  [binomial SE; p is the nominal rate]
    impulse fac  σ/IF ≈ √((σ_peak/peak)² + (σ_mean_abs/mean_abs)²)
    max-win RMS  σ ≈ σ_n / √(2·W)   (uncertainty in RMS over a single window)
    max-win kurt σ ≈ √(24/W)
    cross_corr   σ ≈ (1 - r²) / √N   [Fisher's z-transform result]
    rms_ratio    σ/ratio ≈ √2 · σ_n / (√(2N) · min(rms4, rms5))
    diff_rms     σ ≈ √2 · σ_n / √(2N) = σ_n / √N
                 (noise adds in quadrature for each of the two channels)
    """
    N  = len(g4)
    σn = noise_sigma

    if N == 0:
        return np.zeros(len(FEATURE_NAMES))

    # --- Shared building blocks ---
    rms4   = float(np.sqrt(np.mean(g4 ** 2))) + 1e-12
    rms5   = float(np.sqrt(np.mean(g5 ** 2))) + 1e-12
    peak4  = float(np.max(np.abs(g4))) + 1e-12
    peak5  = float(np.max(np.abs(g5))) + 1e-12
    mean_abs4 = float(np.mean(np.abs(g4))) + 1e-12
    mean_abs5 = float(np.mean(np.abs(g5))) + 1e-12
    r     = float(np.corrcoef(g4, g5)[0, 1]) if N > 1 else 0.0
    W     = WINDOW_MS
    ratio = rms4 / rms5

    σ_rms    = σn / np.sqrt(2 * N)
    σ_mean   = σn / np.sqrt(N)
    σ_std    = σn / np.sqrt(2 * N)
    σ_ptp    = σn * np.sqrt(2)
    σ_kurt   = np.sqrt(24.0 / N)
    σ_skew   = np.sqrt(6.0 / N)

    # Crest factor = peak / rms; σ_peak ≈ σ_n (single-sample dominated)
    σ_crest4 = (peak4 / rms4) * np.sqrt((σn / peak4) ** 2 + (σ_rms / rms4) ** 2)
    σ_crest5 = (peak5 / rms5) * np.sqrt((σn / peak5) ** 2 + (σ_rms / rms5) ** 2)

    # FFT band fractions — compute N_band from actual FFT
    freqs = np.fft.rfftfreq(N, d=1.0 / 1000.0)
    n_low  = int(np.sum(freqs < 50))
    n_mid  = int(np.sum((freqs >= 50)  & (freqs < 200)))
    n_high = int(np.sum((freqs >= 200) & (freqs < 500)))
    total_energy = np.mean(g4 ** 2) + 1e-12
    σ_band_low4  = σn * np.sqrt(2 * n_low)  / (N * total_energy ** 0.5)
    σ_band_mid4  = σn * np.sqrt(2 * n_mid)  / (N * total_energy ** 0.5)
    σ_band_high4 = σn * np.sqrt(2 * n_high) / (N * total_energy ** 0.5)
    total_energy5 = np.mean(g5 ** 2) + 1e-12
    σ_band_low5  = σn * np.sqrt(2 * n_low)  / (N * total_energy5 ** 0.5)
    σ_band_mid5  = σn * np.sqrt(2 * n_mid)  / (N * total_energy5 ** 0.5)
    σ_band_high5 = σn * np.sqrt(2 * n_high) / (N * total_energy5 ** 0.5)

    # Spike features
    PDF_AT_P99 = 0.0267          # φ(Φ⁻¹(0.99))
    σ_p99      = σn / (N * PDF_AT_P99)
    exc4 = float(np.mean(np.abs(g4) > (np.mean(g4) + 3 * np.std(g4))))
    exc5 = float(np.mean(np.abs(g5) > (np.mean(g5) + 3 * np.std(g5))))
    σ_exc4 = np.sqrt(max(exc4, 1e-6) * (1 - exc4) / N)
    σ_exc5 = np.sqrt(max(exc5, 1e-6) * (1 - exc5) / N)

    # Impulse factor = peak / mean(|x|)
    σ_if4 = (peak4 / mean_abs4) * np.sqrt((σn / peak4) ** 2 + (σ_mean / mean_abs4) ** 2)
    σ_if5 = (peak5 / mean_abs5) * np.sqrt((σn / peak5) ** 2 + (σ_mean / mean_abs5) ** 2)

    # Windowed features
    σ_win_rms  = σn / np.sqrt(2 * W)
    σ_win_kurt = np.sqrt(24.0 / W)

    # Cross-channel
    σ_corr     = (1 - r ** 2) / np.sqrt(N)
    σ_ratio    = ratio * np.sqrt((σ_rms / rms4) ** 2 + (σ_rms / rms5) ** 2)
    σ_diff_rms = σn / np.sqrt(N)   # √2·σ_n per sample, divided by √(2N)

    return np.asarray([
        σ_rms, σ_mean, σ_std, σ_ptp, σ_kurt, σ_skew, σ_crest4,
        σ_band_low4, σ_band_mid4, σ_band_high4,
        σ_p99, σ_exc4, σ_if4, σ_win_rms, σ_win_kurt,

        σ_rms, σ_mean, σ_std, σ_ptp, σ_kurt, σ_skew, σ_crest5,
        σ_band_low5, σ_band_mid5, σ_band_high5,
        σ_p99, σ_exc5, σ_if5, σ_win_rms, σ_win_kurt,

        σ_corr, σ_ratio, σ_diff_rms,
    ], dtype=float)


# ---------------------------------------------------------------------------
# Monte Carlo prediction (feature-level)
# ---------------------------------------------------------------------------

def predict_with_uncertainty(
    model,
    daq_path: str,
    motion_path: str,
    sensor_cfg: dict,
) -> dict:
    """
    Predict track health with sensor-noise uncertainty quantification.

    Uses analytical delta-method uncertainty per feature (see
    compute_feature_sigmas) and Monte Carlo sampling at the feature level.
    This correctly preserves cross-channel feature statistics (e.g.
    cross_corr) that would be corrupted by adding independent noise to
    the raw signals.

    Parameters
    ----------
    model       : fitted sklearn Pipeline (from classifier.load_model())
    daq_path    : path to daq_sensors_1000hz.csv
    motion_path : path to arduino_motion_raw.csv
    sensor_cfg  : dict returned by load_sensor_config()

    Returns
    -------
    dict with keys:

      label              str   — modal predicted class
      probabilities      dict  — mean predicted P(class) across MC trials
      confidence         float — fraction of trials agreeing on modal label
      label_distribution dict  — count of each label across trials
      n_trials           int
      noise_sigma_g      float — sensor noise floor used
      feature_uncertainty list — per-feature dicts sorted by rel_std:
                                   {name, nominal, sigma, rel_sigma}
    """
    accel_cfg = sensor_cfg["accelerometer"]
    unc_cfg   = sensor_cfg["uncertainty"]

    noise_sigma = accel_cfg["noise_rms_g"]
    n_trials    = int(unc_cfg["monte_carlo_trials"])
    seed        = int(unc_cfg["random_seed"])

    rng = np.random.default_rng(seed)

    # Load clean signals and compute nominal features once
    g4, g5       = _load_cruise_signals(daq_path, motion_path)
    nominal_feat = _features_from_arrays(g4, g5)

    # Analytical 1-σ per feature from sensor noise spec
    feat_sigmas = compute_feature_sigmas(g4, g5, noise_sigma)

    # Monte Carlo: perturb features independently by their analytical σ
    noise_matrix   = rng.normal(0.0, 1.0, size=(n_trials, len(nominal_feat)))
    trial_features = nominal_feat[np.newaxis, :] + noise_matrix * feat_sigmas[np.newaxis, :]

    # Predict all trials at once
    trial_labels = model.predict(trial_features)
    trial_probas = model.predict_proba(trial_features)
    classes      = list(model.classes_)

    label_counts = Counter(trial_labels.tolist())
    modal_label  = label_counts.most_common(1)[0][0]
    confidence   = label_counts[modal_label] / n_trials

    mean_probas = {
        cls: round(float(trial_probas[:, j].mean()), 4)
        for j, cls in enumerate(classes)
    }

    # Per-feature uncertainty summary
    rel_sigma = feat_sigmas / (np.abs(nominal_feat) + 1e-12)
    rel_sigma = np.minimum(rel_sigma, 10.0)   # cap near-zero nominal features

    feature_uncertainty = sorted(
        [
            {
                "name":      FEATURE_NAMES[i],
                "nominal":   round(float(nominal_feat[i]),  6),
                "sigma":     round(float(feat_sigmas[i]),   8),
                "rel_sigma": round(float(rel_sigma[i]),     6),
            }
            for i in range(len(FEATURE_NAMES))
        ],
        key=lambda d: d["rel_sigma"],
        reverse=True,
    )

    return {
        "label":               modal_label,
        "probabilities":       mean_probas,
        "confidence":          round(confidence, 4),
        "label_distribution":  dict(label_counts),
        "n_trials":            n_trials,
        "noise_sigma_g":       noise_sigma,
        "feature_uncertainty": feature_uncertainty,
    }
