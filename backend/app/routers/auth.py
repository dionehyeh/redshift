from fastapi import APIRouter, Depends

from app.db import get_db
from app.deps import current_user
from app.schemas.auth import UserPrefsUpdate, UserResponse

user_router = APIRouter(tags=["User Profile"])


@user_router.get("/me", response_model=UserResponse)
def get_current_user_profile(user: dict = Depends(current_user)):
    return user


@user_router.patch("/me/prefs")
def update_user_preferences(
    body: UserPrefsUpdate, user: dict = Depends(current_user)
):
    with get_db() as conn:
        if body.language:
            conn.execute(
                "UPDATE users SET language = ? WHERE id = ?",
                (body.language, user["id"]),
            )
        if body.market_toggle is not None or body.default_share_consent is not None:
            conn.execute(
                """UPDATE farmer_prefs
                   SET market_toggle = COALESCE(?, market_toggle),
                       default_share_consent = COALESCE(?, default_share_consent)
                   WHERE user_id = ?""",
                (body.market_toggle, body.default_share_consent, user["id"]),
            )
    return {"status": "updated"}
