"""
plot_capacity.py
----------------
Stage 1, Step 3: Visualise battery degradation from the processed CSV.

Creates three PNG figures in model/reports/figures/:
    1. capacity_vs_cycle.png      - discharge capacity (Ah) of each battery over cycles
    2. soh_vs_cycle.png           - capacity-based SoH (%) with an example threshold line
    3. discharge_curves_B0005.png - voltage curves of early / middle / late cycles

Run from the project root (after preprocess_data.py):
    python model/scripts/plot_capacity.py
"""

import sys

import matplotlib

matplotlib.use("Agg")  # draw to files only; no pop-up windows needed
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from preprocess_data import OUTPUT_CSV, REPORT_DIR, load_cycles  # noqa: E402

FIGURE_DIR = REPORT_DIR / "figures"

# Example threshold for the SoH plot. This is a configurable PROJECT CONVENTION,
# not the official end-of-life definition of the NASA experiments.
EXAMPLE_SOH_THRESHOLD_PCT = 80.0

# Fixed colour + marker per battery (colour-blind-checked palette; markers and
# direct labels mean colour is never the only way to tell lines apart).
STYLE = {
    "B0005": {"color": "#2a78d6", "marker": "o"},
    "B0006": {"color": "#eb6834", "marker": "s"},
    "B0007": {"color": "#1baf7a", "marker": "^"},
    "B0018": {"color": "#eda100", "marker": "D"},
}
TEXT = "#3d3d3a"
MUTED = "#8a8980"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": TEXT,
    "axes.titlecolor": TEXT,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#e6e5e0",
    "grid.linewidth": 0.8,
    "legend.frameon": False,
})


def plot_per_battery(df, column, ylabel, title, filename, threshold=None):
    fig, ax = plt.subplots(figsize=(9, 5))
    line_ends = []
    for battery_id, group in df.groupby("battery_id"):
        style = STYLE.get(battery_id, {"color": TEXT, "marker": "o"})
        ax.plot(
            group["discharge_cycle"], group[column],
            color=style["color"], linewidth=2,
            marker=style["marker"], markersize=4, markevery=10,
            label=battery_id,
        )
        last = group.iloc[-1]
        line_ends.append([battery_id, last["discharge_cycle"], last[column]])

    # Direct labels at the end of each line, nudged apart so they never overlap
    y_low, y_high = ax.get_ylim()
    min_gap = (y_high - y_low) * 0.045
    line_ends.sort(key=lambda item: item[2])
    for i in range(1, len(line_ends)):
        if line_ends[i][2] - line_ends[i - 1][2] < min_gap:
            line_ends[i][2] = line_ends[i - 1][2] + min_gap
    for battery_id, x_end, y_label in line_ends:
        ax.annotate(
            battery_id, (x_end, y_label),
            xytext=(6, 0), textcoords="offset points",
            va="center", fontsize=9, color=TEXT, annotation_clip=False,
        )

    if threshold is not None:
        ax.axhline(threshold, color=MUTED, linestyle="--", linewidth=1.2)
        ax.annotate(
            f"{threshold:.0f}% example threshold (project convention)",
            (0, threshold), xytext=(4, 4), textcoords="offset points",
            fontsize=8, color=MUTED,
        )

    ax.set_xlabel("Discharge cycle number")
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", fontsize=12)
    ax.legend(loc="upper right")
    ax.text(0, -0.14, "Source: NASA PCoE Battery Data Set (Saha & Goebel, 2007). "
            "Laboratory data, not live sensor measurements.",
            transform=ax.transAxes, fontsize=8, color=MUTED)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / filename, dpi=150)
    plt.close(fig)
    print(f"  saved {FIGURE_DIR / filename}")


def plot_discharge_curves(battery_id="B0005"):
    """Voltage vs time for an early, a middle and a late discharge cycle."""
    cycles = load_cycles(battery_id)
    discharges = [c for c in cycles if str(c.get("type", "")).strip() == "discharge"]
    if len(discharges) < 3:
        print(f"  not enough discharge cycles in {battery_id} for curve plot")
        return

    picks = {
        "early": 0,
        "middle": len(discharges) // 2,
        "late": len(discharges) - 1,
    }
    # One hue, light -> dark = early -> late (an ordered sequence)
    shades = ["#86b6ef", "#2a78d6", "#104281"]

    fig, ax = plt.subplots(figsize=(9, 5))
    for (label, idx), color in zip(picks.items(), shades):
        data = discharges[idx]["data"]
        t = np.asarray(data["Time"], dtype=float).ravel()
        v = np.asarray(data["Voltage_measured"], dtype=float).ravel()
        cap = float(np.asarray(data["Capacity"], dtype=float).ravel()[0])
        ax.plot(t / 60, v, color=color, linewidth=2,
                label=f"{label}: cycle {idx + 1} ({cap:.2f} Ah)")

    ax.set_xlabel("Time since discharge start (minutes)")
    ax.set_ylabel("Terminal voltage (V)")
    ax.set_title(f"{battery_id}: discharge voltage curves get shorter as the cell ages",
                 loc="left", fontsize=12)
    ax.legend(loc="upper right")
    ax.text(0, -0.14, "Source: NASA PCoE Battery Data Set (Saha & Goebel, 2007).",
            transform=ax.transAxes, fontsize=8, color=MUTED)
    fig.tight_layout()
    filename = f"discharge_curves_{battery_id}.png"
    fig.savefig(FIGURE_DIR / filename, dpi=150)
    plt.close(fig)
    print(f"  saved {FIGURE_DIR / filename}")


def main():
    if not OUTPUT_CSV.exists():
        print(f"ERROR: {OUTPUT_CSV} not found. Run preprocess_data.py first.")
        sys.exit(1)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(OUTPUT_CSV)
    print(f"Loaded {len(df)} rows from {OUTPUT_CSV}")

    plot_per_battery(
        df, "capacity_ah", "Discharge capacity (Ah)",
        "Discharge capacity fades with repeated cycling",
        "capacity_vs_cycle.png",
    )
    plot_per_battery(
        df, "soh_pct", "State of Health (% of first measured capacity)",
        "Capacity-based State of Health per battery",
        "soh_vs_cycle.png",
        threshold=EXAMPLE_SOH_THRESHOLD_PCT,
    )
    plot_discharge_curves("B0005")
    print("Done.")


if __name__ == "__main__":
    main()