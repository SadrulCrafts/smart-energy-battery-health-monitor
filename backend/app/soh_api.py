"""
soh_api.py
----------
Stage 3, Step 7: endpoints for the SoH model.

    GET  /soh/model-info  - what the model is, what it needs, where it is valid
    POST /soh/predict     - estimate SoH from the 8 early-discharge features

The 8 features describe the FIRST 600 s of a 2 A constant-current discharge
(see model/scripts/build_features.py). No estimate is made when the model file
is missing or any feature lies outside the range seen in training; the answer
then has soh_pct = null, soh_valid = false and a note explaining why.
"""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from .services.soh_model import get_soh_model

router = APIRouter(prefix="/soh", tags=["soh model"])

# Example values = a real NASA row: B0005, discharge cycle 1 (measured SoH 92.82 %)
EXAMPLE_FEATURES = {
    "v_start_v": 4.1915,
    "v_drop_30s_v": 0.1516,
    "v_at_60s_v": 3.9458,
    "v_at_300s_v": 3.8289,
    "v_at_600s_v": 3.7495,
    "v_slope_60_600_mv_per_min": -19.386,
    "temp_start_c": 24.33,
    "temp_rise_600s_c": 5.0745,
}


class SohFeatures(BaseModel):
    """The 8 inputs, all computed from the first 600 s of one discharge."""

    model_config = ConfigDict(
        extra="forbid",        # unknown fields (for example "voltage_v") are rejected
        allow_inf_nan=False,
        json_schema_extra={"examples": [EXAMPLE_FEATURES]},
    )

    v_start_v: float = Field(description="Voltage at t = 0 s, before the load (V)")
    v_drop_30s_v: float = Field(description="Voltage drop in the first 30 s (V)")
    v_at_60s_v: float = Field(description="Voltage at 60 s (V)")
    v_at_300s_v: float = Field(description="Voltage at 300 s (V)")
    v_at_600s_v: float = Field(description="Voltage at 600 s (V)")
    v_slope_60_600_mv_per_min: float = Field(
        description="Voltage slope between 60 s and 600 s (mV per minute, negative)")
    temp_start_c: float = Field(description="Cell temperature at t = 0 s (C)")
    temp_rise_600s_c: float = Field(description="Temperature rise during the first 600 s (C)")


class SohPrediction(BaseModel):
    soh_pct: float | None = Field(description="Estimated SoH in % of rated 2.0 Ah, or null")
    soh_valid: bool = Field(description="True only when an estimate was actually made")
    soh_note: str
    out_of_range: list[str] = Field(description="Features outside the training range")


@router.get("/model-info")
def model_info():
    """Model details, training ranges and the conditions it is valid for."""
    return get_soh_model().info()


@router.post("/predict", response_model=SohPrediction)
def predict_soh(features: SohFeatures):
    """
    Estimate SoH from early-discharge features.
    A refused estimate is still a normal answer (HTTP 200) with soh_valid = false.
    """
    return get_soh_model().predict(features.model_dump())