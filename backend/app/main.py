"""
main.py
-------
Stage 3: the FastAPI application.

Run from the project root:
    uvicorn app.main:app --app-dir backend --reload --reload-dir backend
Then open:
    http://127.0.0.1:8000/health   (status check, including the database)
    http://127.0.0.1:8000/docs     (automatic interactive API documentation)
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import DATABASE_FILE, database_is_reachable, init_db
from .live_api import router as live_router
from .readings_api import router as readings_router
from .services.live import live_connections
from .services.soh_model import get_soh_model
from .soh_api import router as soh_router

API_VERSION = "0.3.0-dev"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts
    init_db()
    soh_model = get_soh_model()  # load the model now, not on the first request
    if not soh_model.available:
        print(f"WARNING: SoH model not available: {soh_model.problem}")
    yield
    # Code after "yield" would run when the server stops (nothing needed yet)


app = FastAPI(
    title="Battery Health Monitor API",
    description=(
        "Stores battery measurements and serves them to the dashboard. "
        "Every record is labeled with its data source (simulated, sensor or nasa)."
    ),
    version=API_VERSION,
    lifespan=lifespan,
)

# The dashboard runs on another address (Next.js on port 3000), so the browser
# needs the API's permission to read its answers. This is called CORS.
FRONTEND_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(readings_router)
app.include_router(live_router)
app.include_router(soh_router)


@app.get("/health", tags=["system"])
def health():
    """Check that the API process and the database are working."""
    database_ok = database_is_reachable()
    return {
        "status": "ok" if database_ok else "degraded",
        "service": "battery-health-monitor-api",
        "version": API_VERSION,
        "database": "ok" if database_ok else "unreachable",
        "database_file": DATABASE_FILE.name,
        "soh_model": "loaded" if get_soh_model().available else "not available",
        "live_clients": live_connections.count,
        "server_time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }