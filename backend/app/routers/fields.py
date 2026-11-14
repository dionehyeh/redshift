import json
import logging
import math
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response

from app.schemas.fields import (
    FieldCreateRequest,
    FieldCreateResponse,
    FieldPatchRequest,
    FieldPatchResponse,
    FieldProfileResponse,
    FeasibleCropsResponse,
    FieldListResponse,
    TimelineResponse,
    MapResponse,
    HistoryResponse,
)
from app.deps import require_role, own_field
from app.errors import AppError
from app.services.field_service import (
    create_field_record,
    list_feasible_crops,
    list_field_history,
    list_field_records,
    onboard_field_task,
    update_field_record,
)
from app.services.climate_service import (
    ClimateDataUnavailable,
    load_cell_timeline,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fields", tags=["Fields"])


def get_owned_field(
    id: int,
    user: dict = Depends(require_role("farmer")),
) -> dict:
    return own_field(id, user)


# ---------------------------------------------------------------------------
# POST /fields — create field and enqueue onboarding job
# ---------------------------------------------------------------------------

@router.post("", status_code=202, response_model=FieldCreateResponse)
def create_field(
    body: FieldCreateRequest,
    tasks: BackgroundTasks,
    user: dict = Depends(require_role("farmer")),
):
    field_id, job_id = create_field_record(
        user["id"],
        body.name,
        body.lat,
        body.lon,
        body.water_source,
        body.water_quality,
        body.area_ha,
        body.boundary_geojson,
    )

    tasks.add_task(onboard_field_task, job_id, field_id)

    return {"field_id": field_id, "job_id": job_id, "status": "queued"}


# ---------------------------------------------------------------------------
# GET /fields — list fields for authenticated farmer
# ---------------------------------------------------------------------------

@router.get("", response_model=FieldListResponse)
def list_fields(
    status: str | None = Query(None, pattern="^(pending|building|ready|failed)$"),
    user: dict = Depends(require_role("farmer")),
):
    items = list_field_records(user["id"], status)
    return {"items": items, "total": len(items)}


# ---------------------------------------------------------------------------
# GET /fields/{id} — full field profile
# ---------------------------------------------------------------------------

@router.get("/{id}", response_model=FieldProfileResponse)
def get_field_profile(id: int, field: dict = Depends(get_owned_field)):
    # Parse stored profile_meta if available
    raw_meta = field.get("profile_meta")
    if raw_meta:
        try:
            meta = json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta
        except (json.JSONDecodeError, TypeError) as exc:
            logger.exception("Invalid profile metadata for field %s", id)
            raise AppError(
                "FIELD_PROFILE_INVALID",
                "Stored field profile metadata is invalid",
                status=500,
            ) from exc
    else:
        meta = {}
    if not isinstance(meta, dict):
        raise AppError(
            "FIELD_PROFILE_INVALID",
            "Stored field profile metadata is invalid",
            status=500,
        )

    def _metric(
        key: str,
        default_value: Any,
        default_source: str,
        resolution: str = "regional",
        confidence: str = "low",
    ) -> dict[str, Any]:
        if key in meta:
            m = meta[key]
            if not isinstance(m, dict):
                raise AppError(
                    "FIELD_PROFILE_INVALID",
                    f"Stored field metadata for {key} is invalid",
                    status=500,
                )
            return {
                "value": m.get("value", default_value),
                "source": m.get("source", default_source),
                "resolution": m.get("resolution", resolution),
                "confidence": m.get("confidence", confidence),
            }
        # Fall back to column value or supplied default
        col_value = field.get(key, default_value)
        return {
            "value": col_value if col_value is not None else default_value,
            "source": default_source,
            "resolution": resolution,
            "confidence": confidence,
        }

    soil_src = field.get("soil_source") or "SoilGrids estimate"
    soil_conf = field.get("soil_confidence") or "low"

    flood_metric = _metric(
        "flood_prone",
        None,
        "Terrain and rainfall estimate",
        "regional",
        "low",
    )
    if flood_metric["value"] is not None:
        flood_metric["value"] = bool(flood_metric["value"])

    profile = {
        "elevation_m": _metric("elevation_m", None, "SRTM GL1", "30 m", "low"),
        "slope": _metric("slope", None, "SRTM terrain model", "30 m", "low"),
        "flood_prone": flood_metric,
        "drainage": _metric("drainage", None, "Soil classification estimate", "regional", "low"),
        "soil_ph": {
            "value": field.get("soil_ph"),
            "source": soil_src,
            "resolution": "250 m",
            "confidence": soil_conf,
        } if "soil_ph" not in meta else _metric("soil_ph", None, soil_src, "250 m", soil_conf),
        "soil_oc": {
            "value": field.get("soil_oc"),
            "source": soil_src,
            "resolution": "250 m",
            "confidence": soil_conf,
        } if "soil_oc" not in meta else _metric("soil_oc", None, soil_src, "250 m", soil_conf),
        "soil_texture": _metric("soil_texture", field.get("soil_texture"), soil_src, "250 m", soil_conf),
        "water_source": _metric("water_source", field.get("water_source", "unknown"), "Farmer profile", "field-level", "high"),
        "water_quality": _metric("water_quality", field.get("water_quality", "unknown"), "Farmer profile", "field-level", "high"),
    }

    return {
        "id": field["id"],
        "farmer_id": field["farmer_id"],
        "name": field["name"],
        "lat": field["lat"],
        "lon": field["lon"],
        "area_ha": field.get("area_ha"),
        "water_source": field["water_source"],
        "water_quality": field["water_quality"],
        "profile_status": field["profile_status"],
        "profile": profile,
        "climate_cell_id": field.get("climate_cell_id"),
        "created_at": str(field["created_at"]),
    }


# ---------------------------------------------------------------------------
# PATCH /fields/{id} — update field metadata and/or submit corrections
# ---------------------------------------------------------------------------

@router.patch("/{id}", response_model=FieldPatchResponse)
def patch_field(
    id: int,
    body: FieldPatchRequest,
    tasks: BackgroundTasks,
    response: Response,
    user: dict = Depends(require_role("farmer")),
    field: dict = Depends(get_owned_field),
):
    updates = body.model_dump(exclude_unset=True, exclude_none=True, exclude={"corrections"})
    corrections = [
        correction.model_dump()
        for correction in body.corrections or []
    ]
    job_id = update_field_record(id, user["id"], field, updates, corrections)
    if job_id:
        response.status_code = 202
        tasks.add_task(onboard_field_task, job_id, id)
        return {"status": "queued", "field_id": id, "job_id": job_id}
    return {"status": "updated", "field_id": id, "job_id": None}


# ---------------------------------------------------------------------------
# GET /fields/{id}/feasible-crops
# ---------------------------------------------------------------------------

@router.get("/{id}/feasible-crops", response_model=FeasibleCropsResponse)
def get_feasible_crops(id: int, field: dict = Depends(get_owned_field)):
    if field["profile_status"] != "ready":
        raise AppError(
            "FIELD_NOT_READY",
            "Field profile is still being processed. Please wait.",
            409,
        )

    suitable = []
    marginal = []
    not_suitable = []
    latest_computed_at = None

    for r_dict in list_feasible_crops(id):
        windows_raw = r_dict.get("start_windows") or ""
        windows_list = [w for w in windows_raw.split(";") if w] if windows_raw else []

        computed_at_str = str(r_dict["computed_at"]) if r_dict.get("computed_at") else None
        if computed_at_str and (latest_computed_at is None or computed_at_str > latest_computed_at):
            latest_computed_at = computed_at_str

        item = {
            "crop_id": r_dict["crop_id"],
            "crop_name": r_dict["name"],
            "name_ml": r_dict.get("name_ml"),
            "family": r_dict.get("family"),
            "water_need": r_dict.get("water_need"),
            "class": r_dict["crop_class"],
            "reason": r_dict["reason"] or "",
            "start_windows": windows_list,
            "duration_days": r_dict.get("duration_days"),
            "computed_at": computed_at_str,
        }

        cls = r_dict["crop_class"]
        if cls == "suitable":
            suitable.append(item)
        elif cls == "marginal":
            marginal.append(item)
        else:
            not_suitable.append(item)

    return {
        "field_id": id,
        "computed_at": latest_computed_at,
        "suitable": suitable,
        "marginal": marginal,
        "not_suitable": not_suitable,
    }


# ---------------------------------------------------------------------------
# GET /fields/{id}/timeline
# ---------------------------------------------------------------------------

@router.get("/{id}/timeline", response_model=TimelineResponse)
def get_field_timeline(
    id: int,
    field: dict = Depends(get_owned_field),
):
    cell_id = field.get("climate_cell_id")
    if not cell_id:
        lat, lon = field["lat"], field["lon"]
        cell_lat = round(lat * 2) / 2
        cell_lon = round(lon * 2) / 2
        lat_hem = "N" if cell_lat >= 0 else "S"
        lon_hem = "E" if cell_lon >= 0 else "W"
        cell_id = f"{abs(cell_lat):04.1f}{lat_hem}_{abs(cell_lon):05.1f}{lon_hem}"
    try:
        climate_data = load_cell_timeline(cell_id)
    except ClimateDataUnavailable as exc:
        raise AppError(
            "DATA_UNAVAILABLE",
            "Climate data is not available for this field",
            status=503,
        ) from exc
    normals = climate_data["normals"]

    def _pad(values: list[Any] | None) -> list[float | None]:
        padded = list(values or [])[:52]
        padded.extend([None] * (52 - len(padded)))
        return [
            float(value) if value is not None and math.isfinite(float(value)) else None
            for value in padded
        ]

    raw_metrics = {
        "rain_mm": normals.get("rain_mm", normals.get("rain")),
        "tmean": normals.get("tmean"),
        "tmax": normals.get("tmax"),
        "ndvi": normals.get("ndvi"),
    }
    normal_values = {
        key: _pad(values)
        for key, values in raw_metrics.items()
        if values is not None
    }
    observed_values = {
        key: _pad(values)
        for key, values in climate_data["observations"].items()
    }
    metric_keys = set(normal_values) | set(observed_values)
    resolutions = {
        "rain_mm": "~50 km",
        "tmean": "~50 km",
        "tmax": "~50 km",
        "ndvi": "~250 m",
    }
    source_names = {
        "rain_mm": "NASA POWER precipitation",
        "tmean": "NASA POWER mean temperature",
        "tmax": "NASA POWER maximum temperature",
        "ndvi": "MODIS vegetation index",
    }
    series = {}
    for key in metric_keys:
        observation = observed_values.get(key)
        has_observations = observation is not None and any(
            value is not None for value in observation
        )
        series[key] = {
            "values": observation if has_observations else normal_values.get(key, [None] * 52),
            "source": (
                f"{source_names[key]} weekly observations ({climate_data['year']})"
                if has_observations
                else f"{source_names[key]} weekly climatology"
            ),
            "resolution": resolutions[key],
            "is_normal": not has_observations,
        }

    has_historical_observations = any(
        value is not None
        for values in observed_values.values()
        for value in values
    )
    historical_year = climate_data["year"] if has_historical_observations else None
    if historical_year is None:
        source_note = (
            "Weekly climatological estimates are shown because no historical weekly "
            "observations are available in the climate cache."
        )
    else:
        source_note = (
            f"Solid lines show weekly observations from {historical_year}; dashed lines "
            "show climatological normals. Metrics not available from a source are omitted."
        )

    return {
        "field_id": id,
        "weeks": list(range(1, 53)),
        "normals": normal_values,
        "series": series,
        "bands": [],
        "source_note": source_note,
    }


# ---------------------------------------------------------------------------
# GET /fields/{id}/map
# ---------------------------------------------------------------------------

@router.get("/{id}/map", response_model=MapResponse)
def get_field_map(id: int, field: dict = Depends(get_owned_field)):
    props = {
        "name": field["name"],
        "elevation_m": field.get("elevation_m"),
        "slope": field.get("slope"),
        "flood_prone": bool(field.get("flood_prone")) if field.get("flood_prone") is not None else None,
        "drainage": field.get("drainage"),
        "area_ha": field.get("area_ha"),
        "profile_status": field["profile_status"],
    }

    boundary_raw = field.get("boundary_geojson")
    if boundary_raw:
        try:
            boundary = json.loads(boundary_raw) if isinstance(boundary_raw, str) else boundary_raw
        except json.JSONDecodeError as exc:
            logger.exception("Invalid stored boundary GeoJSON for field %s", id)
            raise AppError(
                "FIELD_GEOMETRY_INVALID",
                "Stored field boundary is invalid",
                status=500,
            ) from exc

        if not isinstance(boundary, dict):
            raise AppError(
                "FIELD_GEOMETRY_INVALID",
                "Stored field boundary is invalid",
                status=500,
            )
        if boundary.get("type") == "FeatureCollection":
            features = boundary.get("features")
        elif boundary.get("type") == "Feature":
            features = [boundary]
        else:
            features = [{"type": "Feature", "geometry": boundary, "properties": {}}]

        if (
            not isinstance(features, list)
            or not features
            or any(
                not isinstance(feature, dict)
                or feature.get("type") != "Feature"
                or not isinstance(feature.get("geometry"), dict)
                or not isinstance(feature.get("properties") or {}, dict)
                for feature in features
            )
        ):
            raise AppError(
                "FIELD_GEOMETRY_INVALID",
                "Stored field boundary is invalid",
                status=500,
            )
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    **feature,
                    "properties": {**(feature.get("properties") or {}), **props},
                }
                for feature in features
            ],
        }

    # Without a supplied boundary, return only the recorded coordinate.
    lat = field["lat"]
    lon = field["lon"]
    point_feature = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": props,
    }
    return {"type": "FeatureCollection", "features": [point_feature]}


# ---------------------------------------------------------------------------
# GET /fields/{id}/history
# ---------------------------------------------------------------------------

@router.get("/{id}/history", response_model=HistoryResponse)
def get_field_history(id: int, field: dict = Depends(get_owned_field)):
    seasons = list_field_history(id)
    return {"field_id": id, "total": len(seasons), "seasons": seasons}
