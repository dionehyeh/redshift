import json
import math
from datetime import date
from pathlib import Path

from app.engine.scoring import load_crops
from app.errors import AppError

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _read_reference_json(path: Path, label: str) -> dict:
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
    except OSError as exc:
        raise AppError(
            "REFERENCE_DATA_UNAVAILABLE",
            f"{label} reference data is unavailable",
            status=503,
        ) from exc
    except json.JSONDecodeError as exc:
        raise AppError(
            "REFERENCE_DATA_INVALID",
            f"{label} reference data is invalid",
            status=500,
        ) from exc
    if not isinstance(data, dict):
        raise AppError(
            "REFERENCE_DATA_INVALID",
            f"{label} reference data is invalid",
            status=500,
        )
    return data


def _invalid_outlook() -> AppError:
    return AppError(
        "OUTLOOK_DATA_INVALID",
        "Seasonal outlook reference data is invalid",
        status=500,
    )


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
    if lang not in {"en", "ml"}:
        raise AppError("UNSUPPORTED_LANGUAGE", "Language is not supported", status=422)
    data = _read_reference_json(DATA_DIR / "explainers.json", "Explainer")
    cards = []
    for key, entry in data.items():
        translations = entry.get("translations", {}) if isinstance(entry, dict) else {}
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("title"), str)
            or not entry["title"].strip()
            or not isinstance(entry.get("body"), str)
            or not entry["body"].strip()
            or not isinstance(translations, dict)
        ):
            raise AppError(
                "REFERENCE_DATA_INVALID",
                "Explainer reference data is invalid",
                status=500,
            )
        localized = translations.get(lang)
        if (
            lang == "ml"
            and isinstance(localized, dict)
            and isinstance(localized.get("title"), str)
            and localized["title"].strip()
            and isinstance(localized.get("body"), str)
            and localized["body"].strip()
        ):
            title = localized["title"]
            body = localized["body"]
            content_lang = "ml"
        else:
            title = entry["title"]
            body = entry["body"]
            content_lang = "en"
        cards.append(
            {"key": key, "title": title, "body": body, "lang": content_lang}
        )
    return cards

def get_seasons_list() -> list[dict]:
    path = DATA_DIR / "seasons.json"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("seasons", [])

def get_sources_list() -> list[dict]:
    path = DATA_DIR / "sources.json"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("items", [])


def get_seasonal_outlook(region: str = "kerala", today: date | None = None) -> dict:
    data = _read_reference_json(DATA_DIR / "outlooks.json", "Seasonal outlook")
    forecasts = data.get("forecasts")
    if not isinstance(forecasts, list):
        raise _invalid_outlook()

    normalized_region = region.strip().casefold()
    current_date = today or date.today()
    current_forecasts = []
    for forecast in forecasts:
        if (
            not isinstance(forecast, dict)
            or not isinstance(forecast.get("region"), str)
            or not forecast["region"].strip()
        ):
            raise _invalid_outlook()
        if forecast["region"].strip().casefold() != normalized_region:
            continue
        try:
            valid_from = date.fromisoformat(forecast["valid_from"])
            valid_through = date.fromisoformat(forecast["valid_through"])
            entered_on = date.fromisoformat(forecast["entered_on"])
        except (KeyError, TypeError, ValueError) as exc:
            raise _invalid_outlook() from exc
        factor_range = forecast.get("factor_range")
        if (
            not isinstance(forecast.get("label"), str)
            or not forecast["label"].strip()
            or not isinstance(forecast.get("source"), str)
            or not forecast["source"].strip()
            or not isinstance(forecast.get("valid_for"), str)
            or not forecast["valid_for"].strip()
            or valid_from > valid_through
            or entered_on > current_date
            or not isinstance(factor_range, list)
            or len(factor_range) != 2
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in factor_range
            )
            or factor_range[0] <= 0
            or factor_range[0] > factor_range[1]
        ):
            raise _invalid_outlook()
        if valid_from <= current_date <= valid_through:
            current_forecasts.append((entered_on, forecast))

    if current_forecasts:
        _, forecast = max(current_forecasts, key=lambda item: item[0])
        return {
            "region": region.strip(),
            "label": forecast["label"],
            "factor_range": forecast["factor_range"],
            "source": forecast["source"],
            "valid_for": forecast["valid_for"],
            "entered_on": forecast["entered_on"],
        }

    raise AppError(
        "OUTLOOK_UNAVAILABLE",
        "No current seasonal outlook is available for this region",
        status=503,
        details={"region": region.strip()},
    )
