"""
config.py
---------
Alert thresholds in ONE place.

IMPORTANT
    These are DEMONSTRATION values for a single small Li-ion cell in this
    prototype. They are NOT certified safety limits and are NOT valid for every
    battery. Before using real hardware, replace them with the limits from the
    datasheet of the exact cell you use. The alert feature only warns; it does
    not make the setup safe on its own.

Hysteresis
    A status is entered at the threshold but only cleared once the value has
    moved back past the threshold by the hysteresis margin. Example: warning
    starts at 3.20 V and only clears above 3.25 V, so a voltage hovering around
    3.20 V does not switch between normal and warning on every reading.
"""

# Voltage (volts)
VOLTAGE_LOW_WARNING_V = 3.20     # cell is nearly empty
VOLTAGE_LOW_CRITICAL_V = 3.00    # at or below planned cut-off: stop discharging
VOLTAGE_HIGH_WARNING_V = 4.22    # slightly above normal full-charge voltage
VOLTAGE_HIGH_CRITICAL_V = 4.25   # possible over-charge

# Temperature (degrees Celsius)
TEMPERATURE_HIGH_WARNING_C = 40.0
TEMPERATURE_HIGH_CRITICAL_C = 45.0
TEMPERATURE_LOW_WARNING_C = 0.0  # cold: many Li-ion cells must not be charged below 0 C

# Current magnitude (amperes); the planned 10-ohm load draws about 0.4 A
CURRENT_WARNING_A = 1.0
CURRENT_CRITICAL_A = 2.0

# How far a value must move back before an alert clears
VOLTAGE_HYSTERESIS_V = 0.05
TEMPERATURE_HYSTERESIS_C = 2.0
CURRENT_HYSTERESIS_A = 0.1

THRESHOLD_NOTE = ("Demonstration thresholds for a prototype. Not certified safety limits; "
                  "replace with the datasheet values of the actual cell.")
