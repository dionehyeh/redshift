from typing import Any, Literal
from pydantic import BaseModel, Field

class FieldCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    water_source: Literal["rainfed", "borewell", "canal", "unknown"] = "unknown"
    water_quality: Literal["good", "saline", "unknown"] = "unknown"
    area_ha: float | None = Field(None, gt=0)
    boundary_geojson: str | None = None

class FieldCorrectionItem(BaseModel):
    key: str
    value: Any
    note: str | None = None

class FieldPatchRequest(BaseModel):
    name: str | None = None
    water_source: Literal["rainfed", "borewell", "canal", "unknown"] | None = None
    water_quality: Literal["good", "saline", "unknown"] | None = None
    corrections: list[FieldCorrectionItem] | None = None

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
    profile: dict[str, MetricMetadata] = {}
    climate_cell_id: str | None = None
    created_at: str

class FeasibleCropItem(BaseModel):
    crop: str
    name_ml: str | None = None
    class_: Literal["suitable", "marginal", "not_suitable"] = Field(..., alias="class")
    reason: str
    start_windows: list[str] = []
    duration_days: list[int] = []

class FeasibleCropsResponse(BaseModel):
    field_id: int
    computed_at: str
    crops: list[FeasibleCropItem]
