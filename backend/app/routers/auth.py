from fastapi import APIRouter, Depends

from app.db import get_db
from app.deps import current_user, read_user_profile
from app.schemas.auth import UserPrefsUpdate, UserResponse

user_router = APIRouter(tags=["User Profile"])


@user_router.get("/me", response_model=UserResponse)
def get_current_user_profile(user: dict = Depends(current_user)):
    return user


@user_router.patch("/me/prefs", response_model=UserResponse)
def update_user_preferences(body: UserPrefsUpdate, user: dict = Depends(current_user)):
    changes = body.model_dump(exclude_unset=True)
    language = changes.get("language")
    market_toggle = changes.get("market_toggle")
    default_share_consent = changes.get("default_share_consent")

    with get_db() as conn:
        if language is not None:
            conn.execute(
                "UPDATE users SET language = ? WHERE id = ?",
                (language, user["id"]),
            )
        if "market_toggle" in changes or "default_share_consent" in changes:
            conn.execute(
                "INSERT INTO farmer_prefs (user_id) VALUES (?) ON CONFLICT (user_id) DO NOTHING",
                (user["id"],),
            )
        if "market_toggle" in changes:
            conn.execute(
                "UPDATE farmer_prefs SET market_toggle = ? WHERE user_id = ?",
                (market_toggle, user["id"]),
            )
        if "default_share_consent" in changes:
            conn.execute(
                "UPDATE farmer_prefs SET default_share_consent = ? WHERE user_id = ?",
                (
                    default_share_consent
                    if default_share_consent is not None
                    else 0,
                    user["id"],
                ),
            )
        profile = read_user_profile(conn, user["id"])
        if not profile:
            raise RuntimeError(
                "The authenticated user profile disappeared during update"
            )
        return profile
