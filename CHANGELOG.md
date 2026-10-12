# Changelog

All notable changes to this project are documented in this file.

## [0.2.0] - 2026-10-12

### Added
- Early-window feature builder (`build_features.py`): eight voltage and temperature
  features from the first 10 minutes of each discharge, designed to avoid target leakage.
- Leave-one-battery-out training and comparison of a mean baseline, Linear Regression and
  Random Forest (`train_soh_model.py`).
- Saved Random Forest model (`model/artifacts/soh_model.joblib`, recreated by the script)
  and committed model metadata (`soh_model_metadata.json`).
- Evaluation script with per-cell metrics, an extrapolation check, two figures and a
  saved-model load test (`evaluate_model.py`).
- Stage 2 documentation: prediction task, features, results, findings, limitations and
  the reasons RUL is not included yet (`model/README.md`).

### Results
- Random Forest, all held-out predictions: MAE 2.23, RMSE 3.05, R² 0.91
  (SoH percentage points of 2.0 Ah rated capacity).

## [0.1.0] - 2026-10-12

### Added
- Environment check script (`model/scripts/verify_environment.py`).
- Dataset inspection script for the NASA battery `.mat` files (`inspect_dataset.py`).
- Preprocessing pipeline that builds one row per discharge cycle (`preprocess_data.py`):
  validation, voltage/current/temperature summaries, last known impedance (Re, Rct),
  and two capacity-based State of Health columns.
- Degradation plots: capacity, State of Health and discharge voltage curves (`plot_capacity.py`).
- Dataset documentation with test protocol, units, assumptions and limitations (`model/README.md`).
- MIT License.