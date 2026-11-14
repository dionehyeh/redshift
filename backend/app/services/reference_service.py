import json
import os
from app.engine.scoring import load_crops

def get_crops_list() -> list[dict]:
    crops = load_crops()
    return [
        {
            "id": c["name"],
            "name": {"en": c["name"].replace("_", " ").title(), "ml": ""},
            "family": c["family"],
            "duration_days": c["duration_days"],
            "water_need": c["water_need"],
            "market": c["market"],
        }
        for c in crops
    ]

def get_explainers(lang: str = "en") -> list[dict]:
    path = "data/explainers.json"
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [
        {"key": k, "title": v["title"], "body": v["body"], "lang": lang}
        for k, v in data.items()
    ]

def get_seasons_list() -> list[dict]:
    path = "data/seasons.json"
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("seasons", [])

def get_sources_list() -> list[dict]:
    path = "data/sources.json"
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("items", [])
