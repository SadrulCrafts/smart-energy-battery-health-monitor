"""
test_soh_model.py
-----------------
The guarded SoH model service: it must refuse whenever a trustworthy estimate
is impossible. Tests that need the trained model file are skipped when it is
missing (it is not stored in Git; run model/scripts/train_soh_model.py).
"""

import math

import pytest

from app.services import soh_model
from app.services.soh_model import SohModel, get_soh_model

# Real NASA row: cell B0005, discharge cycle 1 (measured SoH 92.82 %)
NASA_EXAMPLE = {
    "v_start_v": 4.1915,
    "v_drop_30s_v": 0.1516,
    "v_at_60s_v": 3.9458,
    "v_at_300s_v": 3.8289,
    "v_at_600s_v": 3.7495,
    "v_slope_60_600_mv_per_min": -19.386,
    "temp_start_c": 24.33,
    "temp_rise_600s_c": 5.0745,
}

needs_model = pytest.mark.skipif(
    not get_soh_model().available, reason="trained model file not present"
)


def test_missing_model_file_is_reported_not_crashed(tmp_path, monkeypatch):
    monkeypatch.setattr(soh_model, "MODEL_FILE", tmp_path / "missing.joblib")
    service = SohModel()
    assert service.available is False
    result = service.predict(NASA_EXAMPLE)
    assert result["soh_pct"] is None and result["soh_valid"] is False
    assert "not found" in result["soh_note"]


@needs_model
def test_single_live_reading_is_refused():
    result = get_soh_model().predict({"v_start_v": 4.2})
    assert result["soh_valid"] is False
    assert "missing features" in result["soh_note"]


@needs_model
def test_non_finite_value_is_refused():
    result = get_soh_model().predict({**NASA_EXAMPLE, "v_at_600s_v": math.nan})
    assert result["soh_valid"] is False


@needs_model
def test_value_outside_training_range_is_refused_and_named():
    result = get_soh_model().predict({**NASA_EXAMPLE, "v_at_600s_v": 3.30})
    assert result["soh_pct"] is None and result["soh_valid"] is False
    assert len(result["out_of_range"]) == 1
    assert result["out_of_range"][0].startswith("v_at_600s_v=")


@needs_model
def test_nasa_example_is_estimated_inside_the_training_target_range():
    service = get_soh_model()
    result = service.predict(NASA_EXAMPLE)
    target = service.info()["target_range"]
    assert result["soh_valid"] is True
    assert target["min"] <= result["soh_pct"] <= target["max"]
    assert result["soh_pct"] == pytest.approx(92.8, abs=2.5)   # measured 92.82 %
    assert "MAE" in result["soh_note"]


@needs_model
def test_predict_endpoint(client):
    ok = client.post("/soh/predict", json=NASA_EXAMPLE)
    assert ok.status_code == 200 and ok.json()["soh_valid"] is True

    refused = client.post("/soh/predict", json={**NASA_EXAMPLE, "v_at_600s_v": 3.30})
    assert refused.status_code == 200 and refused.json()["soh_valid"] is False

    assert client.post("/soh/predict", json={"voltage_v": 3.8}).status_code == 422
