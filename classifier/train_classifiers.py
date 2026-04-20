"""
Train and evaluate two track-health classifiers:
  1. K-Nearest Neighbours (KNN)
  2. Gradient Boosting (GBM)

Data source: classifier/processed/<material>/<condition>/<run_id>/
  - daq_sensors_1000hz.csv   (1 kHz accelerometer: g4, g5)
  - arduino_motion_raw.csv   (10 Hz motion: phase, time_ms)
  - description.json         (label, metadata)

Train/test split is grouped by source_run_id so augmented copies of a run
always land in the same fold as their original — no label leakage.

Outputs written to classifier/output/:
  - confusion_knn.png
  - confusion_gbm.png
  - feature_importance_gbm.png
  - results.json
"""

import csv
import json
import math
import os
import collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import joblib

from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import GroupShuffleSplit, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    classification_report, confusion_matrix, ConfusionMatrixDisplay, balanced_accuracy_score
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE        = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT   = os.path.join(HERE, "processed")
OUTPUT_DIR  = os.path.join(HERE, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

RANDOM_SEED = 42
TEST_SIZE   = 0.20
LABELS      = ["Healthy", "Degraded", "Damaged"]   # display order

# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------
def _cruise_window(motion_path: str) -> tuple[int, int]:
    times = []
    with open(motion_path, newline="") as f:
        for row in csv.DictReader(f):
            if row["phase"] == "CRUISE":
                times.append(int(row["time_ms"]))
    return (min(times), max(times)) if times else (0, 0)


def _stats(values: list[float]) -> dict:
    """Return a dict of scalar statistics for a 1-D signal."""
    a = np.asarray(values, dtype=float)
    if len(a) == 0:
        return {k: 0.0 for k in ("rms", "mean", "std", "peak_to_peak",
                                   "kurtosis", "skewness", "crest_factor")}
    rms  = float(np.sqrt(np.mean(a ** 2)))
    peak = float(np.max(np.abs(a)))
    return {
        "rms":          rms,
        "mean":         float(np.mean(a)),
        "std":          float(np.std(a)),
        "peak_to_peak": float(np.ptp(a)),
        "kurtosis":     float(
            np.mean((a - np.mean(a)) ** 4) / (np.std(a) ** 4 + 1e-12)
        ),
        "skewness":     float(
            np.mean((a - np.mean(a)) ** 3) / (np.std(a) ** 3 + 1e-12)
        ),
        "crest_factor": peak / (rms + 1e-12),
    }


def _fft_band_energies(values: list[float], fs: float = 1000.0) -> dict:
    """
    Normalised energy in three frequency bands (as fraction of total):
      low  : 0 – 50 Hz
      mid  : 50 – 200 Hz
      high : 200 – 500 Hz
    """
    a   = np.asarray(values, dtype=float)
    n   = len(a)
    if n < 8:
        return {"band_low": 0.0, "band_mid": 0.0, "band_high": 0.0}
    mag   = np.abs(np.fft.rfft(a)) ** 2
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    total = mag.sum() + 1e-12
    return {
        "band_low":  float(mag[freqs <  50].sum()  / total),
        "band_mid":  float(mag[(freqs >= 50) & (freqs < 200)].sum() / total),
        "band_high": float(mag[(freqs >= 200) & (freqs < 500)].sum() / total),
    }


WINDOW_MS = 50   # sliding window size for local spike features


def _spike_features(a: np.ndarray, window: int = WINDOW_MS) -> dict:
    """
    Features designed to surface brief, isolated spikes that aggregate
    statistics (RMS, kurtosis) dilute when computed over the full signal.

      p99_abs         : 99th percentile of |a| — spike amplitude proxy
      exceedance_rate : fraction of samples > mean + 3σ — spike frequency
      impulse_factor  : max(|a|) / mean(|a|) — spikier than crest_factor for
                        signals where the mean is near zero
      max_win_rms     : max RMS over sliding `window`-sample windows
      max_win_kurtosis: max kurtosis over sliding windows — a single window
                        containing a spike will have extreme kurtosis even if
                        the full-signal kurtosis is near-Gaussian
    """
    if len(a) < window:
        return {k: 0.0 for k in ("p99_abs", "exceedance_rate",
                                  "impulse_factor", "max_win_rms", "max_win_kurtosis")}

    abs_a  = np.abs(a)
    mean_a = np.mean(a)
    std_a  = np.std(a) + 1e-12

    p99            = float(np.percentile(abs_a, 99))
    exceedance     = float(np.mean(abs_a > (mean_a + 3 * std_a)))
    impulse_factor = float(abs_a.max() / (np.mean(abs_a) + 1e-12))

    # Sliding window — use stride_tricks for efficiency
    shape   = (len(a) - window + 1, window)
    strides = (a.strides[0], a.strides[0])
    wins    = np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)

    win_rms  = np.sqrt(np.mean(wins ** 2, axis=1))
    win_mu   = np.mean(wins, axis=1, keepdims=True)
    win_std  = np.std(wins, axis=1) + 1e-12
    win_kurt = np.mean((wins - win_mu) ** 4, axis=1) / (win_std ** 4)

    return {
        "p99_abs":          p99,
        "exceedance_rate":  exceedance,
        "impulse_factor":   impulse_factor,
        "max_win_rms":      float(win_rms.max()),
        "max_win_kurtosis": float(win_kurt.max()),
    }


