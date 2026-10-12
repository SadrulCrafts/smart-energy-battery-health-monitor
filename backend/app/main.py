"""
main.py
-------
Stage 3, Step 1: the FastAPI application.

Run from the project root:
    uvicorn app.main:app --app-dir backend --reload --reload-dir backend
Then open:
    http://127.0.0.1:8000/health   (simple status check)
    http://127.0.0.1:8000/docs     (automatic interactive API documentation)
"""

from datetime import datetime, timezone

from fastapi import FastAPI

API_VERSION = "0.3.0-dev"

app = FastAPI(
    title="Battery Health Monitor API",
    description=(
        "Stores battery measurements and serves them to the dashboard. "
        "Every record is labeled with its data source (simulated, sensor or nasa)."
    ),
    version=API_VERSION,
)


@app.get("/health", tags=["system"])
def health():
    """Simple check that the API process is running."""
    return {
        "status": "ok",
        "service": "battery-health-monitor-api",
        "version": API_VERSION,
        "server_time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }