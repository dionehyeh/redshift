from typing import Literal
from pydantic import BaseModel, Field

class SeasonCreateRequest(BaseModel):
    crop: str = Field(..., min_length=1)
    start_date: str
    end_date: str
    outcome: Literal["good", "average", "poor", "failed"]
    loss_percent: int | None = Field(None, ge=0, le=100)
    suspected_cause: Literal["water_shortage", "excess_rain", "pests", "unsure"] | str | None = None
    investment: float | None = None
    revenue: float | None = None

class SeasonPatchRequest(BaseModel):
    crop: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    outcome: Literal["good", "average", "poor", "failed"] | None = None
    loss_percent: int | None = None
    suspected_cause: str | None = None

class FindingReviewRequest(BaseModel):
    action: Literal["confirm", "correct", "reject"]
    new_cause: str | None = None
    note: str | None = None

class FindingResponse(BaseModel):
    id: int
    kind: str
    weeks: list[int]
    deviation: str
    unit: str | None = None
    crop_stage: str
    severity: str
    confidence: str
    source: str
    resolution: str
    text: str
    explainer_key: str | None = None
    review_status: str

class SeasonAnalysisResponse(BaseModel):
    season_id: int
    approval_status: str
    comparison_years: str
    findings: list[FindingResponse]
    gaps: list[str] = []
    followup_question: str | None = None
