import math

from app.analysis.core import stored_soil_water, water_outlook
from app.engine.scoring import get_weights, pick_three, verdict
from app.errors import AppError
from app.services.climate_service import load_cell_normals
from app.services.reference_service import get_seasonal_outlook


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
    
    stored_mm, _stored_conf, stored_basis = stored_soil_water(answer=stored_water_answer)
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
