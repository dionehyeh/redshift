from fastapi import APIRouter
from app.services.reference_service import (
    get_crops_list,
    get_explainers,
    get_seasons_list,
    get_sources_list,
)
from app.engine.scoring import load_crops
from app.errors import AppError

router = APIRouter(tags=["Reference Data"])

@router.get("/crops")
def list_crops():
    return {"items": get_crops_list()}

@router.get("/crops/{id}")
def get_crop(id: str):
    crops = {c["name"]: c for c in load_crops()}
    if id not in crops:
        raise AppError("NOT_FOUND", "Crop not found in catalog", status=404)
    return crops[id]

@router.get("/explainers")
def list_explainers(lang: str = "en"):
    return {"items": get_explainers(lang)}

@router.get("/explainers/{key}")
def get_single_explainer(key: str, lang: str = "en"):
    cards = {e["key"]: e for e in get_explainers(lang)}
    if key not in cards:
        raise AppError("NOT_FOUND", "Explainer card not found", status=404)
    return cards[key]

@router.get("/outlook")
def get_seasonal_outlook(region: str = "kerala"):
    return {
        "region": region,
        "label": "below normal",
        "factor_range": [0.80, 0.95],
        "source": "IMD Seasonal Monsoon Outlook (Manual Reference)",
        "valid_for": "2026 Season",
        "entered_on": "2026-11-14",
    }

@router.get("/reference/seasons")
def list_seasons():
    return {"seasons": get_seasons_list()}

@router.get("/sources")
def list_data_sources():
    return {"items": get_sources_list()}
