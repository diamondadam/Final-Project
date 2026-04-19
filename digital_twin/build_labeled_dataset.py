"""
Build Labeled Dataset
=====================
Walks all runs in data/TrainRuns and produces a single CSV where every row
is one run with:

  Metadata (parsed from directory names)
  ─────────────────────────────────────
  run_dir             : relative path to the run directory
  track_type          : raw folder name  (Steel_3_8_in, etc.)
  classification      : Healthy / Degraded / Damaged
  material            : Steel / Aluminum
  thickness_in        : "3/8" or "1/2"
  payload_condition   : raw condition folder name
  payload_kg          : numeric kg (0.0 = Baseline, NaN for Full/Half specials)
  payload_location    : A | B | C | Peg | Left_Pegs | A_Left_C_Right | all | none
  payload_distribution: Equal | Concentrated | Mixed | Full | Half | None
  clipped             : True / False  (Unclipped suffix -> False)
  target_speed_fps    : float if speed encoded in name, else NaN

  Extracted Features (180 per run)
  ─────────────────────────────────
  seg1_g4_rms … seg5_cross_coherence

Output: classifier/output/labeled_dataset.csv
"""

import re
import sys
import csv
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent))
from track_health_classifier import (
    TRACK_LABELS, CLASS_NAMES,
    BASE_DIR, KalmanFilter1D,
    load_and_align, extract_run_features, feature_names,
)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# Metadata parsers
# ══════════════════════════════════════════════════════════════════════════════

def parse_track_type(folder: str) -> dict:
    """
    Steel_3_8_in  → material=Steel,    thickness=3/8, classification=Healthy
    Aluminum_1_2_in → material=Aluminum, thickness=1/2, classification=Degraded
    Aluminum_3_8_in → material=Aluminum, thickness=3/8, classification=Damaged
    """
    parts = folder.split("_")
    material = parts[0]                       # Steel | Aluminum
    # last three tokens before the trailing context: e.g. ['3','8','in']
    thickness = f"{parts[-3]}/{parts[-2]}"    # "3/8" or "1/2"

    label, class_name = TRACK_LABELS[folder]
    return {
        "material":       material,
        "thickness_in":   thickness,
        "classification": class_name,
    }


def parse_payload(condition: str) -> dict:
    """
    Parse the payload condition directory name into structured fields.

    Recognised patterns
    -------------------
    Baseline                              -> 0 kg, no location, clipped
    0_5_kg_Ea_Peg                         -> 0.5 kg equal on pegs
    1_5kg_Ea_Left_Pegs                    -> 1.5 kg equal on left pegs
    2kg_Ea_A_Left_C_Right                 -> 2 kg mixed A-left / C-right
    4kg_Location_A | 4kg_Location_B | ... -> 4 kg concentrated at one location
    4_kg_Location_C_Unclipped_1_5fps      -> 4 kg, unclipped, 1.5 fps
    4_kg_Location_C_Unclipped_3fps        -> 4 kg, unclipped, 3 fps
    4_kg_Location_C_Unclipped_6fps        -> 4 kg, unclipped, 6 fps
    Fully_Loaded_Train                    -> fully loaded (kg=NaN)
    Half_Loaded_Train                     -> half loaded  (kg=NaN)
    """
    result = {
        "payload_kg":           float("nan"),
        "payload_location":     "none",
        "payload_distribution": "None",
        "clipped":              True,
        "target_speed_fps":     float("nan"),
    }

    c = condition.lower()

    # ── Special named loads ───────────────────────────────────────────────────
    if c == "baseline":
        result["payload_kg"]           = 0.0
        result["payload_distribution"] = "None"
        result["payload_location"]     = "none"
        return result

    if "fully_loaded" in c:
        result["payload_distribution"] = "Full"
        result["payload_location"]     = "all"
        return result

    if "half_loaded" in c:
        result["payload_distribution"] = "Half"
        result["payload_location"]     = "all"
        return result

    # ── Clipped flag ──────────────────────────────────────────────────────────
    if "unclipped" in c:
        result["clipped"] = False

    # ── Speed suffix  (e.g. 1_5fps, 3fps, 6fps) ──────────────────────────────
    speed_match = re.search(r"(\d+(?:_\d+)?)fps", c)
    if speed_match:
        raw = speed_match.group(1).replace("_", ".")
        result["target_speed_fps"] = float(raw)

    # ── Weight ────────────────────────────────────────────────────────────────
    # Matches leading patterns like "0_5_kg", "1_5kg", "2kg", "4kg", "4_kg"
    weight_match = re.match(r"^(\d+(?:_\d+)?)_?kg", c)
    if weight_match:
        raw = weight_match.group(1).replace("_", ".")
        result["payload_kg"] = float(raw)

    # ── Location ──────────────────────────────────────────────────────────────
    loc_match = re.search(r"location_([a-c])", c)
    if loc_match:
        result["payload_location"]     = loc_match.group(1).upper()
        result["payload_distribution"] = "Concentrated"
        return result

    if "ea_a_left_c_right" in c:
        result["payload_location"]     = "A_Left_C_Right"
        result["payload_distribution"] = "Mixed"
        return result

    if "ea_left_pegs" in c:
        result["payload_location"]     = "Left_Pegs"
        result["payload_distribution"] = "Equal"
        return result

    if "ea_peg" in c:
        result["payload_location"]     = "Peg"
        result["payload_distribution"] = "Equal"
        return result

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Dataset builder
# ══════════════════════════════════════════════════════════════════════════════

def build_labeled_dataset() -> pd.DataFrame:
    kf = KalmanFilter1D()
    feat_cols = feature_names()

    rows = []
    skipped = 0

    for track_type in sorted(BASE_DIR.iterdir()):
        if track_type.name not in TRACK_LABELS:
            continue

        track_meta = parse_track_type(track_type.name)

        for cond_dir in sorted(track_type.iterdir()):
            payload_meta = parse_payload(cond_dir.name)

            for run_dir in sorted(cond_dir.iterdir()):
                data = load_and_align(run_dir)
                if data is None:
                    skipped += 1
                    continue

                feat_vec = extract_run_features(data, kf)
                if feat_vec is None:
                    skipped += 1
                    continue

                row = {
                    "run_dir":           str(run_dir.relative_to(BASE_DIR)),
                    "track_type":        track_type.name,
                    "payload_condition": cond_dir.name,
                    **track_meta,
                    **payload_meta,
                }
                for name, val in zip(feat_cols, feat_vec):
                    row[name] = float(val)

                rows.append(row)
                print(f"  OK  {track_type.name:20s}  {cond_dir.name:45s}  "
                      f"run={run_dir.name}")

    print(f"\nLoaded {len(rows)} runs, skipped {skipped}")
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("Building Labeled Dataset")
    print("=" * 80)

    df = build_labeled_dataset()

    out_path = OUTPUT_DIR / "labeled_dataset.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {len(df)} rows x {len(df.columns)} columns -> {out_path}")

    # ── Summary ───────────────────────────────────────────────────────────────
    meta_cols = [
        "classification", "material", "thickness_in",
        "payload_condition", "payload_kg", "payload_location",
        "payload_distribution", "clipped", "target_speed_fps",
    ]
    print("\nMetadata columns preview:")
    print(df[meta_cols].to_string(index=False))

    print("\nClass distribution:")
    print(df["classification"].value_counts().to_string())

    print("\nPayload distribution breakdown:")
    print(df.groupby(["classification", "payload_distribution"]).size()
            .rename("count").to_string())

    print("\nPayload location breakdown:")
    print(df.groupby(["classification", "payload_location"]).size()
            .rename("count").to_string())
