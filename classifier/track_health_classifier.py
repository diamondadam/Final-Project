"""
Track Health Classifier Pipeline
=================================
Classifies track structural health (Healthy / Degraded / Damaged) from
dual-accelerometer (g4, g5) vibration signals.

Key design decisions derived from examining the raw data:
  - arduino_motion_raw.csv provides train phase (ACCEL/CRUISE/DECEL/REWIND)
    and position (pos_ft) at ~10 Hz.
  - daq_sensors_1000hz.csv provides g4/g5 accelerations at 1000 Hz.
  - Only CRUISE phase data is used: the ~10 ft section where the train runs
    at constant target speed over the track. ACCEL/DECEL/REWIND introduce
    confounding dynamics unrelated to track structure.
  - Features are extracted per POSITION SEGMENT (not per time window).
    Dividing the cruise section into fixed spatial bins means the same
    physical track location always maps to the same feature slot, regardless
    of train speed. This makes features speed-invariant by design.
  - Velocity from arduino is included as a feature to let the model learn
    any residual speed effects.

Label mapping (track type -> health class):
  Steel_3_8_in    -> 0  Healthy  (steel, highest stiffness)
  Aluminum_1_2_in -> 1  Degraded (aluminum, 1/2-in thick)
  Aluminum_3_8_in -> 2  Damaged  (aluminum, 3/8-in thin, lowest stiffness)

Pipeline:
  1. Load arduino + DAQ, align timestamps, filter to CRUISE only
  2. Kalman filter on g4/g5 (noise reduction)
  3. Divide cruise section into N_SEGMENTS position bins
  4. Per-segment feature extraction (time-domain + cross-sensor)
  5. Random Forest classifier with leave-one-run-out cross-validation
"""

import csv
import math
from bisect import bisect_left
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

from scipy.stats import kurtosis, skew
from scipy.signal import welch
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    classification_report, confusion_matrix,
    ConfusionMatrixDisplay, accuracy_score,
)
from sklearn.preprocessing import StandardScaler

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent / "data" / "TrainRuns"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────────
FS           = 1000       # DAQ sample rate (Hz)
N_SEGMENTS   = 5          # divide cruise section into this many position bins
MIN_SEG_SAMP = 30         # skip run if any segment has fewer samples than this

TRACK_LABELS = {
    "Steel_3_8_in":    (0, "Healthy"),
    "Aluminum_1_2_in": (1, "Degraded"),
    "Aluminum_3_8_in": (2, "Damaged"),
}
CLASS_NAMES = ["Healthy", "Degraded", "Damaged"]


# ══════════════════════════════════════════════════════════════════════════════
# Kalman Filter (1-D, constant-position model)
# ══════════════════════════════════════════════════════════════════════════════

class KalmanFilter1D:
    """
    Reduces sensor noise while preserving the structural vibration signal.
    Q: process noise (how fast true acceleration can change).
    R: measurement noise (~variance of sensor noise floor from idle signal).
    """
    def __init__(self, Q: float = 1e-4, R: float = 9.61e-4):
        self.Q = Q; self.R = R
        self.x = 0.0; self.P = 1.0

    def reset(self, v0: float = 0.0):
        self.x = v0; self.P = 1.0

    def filter(self, z: np.ndarray) -> np.ndarray:
        self.reset(z[0])
        out = np.empty_like(z)
        for i, zi in enumerate(z):
            P_pred = self.P + self.Q
            K      = P_pred / (P_pred + self.R)
            self.x = self.x + K * (zi - self.x)
            self.P = (1.0 - K) * P_pred
            out[i] = self.x
        return out


# ══════════════════════════════════════════════════════════════════════════════
# Data Loading & Phase Alignment
# ══════════════════════════════════════════════════════════════════════════════

