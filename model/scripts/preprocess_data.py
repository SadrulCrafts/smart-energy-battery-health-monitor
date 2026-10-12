"""
preprocess_data.py
------------------
Stage 1, Step 2: Turn the raw NASA battery .mat files into one clean CSV table.

One row = one DISCHARGE cycle of one battery.

Structure this script relies on (confirmed by inspect_dataset.py on the real files):
    <BatteryID>['cycle']  -> list of cycle records
    each record           -> 'type' ('charge' | 'discharge' | 'impedance'),
                             'ambient_temperature', 'time' (6-element date vector),
                             'data' (dict of measurements)
    discharge 'data'      -> Voltage_measured (V), Current_measured (A),
                             Temperature_measured (deg C), Current_load, Voltage_load,
                             Time (s), Capacity (Ah, one number per cycle)
    impedance 'data'      -> Re, Rct (Ohm, one number each) + complex spectra

Output:
    model/data/processed/discharge_cycles.csv
    model/reports/preprocessing_log.txt   (what was kept / skipped and why)

Run from the project root:
    python model/scripts/preprocess_data.py
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat

# ---------------------------------------------------------------------------
# Paths and settings
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_DIR = SCRIPT_DIR.parent
RAW_DIR = MODEL_DIR / "data" / "raw"
PROCESSED_DIR = MODEL_DIR / "data" / "processed"
REPORT_DIR = MODEL_DIR / "reports"
OUTPUT_CSV = PROCESSED_DIR / "discharge_cycles.csv"
LOG_FILE = REPORT_DIR / "preprocessing_log.txt"

BATTERY_IDS = ["B0005", "B0006", "B0007", "B0018"]

# Measurement arrays that every usable discharge cycle must contain
REQUIRED_DISCHARGE_FIELDS = [
    "Voltage_measured",
    "Current_measured",
    "Temperature_measured",
    "Time",
]

# A discharge with fewer samples than this is treated as incomplete
MIN_SAMPLES = 10


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------
def load_cycles(battery_id):
    """Load the list of cycle records for one battery."""
    mat_path = RAW_DIR / f"{battery_id}.mat"
    if not mat_path.exists():
        raise FileNotFoundError(f"{mat_path} not found. Run the download step first.")
    mat = loadmat(str(mat_path), simplify_cells=True)
    return mat[battery_id]["cycle"]


def to_scalar(value):
    """Convert a value that should be a single number into a Python float (or NaN)."""
    arr = np.asarray(value, dtype=float).ravel()
    return float(arr[0]) if arr.size == 1 else float("nan")


def to_datetime(time_vector):
    """Convert a MATLAB date vector [Y, M, D, h, m, s] into a Python datetime."""
    try:
        y, mo, d, h, mi, s = [float(x) for x in np.asarray(time_vector).ravel()[:6]]
        return datetime(int(y), int(mo), int(d), int(h), int(mi)) + timedelta(seconds=s)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Validation and feature extraction
# ---------------------------------------------------------------------------
def check_discharge(data):
    """
    Return None if the discharge record is usable,
    otherwise a short text explaining why it is skipped.
    """
    for field in REQUIRED_DISCHARGE_FIELDS + ["Capacity"]:
        if field not in data:
            return f"missing field '{field}'"

    arrays = [np.asarray(data[f], dtype=float).ravel() for f in REQUIRED_DISCHARGE_FIELDS]
    lengths = {a.size for a in arrays}
    if len(lengths) != 1:
        return f"measurement arrays have different lengths {sorted(lengths)}"
    if arrays[0].size < MIN_SAMPLES:
        return f"only {arrays[0].size} samples (< {MIN_SAMPLES})"
    if any(np.isnan(a).any() for a in arrays):
        return "NaN values in measurements"

    segment = loaded_segment(arrays[1])  # arrays[1] = Current_measured
    if segment is None:
        return "no load current found"
    if segment[1] - segment[0] + 1 < MIN_SAMPLES:
        return f"loaded part has fewer than {MIN_SAMPLES} samples"

    capacity = to_scalar(data["Capacity"])
    if not np.isfinite(capacity) or capacity <= 0:
        return f"invalid capacity {capacity}"
    return None


def loaded_segment(current):
    """
    Return (first, last) sample index of the part of the record where the
    load is actually connected.

    Each NASA discharge record also contains a short rest before the load is
    applied and a recovery period after the load is removed (the voltage climbs
    back up once the current returns to ~0 A). Those rest/recovery samples are
    not part of the discharge, so features are computed on the loaded part only.
    "Loaded" = |current| is at least half of the largest |current| in the record.
    """
    magnitude = np.abs(current)
    if magnitude.max() <= 0:
        return None
    loaded = np.flatnonzero(magnitude >= 0.5 * magnitude.max())
    return int(loaded[0]), int(loaded[-1])


def extract_features(data):
    """
    Summarise one discharge cycle into a few numbers (loaded part only).

    NOTE for Stage 2: 'discharge_duration_s' is almost a direct function of
    capacity (constant-current discharge until a cut-off voltage), so it must
    NOT be used as an input when predicting capacity-based SoH (target leakage).
    It is kept here only for documentation and plotting.
    """
    voltage = np.asarray(data["Voltage_measured"], dtype=float).ravel()
    current = np.asarray(data["Current_measured"], dtype=float).ravel()
    temperature = np.asarray(data["Temperature_measured"], dtype=float).ravel()
    time_s = np.asarray(data["Time"], dtype=float).ravel()

    first, last = loaded_segment(current)
    v = voltage[first:last + 1]
    i = current[first:last + 1]
    temp = temperature[first:last + 1]
    t = time_s[first:last + 1]

    return {
        "capacity_ah": to_scalar(data["Capacity"]),
        "n_samples_total": int(voltage.size),
        "n_samples_loaded": int(v.size),
        "discharge_duration_s": float(t[-1] - t[0]),
        "voltage_rest_start_v": float(voltage[0]),     # before the load is applied
        "voltage_loaded_start_v": float(v[0]),
        "voltage_cutoff_v": float(v.min()),
        "voltage_mean_v": float(v.mean()),
        "voltage_recovered_end_v": float(voltage[-1]),  # after the load is removed
        "current_mean_a": float(i.mean()),
        "temperature_start_c": float(temp[0]),
        "temperature_max_c": float(temp.max()),
        "temperature_mean_c": float(temp.mean()),
        "temperature_rise_c": float(temp.max() - temp[0]),
        "time_to_temp_max_s": float(t[int(temp.argmax())] - t[0]),
    }


def process_battery(battery_id, log):
    """Build one row per valid discharge cycle for a single battery."""
    cycles = load_cycles(battery_id)
    rows = []
    discharge_number = 0          # counts ALL discharge records, valid or not
    latest_re, latest_rct = np.nan, np.nan

    for record_index, cycle in enumerate(cycles):
        cycle_type = str(cycle.get("type", "")).strip()
        data = cycle.get("data", {})

        # Remember the most recent impedance measurement so each discharge
        # row can carry the last known internal-resistance values.
        if cycle_type == "impedance" and isinstance(data, dict):
            latest_re = to_scalar(data.get("Re", np.nan))
            latest_rct = to_scalar(data.get("Rct", np.nan))
            continue

        if cycle_type != "discharge":
            continue

        discharge_number += 1
        problem = check_discharge(data) if isinstance(data, dict) else "no data dict"
        if problem:
            log(f"  SKIP {battery_id} discharge #{discharge_number} "
                f"(record {record_index}): {problem}")
            continue

        start = to_datetime(cycle.get("time"))
        row = {
            "battery_id": battery_id,
            "discharge_cycle": discharge_number,
            "raw_record_index": record_index,
            "start_time": start.isoformat(sep=" ") if start else None,
            "ambient_temperature_c": to_scalar(cycle.get("ambient_temperature", np.nan)),
        }
        row.update(extract_features(data))
        row["re_ohm_last"] = latest_re
        row["rct_ohm_last"] = latest_rct
        rows.append(row)

    df = pd.DataFrame(rows)
    log(f"  {battery_id}: {discharge_number} discharge records found, "
        f"{len(df)} kept, {discharge_number - len(df)} skipped")
    return df


def add_soh(df):
    """
    Add a capacity-based State of Health column.

    Project definition (operational, NOT a universal standard):
        SoH (%) = capacity_ah / reference_capacity_ah * 100
        reference_capacity_ah = first valid discharge capacity of that battery
    """
    df = df.sort_values(["battery_id", "discharge_cycle"]).copy()
    df["reference_capacity_ah"] = df.groupby("battery_id")["capacity_ah"].transform("first")
    df["soh_pct"] = df["capacity_ah"] / df["reference_capacity_ah"] * 100
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    log_lines = []

    def log(text=""):
        print(text)
        log_lines.append(text)

    log("Preprocessing NASA battery discharge cycles")
    frames = []
    for battery_id in BATTERY_IDS:
        try:
            frames.append(process_battery(battery_id, log))
        except FileNotFoundError as exc:
            log(f"  ERROR: {exc}")

    frames = [f for f in frames if not f.empty]
    if not frames:
        log("No data processed. Nothing saved.")
        sys.exit(1)

    df = add_soh(pd.concat(frames, ignore_index=True))
    df.to_csv(OUTPUT_CSV, index=False)

    log("\nSummary per battery:")
    summary = df.groupby("battery_id").agg(
        cycles=("discharge_cycle", "count"),
        first_capacity_ah=("capacity_ah", "first"),
        last_capacity_ah=("capacity_ah", "last"),
        min_soh_pct=("soh_pct", "min"),
        cutoff_voltage_v=("voltage_cutoff_v", "median"),
    )
    log(summary.round(3).to_string())

    log(f"\nMissing values per column (should be 0 except possibly re/rct):")
    missing = df.isna().sum()
    log(missing[missing > 0].to_string() if missing.any() else "  none")

    log(f"\nSaved {len(df)} rows x {df.shape[1]} columns to: {OUTPUT_CSV}")
    LOG_FILE.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"Log saved to: {LOG_FILE}")


if __name__ == "__main__":
    main()