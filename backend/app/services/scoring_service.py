import logging
import math

from app.analysis.core import stored_soil_water, water_outlook
from app.engine.scoring import get_weights, pick_three, verdict
from app.errors import AppError
from app.services.climate_service import (
    load_cell_normals,
    load_point_soil_moisture,
)
from app.services.earth_engine_service import EarthObservationDataUnavailable
from app.services.reference_service import get_seasonal_outlook

logger = logging.getLogger(__name__)


def build_scoring_environment(
    field: dict,
    history: list[dict],
    start_week: int,
    next_week: int,
    stored_water_answer: str | None = None,
    toggle: str | None = None,
    scenario: dict | None = None,
) -> dict:
    cell_id = field.get("climate_cell_id")
    if not cell_id:
        raise AppError(
            "FIELD_PROFILE_INCOMPLETE",
            "The field climate profile is not available",
            status=409,
        )
    if field.get("elevation_m") is None:
        raise AppError(
            "FIELD_PROFILE_INCOMPLETE",
            "Field elevation is unavailable; crop suitability cannot be calculated",
            status=409,
        )
    normals = load_cell_normals(cell_id)
    if not all(
        key in normals
        and len(normals[key]) == 52
        and all(
            value is not None and math.isfinite(float(value))
            for value in normals[key]
        )
        for key in ("rain", "tmean", "tmax")
    ):
        raise AppError(
            "FIELD_PROFILE_INCOMPLETE",
            "Required climate normals are unavailable for this field",
            status=409,
        )
    
    soil_moisture = None
    soil_moisture_gap = None
    if stored_water_answer is None:
        if field.get("lat") is None or field.get("lon") is None:
            soil_moisture_gap = (
                "Field coordinates are unavailable for SMAP/GLDAS sampling; "
                "a low-confidence default estimate is used."
            )
        else:
            try:
                soil_moisture = load_point_soil_moisture(
                    field["lat"], field["lon"]
                )
            except EarthObservationDataUnavailable as exc:
                logger.warning(
                    "Satellite soil moisture is unavailable for field %s",
                    field.get("id"),
                    exc_info=exc,
                )
                soil_moisture_gap = (
                    "SMAP and GLDAS soil-moisture observations are unavailable; "
                    "a low-confidence default estimate is used."
                )

    sm_vol = soil_moisture["sm_vol"] if soil_moisture else None
    stored_mm, stored_confidence, stored_basis = stored_soil_water(
        answer=stored_water_answer,
        sm_vol=sm_vol,
    )
    stored_water = {
        "value_mm": stored_mm,
        "confidence": stored_confidence,
        "basis": stored_basis,
        "source": (
            soil_moisture["source"]
            if soil_moisture
            else "Farmer-provided answer"
            if stored_water_answer is not None
            else "Low-confidence default"
        ),
        "resolution": soil_moisture.get("resolution") if soil_moisture else None,
        "observed_at": soil_moisture.get("observed_at") if soil_moisture else None,
        "stale": soil_moisture.get("stale", False) if soil_moisture else False,
    }
    try:
        seasonal_reference = get_seasonal_outlook()
    except AppError as exc:
        if exc.code not in {"OUTLOOK_UNAVAILABLE", "REFERENCE_DATA_UNAVAILABLE"}:
            raise
        outlook = water_outlook(normals["rain"], start_week, 12)
        outlook.update(
            {
                "forecast_available": False,
                "factor_range": [0.85, 1.15],
                "factor_source": "climatological baseline",
                "source": "No current regional seasonal outlook bulletin",
                "source_gap": (
                    "Scores use a low-confidence climatological baseline until "
                    "a current outlook bulletin is available."
                ),
                "valid_for": None,
                "entered_on": None,
            }
        )
    else:
        factor_range = seasonal_reference["factor_range"]
        outlook = water_outlook(
            normals["rain"],
            start_week,
            12,
            imd_factor_range=(factor_range[0], factor_range[1]),
        )
        outlook.update(
            {
                "forecast_available": True,
                "factor_range": factor_range,
                "factor_source": "IMD seasonal outlook",
                "source": seasonal_reference["source"],
                "valid_for": seasonal_reference["valid_for"],
                "entered_on": seasonal_reference["entered_on"],
            }
        )
    weights = get_weights(dry_outlook=(outlook["factor"] < 0.9), toggle=toggle)

    return {
        "field": {
            "elevation_m": field["elevation_m"],
            "flood_prone": field.get("flood_prone"),
            "drainage": field.get("drainage"),
            "ph": field.get("soil_ph"),
            "water_source": field.get("water_source", "unknown"),
            "slope": field.get("slope"),
            "water_quality": field.get("water_quality") or "unknown",
        },
        "history": history,
        "normals": normals,
        "start_week": start_week,
        "next_week": next_week,
        "outlook_factor": outlook["factor"],
        "dry_outlook": (outlook["factor"] < 0.9),
        "bare_gap_days": 60,
        "stored_mm": stored_mm,
        "stored_water": stored_water,
        "source_gaps": [soil_moisture_gap] if soil_moisture_gap else [],
        "scenario": scenario or {"rain": 1.0, "temp": 0.0},
        "weights": weights,
        "outlook_info": outlook,
        "stored_basis": stored_basis,
    }

def evaluate_rotation_cards(crops: list[dict], env: dict, customary_crop_name: str = "paddy") -> list[dict]:
    cards = pick_three(crops, env, customary_crop_name)
    for c in cards:
        c["verdict"] = verdict(c)
    return cards