def load_and_align(run_dir: Path):
    """
    Load arduino_motion_raw.csv and daq_sensors_1000hz.csv for one run.
    Interpolate train position and velocity to every DAQ timestamp.
    Return only rows where phase == CRUISE.

    Returns dict with keys:
        pos_ft  : np.ndarray  - train position (ft) at each DAQ sample
        vel_fps : np.ndarray  - train velocity (fps) at each DAQ sample
        g4      : np.ndarray  - accelerometer 1 (g)
        g5      : np.ndarray  - accelerometer 2 (g)
    or None if the run has no usable CRUISE data.
    """
    ard_path = run_dir / "arduino_motion_raw.csv"
    daq_path = run_dir / "daq_sensors_1000hz.csv"
    if not ard_path.exists() or not daq_path.exists():
        return None

    # Load arduino: list of (time_ms, phase, pos_ft, vel_fps)
    ard = []
    with open(ard_path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                ard.append((
                    int(row["time_ms"]),
                    row["phase"],
                    float(row["pos_ft"]),
                    float(row["vel_fps"]),
                ))
            except (KeyError, ValueError):
                pass
    if not ard:
        return None
    ard_times = [r[0] for r in ard]

    # Load DAQ: list of (time_ms, g4, g5)
    daq = []
    with open(daq_path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                daq.append((
                    int(row["time_ms"]),
                    float(row["g4"]),
                    float(row["g5"]),
                ))
            except (KeyError, ValueError):
                pass
    if not daq:
        return None

    # For each DAQ sample, find the nearest arduino record and read its fields
    pos_list, vel_list, g4_list, g5_list = [], [], [], []
    for t_ms, g4, g5 in daq:
        idx = bisect_left(ard_times, t_ms)
        idx = min(idx, len(ard) - 1)
        phase, pos, vel = ard[idx][1], ard[idx][2], ard[idx][3]
        if phase == "CRUISE":
            pos_list.append(pos)
            vel_list.append(vel)
            g4_list.append(g4)
            g5_list.append(g5)

    if len(g4_list) < N_SEGMENTS * MIN_SEG_SAMP:
        return None

    return {
        "pos_ft":  np.array(pos_list,  dtype=np.float32),
        "vel_fps": np.array(vel_list,  dtype=np.float32),
        "g4":      np.array(g4_list,   dtype=np.float32),
        "g5":      np.array(g5_list,   dtype=np.float32),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Feature Extraction
# ══════════════════════════════════════════════════════════════════════════════

def _seg_features(g4: np.ndarray, g5: np.ndarray, vel: np.ndarray) -> np.ndarray:
    """
    Extract features from one position segment.

    Per-channel (g4, g5):
        rms, mean, std, peak, crest_factor, kurtosis, skewness,
        vel_norm_rms (rms / mean_vel — speed-normalised vibration intensity)

    Cross-sensor:
        pearson_corr        - g4/g5 correlation; drops when vibration is asymmetric
        rms_ratio           - g4_rms / g5_rms; imbalance between sensor locations
        abs_diff_rms        - rms of (g4 - g5); complementary asymmetry measure

    Kinematic (from arduino):
        mean_vel            - mean train velocity in this segment

    Total: 8*2 + 3 + 1 = 20 features per segment
    """
    feats = []

    mean_vel = float(np.mean(vel)) if len(vel) > 0 else 1e-6

    for sig in (g4, g5):
        rms   = float(np.sqrt(np.mean(sig ** 2)))
        mean_ = float(np.mean(sig))
        std   = float(np.std(sig))
        peak  = float(np.max(np.abs(sig)))
        crest = peak / (rms + 1e-12)
        kurt  = float(kurtosis(sig, fisher=True))
        skw   = float(skew(sig))
        vnrms = rms / (mean_vel + 1e-12)   # speed-normalised RMS
        feats.extend([rms, mean_, std, peak, crest, kurt, skw, vnrms])

    # Cross-sensor
    corr      = float(np.corrcoef(g4, g5)[0, 1]) if len(g4) > 1 else 0.0
    rms_ratio = (float(np.sqrt(np.mean(g4**2))) /
                 (float(np.sqrt(np.mean(g5**2))) + 1e-12))
    diff_rms  = float(np.sqrt(np.mean((g4 - g5) ** 2)))
    feats.extend([corr, rms_ratio, diff_rms])

    # Kinematic
    feats.append(mean_vel)

    return np.array(feats, dtype=np.float32)


def extract_run_features(data: dict, kf: KalmanFilter1D) -> np.ndarray:
    """
    Apply Kalman filter then extract per-segment features.
    Returns a flat vector of length N_SEGMENTS * features_per_segment.
    """
    g4_filt = kf.filter(data["g4"]);  kf.reset()
    g5_filt = kf.filter(data["g5"]);  kf.reset()
    pos     = data["pos_ft"]
    vel     = data["vel_fps"]

    pos_min, pos_max = pos.min(), pos.max()
    edges = np.linspace(pos_min, pos_max, N_SEGMENTS + 1)

    seg_feats = []
    for i in range(N_SEGMENTS):
        mask = (pos >= edges[i]) & (pos < edges[i + 1])
        if i == N_SEGMENTS - 1:
            mask = (pos >= edges[i]) & (pos <= edges[i + 1])
        if mask.sum() < MIN_SEG_SAMP:
            return None                # reject run
        seg_feats.append(_seg_features(g4_filt[mask], g5_filt[mask], vel[mask]))

    return np.concatenate(seg_feats)


def feature_names() -> list[str]:
    per_seg = []
    for ch in ("g4", "g5"):
        for stat in ("rms", "mean", "std", "peak", "crest", "kurtosis", "skewness", "vel_norm_rms"):
            per_seg.append(f"{ch}_{stat}")
    per_seg += ["cross_corr", "cross_rms_ratio", "cross_diff_rms", "mean_vel"]
    return [f"seg{s+1}_{f}" for s in range(N_SEGMENTS) for f in per_seg]


# ══════════════════════════════════════════════════════════════════════════════
# Dataset Builder
# ══════════════════════════════════════════════════════════════════════════════

def build_dataset():
    """
    Walk all runs. Returns X (n_runs, n_features), y (n_runs,), groups (n_runs,).
    Each row is one complete run (not one window), which avoids data leakage
    in cross-validation.
    """
    kf = KalmanFilter1D()
    X_all, y_all, grp_all = [], [], []
    run_id = 0
    skipped = 0

    for track_type, (label, state_name) in TRACK_LABELS.items():
        track_dir = BASE_DIR / track_type
        if not track_dir.exists():
            print(f"  [WARN] missing: {track_dir}")
            continue

        for cond_dir in sorted(track_dir.iterdir()):
            for run_dir in sorted(cond_dir.iterdir()):
                data = load_and_align(run_dir)
                if data is None:
                    skipped += 1
                    continue

                feat_vec = extract_run_features(data, kf)
                if feat_vec is None:
                    skipped += 1
                    continue

                rel = run_dir.relative_to(BASE_DIR)
                cruise_n = len(data["g4"])
                print(f"  {state_name:8s}  {str(rel):<70}  "
                      f"cruise={cruise_n:5d} samples  "
                      f"vel={data['vel_fps'].mean():.2f} fps")

                X_all.append(feat_vec)
                y_all.append(label)
                grp_all.append(run_id)
                run_id += 1

    print(f"\n  Loaded {run_id} runs, skipped {skipped}")
    return (
        np.vstack(X_all).astype(np.float32),
        np.array(y_all,   dtype=np.int32),
        np.array(grp_all, dtype=np.int32),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Training & Evaluation
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline():
    print("=" * 80)
    print("Track Health Classifier — Position-Aligned Feature Extraction")
    print("=" * 80)
    X, y, groups = build_dataset()

    n_feats = X.shape[1]
    print(f"\nDataset: {X.shape[0]} runs x {n_feats} features "
          f"({N_SEGMENTS} segments x {n_feats // N_SEGMENTS} features/segment)")
    for idx, name in enumerate(CLASS_NAMES):
        n = int((y == idx).sum())
        print(f"  Class {idx} ({name}): {n} runs")

    feat_names = feature_names()
    assert len(feat_names) == n_feats, \
        f"Name mismatch: {len(feat_names)} names vs {n_feats} features"

    # ── Leave-one-run-out cross-validation ────────────────────────────────────
    # With one row per run (not per window), every row IS its own group, so
    # StratifiedGroupKFold is a clean leave-multiple-runs-out CV.
    print("\n" + "=" * 80)
    print("5-Fold Stratified Cross-Validation")
    print("=" * 80)

    scaler = StandardScaler()
    clf    = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    fold_accs = []
    all_y_true, all_y_pred = [], []

    for fold, (tr_idx, te_idx) in enumerate(cv.split(X, y, groups), 1):
        X_tr_s = scaler.fit_transform(X[tr_idx])
        X_te_s = scaler.transform(X[te_idx])
        clf.fit(X_tr_s, y[tr_idx])
        preds = clf.predict(X_te_s)

        acc = accuracy_score(y[te_idx], preds)
        fold_accs.append(acc)
        all_y_true.extend(y[te_idx].tolist())
        all_y_pred.extend(preds.tolist())
        print(f"  Fold {fold}: accuracy = {acc:.4f}  "
              f"(n_train={len(tr_idx)}, n_test={len(te_idx)})")

    print(f"\n  Mean CV accuracy : {np.mean(fold_accs):.4f} +/- {np.std(fold_accs):.4f}")

    # ── Classification report ──────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("Aggregate Classification Report")
    print("=" * 80)
    print(classification_report(all_y_true, all_y_pred,
                                target_names=CLASS_NAMES, digits=4))

    # ── Confusion matrix ───────────────────────────────────────────────────────
    cm = confusion_matrix(all_y_true, all_y_pred)
    fig, ax = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay(cm, display_labels=CLASS_NAMES).plot(
        ax=ax, colorbar=True, cmap="Blues")
    ax.set_title("Track Health Classifier\n5-Fold CV Confusion Matrix")
    plt.tight_layout()
    cm_path = OUTPUT_DIR / "confusion_matrix.png"
    fig.savefig(cm_path, dpi=150)
    print(f"Confusion matrix saved -> {cm_path}")
    plt.close(fig)

    # ── Feature importance (retrain on full data) ──────────────────────────────
    print("\n" + "=" * 80)
    print("Feature Importance (full dataset refit)")
    print("=" * 80)
    X_s = scaler.fit_transform(X)
    clf.fit(X_s, y)
    imp = clf.feature_importances_
    order = np.argsort(imp)[::-1]

    print(f"  {'Rank':<5}  {'Feature':<40}  {'Importance':>10}")
    print(f"  {'-'*5}  {'-'*40}  {'-'*10}")
    for rank, idx in enumerate(order[:20], 1):
        print(f"  {rank:<5}  {feat_names[idx]:<40}  {imp[idx]:>10.4f}")

    fig, ax = plt.subplots(figsize=(10, 7))
    top = order[:20]
    ax.barh(range(20), imp[top][::-1], color="steelblue", edgecolor="white")
    ax.set_yticks(range(20))
    ax.set_yticklabels([feat_names[i] for i in top[::-1]], fontsize=9)
    ax.set_xlabel("Mean Decrease in Impurity")
    ax.set_title("Top-20 Feature Importances — Track Health Classifier")
    plt.tight_layout()
    fi_path = OUTPUT_DIR / "feature_importance.png"
    fig.savefig(fi_path, dpi=150)
    print(f"\nFeature importance chart saved -> {fi_path}")
    plt.close(fig)

    # ── Bayesian layer input: mean class probabilities ─────────────────────────
    print("\n" + "=" * 80)
    print("Predicted Class Probabilities per True Class")
    print("(Likelihood estimates for Bayesian reasoning layer)")
    print("=" * 80)
    proba = clf.predict_proba(X_s)
    header = f"  {'True Class':<14}" + "".join(f"  P({n})" for n in CLASS_NAMES)
    print(header)
    for cls, name in enumerate(CLASS_NAMES):
        mask = y == cls
        mp   = proba[mask].mean(axis=0)
        print(f"  {name:<14}" + "".join(f"  {p:>7.4f}" for p in mp))

    print("\nDone.")


if __name__ == "__main__":
    run_pipeline()
