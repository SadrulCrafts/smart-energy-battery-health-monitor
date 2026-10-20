"""
test_capacity.py
----------------
Measured capacity (coulomb counting) on made-up discharges with known answers,
and the GET /capacity endpoint.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app import config
from app.services.capacity import Sample, find_runs
from tests.conftest import reading

T0 = datetime(2026, 10, 20, 8, 0, 0, tzinfo=timezone.utc)


def discharge(rest_v=4.18, start_v=4.10, end_v=2.99, seconds=3600, current=-0.4,
              rest_after=3, step_s=1.0, t0=T0, temperature=25.0):
    """Rest, a constant-current discharge of `seconds` seconds, then rest again."""
    samples = [Sample(t0 + timedelta(seconds=s), rest_v, 0.0, temperature) for s in (0, 1, 2)]
    start = t0 + timedelta(seconds=3)
    steps = int(seconds / step_s)
    for n in range(steps + 1):
        v = start_v + (end_v - start_v) * n / steps
        samples.append(Sample(start + timedelta(seconds=n * step_s), v, current, temperature + n / steps))
    end = start + timedelta(seconds=steps * step_s)
    for n in range(1, rest_after + 1):
        samples.append(Sample(end + timedelta(seconds=n), end_v + 0.25, 0.0, temperature + 1))
    return samples


def test_capacity_of_a_constant_current_discharge():
    (run,) = find_runs(discharge())
    # 0.4 A for exactly one hour = 400 mAh
    assert run.capacity_mah == pytest.approx(400.0, abs=0.1)
    assert run.duration_s == pytest.approx(3600)
    assert run.mean_current_a == pytest.approx(0.4)
    assert run.readings == 3601
    assert run.rest_voltage_v == 4.18
    assert run.ended == "cutoff" and run.started_full


def test_energy_uses_voltage_times_current():
    (run,) = find_runs(discharge(start_v=4.0, end_v=3.0))
    # average voltage 3.5 V x 0.4 A x 1 h = 1.4 Wh
    assert run.energy_wh == pytest.approx(1.4, abs=0.001)


def test_complete_run_from_full_gets_a_measured_soh():
    (run,) = find_runs(discharge(seconds=5 * 3600))     # 0.4 A x 5 h = 2000 mAh
    assert run.soh_pct == pytest.approx(2000 / config.RATED_CAPACITY_MAH * 100, abs=0.1)
    assert "seller's figure" in run.soh_note


def test_run_not_started_from_full_has_no_soh():
    (run,) = find_runs(discharge(rest_v=3.80))
    assert run.capacity_mah == pytest.approx(400.0, abs=0.1)   # still measured
    assert run.soh_pct is None
    assert "not from a full charge" in run.soh_note and "3.800 V" in run.soh_note


def test_run_stopped_before_cutoff_has_no_soh():
    (run,) = find_runs(discharge(end_v=3.40))
    assert run.ended == "stopped_early" and run.soh_pct is None
    assert "before the 3.00 V cut-off" in run.soh_note


def test_gap_in_readings_ends_the_run():
    samples = discharge()
    del samples[1000:1010]                                  # 10 s without readings
    runs = find_runs(samples)
    assert runs[0].ended == "data_gap" and runs[0].soh_pct is None
    assert len(runs) == 2                                   # the part after the gap is a new run


def test_run_without_an_end_is_in_progress_or_interrupted():
    samples = discharge(rest_after=0)[:-100]                # still discharging at the last reading
    last = samples[-1].timestamp
    assert find_runs(samples, now=last + timedelta(seconds=2))[0].ended == "in_progress"
    assert find_runs(samples, now=last + timedelta(minutes=10))[0].ended == "data_gap"


def test_two_discharges_are_two_runs():
    first = discharge(seconds=600)
    second = discharge(seconds=1200, t0=first[-1].timestamp + timedelta(hours=2))
    runs = find_runs(first + second)
    assert [round(r.capacity_mah) for r in runs] == [67, 133]   # 0.4 A x 10 min, x 20 min


def test_no_discharge_no_runs():
    resting = [Sample(T0 + timedelta(seconds=s), 3.9, 0.0, 25.0) for s in range(60)]
    assert find_runs(resting) == []


def test_missing_temperature_is_reported():
    samples = [Sample(s.timestamp, s.voltage_v, s.current_a, None) for s in discharge(seconds=60)]
    (run,) = find_runs(samples)
    assert run.max_temperature_c is None
    assert "No temperature readings" in run.warnings[0]


# --- endpoint ------------------------------------------------------------------------

def post_run(client, samples, source="sensor", device_id="arduino-uno-1"):
    for s in samples:
        body = reading(source=source, device_id=device_id, voltage_v=round(s.voltage_v, 4),
                       current_a=s.current_a, temperature_c=s.temperature_c,
                       timestamp=s.timestamp.isoformat())
        assert client.post("/readings", json=body).status_code == 201


def test_capacity_endpoint_measures_sensor_runs(client):
    post_run(client, discharge(seconds=120))
    body = client.get("/capacity", params={"device_id": "arduino-uno-1"}).json()
    assert body["available"] is True
    assert body["rated_capacity_mah"] == config.RATED_CAPACITY_MAH
    (run,) = body["runs"]
    assert run["capacity_mah"] == pytest.approx(0.4 * 120 / 3.6, abs=0.1)
    assert run["ended"] == "cutoff"


def test_capacity_endpoint_keeps_devices_apart(client):
    post_run(client, discharge(seconds=60), device_id="a")
    assert client.get("/capacity", params={"device_id": "b"}).json()["runs"] == []


def test_capacity_endpoint_refuses_simulated_data(client):
    post_run(client, discharge(seconds=30), source="simulated", device_id="simulator-1")
    body = client.get("/capacity", params={"source": "simulated", "device_id": "simulator-1"}).json()
    assert body["available"] is False and body["runs"] == []
    assert "compressed time" in body["note"]
