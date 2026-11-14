from app.engine.scoring import load_crops, get_weights, pick_three, evaluate, verdict
from app.services.climate_service import load_cell_normals
from app.analysis.core import water_outlook, stored_soil_water

def build_scoring_environment(
    field: dict,
    history: list[dict],
    start_week: int,
    next_week: int,
    stored_water_answer: str | None = None,
    toggle: str | None = None,
    scenario: dict | None = None,
) -> dict:
    cell_id = field.get("climate_cell_id") or "09.5N_076.5E"
    normals = load_cell_normals(cell_id)
    
    stored_mm, stored_conf, stored_basis = stored_soil_water(answer=stored_water_answer)
    outlook = water_outlook(normals["rain"], start_week, 12, imd_factor_range=(0.80, 0.95))
    weights = get_weights(dry_outlook=(outlook["factor"] < 0.9), toggle=toggle)

    return {
        "field": {
            "elevation_m": field.get("elevation_m") or 4.0,
            "flood_prone": bool(field.get("flood_prone")),
            "drainage": field.get("drainage") or "poor",
            "ph": field.get("soil_ph") or 5.4,
            "water_source": field.get("water_source") or "rainfed",
            "slope": field.get("slope") or "low",
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
