"""
schemas.py
----------
Stage 3, Step 3: rules for data coming INTO and going OUT OF the API (Pydantic).

ReadingCreate  - what a client (simulator / Arduino bridge) may send.
                 Only measurements are accepted. The client can NOT send
                 soh_pct, status or alerts: those are decided by the server.
ReadingOut     - what the API returns for one stored reading.
StatusOut      - response of GET /status.
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Source = Literal["simulated", "sensor", "nasa"]
Status = Literal["normal", "warning", "critical"]


def as_utc(value: datetime) -> datetime:
    """Treat a time without timezone as UTC; convert others to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ReadingCreate(BaseModel):
    # extra="forbid": unknown fields (for example "soh_pct") are rejected
    # allow_inf_nan=False: "NaN" / "Infinity" are rejected
    model_config = ConfigDict(
        extra="forbid",
        allow_inf_nan=False,
        json_schema_extra={
            "examples": [{
                "source": "simulated",
                "device_id": "manual-test",
                "voltage_v": 3.85,
                "current_a": -0.40,
                "temperature_c": 26.1,
            }]
        },
    )

    source: Source = Field(description="Where the data comes from: simulated, sensor or nasa")
    device_id: str | None = Field(default=None, max_length=64)
    timestamp: datetime | None = Field(
        default=None, description="Measurement time. If omitted, the server time (UTC) is used."
    )
    # Plausibility limits for a single-cell prototype (not safety limits)
    voltage_v: float = Field(ge=0, le=30, description="Battery voltage in volts")
    current_a: float = Field(ge=-10, le=10, description="Current in amperes (negative = discharge)")
    temperature_c: float | None = Field(
        default=None, ge=-55, le=125, description="Battery temperature in degrees Celsius"
    )

    @field_validator("timestamp")
    @classmethod
    def timestamp_to_utc(cls, value):
        return as_utc(value) if value is not None else None


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # read directly from a database row

    id: int
    timestamp: datetime
    source: Source
    device_id: str | None
    voltage_v: float
    current_a: float
    temperature_c: float | None
    soh_pct: float | None
    soh_valid: bool
    soh_note: str | None
    status: Status
    alert_message: str | None

    @field_validator("timestamp")
    @classmethod
    def timestamp_to_utc(cls, value):
        # SQLite returns times without timezone; they are stored as UTC
        return as_utc(value)


class DeviceOut(BaseModel):
    """One device that has sent readings (GET /devices)."""
    source: Source
    device_id: str | None
    readings: int
    last_seen: datetime
    last_status: Status

    @field_validator("last_seen")
    @classmethod
    def last_seen_to_utc(cls, value):
        return as_utc(value)


class StatusOut(BaseModel):
    has_data: bool
    total_readings: int
    latest: ReadingOut | None
