from typing import Literal

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    name: str
    role: str
    language: str
    contact: str
    helper_type: str | None = None


class UserPrefsUpdate(BaseModel):
    language: Literal["en", "ml"] | None = None
    market_toggle: Literal["earn_more", "play_safe"] | None = None
    default_share_consent: int | None = None
