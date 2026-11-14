import json
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _validate_boundary_geojson(value: str | None) -> str | None:
    if value is None:
        return None

    try:
        boundary = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("boundary_geojson must contain valid JSON") from exc

    def polygon_geometry(geometry: Any) -> bool:
        if not isinstance(geometry, dict):
            return False
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates")

        def finite_number(value: Any) -> bool:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return False
            try:
                return math.isfinite(float(value))
            except (OverflowError, ValueError):
                return False

        def valid_position(position: Any) -> bool:
            return (
                isinstance(position, list)
                and len(position) >= 2
                and all(finite_number(value) for value in position)
                and -180 <= position[0] <= 180
                and -90 <= position[1] <= 90
            )

        def valid_ring(ring: Any) -> bool:
            return (
                isinstance(ring, list)
                and len(ring) >= 4
                and all(valid_position(position) for position in ring)
                and ring[0] == ring[-1]
            )

        def valid_polygon(polygon: Any) -> bool:
            return (
                isinstance(polygon, list)
                and bool(polygon)
                and all(valid_ring(ring) for ring in polygon)
            )

        if geometry_type == "Polygon":
            return valid_polygon(coordinates)
        if geometry_type == "MultiPolygon":
            return (
                isinstance(coordinates, list)
                and bool(coordinates)
                and all(valid_polygon(polygon) for polygon in coordinates)
            )
        return False

    if not isinstance(boundary, dict):
        raise ValueError("boundary_geojson must be a GeoJSON object")

    boundary_type = boundary.get("type")
    if boundary_type == "Feature":
        valid = polygon_geometry(boundary.get("geometry"))
    elif boundary_type == "FeatureCollection":
        features = boundary.get("features")
        valid = isinstance(features, list) and bool(features) and all(
            isinstance(feature, dict)
            and feature.get("type") == "Feature"
            and polygon_geometry(feature.get("geometry"))
            and (
                feature.get("properties") is None
                or isinstance(feature.get("properties"), dict)
            )
            for feature in features
        )
    else:
        valid = polygon_geometry(boundary)

    if not valid:
        raise ValueError("boundary_geojson must contain polygon geometry")
    return value


# ---------------------------------------------------------------------------
# Existing schemas (preserved)
# ---------------------------------------------------------------------------

class FieldCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    lat: float = Field(..., ge=-90.0, le=90.0, allow_inf_nan=False)
    lon: float = Field(..., ge=-180.0, le=180.0, allow_inf_nan=False)
    water_source: Literal["rainfed", "borewell", "canal", "unknown"] = "unknown"
    water_quality: Literal["good", "saline", "unknown"] = "unknown"
    area_ha: float | None = Field(None, gt=0, allow_inf_nan=False)
    boundary_geojson: str | None = None

    @field_validator("boundary_geojson")
    @classmethod
    def validate_boundary_geojson(cls, value: str | None) -> str | None:
        return _validate_boundary_geojson(value)


class FieldCorrectionItem(BaseModel):
    key: Literal["soil_ph", "soil_oc", "soil_texture"]
    value: Any
    note: str | None = None

    @model_validator(mode="after")
    def validate_correction_value(self) -> "FieldCorrectionItem":
        if self.key == "soil_ph":
            if (
                isinstance(self.value, bool)
                or not isinstance(self.value, (int, float))
                or not 0 <= self.value <= 14
            ):
                raise ValueError("soil_ph must be a number between 0 and 14")
        elif self.key == "soil_oc":
            if (
                isinstance(self.value, bool)
                or not isinstance(self.value, (int, float))
                or (isinstance(self.value, float) and not math.isfinite(self.value))
                or not 0 <= self.value <= 100
            ):
                raise ValueError("soil_oc must be a number between 0 and 100")
        elif not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("soil_texture must be a non-empty string")
        if self.note is not None and len(self.note) > 500:
            raise ValueError("note must be at most 500 characters")
        return self


class FieldPatchRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    lat: float | None = Field(None, ge=-90.0, le=90.0, allow_inf_nan=False)
    lon: float | None = Field(None, ge=-180.0, le=180.0, allow_inf_nan=False)
    water_source: Literal["rainfed", "borewell", "canal", "unknown"] | None = None
    water_quality: Literal["good", "saline", "unknown"] | None = None
    area_ha: float | None = Field(None, gt=0, allow_inf_nan=False)
    boundary_geojson: str | None = None
    corrections: list[FieldCorrectionItem] | None = None

    @field_validator("boundary_geojson")
    @classmethod
    def validate_boundary_geojson(cls, value: str | None) -> str | None:
        return _validate_boundary_geojson(value)

    @model_validator(mode="after")
    def require_update(self) -> "FieldPatchRequest":
        for key in (
            "name",
            "lat",
            "lon",
            "water_source",
            "water_quality",
            "area_ha",
            "boundary_geojson",
        ):
            if key in self.model_fields_set and getattr(self, key) is None:
                raise ValueError(f"{key} cannot be null")
        if (
            self.name is None
            and self.lat is None
            and self.lon is None
            and self.water_source is None
            and self.water_quality is None
            and self.area_ha is None
            and self.boundary_geojson is None
            and not self.corrections
        ):
            raise ValueError("At least one field update or soil correction is required")
        return self


class MetricMetadata(BaseModel):
    value: Any
    source: str
    resolution: str | None = None
    confidence: str
    estimate: dict[str, Any] | None = None


class FieldProfileResponse(BaseModel):
    id: int
    farmer_id: int
    name: str
    lat: float
    lon: float
    area_ha: float | None = None
    water_source: str
    water_quality: str
    profile_status: str
    profile: dict[str, MetricMetadata] = Field(default_factory=dict)
    gaps: list[str] = Field(default_factory=list)
    climate_cell_id: str | None = None
    created_at: str


class FeasibleCropItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    crop_id: int
    crop_name: str
    name_ml: str | None = None
    family: str | None = None
    water_need: str | None = None
    class_: Literal["suitable", "marginal", "not_suitable"] = Field(..., alias="class")
    reason: str
    start_windows: list[str] = Field(default_factory=list)
    duration_days: int | None = None
    computed_at: str | None = None


class FeasibleCropsResponse(BaseModel):
    field_id: int
    computed_at: str | None = None
    suitable: list[FeasibleCropItem] = Field(default_factory=list)
    marginal: list[FeasibleCropItem] = Field(default_factory=list)
    not_suitable: list[FeasibleCropItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# New schemas
# ---------------------------------------------------------------------------

class FieldCreateResponse(BaseModel):
    field_id: int
    job_id: str
    status: Literal["queued"]


class FieldPatchResponse(BaseModel):
    status: Literal["updated", "queued"]
    field_id: int
    job_id: str | None = None


class FieldListItem(BaseModel):
    id: int
    name: str
    lat: float
    lon: float
    area_ha: float | None = None
    profile_status: Literal["pending", "building", "ready", "failed"]
    climate_cell_id: str | None = None
    water_source: str
    created_at: str


class FieldListResponse(BaseModel):
    items: list[FieldListItem]
    total: int


class TimelineSeries(BaseModel):
    values: list[float | None]
    source: str
    resolution: str | None = None
    is_normal: bool = True


class TimelineResponse(BaseModel):
    field_id: int
    weeks: list[int]
    normals: dict[str, list[float | None]]
    series: dict[str, TimelineSeries]
    bands: list[dict[str, Any]] = Field(default_factory=list)
    source_note: str


class MapFeatureProperties(BaseModel):
    name: str
    elevation_m: float | None = None
    slope: str | None = None
    flood_prone: bool | None = None
    drainage: str | None = None
    area_ha: float | None = None
    profile_status: str | None = None


class MapResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[dict[str, Any]]


class HistorySeasonItem(BaseModel):
    id: int
    crop_id: int | None = None
    field_id: int
    status: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    outcome: str | None = None
    loss_percent: float | None = None
    suspected_cause: str | None = None
    approval_status: str | None = None
    approved_cause: str | None = None
    approver_role: str | None = None
    investment: float | None = None
    revenue: float | None = None
    created_at: str | None = None
    crop_name: str | None = None
    name_ml: str | None = None
    family: str | None = None
    approved_by_name: str | None = None


class HistoryResponse(BaseModel):
    field_id: int
    total: int
    seasons: list[HistorySeasonItem]
