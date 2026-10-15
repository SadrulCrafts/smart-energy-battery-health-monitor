"""
test_bridge.py
--------------
The serial bridge: reading the Arduino's lines correctly, ignoring broken ones,
and labeling data honestly. No hardware needed.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # backend/ (bridge.py, simulator.py)

from bridge import FakeArduino, build_payload, format_reading_line, parse_line  # noqa: E402


def test_reading_line_is_parsed():
    kind, data = parse_line("READING v=3.842 i=-0.381 t=26.40 load=1\r\n")
    assert kind == "reading"
    assert data == {"voltage_v": 3.842, "current_a": -0.381, "temperature_c": 26.40, "load_on": True}


@pytest.mark.parametrize("temperature", ["nan", "-127.00"])
def test_missing_temperature_sensor_becomes_none(temperature):
    kind, data = parse_line(f"READING v=3.9 i=-0.4 t={temperature} load=0")
    assert kind == "reading"
    assert data["temperature_c"] is None and data["load_on"] is False


def test_load_field_is_optional():
    assert parse_line("READING v=3.9 i=-0.4 t=25.0")[1]["load_on"] is None


@pytest.mark.parametrize(
    "line",
    [
        "",
        "READING v=3.9 t=25.0",            # no current
        "READING v=abc i=-0.4 t=25.0",     # not a number
        "READING v=nan i=-0.4 t=25.0",     # voltage must be a real number
        "READING v=3.9 i -0.4",            # broken field
        "\x00\x13garbage from a reset",    # noise right after the port opens
        "EADING v=3.9 i=-0.4 t=25",        # first characters lost
    ],
)
def test_broken_lines_are_ignored(line):
    assert parse_line(line)[0] == "invalid"


def test_info_and_error_lines():
    assert parse_line("INFO firmware 1.0 started") == ("info", "firmware 1.0 started")
    assert parse_line("ERROR INA219 not found") == ("error", "INA219 not found")


def test_payload_keeps_the_given_source_and_drops_load():
    _, data = parse_line("READING v=3.84249 i=-0.38149 t=26.4049 load=1")
    payload = build_payload(data, "sensor", "arduino-uno-1")
    assert payload == {
        "source": "sensor",
        "device_id": "arduino-uno-1",
        "voltage_v": 3.8425,
        "current_a": -0.3815,
        "temperature_c": 26.4,
    }


def test_format_and_parse_round_trip():
    line = format_reading_line(3.7, -0.37, None, True)
    assert line == "READING v=3.700 i=-0.370 t=nan load=1\n"
    assert parse_line(line)[1]["temperature_c"] is None


def test_fake_arduino_lines_are_all_valid():
    fake = FakeArduino(port=None, interval_s=1.0, speed=60.0)
    kinds = [parse_line(line)[0] for line in fake.lines(60)]
    assert kinds.count("reading") == 60
    assert set(kinds) <= {"reading", "info"}


def test_fake_arduino_through_an_in_memory_serial_port():
    serial = pytest.importorskip("serial")
    port = serial.serial_for_url("loop://", timeout=0.5)
    fake = FakeArduino(port, interval_s=1.0, speed=60.0)
    for line in fake.lines(5):
        port.write(line.encode("ascii"))
    readings = [parse_line(port.readline().decode("ascii")) for _ in range(5)]
    port.close()
    assert all(kind == "reading" for kind, _ in readings)
    assert 3.0 <= readings[0][1]["voltage_v"] <= 4.25
