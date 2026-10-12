"""
models.py
---------
Stage 3, Step 2: database tables.

Every reading MUST carry a `source` so that simulated data, real sensor
measurements and NASA laboratory data are never mixed up.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

ALLOWED_SOURCES = ("simulated", "sensor", "nasa")
ALLOWED_STATUSES = ("normal", "warning", "critical")


def utc_now():
    return datetime.now(timezone.utc)


class Reading(Base):
    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    # Where the data came from: "simulated", "sensor" or "nasa"
    source: Mapped[str] = mapped_column(String(16), index=True)
    device_id: Mapped[str | None] = mapped_column(String(64))

    # Measurements
    voltage_v: Mapped[float]
    current_a: Mapped[float]
    temperature_c: Mapped[float | None]

    # Model output: only filled when the input matches the validated conditions
    soh_pct: Mapped[float | None]
    soh_valid: Mapped[bool] = mapped_column(default=False)
    soh_note: Mapped[str | None] = mapped_column(String(255))

    # Alert state
    status: Mapped[str] = mapped_column(String(16), default="normal")
    alert_message: Mapped[str | None] = mapped_column(String(255))

    def __repr__(self):
        return (f"Reading(id={self.id}, source={self.source}, "
                f"V={self.voltage_v}, I={self.current_a}, T={self.temperature_c})")