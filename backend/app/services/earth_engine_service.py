"""Point time-series extraction from public NASA Earth Engine collections."""

import logging
import math
from datetime import UTC, date, datetime, timedelta
from typing import Any

from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import HttpError

from app.config import settings

MODIS_COLLECTION = "MODIS/061/MOD13Q1"
IMERG_COLLECTION = "NASA/GPM_L3/IMERG_V07"
logger = logging.getLogger(__name__)


class EarthObservationDataUnavailable(RuntimeError):
    """Raised when Earth Engine data or credentials are unavailable."""


def _earth_engine():
    if not settings.ee_project:
        raise EarthObservationDataUnavailable(
            "EE_PROJECT is required to retrieve MODIS and IMERG data"
        )
    try:
        import ee
    except ImportError as exc:
        raise EarthObservationDataUnavailable(
            "earthengine-api is required to retrieve MODIS and IMERG data"
        ) from exc

    try:
        ee.Initialize(project=settings.ee_project)
    except (ee.EEException, GoogleAuthError, HttpError, OSError, ValueError) as exc:
        logger.warning("Could not initialize Google Earth Engine", exc_info=exc)
        raise EarthObservationDataUnavailable(
            "Google Earth Engine credentials or project configuration are unavailable"
        ) from exc
    return ee


def fetch_modis_ndvi(
    lat: float,
    lon: float,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    if start_date >= end_date:
        raise ValueError("start_date must be before end_date")
    ee = _earth_engine()
    point = ee.Geometry.Point([lon, lat])
    collection = (
        ee.ImageCollection(MODIS_COLLECTION)
        .filterDate(start_date.isoformat(), end_date.isoformat())
        .select(["NDVI", "SummaryQA"])
    )

    def sample(image):
        values = image.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=250,
            maxPixels=1000,
        )
        return ee.Feature(
            None,
            {
                "timestamp": image.get("system:time_start"),
                "ndvi": values.get("NDVI"),
                "qa": values.get("SummaryQA"),
            },
        )

    try:
        response = ee.FeatureCollection(collection.map(sample)).getInfo()
    except (ee.EEException, GoogleAuthError, HttpError, OSError, ValueError) as exc:
        logger.warning("Could not retrieve MODIS NDVI", exc_info=exc)
        raise EarthObservationDataUnavailable("MODIS NDVI is unavailable") from exc

    features = response.get("features") if isinstance(response, dict) else None
    if not isinstance(features, list):
        raise EarthObservationDataUnavailable("MODIS returned an invalid response")
    samples = []
    for feature in features:
        properties = feature.get("properties") if isinstance(feature, dict) else None
        if not isinstance(properties, dict):
            continue
        timestamp = properties.get("timestamp")
        if isinstance(timestamp, (int, float)) and math.isfinite(float(timestamp)):
            samples.append(
                {
                    "timestamp": int(timestamp),
                    "ndvi": properties.get("ndvi"),
                    "qa": properties.get("qa"),
                }
            )
    return sorted(samples, key=lambda item: item["timestamp"])


def modis_samples_to_daily(
    samples: list[dict[str, Any]],
    start_date: date,
    end_date: date,
    composite_days: int = 16,
) -> dict[date, float | None]:
    if composite_days < 1:
        raise ValueError("composite_days must be positive")
    daily_samples: dict[date, list[float]] = {}
    for sample in samples:
        timestamp = sample.get("timestamp")
        if not isinstance(timestamp, (int, float)) or not math.isfinite(float(timestamp)):
            continue
        sample_date = datetime.fromtimestamp(
            float(timestamp) / 1000, UTC
        ).date()
        if (
            sample_date >= end_date
            or sample_date + timedelta(days=composite_days) <= start_date
        ):
            continue
        ndvi = sample.get("ndvi")
        qa = sample.get("qa")
        valid = (
            isinstance(ndvi, (int, float))
            and not isinstance(ndvi, bool)
            and math.isfinite(float(ndvi))
            and -2000 <= float(ndvi) <= 10000
            and isinstance(qa, (int, float))
            and not isinstance(qa, bool)
            and 0 <= float(qa) <= 1
        )
        for day_offset in range(composite_days):
            observation_day = sample_date + timedelta(days=day_offset)
            if not start_date <= observation_day < end_date:
                continue
            if valid:
                daily_samples.setdefault(observation_day, []).append(float(ndvi) * 0.0001)

    result: dict[date, float | None] = {}
    for ordinal in range(start_date.toordinal(), end_date.toordinal()):
        day = date.fromordinal(ordinal)
        values = daily_samples.get(day)
        result[day] = sum(values) / len(values) if values else None
    return result


def _iso_week_bounds(year: int, week: int) -> tuple[date, date]:
    start = date.fromisocalendar(year, week, 1)
    end = (
        date.fromisocalendar(year + 1, 1, 1)
        if week == 52
        else date.fromisocalendar(year, week + 1, 1)
    )
    return start, end


def imerg_features_to_weekly(
    features: list[dict[str, Any]],
    year: int,
) -> dict[int, float | None]:
    bounds = {week: _iso_week_bounds(year, week) for week in range(1, 53)}
    weekly: dict[int, float | None] = {week: None for week in bounds}
    for feature in features:
        properties = feature.get("properties") if isinstance(feature, dict) else None
        if not isinstance(properties, dict):
            continue
        week = properties.get("week")
        rain = properties.get("rain_mm")
        count = properties.get("valid_intervals")
        if (
            not isinstance(week, (int, float))
            or isinstance(week, bool)
            or not float(week).is_integer()
            or int(week) not in bounds
        ):
            continue
        week = int(week)
        start, end = bounds[week]
        expected_count = (end - start).days * 48
        if (
            isinstance(rain, (int, float))
            and not isinstance(rain, bool)
            and math.isfinite(float(rain))
            and isinstance(count, (int, float))
            and math.isfinite(float(count))
            and float(count).is_integer()
            and float(count) >= 0
            and float(count) >= expected_count * 0.8
        ):
            weekly[week] = max(0.0, float(rain))
    return weekly


def fetch_imerg_weekly(
    lat: float,
    lon: float,
    year: int,
) -> dict[int, float | None]:
    ee = _earth_engine()
    point = ee.Geometry.Point([lon, lat])
    images = ee.ImageCollection(IMERG_COLLECTION).select("precipitation")
    features = []
    bounds = {}
    for week in range(1, 53):
        start, end = _iso_week_bounds(year, week)
        bounds[week] = (start, end)
        collection = images.filterDate(start.isoformat(), end.isoformat())
        total = collection.map(lambda image: image.multiply(0.5)).sum().rename("rain_mm")
        count = collection.count().rename("valid_intervals")
        values = ee.Image.cat([total, count]).reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=11132,
            maxPixels=1000,
        )
        features.append(
            ee.Feature(
                None,
                {
                    "week": week,
                    "rain_mm": values.get("rain_mm"),
                    "valid_intervals": values.get("valid_intervals"),
                },
            )
        )

    try:
        response = ee.FeatureCollection(features).getInfo()
    except (ee.EEException, GoogleAuthError, HttpError, OSError, ValueError) as exc:
        logger.warning("Could not retrieve GPM IMERG rainfall", exc_info=exc)
        raise EarthObservationDataUnavailable("GPM IMERG rainfall is unavailable") from exc

    features_data = response.get("features") if isinstance(response, dict) else None
    if not isinstance(features_data, list):
        raise EarthObservationDataUnavailable("GPM IMERG returned an invalid response")
    return imerg_features_to_weekly(features_data, year)
