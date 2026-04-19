"""
ETL pipeline: label raw train-run data and produce an augmented dataset.

Output layout:
  ETL/processed/<material>/<condition>/<run_id>/
      daq_sensors_1000hz.csv   (original, or spike-augmented)
      arduino_motion_raw.csv   (unchanged copy)
      description.json         (label + structured metadata)

Labeling rules:
  - Non-unclipped run (any material)  → Healthy
  - Unclipped run, CRUISE RMS < 0.09G → Degraded
  - Unclipped run, CRUISE RMS ≥ 0.09G → Damaged
  - Synthetic copy with small spikes  → Degraded  (suffix _aug_degraded)
  - Synthetic copy with large spikes  → Damaged   (suffix _aug_damaged)

Augmentation:
  Each non-unclipped (Healthy) run gets two synthetic copies with
  Gaussian impulse spikes injected during CRUISE phase:
    small  → 0.30 G amplitude, σ=8 ms,  3–5 spikes
    large  → 0.65 G amplitude, σ=15 ms, 5–8 spikes
  Both g4 and g5 get correlated spikes (same positions, ±10 % amplitude jitter).
"""

import csv
import json
import math
import os
import random
import re
import shutil

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_ROOT = os.path.join(os.path.dirname(__file__), "..", "data", "TrainRuns")
OUT_ROOT  = os.path.join(os.path.dirname(__file__), "processed")

UNCLIPPED_RMS_THRESHOLD = 0.090  # G — below → Degraded, at/above → Damaged

SPIKE_SMALL = dict(amplitude_g=0.30, sigma_ms=8,  count_range=(3, 5))
SPIKE_LARGE = dict(amplitude_g=0.65, sigma_ms=15, count_range=(5, 8))

RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Condition-name parser
# ---------------------------------------------------------------------------
def parse_condition(condition: str) -> dict:
    """Return structured metadata extracted from the condition directory name."""
    meta = {
        "weight_kg": None,
        "weight_location": None,
        "weight_distribution": None,
        "speed_fps": None,
        "load_level": None,
        "is_unclipped": "Unclipped" in condition,
    }

    if condition == "Baseline":
        return meta

    if condition == "Fully_Loaded_Train":
        meta["load_level"] = "full"
        return meta

    if condition == "Half_Loaded_Train":
        meta["load_level"] = "half"
        return meta

    # Speed suffix for unclipped variants, e.g. "_1_5fps" or "_3fps"
    speed_match = re.search(r"(\d+(?:_\d+)?)fps", condition)
    if speed_match:
        meta["speed_fps"] = float(speed_match.group(1).replace("_", "."))

    # Weight — handles "0_5_kg", "1_5kg", "2kg", "4kg", "4_kg"
    weight_match = re.match(r"(\d+(?:_\d+)?)_?kg", condition)
    if weight_match:
        meta["weight_kg"] = float(weight_match.group(1).replace("_", "."))

    # Single location: "Location_A", "Location_B", "Location_C"
    loc_match = re.search(r"Location_([ABC])", condition)
    if loc_match:
        meta["weight_location"] = loc_match.group(1)

    # Distributed: "A_Left_C_Right"
    if "A_Left_C_Right" in condition:
        meta["weight_distribution"] = "A_left_C_right"

    # "Ea_Peg" / "Ea_Left_Pegs"
    if "Ea_Peg" in condition:
        meta["weight_distribution"] = "each_peg"
    elif "Ea_Left_Pegs" in condition:
        meta["weight_distribution"] = "each_left_peg"

    return meta


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------
def read_csv(path: str) -> tuple[list[str], list[list[str]]]:
    with open(path, newline="") as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)
    return headers, rows


