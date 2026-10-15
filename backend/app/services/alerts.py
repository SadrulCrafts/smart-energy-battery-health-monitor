"""
alerts.py
---------
Decide the status of one reading: normal, warning or critical.

Rules
    Each limit (low voltage, high voltage, high temperature, ...) is checked on
    its own. Every limit that fires is listed in the message, and the most
    severe one decides the status.

Hysteresis
    AlertTracker remembers the last level of every limit for every device.
    A level is entered at its threshold, but only left once the value has moved
    back past the threshold by the margin in config.py. Without this, a voltage
    sitting right at 3.20 V would switch between normal and warning on every
    reading ("flapping").

    The memory lives in the running server only. After a restart the first
    reading of each device is judged on the thresholds alone.
"""

from dataclasses import dataclass
from threading import Lock

from .. import config

SEVERITY_ORDER = {"normal": 0, "warning": 1, "critical": 2}


@dataclass(frozen=True)
class Limit:
    key: str                 # short name, used to remember the level
    quantity: str            # "voltage", "current" or "temperature"
    direction: str           # "below": low values are bad; "above": high values are bad
    warning: float
    critical: float | None   # None = this limit has no critical level
    margin: float            # hysteresis margin
    unit: str
    entered_text: str        # e.g. "low" or "high"


LIMITS = (
    Limit("voltage_low", "voltage", "below", config.VOLTAGE_LOW_WARNING_V,
          config.VOLTAGE_LOW_CRITICAL_V, config.VOLTAGE_HYSTERESIS_V, "V", "low"),
    Limit("voltage_high", "voltage", "above", config.VOLTAGE_HIGH_WARNING_V,
          config.VOLTAGE_HIGH_CRITICAL_V, config.VOLTAGE_HYSTERESIS_V, "V", "high"),
    Limit("current", "current", "above", config.CURRENT_WARNING_A,
          config.CURRENT_CRITICAL_A, config.CURRENT_HYSTERESIS_A, "A", "high"),
    Limit("temperature_high", "temperature", "above", config.TEMPERATURE_HIGH_WARNING_C,
          config.TEMPERATURE_HIGH_CRITICAL_C, config.TEMPERATURE_HYSTERESIS_C, "C", "high"),
    Limit("temperature_low", "temperature", "below", config.TEMPERATURE_LOW_WARNING_C,
          None, config.TEMPERATURE_HYSTERESIS_C, "C", "very low"),
)


def _is_beyond(value, threshold, direction, margin=0.0):
    """True if value is on the bad side of threshold, with the threshold moved by margin."""
    if direction == "below":
        return value <= threshold + margin
    return value >= threshold - margin


def limit_level(limit, value, previous="normal"):
    """Level of one limit for one value, given the level this limit had before."""
    level = "normal"
    for severity, threshold in (("warning", limit.warning), ("critical", limit.critical)):
        if threshold is None:
            continue
        entered = _is_beyond(value, threshold, limit.direction)
        held = (SEVERITY_ORDER[previous] >= SEVERITY_ORDER[severity]
                and _is_beyond(value, threshold, limit.direction, limit.margin))
        if entered or held:
            level = severity
    return level


def _message(limit, level, value, display_value):
    """Human-readable text for one active limit."""
    threshold = limit.critical if level == "critical" else limit.warning
    sign = "<=" if limit.direction == "below" else ">="
    name = limit.quantity.capitalize()
    digits = 3 if limit.unit in ("V", "A") else 1
    shown = f"{display_value:+.3f}" if limit.quantity == "current" else f"{display_value:.{digits}f}"
    limit_text = f"{threshold:.2f} {limit.unit}" if limit.unit in ("V", "A") else f"{threshold:.0f} {limit.unit}"

    if _is_beyond(value, threshold, limit.direction):
        return f"{name} {shown} {limit.unit} is {limit.entered_text} ({sign} {limit_text})"
    # Still active only because of hysteresis: say when it will clear
    clear_at = threshold + limit.margin if limit.direction == "below" else threshold - limit.margin
    clear_sign = "above" if limit.direction == "below" else "below"
    clear_text = f"{clear_at:.2f} {limit.unit}" if limit.unit in ("V", "A") else f"{clear_at:.0f} {limit.unit}"
    return f"{name} {shown} {limit.unit} is recovering ({level} clears {clear_sign} {clear_text})"


def evaluate_reading(voltage_v, current_a, temperature_c, previous_levels=None):
    """
    Return (status, message, levels).
    previous_levels: {limit key: level} from the device's last reading, or None.
    message is None when the status is normal.
    """
    previous_levels = previous_levels or {}
    values = {"voltage": voltage_v, "current": current_a, "temperature": temperature_c}
    levels, findings = {}, []

    for limit in LIMITS:
        raw = values[limit.quantity]
        if raw is None:                      # e.g. no temperature sensor attached
            continue
        checked = abs(raw) if limit.quantity == "current" else raw   # direction does not matter
        level = limit_level(limit, checked, previous_levels.get(limit.key, "normal"))
        levels[limit.key] = level
        if level != "normal":
            findings.append((level, _message(limit, level, checked, raw)))

    if not findings:
        return "normal", None, levels
    status = max((level for level, _ in findings), key=SEVERITY_ORDER.get)
    return status, "; ".join(text for _, text in findings), levels


class AlertTracker:
    """Remembers each device's limit levels between readings (for hysteresis)."""

    def __init__(self):
        self._levels = {}
        self._lock = Lock()

    def evaluate(self, device_key, voltage_v, current_a, temperature_c):
        """Status and message for a reading from device_key, e.g. ("sensor", "arduino-1")."""
        with self._lock:
            status, message, levels = evaluate_reading(
                voltage_v, current_a, temperature_c, self._levels.get(device_key))
            self._levels[device_key] = levels
        return status, message

    def reset(self):
        with self._lock:
            self._levels.clear()


# One shared tracker for the running server
alert_tracker = AlertTracker()
