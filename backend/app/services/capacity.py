"""
capacity.py
-----------
Stage 4: MEASURED capacity of a cell, from its own sensor readings.

During a discharge the INA219 reports the current once per second. Adding up
current x time (coulomb counting) gives the charge the cell delivered:

    capacity_mAh = sum( |I| * dt ) / 3.6        (I in A, dt in s)

This is a measurement, not a prediction, so it needs no model. It is only as
good as the readings, so every result says how it may be limited:

    - Only "sensor" readings are used. The simulator and the fake Arduino compress
      time (one reading can stand for a minute), so a capacity from their server
      timestamps would be meaningless.
    - A run that did not start from a full charge (resting voltage below
      FULL_REST_V) gives the capacity from that voltage down to the cut-off only.
    - A run that stopped before the cut-off, or has a gap in its readings, gives
      less than the real capacity.
    - The discharge ends at CUTOFF_V (3.0 V on this rig), above the cell's lowest
      allowed voltage, so even a complete run measures "capacity to 3.0 V".

A State of Health is only given for a complete run from full to the cut-off:
    soh_pct = capacity_mAh / rated_capacity_mAh * 100
"""

from dataclasses import dataclass, field
from datetime import datetime

from .. import config


@dataclass
class Sample:
    """The fields of one stored reading that the calculation needs."""
    timestamp: datetime
    voltage_v: float
    current_a: float
    temperature_c: float | None


@dataclass
class DischargeRun:
    start: datetime
    end: datetime
    duration_s: float
    readings: int
    rest_voltage_v: float | None      # resting voltage just before the load was connected
    start_voltage_v: float            # first voltage under load
    end_voltage_v: float              # last voltage under load
    capacity_mah: float
    energy_wh: float
    mean_current_a: float             # magnitude
    max_temperature_c: float | None
    temperature_rise_c: float | None
    ended: str                        # "cutoff", "stopped_early", "data_gap" or "in_progress"
    started_full: bool
    soh_pct: float | None = None
    soh_note: str = ""
    warnings: list[str] = field(default_factory=list)


def is_discharging(sample: Sample) -> bool:
    return sample.current_a <= -config.CAPACITY_DISCHARGE_MIN_A


def _seconds(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds()


def find_runs(samples: list[Sample], now: datetime | None = None) -> list[DischargeRun]:
    """
    Split one device's readings (oldest first) into discharge runs and measure each.
    `now` lets a run that is still "in progress" but has had no reading for a while
    be reported as interrupted (for example, the bridge was closed mid-discharge).
    """
    runs = []
    k = 0
    n = len(samples)
    while k < n:
        if not is_discharging(samples[k]):
            k += 1
            continue

        first = k
        # Resting voltage: the last non-discharging reading shortly before the load came on
        rest_v = None
        if first > 0 and _seconds(samples[first - 1].timestamp, samples[first].timestamp) <= config.CAPACITY_MAX_GAP_S:
            rest_v = samples[first - 1].voltage_v

        charge_as = 0.0      # ampere-seconds
        energy_ws = 0.0      # watt-seconds
        ended = "in_progress"
        k = first + 1
        while k < n:
            previous, current = samples[k - 1], samples[k]
            dt = _seconds(previous.timestamp, current.timestamp)
            if dt > config.CAPACITY_MAX_GAP_S:
                ended = "data_gap"
                break
            if not is_discharging(current):
                ended = "cutoff" if previous.voltage_v <= config.CAPACITY_CUTOFF_V + config.CAPACITY_CUTOFF_MARGIN_V else "stopped_early"
                break
            # trapezoid rule: average of the two readings times the time between them
            charge_as += (abs(previous.current_a) + abs(current.current_a)) / 2 * dt
            energy_ws += (abs(previous.voltage_v * previous.current_a) + abs(current.voltage_v * current.current_a)) / 2 * dt
            k += 1
        last = k - 1
        if ended == "in_progress" and now is not None and _seconds(samples[last].timestamp, now) > config.CAPACITY_MAX_GAP_S:
            ended = "data_gap"
        runs.append(_measure(samples[first:last + 1], rest_v, charge_as, energy_ws, ended))
    return runs


def _measure(run: list[Sample], rest_v, charge_as, energy_ws, ended) -> DischargeRun:
    duration = _seconds(run[0].timestamp, run[-1].timestamp)
    temperatures = [s.temperature_c for s in run if s.temperature_c is not None]
    started_full = rest_v is not None and rest_v >= config.CAPACITY_FULL_REST_V
    result = DischargeRun(
        start=run[0].timestamp,
        end=run[-1].timestamp,
        duration_s=round(duration, 1),
        readings=len(run),
        rest_voltage_v=rest_v,
        start_voltage_v=run[0].voltage_v,
        end_voltage_v=run[-1].voltage_v,
        capacity_mah=round(charge_as / 3.6, 1),
        energy_wh=round(energy_ws / 3600, 3),
        mean_current_a=round(charge_as / duration, 3) if duration > 0 else abs(run[0].current_a),
        max_temperature_c=max(temperatures) if temperatures else None,
        temperature_rise_c=round(max(temperatures) - temperatures[0], 2) if temperatures else None,
        ended=ended,
        started_full=started_full,
    )

    if not temperatures:
        result.warnings.append("No temperature readings during this run.")
    if rest_v is None:
        result.warnings.append("No resting voltage before the load was connected.")

    rated = config.RATED_CAPACITY_MAH
    cutoff = f"{config.CAPACITY_CUTOFF_V:.2f} V"
    if ended == "in_progress":
        result.soh_note = "Discharge still running: the capacity so far keeps growing."
    elif ended == "data_gap":
        result.soh_note = (f"Not evaluated: readings stopped for more than {config.CAPACITY_MAX_GAP_S:g} s, "
                           "so part of the discharge was not measured.")
    elif ended == "stopped_early":
        result.soh_note = (f"Not evaluated: the load was disconnected at {run[-1].voltage_v:.3f} V, "
                           f"before the {cutoff} cut-off.")
    elif not started_full:
        start_text = f"{rest_v:.3f} V" if rest_v is not None else "an unknown voltage"
        result.soh_note = (f"Not evaluated: the run started at {start_text}, not from a full charge "
                           f"(at least {config.CAPACITY_FULL_REST_V:.2f} V at rest). This is the capacity "
                           f"from that voltage down to {cutoff}, not the full capacity.")
    else:
        result.soh_pct = round(result.capacity_mah / rated * 100, 1)
        result.soh_note = (f"Measured capacity to {cutoff} divided by the rated {rated:g} mAh "
                           "(the seller's figure). The cut-off is above the cell's lowest allowed "
                           "voltage, so this slightly understates the full capacity.")
    return result
