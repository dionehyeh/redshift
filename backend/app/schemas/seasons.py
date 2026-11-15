from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SeasonOutcome = Literal["good", "average", "poor", "failed"]
FindingReviewAction = Literal["confirm", "correct", "reject"]


class SeasonCreateRequest(BaseModel):
    crop: str = Field(..., min_length=1, max_length=100)
    start_date: date
    end_date: date
    outcome: SeasonOutcome
    loss_percent: int | None = Field(None, ge=0, le=100)
    suspected_cause: str | None = Field(None, min_length=1, max_length=100)
    investment: float | None = Field(None, ge=0, allow_inf_nan=False)
    revenue: float | None = Field(None, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_season_dates(self) -> "SeasonCreateRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class SeasonPatchRequest(BaseModel):
    crop: str | None = Field(None, min_length=1, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    outcome: SeasonOutcome | None = None
    loss_percent: int | None = Field(None, ge=0, le=100)
    suspected_cause: str | None = Field(None, min_length=1, max_length=100)
    investment: float | None = Field(None, ge=0, allow_inf_nan=False)
    revenue: float | None = Field(None, ge=0, allow_inf_nan=False)

    @field_validator("crop", "start_date", "end_date", "outcome", mode="before")
    @classmethod
    def reject_null_required_updates(cls, value):
        if value is None:
            raise ValueError("This field cannot be cleared")
        return value

    @model_validator(mode="after")
    def validate_patch_has_updates(self) -> "SeasonPatchRequest":
        if not self.model_fields_set:
            raise ValueError("At least one season field must be provided")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must be on or after start_date")
        return self


class FindingReviewRequest(BaseModel):
    action: FindingReviewAction
    new_cause: str | None = Field(None, min_length=1, max_length=100)
    note: str | None = Field(None, max_length=1000)

    @model_validator(mode="after")
    def validate_correction_cause(self) -> "FindingReviewRequest":
        if self.action == "correct" and self.new_cause is None:
            raise ValueError("new_cause is required when correcting a finding")
        return self


class SeasonResponse(BaseModel):
    id: int
    field_id: int
    crop_id: int | None = None
    crop: str | None = None
    status: str
    start_date: str | None = None
    end_date: str | None = None
    outcome: SeasonOutcome | None = None
    loss_percent: int | None = None
    suspected_cause: str | None = None
    investment: float | None = None
    revenue: float | None = None
    approval_status: str
    approved_cause: str | None = None
    approver_role: str | None = None


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
    analysis_status: Literal[
        "not_started", "queued", "running", "done", "done_with_gaps", "failed"
    ]
    job_id: str | None = None
    comparison_years: str | None = None
    findings: list[FindingResponse] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    likely_causes: dict | None = None
    followup_question: str | None = None
    analysis_error: str | None = None
