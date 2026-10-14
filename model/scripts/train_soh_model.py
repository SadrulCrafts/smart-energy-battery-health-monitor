"""
train_soh_model.py
------------------
Stage 2, Step 2: Train and compare SoH models with battery-wise evaluation.

Evaluation method: leave-one-battery-out (LOBO)
    For each of the 4 cells: train on the other 3 cells, test on the held-out cell.
    The test cell is never seen during training, so this estimates how well the
    model works on a NEW cell of the same type tested the same way.
    (A random row split would mix cycles of the same cell into train and test
    and give over-optimistic results.)

Models compared
    mean_baseline     - always predicts the average SoH of the training cells
    linear_regression - straight-line model on the scaled features
    random_forest     - many decision trees averaged together

Outputs
    model/reports/lobo_predictions.csv     - every held-out prediction
    model/reports/lobo_metrics.csv         - MAE / RMSE / R2 per cell and model
    model/artifacts/soh_model.joblib       - final Random Forest trained on all 4 cells
    model/artifacts/soh_model_metadata.json

Run from the project root (after build_features.py):
    python model/scripts/train_soh_model.py
"""

import json
import sys
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from build_features import FEATURE_COLUMNS, FEATURES_CSV, TARGET_COLUMN, WINDOW_S
from preprocess_data import MODEL_DIR, REPORT_DIR

ARTIFACT_DIR = MODEL_DIR / "artifacts"
MODEL_FILE = ARTIFACT_DIR / "soh_model.joblib"
METADATA_FILE = ARTIFACT_DIR / "soh_model_metadata.json"
PREDICTIONS_CSV = REPORT_DIR / "lobo_predictions.csv"
METRICS_CSV = REPORT_DIR / "lobo_metrics.csv"

RANDOM_STATE = 42  # fixed seed so results are reproducible


def make_models():
    """Fresh, untrained copies of every model we compare."""
    return {
        "mean_baseline": DummyRegressor(strategy="mean"),
        "linear_regression": make_pipeline(StandardScaler(), LinearRegression()),
        "random_forest": RandomForestRegressor(
            n_estimators=300, min_samples_leaf=2, random_state=RANDOM_STATE, n_jobs=-1
        ),
    }


def score(y_true, y_pred):
    return {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": r2_score(y_true, y_pred),
    }


def leave_one_battery_out(df):
    """Run LOBO evaluation for all models. Returns (predictions, metrics) tables."""
    prediction_rows, metric_rows = [], []
    batteries = sorted(df["battery_id"].unique())

    for test_battery in batteries:
        train = df[df["battery_id"] != test_battery]
        test = df[df["battery_id"] == test_battery]
        X_train, y_train = train[FEATURE_COLUMNS], train[TARGET_COLUMN]
        X_test, y_test = test[FEATURE_COLUMNS], test[TARGET_COLUMN]

        for name, model in make_models().items():
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            metric_rows.append({"test_battery": test_battery, "model": name,
                                "n_test": len(test), **score(y_test, y_pred)})
            prediction_rows.append(pd.DataFrame({
                "test_battery": test_battery,
                "model": name,
                "discharge_cycle": test["discharge_cycle"].to_numpy(),
                "actual": y_test.to_numpy(),
                "predicted": y_pred,
            }))

    return pd.concat(prediction_rows, ignore_index=True), pd.DataFrame(metric_rows)


def main():
    if not FEATURES_CSV.exists():
        print(f"ERROR: {FEATURES_CSV} not found. Run build_features.py first.")
        sys.exit(1)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(FEATURES_CSV)
    print(f"Loaded {len(df)} rows, {len(FEATURE_COLUMNS)} features, target = {TARGET_COLUMN}")
    print(f"Cells: {', '.join(sorted(df['battery_id'].unique()))}")

    # 1) Battery-wise evaluation
    print("\nLeave-one-battery-out evaluation (SoH in % of rated 2.0 Ah):")
    predictions, metrics = leave_one_battery_out(df)
    predictions.to_csv(PREDICTIONS_CSV, index=False)
    metrics.to_csv(METRICS_CSV, index=False)

    table = metrics.pivot(index="test_battery", columns="model", values="mae").round(2)
    print("\nMAE per held-out cell (lower is better, in SoH percentage points):")
    print(table.to_string())

    # Overall error over all held-out predictions (each cell tested once)
    overall = pd.DataFrame({
        name: score(group["actual"], group["predicted"])
        for name, group in predictions.groupby("model")
    }).T.round(3)
    print("\nOverall (all held-out predictions pooled):")
    print(overall.to_string())

    # 2) Final model: Random Forest trained on ALL cells, for later use by the backend
    final_model = make_models()["random_forest"]
    final_model.fit(df[FEATURE_COLUMNS], df[TARGET_COLUMN])
    joblib.dump(final_model, MODEL_FILE)

    metadata = {
        "model_type": "RandomForestRegressor",
        "target": TARGET_COLUMN,
        "target_definition": "discharge capacity / 2.0 Ah rated capacity * 100",
        "feature_columns": FEATURE_COLUMNS,
        "feature_window_s": WINDOW_S,
        "trained_on_cells": sorted(df["battery_id"].unique().tolist()),
        "n_training_rows": int(len(df)),
        "lobo_overall_metrics": {k: float(v) for k, v in overall.loc["random_forest"].items()},
        # Lowest and highest value of every input seen during training.
        # The backend refuses to predict when an input falls outside these limits.
        "feature_ranges": {
            column: {"min": float(df[column].min()), "max": float(df[column].max())}
            for column in FEATURE_COLUMNS
        },
        # A Random Forest can never predict outside the SoH range it was trained on
        "target_range": {"min": float(df[TARGET_COLUMN].min()),
                         "max": float(df[TARGET_COLUMN].max())},
        "valid_for": ("NASA PCoE 18650 cells, 2 A constant-current discharge at about 24 C "
                      "ambient. Not validated for any other battery or operating condition."),
        "sklearn_version": sklearn.__version__,
        "created": datetime.now().isoformat(timespec="seconds"),
    }
    METADATA_FILE.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"\nSaved predictions : {PREDICTIONS_CSV}")
    print(f"Saved metrics     : {METRICS_CSV}")
    print(f"Saved final model : {MODEL_FILE}")
    print(f"Saved metadata    : {METADATA_FILE}")


if __name__ == "__main__":
    main()