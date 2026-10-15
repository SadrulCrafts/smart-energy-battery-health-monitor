"""
readings_api.py
---------------
Endpoints for battery readings.

    POST /readings   - store one new reading (status decided by the alert service)
    GET  /status     - latest reading + total count
    GET  /history    - recent readings (oldest first, ready for charts)
    GET  /thresholds - the alert limits currently in use

Every stored reading is also pushed to connected WebSocket clients (see live_api.py).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import config
from .database import get_db
from .models import Reading, utc_now
from .schemas import ReadingCreate, ReadingOut, Source, StatusOut
from .services.alerts import alert_tracker
from .services.live import live_connections

router = APIRouter(tags=["readings"])

DbSession = Annotated[Session, Depends(get_db)]

# A single reading (one V, I, T) cannot be used by the SoH model: it needs features
# from the first 600 s of a 2 A discharge. See GET /soh/model-info.
SOH_NOT_CONNECTED = ("Not evaluated: a single reading is not enough. The SoH model needs "
                     "features from the first 600 s of a 2 A discharge (see /soh/model-info).")


@router.post("/readings", response_model=ReadingOut, status_code=201)
async def create_reading(payload: ReadingCreate, db: DbSession):
    """Validate and store one measurement. SoH and alerts are decided by the server."""
    # Each device has its own alert memory (hysteresis), so two devices never mix
    status, alert_message = alert_tracker.evaluate(
        (payload.source, payload.device_id),
        payload.voltage_v, payload.current_a, payload.temperature_c,
    )
    reading = Reading(
        timestamp=payload.timestamp or utc_now(),
        source=payload.source,
        device_id=payload.device_id,
        voltage_v=payload.voltage_v,
        current_a=payload.current_a,
        temperature_c=payload.temperature_c,
        soh_pct=None,
        soh_valid=False,
        soh_note=SOH_NOT_CONNECTED,
        status=status,
        alert_message=alert_message,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    stored = ReadingOut.model_validate(reading)
    await live_connections.broadcast({"type": "reading", "data": stored.model_dump(mode="json")})
    return stored


@router.get("/status", response_model=StatusOut)
def get_status(db: DbSession):
    """Latest stored reading (or an empty state if there is none yet)."""
    latest = db.scalars(
        select(Reading).order_by(Reading.timestamp.desc(), Reading.id.desc()).limit(1)
    ).first()
    total = db.scalar(select(func.count()).select_from(Reading)) or 0
    return StatusOut(
        has_data=latest is not None,
        total_readings=total,
        latest=ReadingOut.model_validate(latest) if latest is not None else None,
    )


@router.get("/history", response_model=list[ReadingOut])
def get_history(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=1000, description="How many readings")] = 100,
    source: Annotated[Source | None, Query(description="Only this data source")] = None,
):
    """The most recent readings, returned oldest-first so charts can draw them directly."""
    query = select(Reading)
    if source is not None:
        query = query.where(Reading.source == source)
    query = query.order_by(Reading.timestamp.desc(), Reading.id.desc()).limit(limit)
    rows = list(db.scalars(query))
    rows.reverse()
    return rows


@router.get("/thresholds", tags=["system"])
def get_thresholds():
    """Alert limits used by the server (demonstration values, see config.py)."""
    return {
        "voltage_low_warning_v": config.VOLTAGE_LOW_WARNING_V,
        "voltage_low_critical_v": config.VOLTAGE_LOW_CRITICAL_V,
        "voltage_high_warning_v": config.VOLTAGE_HIGH_WARNING_V,
        "voltage_high_critical_v": config.VOLTAGE_HIGH_CRITICAL_V,
        "temperature_high_warning_c": config.TEMPERATURE_HIGH_WARNING_C,
        "temperature_high_critical_c": config.TEMPERATURE_HIGH_CRITICAL_C,
        "temperature_low_warning_c": config.TEMPERATURE_LOW_WARNING_C,
        "current_warning_a": config.CURRENT_WARNING_A,
        "current_critical_a": config.CURRENT_CRITICAL_A,
        "voltage_hysteresis_v": config.VOLTAGE_HYSTERESIS_V,
        "temperature_hysteresis_c": config.TEMPERATURE_HYSTERESIS_C,
        "current_hysteresis_a": config.CURRENT_HYSTERESIS_A,
        "note": config.THRESHOLD_NOTE,
    }
