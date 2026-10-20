"""
capacity_api.py
---------------
Stage 4: measured capacity.

    GET /capacity?device_id=arduino-uno-1&source=sensor

Finds the discharges in one device's readings and measures how much charge the
cell delivered in each (see services/capacity.py). Only sensor readings are
measured; simulated readings use compressed time.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .database import get_db
from .models import Reading, utc_now
from .schemas import CapacityOut, DischargeRunOut, Source, as_utc
from .services.capacity import Sample, find_runs

router = APIRouter(tags=["capacity"])

DbSession = Annotated[Session, Depends(get_db)]

MAX_READINGS = 200_000   # about 55 hours of readings at one per second
MAX_RUNS = 10

NOT_SENSOR_NOTE = ("Capacity is only measured from sensor readings. Simulated readings use "
                   "compressed time (one reading can stand for a minute), so a capacity "
                   "calculated from them would be meaningless.")


@router.get("/capacity", response_model=CapacityOut)
def get_capacity(
    db: DbSession,
    source: Annotated[Source, Query(description="Data source of the device")] = "sensor",
    device_id: Annotated[str | None, Query(description="Device, for example arduino-uno-1")] = None,
):
    """Measured capacity of each discharge of one device, most recent first."""
    base = dict(
        source=source,
        device_id=device_id,
        rated_capacity_mah=config.RATED_CAPACITY_MAH,
        cutoff_v=config.CAPACITY_CUTOFF_V,
        full_rest_v=config.CAPACITY_FULL_REST_V,
    )
    if source != "sensor":
        return CapacityOut(available=False, note=NOT_SENSOR_NOTE, runs=[], **base)

    query = select(Reading).where(Reading.source == source)
    query = query.where(Reading.device_id.is_(None) if device_id is None else Reading.device_id == device_id)
    rows = list(db.scalars(query.order_by(Reading.timestamp.desc(), Reading.id.desc()).limit(MAX_READINGS)))
    rows.reverse()
    samples = [Sample(as_utc(r.timestamp), r.voltage_v, r.current_a, r.temperature_c) for r in rows]

    runs = find_runs(samples, now=utc_now())
    runs.reverse()   # most recent first
    note = ("Coulomb counting: the current is added up over time during each discharge."
            if runs else "No discharge recorded for this device yet.")
    return CapacityOut(
        available=True,
        note=note,
        runs=[DischargeRunOut.model_validate(run, from_attributes=True) for run in runs[:MAX_RUNS]],
        **base,
    )
