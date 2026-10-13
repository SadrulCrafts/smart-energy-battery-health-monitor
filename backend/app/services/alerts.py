"""
alerts.py
---------
Stage 3, Step 5: decide the status of one reading.

    normal   - every checked value is inside its range
    warning  - at least one value is close to a limit
    critical - at least one value is beyond a limit

All triggered rules are reported, and the most severe one decides the status.
"""

from .. import config

SEVERITY_ORDER = {"normal": 0, "warning": 1, "critical": 2}


def evaluate_reading(voltage_v, current_a, temperature_c):
    """Return (status, message). message is None when the status is normal."""
    findings = []   # list of (severity, text)

    # Voltage
    if voltage_v <= config.VOLTAGE_LOW_CRITICAL_V:
        findings.append(("critical", f"Voltage {voltage_v:.3f} V at or below "
                                     f"{config.VOLTAGE_LOW_CRITICAL_V:.2f} V (cut-off)"))
    elif voltage_v <= config.VOLTAGE_LOW_WARNING_V:
        findings.append(("warning", f"Voltage {voltage_v:.3f} V is low "
                                    f"(<= {config.VOLTAGE_LOW_WARNING_V:.2f} V)"))
    if voltage_v >= config.VOLTAGE_HIGH_CRITICAL_V:
        findings.append(("critical", f"Voltage {voltage_v:.3f} V at or above "
                                     f"{config.VOLTAGE_HIGH_CRITICAL_V:.2f} V (possible over-charge)"))
    elif voltage_v >= config.VOLTAGE_HIGH_WARNING_V:
        findings.append(("warning", f"Voltage {voltage_v:.3f} V is high "
                                    f"(>= {config.VOLTAGE_HIGH_WARNING_V:.2f} V)"))

    # Current (direction does not matter here, only size)
    if abs(current_a) >= config.CURRENT_CRITICAL_A:
        findings.append(("critical", f"Current {current_a:+.3f} A exceeds "
                                     f"{config.CURRENT_CRITICAL_A:.1f} A"))
    elif abs(current_a) >= config.CURRENT_WARNING_A:
        findings.append(("warning", f"Current {current_a:+.3f} A is higher than expected "
                                    f"(>= {config.CURRENT_WARNING_A:.1f} A)"))

    # Temperature (may be missing if no sensor is attached)
    if temperature_c is not None:
        if temperature_c >= config.TEMPERATURE_HIGH_CRITICAL_C:
            findings.append(("critical", f"Temperature {temperature_c:.1f} C at or above "
                                         f"{config.TEMPERATURE_HIGH_CRITICAL_C:.0f} C"))
        elif temperature_c >= config.TEMPERATURE_HIGH_WARNING_C:
            findings.append(("warning", f"Temperature {temperature_c:.1f} C is high "
                                        f"(>= {config.TEMPERATURE_HIGH_WARNING_C:.0f} C)"))
        if temperature_c <= config.TEMPERATURE_LOW_WARNING_C:
            findings.append(("warning", f"Temperature {temperature_c:.1f} C is very low "
                                        f"(<= {config.TEMPERATURE_LOW_WARNING_C:.0f} C)"))

    if not findings:
        return "normal", None

    status = max((severity for severity, _ in findings), key=SEVERITY_ORDER.get)
    message = "; ".join(text for _, text in findings)
    return status, message