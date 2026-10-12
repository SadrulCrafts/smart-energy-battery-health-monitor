"""
build_features.py
-----------------
Stage 2, Step 1: Build model inputs (features) for State of Health (SoH) estimation.

Prediction scenario
    "Given only the FIRST 10 MINUTES of a 2 A discharge, estimate the cell's
     capacity-based SoH."

Why only the first 10 minutes?
    Capacity is measured by discharging all the way to the cut-off voltage.
    Anything that describes the WHOLE discharge (its duration, the time of the
    temperature peak, the full voltage curve, ...) almost directly reveals the
    capacity, so using it would be target leakage. Every NASA discharge lasts
    well over 10 minutes, so this window never reaches the cut-off voltage and is
    not affected by the different cut-off voltages of the four cells.

Target
    soh_rated_pct = capacity_ah / 2.0 Ah (rated capacity, NASA README) * 100

Output
    model/data/processed/features_soh.csv

Run from the project root (after preprocess_data.py):
    python model/scripts/build_features.py
"""

import sys

import numpy as np
import pandas as pd

from preprocess_data import BATTERY_IDS, OUTPUT_CSV, PROCESSED_DIR, load_cycles

FEATURES_CSV = PROCESSED_DIR / "features_soh.csv"

# Length of the early-discharge window used for features (seconds)
WINDOW_S = 600

TARGET_COLUMN = "soh_rated_pct"

# The model may ONLY use these columns as inputs
FEATURE_COLUMNS = [
    "v_start_v",          # voltage at t = 0 s (end of rest, before load)
    "v_drop_30s_v",       # voltage drop in the first 30 s (internal-resistance effect)
    "v_at_60s_v",
    "v_at_300s_v",
    "v_at_600s_v",
    "v_slope_60_600_mv_per_min",   # how fast voltage falls between 1 and 10 min
    "temp_start_c",
    "temp_rise_600s_c",   # temperature increase during the first 10 min
]

# Kept in the CSV for reference and plots, but NEVER used as model inputs
REFERENCE_COLUMNS = ["capacity_ah", "soh_pct"]


def value_at(time_s, values, t):
    """Linearly interpolate a measurement at time t (seconds)."""
    return float(np.interp(t, time_s, values))


def window_features(data):
    """
    Compute features from the first WINDOW_S seconds of one discharge.
    Returns None if the record is too short for the window.
    """
    time_s = np.asarray(data["Time"], dtype=float).ravel()
    voltage = np.asarray(data["Voltage_measured"], dtype=float).ravel()
    temperature = np.asarray(data["Temperature_measured"], dtype=float).ravel()

    time_s = time_s - time_s[0]
    if time_s[-1] < WINDOW_S:
        return None

    in_window = (time_s >= 60) & (time_s <= WINDOW_S)
    if in_window.sum() < 3:
        return None
    # Linear fit of voltage vs time between 60 s and 600 s -> slope in V/s
    slope_v_per_s = np.polyfit(time_s[in_window], voltage[in_window], 1)[0]

    v_start = float(voltage[0])
    return {
        "v_start_v": v_start,
        "v_drop_30s_v": v_start - value_at(time_s, voltage, 30),
        "v_at_60s_v": value_at(time_s, voltage, 60),
        "v_at_300s_v": value_at(time_s, voltage, 300),
        "v_at_600s_v": value_at(time_s, voltage, WINDOW_S),
        "v_slope_60_600_mv_per_min": slope_v_per_s * 1000 * 60,
        "temp_start_c": float(temperature[0]),
        "temp_rise_600s_c": value_at(time_s, temperature, WINDOW_S) - float(temperature[0]),
    }


def build_for_battery(battery_id, wanted_cycles):
    """Return a list of feature rows for the discharge cycles kept in Stage 1."""
    rows, skipped = [], 0
    discharge_number = 0
    for cycle in load_cycles(battery_id):
        if str(cycle.get("type", "")).strip() != "discharge":
            continue
        discharge_number += 1          # same counting rule as preprocess_data.py
        if discharge_number not in wanted_cycles:
            continue
        feats = window_features(cycle["data"])
        if feats is None:
            skipped += 1
            continue
        rows.append({"battery_id": battery_id, "discharge_cycle": discharge_number, **feats})
    print(f"  {battery_id}: {len(rows)} feature rows, {skipped} skipped (shorter than window)")
    return rows


def main():
    if not OUTPUT_CSV.exists():
        print(f"ERROR: {OUTPUT_CSV} not found. Run preprocess_data.py first.")
        sys.exit(1)

    cycles_df = pd.read_csv(OUTPUT_CSV)
    print(f"Building early-window features (first {WINDOW_S} s of each discharge)")

    rows = []
    for battery_id in BATTERY_IDS:
        wanted = set(cycles_df.loc[cycles_df["battery_id"] == battery_id, "discharge_cycle"])
        rows.extend(build_for_battery(battery_id, wanted))

    features = pd.DataFrame(rows)
    keep = ["battery_id", "discharge_cycle", TARGET_COLUMN] + REFERENCE_COLUMNS
    df = features.merge(cycles_df[keep], on=["battery_id", "discharge_cycle"], how="inner")

    missing = df[FEATURE_COLUMNS + [TARGET_COLUMN]].isna().sum()
    if missing.any():
        print("\nWARNING: missing values found:")
        print(missing[missing > 0].to_string())

    df.to_csv(FEATURES_CSV, index=False)

    print(f"\nTarget: {TARGET_COLUMN} (capacity / 2.0 Ah rated * 100)")
    print("\nCorrelation of each feature with the target (all cells pooled):")
    for column in FEATURE_COLUMNS:
        if df[column].std() == 0:
            print(f"  {column:<28} constant value (no information)")
        else:
            print(f"  {column:<28} {df[column].corr(df[TARGET_COLUMN]):+.3f}")

    print(f"\nSaved {len(df)} rows x {df.shape[1]} columns to: {FEATURES_CSV}")


if __name__ == "__main__":
    main()