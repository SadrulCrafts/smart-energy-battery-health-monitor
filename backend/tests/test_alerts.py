"""
test_alerts.py
--------------
The alert rules on their own: thresholds, the most severe rule winning, and
hysteresis (an alert clears only after the value moves back past a margin).
"""

import pytest

from app import config
from app.services.alerts import AlertTracker, evaluate_reading


@pytest.mark.parametrize(
    ("voltage", "expected"),
    [
        (3.85, "normal"),
        (config.VOLTAGE_LOW_WARNING_V + 0.001, "normal"),
        (config.VOLTAGE_LOW_WARNING_V, "warning"),       # "at or below" counts
        (3.10, "warning"),
        (config.VOLTAGE_LOW_CRITICAL_V, "critical"),
        (2.50, "critical"),
        (config.VOLTAGE_HIGH_WARNING_V, "warning"),
        (config.VOLTAGE_HIGH_CRITICAL_V, "critical"),
    ],
)
def test_voltage_thresholds(voltage, expected):
    status, _, _ = evaluate_reading(voltage, -0.4, 25.0)
    assert status == expected


def test_normal_reading_has_no_message():
    assert evaluate_reading(3.85, -0.4, 25.0)[:2] == ("normal", None)


def test_most_severe_rule_wins_and_all_rules_are_listed():
    status, message, _ = evaluate_reading(3.10, -0.4, config.TEMPERATURE_HIGH_CRITICAL_C + 1)
    assert status == "critical"
    assert "Voltage" in message and "Temperature" in message


def test_current_direction_does_not_matter():
    charging = evaluate_reading(3.85, +1.5, 25.0)[0]
    discharging = evaluate_reading(3.85, -1.5, 25.0)[0]
    assert charging == discharging == "warning"


def test_missing_temperature_is_skipped():
    status, message, levels = evaluate_reading(3.85, -0.4, None)
    assert status == "normal" and message is None
    assert "temperature_high" not in levels


def test_cold_temperature_warns():
    assert evaluate_reading(3.85, -0.4, config.TEMPERATURE_LOW_WARNING_C)[0] == "warning"


def run(tracker, voltages, device=("simulated", "a")):
    return [tracker.evaluate(device, v, -0.3, 25.0)[0] for v in voltages]


def test_hysteresis_holds_warning_until_margin_is_passed():
    warn, margin = config.VOLTAGE_LOW_WARNING_V, config.VOLTAGE_HYSTERESIS_V
    tracker = AlertTracker()
    statuses = run(tracker, [3.30, warn - 0.001, warn + 0.01, warn + margin - 0.001, warn + margin + 0.001])
    assert statuses == ["normal", "warning", "warning", "warning", "normal"]


def test_without_history_the_same_voltage_is_normal():
    # 3.21 V is above the 3.20 V warning threshold: only hysteresis can hold a warning there
    assert evaluate_reading(3.21, -0.3, 25.0)[0] == "normal"


def test_hysteresis_message_says_when_alert_clears():
    tracker = AlertTracker()
    tracker.evaluate(("s", "a"), 3.19, -0.3, 25.0)
    status, message = tracker.evaluate(("s", "a"), 3.22, -0.3, 25.0)
    assert status == "warning"
    assert "recovering" in message and "3.25" in message


def test_critical_steps_down_to_warning_then_normal():
    tracker = AlertTracker()
    statuses = run(tracker, [2.99, 3.04, 3.06, 3.24, 3.26])
    assert statuses == ["critical", "critical", "warning", "warning", "normal"]


def test_voltage_hovering_at_threshold_does_not_flap():
    tracker = AlertTracker()
    statuses = run(tracker, [3.199, 3.201, 3.199, 3.202, 3.198, 3.203])
    assert statuses == ["warning"] * 6     # without hysteresis this would alternate


def test_devices_have_separate_memory():
    tracker = AlertTracker()
    tracker.evaluate(("sensor", "a"), 3.19, -0.3, 25.0)
    assert tracker.evaluate(("sensor", "b"), 3.22, -0.3, 25.0)[0] == "normal"
    assert tracker.evaluate(("sensor", "a"), 3.22, -0.3, 25.0)[0] == "warning"


def test_reset_forgets_previous_levels():
    tracker = AlertTracker()
    tracker.evaluate(("s", "a"), 3.19, -0.3, 25.0)
    tracker.reset()
    assert tracker.evaluate(("s", "a"), 3.22, -0.3, 25.0)[0] == "normal"
