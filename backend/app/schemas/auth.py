from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    id: int
    name: str
    role: str
    language: str
    contact: str
    helper_type: str | None = None
    market_toggle: Literal["earn_more", "play_safe"] | None = None
    default_share_consent: int = 0


class UserPrefsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: Literal["en", "ml"] | None = None
    market_toggle: Literal["earn_more", "play_safe"] | None = None
    default_share_consent: int | None = Field(default=None, ge=0, le=1)
