"""Terrain profile lookup from the 30 m SRTM elevation model."""

import math
from statistics import median
from typing import Any

import requests

TERRAIN_URL = "https://api.opentopodata.org/v1/srtm30m"
GRID_RADIUS = 3
GRID_SPACING_M = 30


class TerrainDataUnavailable(RuntimeError):
    """Raised when an SRTM profile cannot be retrieved or validated."""


def fetch_terrain_profile(
    lat: float,
    lon: float,
    timeout: float = 30,
) -> dict[str, Any]:
    if not (-56 <= lat <= 60) or not (-180 <= lon <= 180):
        raise ValueError("Coordinates are outside SRTM coverage")

    lat_step = GRID_SPACING_M / 111_320
    lon_scale = math.cos(math.radians(lat))
    if lon_scale <= 0:
        raise ValueError("Longitude grid spacing is undefined at this latitude")
    lon_step = GRID_SPACING_M / (111_320 * lon_scale)
    locations = [
        (lat + row * lat_step, lon + column * lon_step)
        for row in range(-GRID_RADIUS, GRID_RADIUS + 1)
        for column in range(-GRID_RADIUS, GRID_RADIUS + 1)
    ]

    try:
        response = requests.get(
            TERRAIN_URL,
            params={
                "locations": "|".join(f"{point_lat},{point_lon}" for point_lat, point_lon in locations),
                "interpolation": "bilinear",
                "nodata_value": "null",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise TerrainDataUnavailable("SRTM terrain service is unavailable") from exc

    results = payload.get("results") if isinstance(payload, dict) else None
    if (
        not isinstance(payload, dict)
        or payload.get("status") != "OK"
        or not isinstance(results, list)
        or len(results) != len(locations)
    ):
        raise TerrainDataUnavailable("SRTM returned an incomplete terrain grid")

    elevations: list[list[float]] = []
    for row in range(2 * GRID_RADIUS + 1):
        values = []
        for column in range(2 * GRID_RADIUS + 1):
            result = results[row * (2 * GRID_RADIUS + 1) + column]
            elevation = result.get("elevation") if isinstance(result, dict) else None
            if (
                isinstance(elevation, bool)
                or not isinstance(elevation, (int, float))
                or not math.isfinite(float(elevation))
            ):
                raise TerrainDataUnavailable("SRTM has no elevation for this location")
            values.append(float(elevation))
        elevations.append(values)

    center = GRID_RADIUS
    window = [line[center - 1 : center + 2] for line in elevations[center - 1 : center + 2]]
    dz_dx = (
        window[0][2]
        + 2 * window[1][2]
        + window[2][2]
        - window[0][0]
        - 2 * window[1][0]
        - window[2][0]
    ) / (8 * GRID_SPACING_M)
    dz_dy = (
        window[2][0]
        + 2 * window[2][1]
        + window[2][2]
        - window[0][0]
        - 2 * window[0][1]
        - window[0][2]
    ) / (8 * GRID_SPACING_M)
    slope_pct = math.hypot(dz_dx, dz_dy) * 100
    slope_class = "low" if slope_pct < 3 else "moderate" if slope_pct < 8 else "steep"

    surrounding = [
        value
        for row, values in enumerate(elevations)
        for column, value in enumerate(values)
        if (row, column) != (center, center)
    ]
    relative_elevation = elevations[center][center] - median(surrounding)
    flood_prone = relative_elevation <= -2 and slope_pct <= 2

    return {
        "elevation_m": elevations[center][center],
        "slope": slope_class,
        "slope_pct": slope_pct,
        "relative_elevation_m": relative_elevation,
        "flood_prone": flood_prone,
        "source": "SRTM GL1 via OpenTopoData",
        "resolution": "30 m",
        "confidence": "low",
    }
