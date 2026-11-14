from typing import Literal
from pydantic import BaseModel, Field

class ReportCreateRequest(BaseModel):
    plan_id: int
    mentor_id: int
    share: list[Literal["field_profile", "history", "cards", "findings"]] = Field(..., min_length=1)
    expires_days: Literal[7, 14, 30] = 14

class CommentCreateRequest(BaseModel):
    text: str = Field(..., min_length=2, max_length=2000)

class CommentResponse(BaseModel):
    id: int
    author_label: str
    body: str
    created_at: str

class ReportResponse(BaseModel):
    id: int
    status: str
    share_token: str
    shared_fields: list[str]
    snapshot: dict
    expires_at: str
    revoked_at: str | None = None
    comments: list[CommentResponse] = []
    created_at: str
