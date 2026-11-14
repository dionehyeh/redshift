from typing import Literal

from fastapi import APIRouter, Query

from app.engine.scoring import load_crops
from app.errors import AppError
from app.schemas.reference import SeasonalOutlookResponse
from app.services.reference_service import (
    get_crops_list,
    get_explainers,
    get_seasonal_outlook,
    get_seasons_list,
    get_sources_list,
)

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
def list_explainers(lang: Literal["en", "ml"] = "en"):
    return {"items": get_explainers(lang)}

@router.get("/explainers/{key}")
def get_single_explainer(key: str, lang: Literal["en", "ml"] = "en"):
    cards = {e["key"]: e for e in get_explainers(lang)}
    if key not in cards:
        raise AppError("NOT_FOUND", "Explainer card not found", status=404)
    return cards[key]

@router.get("/outlook", response_model=SeasonalOutlookResponse)
def get_outlook(region: str = Query("kerala", min_length=1, max_length=80)):
    return get_seasonal_outlook(region)

@router.get("/reference/seasons")
def list_seasons():
    return {"seasons": get_seasons_list()}

@router.get("/sources")
def list_data_sources():
    return {"items": get_sources_list()}
