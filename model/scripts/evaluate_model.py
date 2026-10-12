"""
evaluate_model.py
-----------------
Stage 2, Step 3: Evaluate the leave-one-battery-out (LOBO) results and check
that the saved model can be loaded and used.

What it does
    1. Prints MAE / RMSE / R2 per held-out cell for every model.
    2. Checks "extrapolation": how many test values lie outside the SoH range
       the model saw during training. Tree models (Random Forest) cannot predict
       values below the training minimum or above the training maximum.
    3. Saves two figures:
         model/reports/figures/lobo_predictions.png  - actual vs predicted per cell
         model/reports/figures/lobo_parity.png       - predicted vs actual scatter
    4. Loads model/artifacts/soh_model.joblib and makes one test prediction.

Run from the project root (after train_soh_model.py):
    python model/scripts/evaluate_model.py
"""

import json
import sys

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from build_features import FEATURE_COLUMNS, FEATURES_CSV, TARGET_COLUMN  # noqa: E402
from plot_capacity import FIGURE_DIR, MUTED, STYLE, TEXT  # noqa: E402
from train_soh_model import (  # noqa: E402
    METADATA_FILE, METRICS_CSV, MODEL_FILE, PREDICTIONS_CSV,
)

MODEL_STYLE = {
    "random_forest": {"color": "#2a78d6", "label": "Random Forest", "dash": "-"},
    "linear_regression": {"color": "#eb6834", "label": "Linear Regression", "dash": "--"},
}


def print_metrics():
    metrics = pd.read_csv(METRICS_CSV)
    for name in ["mean_baseline", "linear_regression", "random_forest"]:
        part = metrics[metrics["model"] == name].set_index("test_battery")
        print(f"\n{name}")
        print(part[["n_test", "mae", "rmse", "r2"]].round(3).to_string())


def extrapolation_check(features):
    """For each held-out cell, count test targets outside the training range."""
    print("\nExtrapolation check (test values outside the SoH range seen in training):")
    rows = []
    for cell in sorted(features["battery_id"].unique()):
        train = features.loc[features["battery_id"] != cell, TARGET_COLUMN]
        test = features.loc[features["battery_id"] == cell, TARGET_COLUMN]
        rows.append({
            "test_battery": cell,
            "train_range": f"{train.min():.1f} - {train.max():.1f}",
            "test_range": f"{test.min():.1f} - {test.max():.1f}",
            "below_train_min": f"{int((test < train.min()).sum())}/{len(test)}",
            "above_train_max": f"{int((test > train.max()).sum())}/{len(test)}",
            "train_min": train.min(),
        })
    table = pd.DataFrame(rows).set_index("test_battery")
    print(table.drop(columns="train_min").to_string())
    return table["train_min"].to_dict()


def plot_predictions(predictions, train_minimums):
    cells = sorted(predictions["test_battery"].unique())
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), sharey=True)
    for ax, cell in zip(axes.ravel(), cells):
        part = predictions[predictions["test_battery"] == cell]
        actual = part[part["model"] == "random_forest"]
        ax.plot(actual["discharge_cycle"], actual["actual"], color=TEXT, linewidth=2,
                label="Actual")
        for name, style in MODEL_STYLE.items():
            pred = part[part["model"] == name]
            ax.plot(pred["discharge_cycle"], pred["predicted"], color=style["color"],
                    linestyle=style["dash"], linewidth=1.6, label=style["label"])
        ax.axhline(train_minimums[cell], color=MUTED, linestyle=":", linewidth=1.2)
        ax.annotate("lowest SoH in training cells", (0, train_minimums[cell]),
                    xytext=(4, -10), textcoords="offset points", fontsize=7, color=MUTED)
        ax.set_title(f"Held-out cell: {cell}", loc="left", fontsize=10)
        ax.set_xlabel("Discharge cycle")
    for ax in axes[:, 0]:
        ax.set_ylabel("SoH (% of rated 2.0 Ah)")
    axes[0, 0].legend(loc="upper right", fontsize=8)
    fig.suptitle("Leave-one-battery-out: each panel is a cell the model never saw",
                 x=0.01, ha="left", fontsize=12, color=TEXT)
    fig.text(0.01, 0.005, "Source: NASA PCoE Battery Data Set (Saha & Goebel, 2007). "
             "Features: first 10 min of each discharge.", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    path = FIGURE_DIR / "lobo_predictions.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  saved {path}")


def plot_parity(predictions):
    rf = predictions[predictions["model"] == "random_forest"]
    fig, ax = plt.subplots(figsize=(6.5, 6))
    low = min(rf["actual"].min(), rf["predicted"].min()) - 2
    high = max(rf["actual"].max(), rf["predicted"].max()) + 2
    ax.plot([low, high], [low, high], color=MUTED, linestyle="--", linewidth=1.2)
    ax.annotate("perfect prediction", (high, high), xytext=(-95, -14),
                textcoords="offset points", fontsize=8, color=MUTED)
    for cell, group in rf.groupby("test_battery"):
        style = STYLE.get(cell, {"color": TEXT, "marker": "o"})
        ax.scatter(group["actual"], group["predicted"], s=18, color=style["color"],
                   marker=style["marker"], alpha=0.8, label=cell,
                   edgecolors="white", linewidths=0.4)
    ax.set_xlim(low, high)
    ax.set_ylim(low, high)
    ax.set_xlabel("Actual SoH (% of rated 2.0 Ah)")
    ax.set_ylabel("Predicted SoH (%)")
    ax.set_title("Random Forest, held-out predictions", loc="left", fontsize=12)
    ax.legend(title="Held-out cell", loc="upper left", fontsize=8)
    fig.tight_layout()
    path = FIGURE_DIR / "lobo_parity.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  saved {path}")


def check_saved_model(features):
    """Load the saved model + metadata and predict one known row."""
    model = joblib.load(MODEL_FILE)
    metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    if metadata["feature_columns"] != FEATURE_COLUMNS:
        print("ERROR: feature list in metadata does not match build_features.py")
        sys.exit(1)

    sample = features.iloc[[0]]
    predicted = float(model.predict(sample[FEATURE_COLUMNS])[0])
    print("\nSaved model check:")
    print(f"  loaded {type(model).__name__} trained on {metadata['trained_on_cells']}")
    print(f"  sample: {sample['battery_id'].iat[0]} discharge cycle "
          f"{sample['discharge_cycle'].iat[0]}")
    print(f"  actual SoH {sample[TARGET_COLUMN].iat[0]:.2f}%  ->  predicted {predicted:.2f}%")
    print("  (this cell was part of training, so this only proves the file works;"
          " it is NOT an accuracy result)")


def main():
    for path in [PREDICTIONS_CSV, METRICS_CSV, MODEL_FILE, METADATA_FILE]:
        if not path.exists():
            print(f"ERROR: {path} not found. Run train_soh_model.py first.")
            sys.exit(1)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    features = pd.read_csv(FEATURES_CSV)
    predictions = pd.read_csv(PREDICTIONS_CSV)

    print("Per-cell metrics (SoH percentage points):")
    print_metrics()
    train_minimums = extrapolation_check(features)

    print("\nFigures:")
    plot_predictions(predictions, train_minimums)
    plot_parity(predictions)

    check_saved_model(features)


if __name__ == "__main__":
    main()