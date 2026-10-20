# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added
- `GET /devices`: every device that has sent readings, with its source, number of readings,
  last time seen and last status, most recent first. `/status` and `/history` accept a
  `device_id` filter.
- Dashboard device picker: appears when more than one device is sending data and shows one
  device at a time (by default the most recently active one), so readings from the
  simulator, the fake Arduino and the real Arduino never mix in one chart.
- The dashboard remembers the dark or light theme in the browser and applies it before the
  page is drawn.
- README architecture diagram drawn with Mermaid.
- Continuous integration (`.github/workflows/ci.yml`): on every push, GitHub Actions runs
  the backend tests (Python 3.11), lints and builds the dashboard (Node 24), and compiles
  the firmware for the Arduino Uno. Tests that need the trained model are skipped there
  because the model file is not stored in Git. CI badge in the README.
- Hardware guide updated to the parts actually bought: MCU-219 INA219, DS18B20 with
  adapter, low-level-trigger relay, 5 W load resistor (with heat warning), 2200 mAh cell;
  LED and buzzer marked optional; a polarity check for when no multimeter is available;
  no charging until a proper charger is available.
- Alert hysteresis: an alert clears only after the value moves back past its threshold by
  a margin (0.05 V, 2 °C, 0.1 A), tracked separately per device. The message says when a
  held alert will clear. Margins are shown in `/thresholds`.
- Arduino Uno firmware (`firmware/battery_monitor`): reads the INA219 and DS18B20 once per
  second, prints `READING` lines for the bridge, and protects the cell on its own: relay off
  at power-up, cut-off at 3.00 V (3 readings in a row), over-temperature and lost-sensor
  cut-offs, load stays off until a manual reset. Compiled for the Uno and its logic checked
  in a PC simulation; not yet tested on real hardware.
- Hardware guide (`docs/hardware/wiring.md`): parts, power path, signal wiring, pre-power
  checklist, step-by-step bring-up and charging rules.
- Serial bridge (`backend/bridge.py`): reads the Arduino's `READING v=.. i=.. t=.. load=..`
  lines over USB and posts them as `source = "sensor"`; ignores broken lines; `--fake` mode
  with a fake Arduino on an in-memory serial port (data labeled `simulated`), `--dry-run`
  and `--list-ports`. Adds `pyserial` to the backend requirements.
- Backend test suite (`backend/tests`, 56 tests with pytest): alert thresholds and
  hysteresis, all endpoints (including the device filter), WebSocket push, CORS, the SoH service's refusals, and the
  serial bridge.

## [0.3.0] - 2026-10-15

### Added
- FastAPI backend with SQLite storage (`backend/`): `/health`, `POST /readings`, `/status`,
  `/history`, `/thresholds`. Clients can only send measurements; the server decides the
  status and the SoH note.
- Alert service with demonstration thresholds in one place (`app/config.py`): every rule
  that fires is reported and the most severe one sets normal, warning or critical.
- Live updates: WebSocket `/ws` pushes each stored reading; `ws_listen.py` test client.
- Guarded SoH model service (`app/services/soh_model.py`, `/soh/model-info`,
  `/soh/predict`): loads the model once and refuses to predict when the model is missing or
  any feature is outside its training range. Training now saves each feature's range in the
  model metadata.
- Simulator (`backend/simulator.py`) that sends readings labeled `source = "simulated"`.
- Next.js dashboard (`frontend/`): sidebar, live status banner, battery graphic, voltage
  chart with alert bands, current, temperature and power tiles, recent readings table,
  honest State of Health panel with a NASA example, dark and light themes, phone layout,
  automatic reconnect.
- Brand identity: logo mark, Cobalt-to-Ion colors, Unbounded and IBM Plex Sans fonts.
- Backend and dashboard documentation (`backend/README.md`, `frontend/README.md`).

### Known limitations
- The dashboard runs on simulated data; sensor hardware follows in v0.4.0.
- The SoH model is not validated for this project's own hardware (about 0.4 A load versus
  NASA's 2 A discharges).
- Alerts have no hysteresis yet; the theme choice is not remembered.

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