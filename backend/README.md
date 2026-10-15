# Backend

FastAPI service that stores battery readings in SQLite, decides an alert status for each
reading, pushes new readings to the dashboard over a WebSocket, and serves the State of
Health model inside the conditions it was trained on.

## Run

From the project root, with the virtual environment active:

    pip install -r backend/requirements.txt
    uvicorn app.main:app --app-dir backend --reload --reload-dir backend

- Health check: http://127.0.0.1:8000/health
- Interactive API documentation: http://127.0.0.1:8000/docs

The database file `backend/data/monitor.db` is created on first start and is not stored
in Git. To start again with an empty database, stop the server and delete that file.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | API, database and SoH model status, number of live clients |
| POST | `/readings` | Store one reading; the server decides its status and SoH note |
| GET | `/status` | Latest reading and total number of stored readings |
| GET | `/history?limit=100&source=simulated` | Recent readings, oldest first (for charts) |
| GET | `/thresholds` | Alert limits currently in use |
| WS | `/ws` | Pushes every newly stored reading as `{"type": "reading", "data": {...}}` |
| GET | `/soh/model-info` | Model details, training ranges and validity conditions |
| POST | `/soh/predict` | SoH estimate from the 8 early-discharge features |

### What a client may send

`POST /readings` accepts only measurements:

```json
{
  "source": "simulated",
  "device_id": "simulator-1",
  "voltage_v": 3.85,
  "current_a": -0.40,
  "temperature_c": 26.1
}
```

`source` must be `simulated`, `sensor` or `nasa`. Unknown fields (for example `soh_pct` or
`status`) are rejected with HTTP 422, so a client cannot set the alert status or the SoH.
`timestamp` is optional; without it the server time (UTC) is used.

## Alerts

`app/services/alerts.py` checks voltage, current magnitude and temperature against the
limits in `app/config.py`. Every rule that fires is listed in the message, and the most
severe one decides the status.

| Quantity | Warning | Critical |
|---|---|---|
| Voltage, low | ≤ 3.20 V | ≤ 3.00 V |
| Voltage, high | ≥ 4.22 V | ≥ 4.25 V |
| Temperature, high | ≥ 40 °C | ≥ 45 °C |
| Temperature, low | ≤ 0 °C | |
| Current magnitude | ≥ 1.0 A | ≥ 2.0 A |

These are **demonstration values**, not certified safety limits. Replace them with the
datasheet limits of the actual cell before connecting hardware.

## SoH model service

`app/services/soh_model.py` loads `model/artifacts/soh_model.joblib` once at start-up.

- It needs the 8 features of `model/scripts/build_features.py`, computed from the first
  600 s of a 2 A discharge. A single live reading does not contain them, so live readings
  are stored with `soh_valid = false` and a note explaining why.
- `POST /soh/predict` refuses (HTTP 200, `soh_pct: null`, `soh_valid: false`) when any
  feature lies outside the range seen in training, and lists which ones. Being inside every
  range is necessary but not sufficient for a trustworthy estimate.
- If the model file is missing (it is not stored in Git), the backend still runs and the
  SoH endpoints report that the model is not available. Run
  `model/scripts/train_soh_model.py` to create it.

## Simulator

`simulator.py` sends readings exactly as the Arduino bridge will, but always with
`source = "simulated"`. The numbers come from a simple made-up model of one 18650 cell on
a 10 Ω load (discharge to 3.0 V, rest, charge to 4.2 V, rest, repeat).

    python backend/simulator.py                    # one reading every 2 s, 60x time
    python backend/simulator.py --speed 300        # faster cycles
    python backend/simulator.py --steps 20         # send 20 readings, then stop

## Live test client

`ws_listen.py` prints every reading the backend pushes, which is handy for checking the
WebSocket without the dashboard:

    python backend/ws_listen.py

## Files

```
backend/
├── app/
│   ├── main.py            FastAPI app, CORS, /health
│   ├── config.py          alert thresholds
│   ├── database.py        SQLite engine, sessions, table creation
│   ├── models.py          Reading table
│   ├── schemas.py         request and response rules (Pydantic)
│   ├── readings_api.py    /readings, /status, /history, /thresholds
│   ├── live_api.py        WebSocket /ws
│   ├── soh_api.py         /soh/model-info, /soh/predict
│   └── services/
│       ├── alerts.py      status decision
│       ├── live.py        connected WebSocket clients
│       └── soh_model.py   guarded model loading and prediction
├── simulator.py
├── ws_listen.py
└── requirements.txt
```

## Known limitations

- No hysteresis on alerts: the status can flicker while a value sits right at a limit.
- Database calls inside the async `POST /readings` endpoint are synchronous; fine for one
  device, not for many.
- No authentication. CORS allows only the local dashboard (`localhost:3000`).