def extract_features(daq_path: str, motion_path: str) -> np.ndarray:
    """
    Return a 1-D feature vector for one run.

    Features (33 total):
      g4: rms, mean, std, peak_to_peak, kurtosis, skewness, crest_factor,
          band_low, band_mid, band_high,
          p99_abs, exceedance_rate, impulse_factor,
          max_win_rms, max_win_kurtosis                                      (15)
      g5: same 15                                                            (15)
      cross: pearson_corr, rms_ratio, diff_rms                               (3)
    """
    t_min, t_max = _cruise_window(motion_path)

    g4_vals, g5_vals = [], []
    with open(daq_path, newline="") as f:
        for row in csv.DictReader(f):
            t = int(row["time_ms"])
            if t_min <= t <= t_max:
                g4_vals.append(float(row["g4"]))
                g5_vals.append(float(row["g5"]))

    s4 = _stats(g4_vals)
    s5 = _stats(g5_vals)
    b4 = _fft_band_energies(g4_vals)
    b5 = _fft_band_energies(g5_vals)

    g4 = np.asarray(g4_vals)
    g5 = np.asarray(g5_vals)

    k4 = _spike_features(g4)
    k5 = _spike_features(g5)

    if len(g4) > 1 and len(g5) > 1:
        corr = float(np.corrcoef(g4, g5)[0, 1])
    else:
        corr = 0.0

    rms4     = s4["rms"] + 1e-12
    rms5     = s5["rms"] + 1e-12
    diff_rms = float(np.sqrt(np.mean((g4 - g5) ** 2))) if len(g4) else 0.0

    feat = [
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
    ]
    return np.asarray(feat, dtype=float)


FEATURE_NAMES = [
    "g4_rms", "g4_mean", "g4_std", "g4_ptp", "g4_kurtosis", "g4_skewness", "g4_crest",
    "g4_band_low", "g4_band_mid", "g4_band_high",
    "g4_p99_abs", "g4_exceedance_rate", "g4_impulse_factor",
    "g4_max_win_rms", "g4_max_win_kurtosis",

    "g5_rms", "g5_mean", "g5_std", "g5_ptp", "g5_kurtosis", "g5_skewness", "g5_crest",
    "g5_band_low", "g5_band_mid", "g5_band_high",
    "g5_p99_abs", "g5_exceedance_rate", "g5_impulse_factor",
    "g5_max_win_rms", "g5_max_win_kurtosis",

    "cross_corr", "rms_ratio", "diff_rms",
]


