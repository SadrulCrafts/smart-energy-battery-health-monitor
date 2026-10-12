"""
inspect_dataset.py
------------------
Stage 1, Step 1: Inspect the raw NASA battery .mat files BEFORE writing any
preprocessing logic.

What this script does:
  1. Searches model/data/raw/ (and all sub-folders) for .mat files.
  2. Warns if there are still un-extracted .zip files inside raw/.
  3. For each target battery (B0005, B0006, B0007, B0018):
       - loads the file with scipy.io.loadmat()
       - prints the top-level keys
       - prints the nested structure (field names, types, shapes)
       - IF a "cycle" list is found, prints a summary per cycle type
         (how many cycles, which measurement fields exist, their lengths)
  4. Optionally saves the whole report to model/reports/inspection_report.txt

It does NOT assume the structure is correct. Every access is guarded,
so if the real files look different, the report will show it.

Run from the project root:
    python model/scripts/inspect_dataset.py
    python model/scripts/inspect_dataset.py --save
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.io import loadmat

# ---------------------------------------------------------------------------
# Paths (computed relative to this file, so it works from any working folder)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent          # model/scripts
MODEL_DIR = SCRIPT_DIR.parent                         # model
RAW_DIR = MODEL_DIR / "data" / "raw"
REPORT_DIR = MODEL_DIR / "reports"

TARGET_BATTERIES = ["B0005", "B0006", "B0007", "B0018"]

# How deep to print nested structures (keeps output readable)
MAX_DEPTH = 4


class Tee:
    """Write output to the console and (optionally) to a file at the same time."""

    def __init__(self, file_path=None):
        self.file = open(file_path, "w", encoding="utf-8") if file_path else None

    def __call__(self, text=""):
        print(text)
        if self.file:
            self.file.write(text + "\n")

    def close(self):
        if self.file:
            self.file.close()


def describe_value(value):
    """Return a short one-line description of any value loaded from a .mat file."""
    if isinstance(value, dict):
        return f"dict with {len(value)} keys"
    if isinstance(value, (list, tuple)):
        return f"list of length {len(value)}"
    if isinstance(value, np.ndarray):
        text = f"ndarray shape={value.shape} dtype={value.dtype}"
        if value.size > 0 and value.dtype.kind in "fiu":  # real numbers only
            finite = value[np.isfinite(value)] if value.dtype.kind == "f" else value.ravel()
            if finite.size > 0:
                text += f" min={finite.min():.4g} max={finite.max():.4g}"
            if value.dtype.kind == "f":
                n_nan = int(np.isnan(value).sum())
                if n_nan:
                    text += f" NaN_count={n_nan}"
        return text
    if isinstance(value, str):
        return f"str = '{value}'"
    return f"{type(value).__name__} = {value!r}"


def print_structure(value, out, name="root", depth=0):
    """Recursively print the structure of a loaded .mat object."""
    indent = "    " * depth
    out(f"{indent}- {name}: {describe_value(value)}")

    if depth >= MAX_DEPTH:
        return

    if isinstance(value, dict):
        for key, sub_value in value.items():
            print_structure(sub_value, out, name=str(key), depth=depth + 1)
    elif isinstance(value, (list, tuple)) and len(value) > 0:
        # Only show the first element; long lists are summarised elsewhere.
        print_structure(value[0], out, name=f"{name}[0] (first item only)", depth=depth + 1)


def summarise_cycles(cycles, out):
    """
    If the file contains a list of cycle records, summarise them.
    Every field access is checked, so nothing is assumed.
    """
    if not isinstance(cycles, (list, tuple)):
        # A single cycle may be returned as a dict instead of a list
        cycles = [cycles]

    out(f"  Total cycle records: {len(cycles)}")

    type_counter = Counter()
    fields_by_type = {}
    lengths_by_type = {}
    nan_by_type = {}
    missing_data = 0

    for cycle in cycles:
        if not isinstance(cycle, dict):
            type_counter["<not a dict>"] += 1
            continue

        cycle_type = str(cycle.get("type", "<no 'type' field>")).strip()
        type_counter[cycle_type] += 1

        data = cycle.get("data")
        if not isinstance(data, dict):
            missing_data += 1
            continue

        # Remember every field name seen for this cycle type
        fields_by_type.setdefault(cycle_type, Counter()).update(data.keys())

        # Record the length of each measurement array (to spot inconsistencies)
        for field, arr in data.items():
            arr = np.asarray(arr)
            lengths_by_type.setdefault(cycle_type, {}).setdefault(field, []).append(arr.size)
            if arr.dtype.kind == "f" and np.isnan(arr).any():
                nan_by_type.setdefault(cycle_type, Counter())[field] += 1

    out("  Cycle counts by 'type':")
    for cycle_type, count in type_counter.items():
        out(f"    {cycle_type:<15} {count}")

    if missing_data:
        out(f"  WARNING: {missing_data} cycle(s) have no usable 'data' dict.")

    for cycle_type, field_counts in fields_by_type.items():
        n_cycles = type_counter[cycle_type]
        out(f"\n  Fields inside 'data' for type '{cycle_type}':")
        for field, count in field_counts.items():
            sizes = lengths_by_type[cycle_type][field]
            presence = "all cycles" if count == n_cycles else f"only {count}/{n_cycles} cycles"
            n_nan = nan_by_type.get(cycle_type, Counter())[field]
            nan_note = f"  NaN in {n_nan} cycle(s)" if n_nan else ""
            out(
                f"    {field:<25} present in {presence:<20} "
                f"array size min={min(sizes)} max={max(sizes)}{nan_note}"
            )

    # Show other keys that exist directly on each cycle (e.g. temperature, time)
    other_keys = Counter()
    for cycle in cycles:
        if isinstance(cycle, dict):
            other_keys.update(k for k in cycle.keys() if k != "data")
    out("\n  Keys found directly on cycle records (excluding 'data'):")
    for key, count in other_keys.items():
        out(f"    {key:<25} present in {count}/{len(cycles)} cycles")

    # Show the first cycle of each type in a bit more detail
    shown = set()
    for i, cycle in enumerate(cycles):
        if not isinstance(cycle, dict):
            continue
        cycle_type = str(cycle.get("type", "")).strip()
        if cycle_type in shown:
            continue
        shown.add(cycle_type)
        out(f"\n  Example: first '{cycle_type}' record (index {i}):")
        for key, value in cycle.items():
            if key == "data" and isinstance(value, dict):
                out("    data:")
                for field, arr in value.items():
                    out(f"      {field:<23} {describe_value(np.asarray(arr))}")
            else:
                out(f"    {key:<25} {describe_value(value)}")


def find_cycles(mat_dict, battery_id):
    """
    Try to locate the list of cycles without assuming too much.
    Returns (cycles, path_description) or (None, reason).
    """
    root = mat_dict.get(battery_id)
    if root is None:
        return None, f"top-level key '{battery_id}' not found"
    if isinstance(root, dict) and "cycle" in root:
        return root["cycle"], f"{battery_id}['cycle']"
    return None, f"'{battery_id}' exists but has no 'cycle' field"


def inspect_file(mat_path, battery_id, out):
    out("=" * 78)
    out(f"FILE: {mat_path}")
    out(f"Size: {mat_path.stat().st_size / 1_000_000:.2f} MB")
    out("=" * 78)

    try:
        # simplify_cells=True converts MATLAB structs into Python dicts/lists,
        # which are much easier to explore than the default numpy object arrays.
        mat = loadmat(str(mat_path), simplify_cells=True)
    except NotImplementedError:
        out("ERROR: This looks like a MATLAB v7.3 (HDF5) file. scipy cannot read it.")
        out("       Tell your mentor; we would need the h5py library instead.")
        return
    except Exception as exc:  # noqa: BLE001 - we want to report any loading error
        out(f"ERROR: could not load file: {type(exc).__name__}: {exc}")
        return

    user_keys = [k for k in mat.keys() if not k.startswith("__")]
    meta_keys = [k for k in mat.keys() if k.startswith("__")]
    out(f"Top-level keys (data): {user_keys}")
    out(f"Top-level keys (metadata): {meta_keys}")
    if "__header__" in mat:
        out(f"Header: {mat['__header__']}")

    out("\n--- Nested structure (first item of each list only) ---")
    for key in user_keys:
        print_structure(mat[key], out, name=key)

    out("\n--- Cycle summary ---")
    cycles, where = find_cycles(mat, battery_id)
    if cycles is None:
        out(f"  Could not find cycles automatically: {where}")
        out("  -> Look at the nested structure above and share it with your mentor.")
    else:
        out(f"  Cycles found at: {where}")
        summarise_cycles(cycles, out)
    out("")


def main():
    parser = argparse.ArgumentParser(description="Inspect NASA battery .mat files.")
    parser.add_argument(
        "--save",
        action="store_true",
        help="Also save the report to model/reports/inspection_report.txt",
    )
    args = parser.parse_args()

    report_path = None
    if args.save:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / "inspection_report.txt"
    out = Tee(report_path)

    out(f"Python: {sys.version.split()[0]}")
    out(f"Looking for raw data in: {RAW_DIR}")

    if not RAW_DIR.exists():
        out("ERROR: raw data folder does not exist. Create model/data/raw/ first.")
        out.close()
        sys.exit(1)

    leftover_zips = sorted(RAW_DIR.rglob("*.zip"))
    if leftover_zips:
        out("\nNOTE: Found .zip files inside raw/. If a battery file is missing,")
        out("      it may still be inside one of these archives - extract it:")
        for z in leftover_zips:
            out(f"      {z.relative_to(RAW_DIR)}")

    mat_files = sorted(RAW_DIR.rglob("*.mat"))
    out(f"\nFound {len(mat_files)} .mat file(s) in total.")
    for f in mat_files:
        out(f"  {f.relative_to(RAW_DIR)}")

    found_any = False
    for battery_id in TARGET_BATTERIES:
        matches = [f for f in mat_files if f.stem.upper() == battery_id]
        if not matches:
            out(f"\nMISSING: {battery_id}.mat was not found under raw/.")
            continue
        if len(matches) > 1:
            out(f"\nNOTE: {battery_id}.mat found {len(matches)} times; using the first one.")
        found_any = True
        out("")
        inspect_file(matches[0], battery_id, out)

    if not found_any:
        out("\nNo target battery files found. Check the download/extraction step.")
        out.close()
        sys.exit(1)

    if report_path:
        out(f"Report saved to: {report_path}")
    out.close()


if __name__ == "__main__":
    main()