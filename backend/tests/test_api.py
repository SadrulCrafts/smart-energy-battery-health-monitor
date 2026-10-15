"""
test_api.py
-----------
The HTTP and WebSocket endpoints, each test with a fresh in-memory database.
"""

from app import config
from tests.conftest import reading


def test_store_reading_server_decides_status_and_soh(client):
    response = client.post("/readings", json=reading())
    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "simulated"
    assert body["status"] == "normal"
    assert body["alert_message"] is None
    assert body["soh_pct"] is None and body["soh_valid"] is False
    assert "single reading is not enough" in body["soh_note"]
    assert body["timestamp"].endswith(("Z", "+00:00"))     # always UTC


def test_client_cannot_set_status_or_soh(client):
    response = client.post("/readings", json=reading(status="normal", soh_pct=99.0))
    assert response.status_code == 422


def test_invalid_values_are_rejected(client):
    assert client.post("/readings", json=reading(source="made-up")).status_code == 422
    assert client.post("/readings", json=reading(voltage_v=-1)).status_code == 422
    assert client.post("/readings", json=reading(temperature_c=500)).status_code == 422


def test_low_voltage_gives_warning_with_message(client):
    body = client.post("/readings", json=reading(voltage_v=3.15)).json()
    assert body["status"] == "warning"
    assert "Voltage 3.150 V is low" in body["alert_message"]


def test_hysteresis_through_the_api(client):
    statuses = [
        client.post("/readings", json=reading(voltage_v=v)).json()["status"]
        for v in (3.19, 3.22, 3.26)
    ]
    assert statuses == ["warning", "warning", "normal"]


def test_hysteresis_is_per_device(client):
    client.post("/readings", json=reading(device_id="a", voltage_v=3.19))
    other = client.post("/readings", json=reading(device_id="b", voltage_v=3.22)).json()
    assert other["status"] == "normal"


def test_status_empty_then_latest(client):
    empty = client.get("/status").json()
    assert empty == {"has_data": False, "total_readings": 0, "latest": None}
    client.post("/readings", json=reading(voltage_v=3.70))
    client.post("/readings", json=reading(voltage_v=3.60))
    status = client.get("/status").json()
    assert status["total_readings"] == 2
    assert status["latest"]["voltage_v"] == 3.60


def test_history_is_oldest_first_and_can_filter_by_source(client):
    for v in (3.9, 3.8, 3.7):
        client.post("/readings", json=reading(voltage_v=v))
    client.post("/readings", json=reading(source="sensor", voltage_v=4.0))

    history = client.get("/history?limit=10").json()
    assert [r["voltage_v"] for r in history] == [3.9, 3.8, 3.7, 4.0]

    simulated = client.get("/history?source=simulated").json()
    assert {r["source"] for r in simulated} == {"simulated"}
    assert len(client.get("/history?limit=2").json()) == 2


def test_thresholds_include_hysteresis_and_note(client):
    limits = client.get("/thresholds").json()
    assert limits["voltage_low_warning_v"] == config.VOLTAGE_LOW_WARNING_V
    assert limits["voltage_hysteresis_v"] == config.VOLTAGE_HYSTERESIS_V
    assert "Not certified" in limits["note"]


def test_websocket_pushes_each_new_reading(client):
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        client.post("/readings", json=reading(voltage_v=3.55))
        message = ws.receive_json()
    assert message["type"] == "reading"
    assert message["data"]["voltage_v"] == 3.55


def test_cors_allows_only_the_dashboard(client):
    def preflight(origin):
        return client.options(
            "/readings",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        )

    allowed = preflight("http://localhost:3000")
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-origin" not in preflight("http://evil.example").headers


def test_health_reports_version(client):
    body = client.get("/health").json()
    assert body["service"] == "battery-health-monitor-api"
    assert body["version"]