# ---------------------------------------------------------------------------
# Dataset loader
# ---------------------------------------------------------------------------
def load_dataset() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns:
        X      : (n_runs, n_features) float array
        y      : (n_runs,) string labels
        groups : (n_runs,) source_run_id strings  — used for grouped splitting
    """
    X_list, y_list, g_list = [], [], []

    for material in sorted(os.listdir(DATA_ROOT)):
        mat_path = os.path.join(DATA_ROOT, material)
        if not os.path.isdir(mat_path):
            continue
        for condition in sorted(os.listdir(mat_path)):
            cond_path = os.path.join(mat_path, condition)
            if not os.path.isdir(cond_path):
                continue
            for run_id in sorted(os.listdir(cond_path)):
                run_path    = os.path.join(cond_path, run_id)
                daq_path    = os.path.join(run_path, "daq_sensors_1000hz.csv")
                motion_path = os.path.join(run_path, "arduino_motion_raw.csv")
                desc_path   = os.path.join(run_path, "description.json")

                if not all(os.path.exists(p) for p in (daq_path, motion_path, desc_path)):
                    continue

                desc = json.load(open(desc_path))
                feat = extract_features(daq_path, motion_path)

                X_list.append(feat)
                y_list.append(desc["health_label"])
                g_list.append(desc["source_run_id"])

    return (
        np.array(X_list, dtype=float),
        np.array(y_list),
        np.array(g_list),
    )


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------
def plot_confusion(y_true, y_pred, title: str, out_path: str) -> None:
    cm = confusion_matrix(y_true, y_pred, labels=LABELS)
    fig, ax = plt.subplots(figsize=(6, 5))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=LABELS)
    disp.plot(ax=ax, colorbar=True, cmap="Blues")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_path}")


def plot_feature_importance(importances: np.ndarray, title: str, out_path: str) -> None:
    idx    = np.argsort(importances)[-20:]  # top 20
    names  = [FEATURE_NAMES[i] for i in idx]
    values = importances[idx]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(names, values, color="steelblue")
    ax.set_xlabel("Importance")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("Loading dataset ...")
    X, y, groups = load_dataset()
    print(f"  {len(X)} runs, {X.shape[1]} features")
    print(f"  Label counts: {dict(zip(*np.unique(y, return_counts=True)))}")

    # --- Train / test split grouped by source_run_id ----------------------
    splitter = GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE, random_state=RANDOM_SEED)
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))

    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    print(f"\nTrain: {len(X_train)} | Test: {len(X_test)}")
    print(f"  Train labels: {dict(zip(*np.unique(y_train, return_counts=True)))}")
    print(f"  Test labels:  {dict(zip(*np.unique(y_test,  return_counts=True)))}")

    # --- KNN ---------------------------------------------------------------
    print("\n--- KNN ---")
    knn_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("knn",    KNeighborsClassifier(n_neighbors=7, metric="euclidean", weights="distance")),
    ])

    # Cross-validate on training set (grouped folds)
    cv_knn = cross_val_score(
        knn_pipe, X_train, y_train,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED),
        scoring="balanced_accuracy",
    )
    print(f"  CV balanced-accuracy: {cv_knn.mean():.3f} ± {cv_knn.std():.3f}")

    knn_pipe.fit(X_train, y_train)
    y_pred_knn = knn_pipe.predict(X_test)

    print(f"  Test balanced-accuracy: {balanced_accuracy_score(y_test, y_pred_knn):.3f}")
    print(classification_report(y_test, y_pred_knn, target_names=LABELS, zero_division=0))
    plot_confusion(y_test, y_pred_knn, "KNN — Confusion Matrix",
                   os.path.join(OUTPUT_DIR, "confusion_knn.png"))

    # --- Gradient Boosting -------------------------------------------------
    print("\n--- Gradient Boosting ---")
    gbm_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("gbm",    GradientBoostingClassifier(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=4,
            subsample=0.8,
            random_state=RANDOM_SEED,
        )),
    ])

    cv_gbm = cross_val_score(
        gbm_pipe, X_train, y_train,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED),
        scoring="balanced_accuracy",
    )
    print(f"  CV balanced-accuracy: {cv_gbm.mean():.3f} ± {cv_gbm.std():.3f}")

    gbm_pipe.fit(X_train, y_train)
    y_pred_gbm = gbm_pipe.predict(X_test)

    print(f"  Test balanced-accuracy: {balanced_accuracy_score(y_test, y_pred_gbm):.3f}")
    print(classification_report(y_test, y_pred_gbm, target_names=LABELS, zero_division=0))
    plot_confusion(y_test, y_pred_gbm, "Gradient Boosting — Confusion Matrix",
                   os.path.join(OUTPUT_DIR, "confusion_gbm.png"))

    importances = gbm_pipe.named_steps["gbm"].feature_importances_
    plot_feature_importance(importances, "GBM — Top Feature Importances",
                            os.path.join(OUTPUT_DIR, "feature_importance_gbm.png"))

    # --- Persist trained models -------------------------------------------
    joblib.dump(knn_pipe, os.path.join(OUTPUT_DIR, "model_knn.joblib"))
    joblib.dump(gbm_pipe, os.path.join(OUTPUT_DIR, "model_gbm.joblib"))
    print(f"\nModels saved to {OUTPUT_DIR}")

    # --- Save results summary ---------------------------------------------
    results = {
        "n_train": int(len(X_train)),
        "n_test":  int(len(X_test)),
        "knn": {
            "k": 7,
            "cv_balanced_accuracy_mean": round(float(cv_knn.mean()), 4),
            "cv_balanced_accuracy_std":  round(float(cv_knn.std()),  4),
            "test_balanced_accuracy":    round(float(balanced_accuracy_score(y_test, y_pred_knn)), 4),
        },
        "gbm": {
            "n_estimators": 300,
            "learning_rate": 0.05,
            "cv_balanced_accuracy_mean": round(float(cv_gbm.mean()), 4),
            "cv_balanced_accuracy_std":  round(float(cv_gbm.std()),  4),
            "test_balanced_accuracy":    round(float(balanced_accuracy_score(y_test, y_pred_gbm)), 4),
            "top_features": [
                {"feature": FEATURE_NAMES[i], "importance": round(float(importances[i]), 4)}
                for i in np.argsort(importances)[::-1][:10]
            ],
        },
    }
    results_path = os.path.join(OUTPUT_DIR, "results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    main()
