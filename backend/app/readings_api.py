"""
readings_api.py
---------------
Stage 3, Step 3: endpoints for battery readings.

    POST /readings  - store one new reading
    GET  /status    - latest reading + total count
    GET  /history   - recent readings (oldest first, ready for charts)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import get_db
from .models import Reading, utc_now
from .schemas import ReadingCreate, ReadingOut, Source, StatusOut

router = APIRouter(tags=["readings"])

DbSession = Annotated[Session, Depends(get_db)]

# Shown until the SoH model service is connected in a later step
SOH_NOT_CONNECTED = "Not evaluated: SoH model service not connected yet."


@router.post("/readings", response_model=ReadingOut, status_code=201)
def create_reading(payload: ReadingCreate, db: DbSession):
    """Validate and store one measurement. SoH and alerts are decided by the server."""
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
        status="normal",
        alert_message=None,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


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