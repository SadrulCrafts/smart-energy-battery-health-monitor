"""
soh_model.py
------------
Stage 3, Step 7: load the trained SoH model once and use it ONLY inside the
conditions it was trained and evaluated for.

What the model needs
    The 8 features from model/scripts/build_features.py, computed from the
    FIRST 600 s of a 2 A constant-current discharge of a NASA PCoE-type 18650
    cell. A single live reading (one V, I, T) is NOT enough to compute them.

Guard rails
    1. Model file missing -> no prediction, the note explains why.
    2. Any feature outside the range seen in training -> no prediction.
       A Random Forest cannot extrapolate (we saw this on B0006 in Stage 2).
       Passing this check is necessary, not sufficient: every feature can be
       inside its own range while the combination is still unusual.
    3. Every prediction carries the leave-one-battery-out error, so it is never
       presented as an exact value.

Self-check (run from the project root):
    python backend/app/services/soh_model.py
"""

import json
import math
from functools import lru_cache
from pathlib import Path

# backend/app/services/soh_model.py -> parents[3] is the project root
PROJECT_DIR = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = PROJECT_DIR / "model" / "artifacts"
MODEL_FILE = ARTIFACT_DIR / "soh_model.joblib"
METADATA_FILE = ARTIFACT_DIR / "soh_model_metadata.json"
FEATURES_CSV = PROJECT_DIR / "model" / "data" / "processed" / "features_soh.csv"


class SohModel:
    """Loads the model + metadata once and makes guarded predictions."""

    def __init__(self):
        self.model = None
        self.metadata = {}
        self.problem = None   # why predictions are impossible (None = model is usable)
        self.warning = None   # something to know, but predictions still work
        self._load()

    def _load(self):
        if not MODEL_FILE.exists() or not METADATA_FILE.exists():
            self.problem = ("Model file not found. Run model/scripts/train_soh_model.py first "
                            "(the .joblib file is not stored in Git).")
            return
        try:
            import joblib
            import sklearn

            self.metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
            if "feature_ranges" not in self.metadata:
                self.problem = "Metadata has no feature_ranges. Re-run train_soh_model.py."
                return
            self.model = joblib.load(MODEL_FILE)
        except Exception as exc:  # a broken file must not crash the whole backend
            self.model = None
            self.problem = f"Model could not be loaded: {exc}"
            return

        trained_with = self.metadata.get("sklearn_version")
        if trained_with != sklearn.__version__:
            self.warning = (f"Model was saved with scikit-learn {trained_with}, "
                            f"running {sklearn.__version__}. Re-train if results look wrong.")

    @property
    def available(self):
        return self.model is not None

    def info(self):
        """Everything a client needs to know about the model and its limits."""
        meta = self.metadata
        return {
            "available": self.available,
            "problem": self.problem,
            "warning": self.warning,
            "model_type": meta.get("model_type"),
            "target_definition": meta.get("target_definition"),
            "feature_window_s": meta.get("feature_window_s"),
            "feature_columns": meta.get("feature_columns", []),
            "feature_ranges": meta.get("feature_ranges", {}),
            "target_range": meta.get("target_range"),
            "trained_on_cells": meta.get("trained_on_cells", []),
            "lobo_overall_metrics": meta.get("lobo_overall_metrics"),
            "valid_for": meta.get("valid_for"),
        }

    @staticmethod
    def _refuse(note, out_of_range=None):
        return {"soh_pct": None, "soh_valid": False, "soh_note": note,
                "out_of_range": out_of_range or []}

    def predict(self, features):
        """
        features: dict with the 8 feature names -> numbers.
        Returns {"soh_pct", "soh_valid", "soh_note", "out_of_range"}.
        soh_pct is None whenever a trustworthy estimate is not possible.
        """
        if not self.available:
            return self._refuse(f"Not evaluated: {self.problem}")

        columns = self.metadata["feature_columns"]
        missing = [c for c in columns if c not in features]
        if missing:
            return self._refuse(f"Not evaluated: missing features {', '.join(missing)}.")

        values = {}
        for column in columns:
            try:
                value = float(features[column])
            except (TypeError, ValueError):
                return self._refuse(f"Not evaluated: {column} is not a number.")
            if not math.isfinite(value):
                return self._refuse(f"Not evaluated: {column} is not a finite number.")
            values[column] = value

        out_of_range = []
        for column in columns:
            low = self.metadata["feature_ranges"][column]["min"]
            high = self.metadata["feature_ranges"][column]["max"]
            if not low <= values[column] <= high:
                out_of_range.append(f"{column}={values[column]:.4g} "
                                    f"(training range {low:.4g} to {high:.4g})")
        if out_of_range:
            return self._refuse(
                "Not evaluated: input is outside the conditions the model was trained on.",
                out_of_range,
            )

        import pandas as pd  # the model was fitted on a DataFrame with these column names

        row = pd.DataFrame([[values[c] for c in columns]], columns=columns)
        soh = float(self.model.predict(row)[0])
        mae = self.metadata["lobo_overall_metrics"]["mae"]
        note = (f"Estimate from the first {self.metadata['feature_window_s']} s of a discharge. "
                f"Typical error on unseen NASA cells (leave-one-battery-out): "
                f"MAE {mae:.2f} percentage points. Valid only for: {self.metadata['valid_for']}")
        return {"soh_pct": round(soh, 2), "soh_valid": True, "soh_note": note,
                "out_of_range": []}


@lru_cache(maxsize=1)
def get_soh_model():
    """The one shared SohModel (loaded the first time it is needed)."""
    return SohModel()


def _self_check():
    service = get_soh_model()
    info = service.info()
    print(f"Model available: {info['available']}")
    if not info["available"]:
        print(f"Problem: {info['problem']}")
        return
    if info["warning"]:
        print(f"Warning: {info['warning']}")
    print(f"Trained on: {', '.join(info['trained_on_cells'])}   "
          f"LOBO MAE: {info['lobo_overall_metrics']['mae']} percentage points")

    import pandas as pd

    df = pd.read_csv(FEATURES_CSV)
    columns = info["feature_columns"]
    cell = df[df["battery_id"] == "B0005"]

    print("\n1) Real NASA rows from B0005 (this cell WAS used for training, so this only")
    print("   shows that the service works. It is NOT an accuracy result.)")
    for _, row in [("first", cell.iloc[0]), ("last", cell.iloc[-1])]:
        result = service.predict(row[columns].to_dict())
        print(f"   discharge cycle {int(row['discharge_cycle']):>3}: "
              f"actual {row['soh_rated_pct']:.2f}%  ->  predicted {result['soh_pct']}%  "
              f"(soh_valid={result['soh_valid']})")

    print("\n2) Same first row, but v_at_600s_v changed to 3.30 V (outside training range):")
    changed = cell.iloc[0][columns].to_dict()
    changed["v_at_600s_v"] = 3.30
    result = service.predict(changed)
    print(f"   soh_pct={result['soh_pct']}  soh_valid={result['soh_valid']}")
    print(f"   note: {result['soh_note']}")
    print(f"   out_of_range: {result['out_of_range']}")

    print("\n3) Only one feature given (like a single live reading):")
    result = service.predict({"v_start_v": 4.2})
    print(f"   soh_pct={result['soh_pct']}  soh_valid={result['soh_valid']}")
    print(f"   note: {result['soh_note']}")


if __name__ == "__main__":
    _self_check()