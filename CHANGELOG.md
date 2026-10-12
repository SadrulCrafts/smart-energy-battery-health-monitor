# Changelog

All notable changes to this project are documented in this file.

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