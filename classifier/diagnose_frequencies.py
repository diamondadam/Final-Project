"""
Diagnostic: find where PSDs actually differ between track types.
Plots full-spectrum PSD differences and time-domain feature distributions.
"""
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.signal import welch
from scipy.stats import kurtosis, skew, f_oneway

BASE_DIR   = Path(__file__).parent.parent / "data" / "TrainRuns"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

FS          = 1000
WINDOW_SIZE = 512

TRACK_LABELS = {
    "Steel_3_8_in":    "Healthy",
    "Aluminum_1_2_in": "Degraded",
    "Aluminum_3_8_in": "Damaged",
}

# Collect per-window PSDs and time-domain stats
psds   = {n: [] for n in TRACK_LABELS.values()}
td_rms = {n: [] for n in TRACK_LABELS.values()}
td_kur = {n: [] for n in TRACK_LABELS.values()}
td_cre = {n: [] for n in TRACK_LABELS.values()}

for track_type, state_name in TRACK_LABELS.items():
    track_dir = BASE_DIR / track_type
    for condition_dir in sorted(track_dir.iterdir()):
        for run_dir in sorted(condition_dir.iterdir()):
            csv_path = run_dir / "daq_sensors_1000hz.csv"
            if not csv_path.exists():
                continue
            g4 = []
            with open(csv_path, newline="") as fh:
                for row in csv.DictReader(fh):
                    try:
                        g4.append(float(row["g4"]))
                    except (KeyError, ValueError):
                        pass
            if len(g4) < WINDOW_SIZE:
                continue
            g4 = np.array(g4, dtype=np.float32)
            for start in range(0, len(g4) - WINDOW_SIZE, 256):
                win = g4[start:start+WINDOW_SIZE]
                f, p = welch(win, fs=FS, nperseg=WINDOW_SIZE)
                psds[state_name].append(p)
                rms = float(np.sqrt(np.mean(win**2)))
                td_rms[state_name].append(rms)
                td_kur[state_name].append(float(kurtosis(win, fisher=True)))
                td_cre[state_name].append(float(np.max(np.abs(win)) / (rms + 1e-12)))

freqs = f
colors = {"Healthy": "green", "Degraded": "orange", "Damaged": "red"}

# ── 1. Mean PSD per class (full spectrum) ─────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

ax = axes[0, 0]
for name in ["Healthy", "Degraded", "Damaged"]:
    mean_p = np.mean(psds[name], axis=0)
    ax.semilogy(freqs, mean_p, label=name, color=colors[name], linewidth=1.5)
ax.set_xlabel("Frequency (Hz)")
ax.set_ylabel("PSD (g^2/Hz)")
ax.set_title("Mean PSD — Full Spectrum (0-500 Hz)")
ax.legend(); ax.grid(True, which="both", alpha=0.3)

ax = axes[0, 1]
for name in ["Healthy", "Degraded", "Damaged"]:
    mean_p = np.mean(psds[name], axis=0)
    mask = (freqs >= 5) & (freqs <= 100)
    ax.semilogy(freqs[mask], mean_p[mask], label=name, color=colors[name], linewidth=1.5)
ax.set_xlabel("Frequency (Hz)")
ax.set_ylabel("PSD (g^2/Hz)")
ax.set_title("Mean PSD — 5-100 Hz Zoom")
ax.legend(); ax.grid(True, which="both", alpha=0.3)

# ── 2. F-statistic per frequency bin (where do classes differ most?) ──────────
ax = axes[1, 0]
f_stats = []
for i in range(len(freqs)):
    bin_data = [np.array(psds[n])[:, i] for n in ["Healthy", "Degraded", "Damaged"]]
    try:
        stat, _ = f_oneway(*bin_data)
        f_stats.append(stat if np.isfinite(stat) else 0)
    except Exception:
        f_stats.append(0)
f_stats = np.array(f_stats)
ax.plot(freqs, f_stats, color="purple", linewidth=1)
ax.set_xlabel("Frequency (Hz)")
ax.set_ylabel("F-statistic (ANOVA)")
ax.set_title("Discriminative Power per Frequency Bin\n(higher = more separable)")
ax.grid(True, alpha=0.3)
top10_idx = np.argsort(f_stats)[-10:][::-1]
print("Top-10 most discriminative frequency bins:")
for i in top10_idx:
    print(f"  {freqs[i]:.2f} Hz  F={f_stats[i]:.2f}")

# Mark top bins
for i in top10_idx[:5]:
    ax.axvline(freqs[i], color="red", alpha=0.4, linewidth=1, linestyle="--")

# ── 3. Time-domain feature distributions ──────────────────────────────────────
ax = axes[1, 1]
for feat_name, data_dict in [("RMS", td_rms), ("Kurtosis", td_kur), ("Crest", td_cre)]:
    pass  # use boxplot below

ax.set_visible(False)
fig.delaxes(axes[1, 1])

# Replace with 3 boxplots
ax1 = fig.add_subplot(2, 3, 4)
ax2 = fig.add_subplot(2, 3, 5)
ax3 = fig.add_subplot(2, 3, 6)

names = ["Healthy", "Degraded", "Damaged"]
for ax_td, feat_name, data_dict in [
    (ax1, "RMS (g)", td_rms),
    (ax2, "Kurtosis", td_kur),
    (ax3, "Crest Factor", td_cre),
]:
    bp = ax_td.boxplot(
        [data_dict[n] for n in names],
        labels=names,
        patch_artist=True,
        medianprops={"color": "black", "linewidth": 2},
    )
    for patch, name in zip(bp["boxes"], names):
        patch.set_facecolor(colors[name])
        patch.set_alpha(0.7)
    ax_td.set_title(f"Distribution of {feat_name}")
    ax_td.set_ylabel(feat_name)
    ax_td.grid(True, axis="y", alpha=0.3)
    # Print means
    for name in names:
        print(f"  {feat_name:14s}  {name}: mean={np.mean(data_dict[name]):.5f}  "
              f"std={np.std(data_dict[name]):.5f}")

plt.tight_layout()
out = OUTPUT_DIR / "frequency_diagnostics.png"
fig.savefig(out, dpi=150)
print(f"\nDiagnostic plot saved -> {out}")

# ── 4. PSD ratio between Damaged and Healthy ─────────────────────────────────
mean_healthy = np.mean(psds["Healthy"], axis=0)
mean_damaged = np.mean(psds["Damaged"], axis=0)
ratio = mean_damaged / (mean_healthy + 1e-30)
top5_ratio_idx = np.argsort(np.abs(np.log(ratio)))[-5:][::-1]
print("\nFrequency bins with largest Damaged/Healthy PSD ratio:")
for i in top5_ratio_idx:
    print(f"  {freqs[i]:.2f} Hz  ratio={ratio[i]:.4f}")