def write_csv(path: str, headers: list[str], rows: list[list[str]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# CRUISE window + RMS
# ---------------------------------------------------------------------------
def cruise_window(motion_path: str) -> tuple[int, int]:
    """Return (t_min_ms, t_max_ms) covering the CRUISE phase."""
    times = []
    with open(motion_path, newline="") as f:
        for row in csv.DictReader(f):
            if row["phase"] == "CRUISE":
                times.append(int(row["time_ms"]))
    if not times:
        return (0, 0)
    return (min(times), max(times))


def cruise_rms(daq_path: str, t_min: int, t_max: int) -> float:
    total, n = 0.0, 0
    with open(daq_path, newline="") as f:
        for row in csv.DictReader(f):
            t = int(row["time_ms"])
            if t_min <= t <= t_max:
                total += float(row["g4"]) ** 2
                n += 1
    return math.sqrt(total / n) if n else 0.0


# ---------------------------------------------------------------------------
# Spike injection
# ---------------------------------------------------------------------------
def gaussian_spike(length: int, center: int, sigma: int, amplitude: float) -> list[float]:
    """Return a list of length floats: Gaussian impulse centred at `center`."""
    return [
        amplitude * math.exp(-0.5 * ((i - center) / sigma) ** 2)
        for i in range(length)
    ]


def inject_spikes(
    daq_headers: list[str],
    daq_rows: list[list[str]],
    t_min: int,
    t_max: int,
    spike_cfg: dict,
    rng: random.Random,
) -> tuple[list[list[str]], list[dict]]:
    """
    Return modified rows (copies) and a list of spike event descriptors.
    Spikes land only inside [t_min, t_max].
    """
    g4_idx = daq_headers.index("g4")
    g5_idx = daq_headers.index("g5")

    # Collect indices of CRUISE rows
    cruise_indices = [
        i for i, r in enumerate(daq_rows)
        if t_min <= int(r[0]) <= t_max
    ]
    if not cruise_indices:
        return daq_rows, []

    amp   = spike_cfg["amplitude_g"]
    sigma = spike_cfg["sigma_ms"]       # 1 sample ≈ 1 ms at 1000 Hz
    count = rng.randint(*spike_cfg["count_range"])
    min_gap = sigma * 20                # keep spikes well separated

    # Choose spike centre indices, enforcing minimum gap
    centres = []
    attempts = 0
    while len(centres) < count and attempts < 10000:
        attempts += 1
        c = rng.choice(cruise_indices)
        if all(abs(c - x) >= min_gap for x in centres):
            centres.append(c)

    rows = [list(r) for r in daq_rows]  # deep copy
    spike_events = []

    for c in centres:
        # ±10 % jitter between sensors for realism
        amp4 = amp * rng.uniform(0.90, 1.10)
        amp5 = amp * rng.uniform(0.90, 1.10)
        sign = rng.choice([-1, 1])

        win = sigma * 4
        for offset in range(-win, win + 1):
            idx = c + offset
            if 0 <= idx < len(rows):
                g = math.exp(-0.5 * (offset / sigma) ** 2)
                rows[idx][g4_idx] = str(round(float(rows[idx][g4_idx]) + sign * amp4 * g, 6))
                rows[idx][g5_idx] = str(round(float(rows[idx][g5_idx]) + sign * amp5 * g, 6))

        spike_events.append({
            "row_index": c,
            "time_ms": int(rows[c][0]),
            "amplitude_g": round(amp, 4),
            "sign": sign,
        })

    return rows, spike_events


# ---------------------------------------------------------------------------
# Write one output run
# ---------------------------------------------------------------------------
def write_run(
    out_dir: str,
    daq_headers: list[str],
    daq_rows: list[list[str]],
    motion_src: str,
    description: dict,
) -> None:
    os.makedirs(out_dir, exist_ok=True)
    write_csv(os.path.join(out_dir, "daq_sensors_1000hz.csv"), daq_headers, daq_rows)
    shutil.copy2(motion_src, os.path.join(out_dir, "arduino_motion_raw.csv"))
    with open(os.path.join(out_dir, "description.json"), "w") as f:
        json.dump(description, f, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    rng = random.Random(RANDOM_SEED)

    materials = [d for d in os.listdir(DATA_ROOT)
                 if os.path.isdir(os.path.join(DATA_ROOT, d))]

    processed = augmented = 0

    for material in sorted(materials):
        mat_path = os.path.join(DATA_ROOT, material)
        for condition in sorted(os.listdir(mat_path)):
            cond_path = os.path.join(mat_path, condition)
            if not os.path.isdir(cond_path):
                continue

            cond_meta = parse_condition(condition)
            is_unclipped = cond_meta["is_unclipped"]

            for run_id in sorted(os.listdir(cond_path)):
                run_path = os.path.join(cond_path, run_id)
                daq_path    = os.path.join(run_path, "daq_sensors_1000hz.csv")
                motion_path = os.path.join(run_path, "arduino_motion_raw.csv")

                if not (os.path.exists(daq_path) and os.path.exists(motion_path)):
                    continue

                daq_headers, daq_rows = read_csv(daq_path)
                t_min, t_max = cruise_window(motion_path)
                rms = cruise_rms(daq_path, t_min, t_max)

                # --- Determine label ---
                if is_unclipped:
                    label = "Damaged" if rms >= UNCLIPPED_RMS_THRESHOLD else "Degraded"
                    label_source = f"unclipped_rms_{rms:.4f}g"
                else:
                    label = "Healthy"
                    label_source = "non_unclipped"

                base_desc = {
                    "run_id": run_id,
                    "source_run_id": run_id,
                    "material": material,
                    "condition": condition,
                    "health_label": label,
                    "health_label_source": label_source,
                    "cruise_rms_g": round(rms, 5),
                    "is_augmented": False,
                    "augmentation": None,
                    **cond_meta,
                }

                out_dir = os.path.join(OUT_ROOT, material, condition, run_id)
                write_run(out_dir, daq_headers, daq_rows, motion_path, base_desc)
                processed += 1

                # --- Synthetic augmented copies for Healthy runs only ---
                if not is_unclipped:
                    for tier, spike_cfg, aug_label in [
                        ("degraded", SPIKE_SMALL, "Degraded"),
                        ("damaged",  SPIKE_LARGE, "Damaged"),
                    ]:
                        aug_rows, spike_events = inject_spikes(
                            daq_headers, daq_rows, t_min, t_max, spike_cfg, rng
                        )
                        aug_id = f"{run_id}_aug_{tier}"
                        aug_desc = {
                            **base_desc,
                            "run_id": aug_id,
                            "source_run_id": run_id,
                            "health_label": aug_label,
                            "health_label_source": f"synthetic_{tier}_spikes",
                            "is_augmented": True,
                            "augmentation": {
                                "tier": tier,
                                "amplitude_g": spike_cfg["amplitude_g"],
                                "sigma_ms": spike_cfg["sigma_ms"],
                                "spike_count": len(spike_events),
                                "spikes": spike_events,
                                "random_seed": RANDOM_SEED,
                            },
                        }
                        aug_out = os.path.join(OUT_ROOT, material, condition, aug_id)
                        write_run(aug_out, daq_headers, aug_rows, motion_path, aug_desc)
                        augmented += 1

    print(f"Done. {processed} original runs + {augmented} augmented copies written to {OUT_ROOT}")
    print(f"Total: {processed + augmented} runs")


if __name__ == "__main__":
    main()
