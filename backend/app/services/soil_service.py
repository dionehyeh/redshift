"""Point soil estimates from the ISRIC SoilGrids v2.0 API."""

import math
from typing import Any

import requests

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
SOIL_PROPERTIES = ("phh2o", "soc", "clay", "sand", "silt")
SOIL_DEPTH = "0-5cm"


class SoilDataUnavailable(RuntimeError):
    """Raised when SoilGrids has no valid soil estimate for a location."""


def _texture_class(clay: float, sand: float, silt: float) -> str | None:
    total = clay + sand + silt
    if total <= 0:
        raise ValueError("Soil texture fractions must have a positive sum")
    clay, sand, silt = (fraction * 100 / total for fraction in (clay, sand, silt))

    if clay >= 40 and sand <= 45 and silt < 40:
        return "clay"
    if clay >= 40 and sand < 20 and silt >= 40:
        return "silty_clay"
    if clay >= 35 and sand >= 45 and silt < 20:
        return "sandy_clay"
    if 27 <= clay < 40 and sand < 20 and silt >= 40:
        return "silty_clay_loam"
    if 27 <= clay < 40 and 20 <= sand <= 45 and 15 <= silt < 53:
        return "clay_loam"
    if 20 <= clay < 35 and sand > 45 and silt < 28:
        return "sandy_clay_loam"
    if silt >= 80 and clay < 12:
        return "silt"
    if silt >= 50 and clay < 27:
        return "silt_loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and 23 <= sand <= 52:
        return "loam"
    if clay < 20 and 52 <= sand < 85:
        return "sandy_loam"
    if sand >= 85:
        return "sand"
    return None


def _layer_values(payload: dict[str, Any]) -> dict[str, float | None]:
    properties = payload.get("properties")
    layers = properties.get("layers") if isinstance(properties, dict) else None
    if not isinstance(layers, list):
        raise SoilDataUnavailable("SoilGrids returned an invalid soil profile")

    values: dict[str, float | None] = {name: None for name in SOIL_PROPERTIES}
    for layer in layers:
        if (
            not isinstance(layer, dict)
            or not isinstance(layer.get("name"), str)
            or layer["name"] not in values
        ):
            continue
        depths = layer.get("depths")
        if not isinstance(depths, list):
            continue
        depth = next(
            (item for item in depths if isinstance(item, dict) and item.get("label") == SOIL_DEPTH),
            None,
        )
        unit_measure = layer.get("unit_measure")
        factor = unit_measure.get("d_factor") if isinstance(unit_measure, dict) else None
        measurement = (
            depth.get("values", {}).get("mean")
            if isinstance(depth, dict) and isinstance(depth.get("values"), dict)
            else None
        )
        if (
            isinstance(measurement, bool)
            or not isinstance(measurement, (int, float))
            or not math.isfinite(float(measurement))
            or isinstance(factor, bool)
            or not isinstance(factor, (int, float))
            or not math.isfinite(float(factor))
            or factor <= 0
        ):
            continue
        raw_value = float(measurement) / float(factor)
        name = layer["name"]
        if name == "phh2o":
            values[name] = raw_value
        elif name == "soc":
            values[name] = raw_value / 10
        else:
            values[name] = raw_value
    return values


def fetch_soil_profile(
    lat: float,
    lon: float,
    timeout: float = 30,
) -> dict[str, Any]:
    try:
        response = requests.get(
            SOILGRIDS_URL,
            params={
                "lat": lat,
                "lon": lon,
                "property": list(SOIL_PROPERTIES),
                "depth": [SOIL_DEPTH],
                "value": ["mean"],
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise SoilDataUnavailable("SoilGrids service is unavailable") from exc

    if not isinstance(payload, dict):
        raise SoilDataUnavailable("SoilGrids returned an invalid soil profile")
    values = _layer_values(payload)
    if not any(value is not None for value in values.values()):
        raise SoilDataUnavailable("SoilGrids has no soil estimate for this location")

    clay, sand, silt = values["clay"], values["sand"], values["silt"]
    texture = (
        _texture_class(clay, sand, silt)
        if clay is not None and sand is not None and silt is not None
        else None
    )
    return {
        "soil_ph": values["phh2o"],
        "soil_oc": values["soc"],
        "soil_texture": texture,
        "clay_pct": clay,
        "sand_pct": sand,
        "silt_pct": silt,
        "source": "ISRIC SoilGrids v2.0",
        "resolution": "250 m",
        "confidence": "medium",
    }


def estimate_drainage(
    clay_pct: float | None,
    sand_pct: float | None,
    slope_pct: float | None,
) -> str | None:
    if clay_pct is None or slope_pct is None:
        return None
    if clay_pct >= 40 and slope_pct < 2:
        return "poor"
    if (sand_pct is not None and sand_pct >= 70) or slope_pct >= 8:
        return "good"
    return "moderate"
