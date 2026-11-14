import json
import logging
from typing import Any

import httpx
import jwt
from fastapi import Depends, Header
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError
from psycopg2.errors import UniqueViolation

from app.config import settings
from app.db import get_db
from app.errors import AppError
from app.security import ClerkConfigurationError, decode_clerk_token
from app.services.report_service import report_is_active

logger = logging.getLogger(__name__)
VALID_ROLES = {"farmer", "mentor", "officer", "admin"}
VALID_HELPER_TYPES = {"student", "volunteer", "college", "officer"}


def _clerk_contact(profile: dict[str, Any]) -> str:
    email_addresses = profile.get("email_addresses")
    if not isinstance(email_addresses, list):
        email_addresses = []
    primary_email_id = profile.get("primary_email_address_id")
    for email in email_addresses:
        if (
            isinstance(email, dict)
            and email.get("id") == primary_email_id
            and isinstance(email.get("email_address"), str)
        ):
            return email["email_address"]
    if email_addresses:
        email = email_addresses[0]
        if isinstance(email, dict) and isinstance(email.get("email_address"), str):
            return email["email_address"]

    phone_numbers = profile.get("phone_numbers")
    if not isinstance(phone_numbers, list):
        phone_numbers = []
    primary_phone_id = profile.get("primary_phone_number_id")
    for phone in phone_numbers:
        if (
            isinstance(phone, dict)
            and phone.get("id") == primary_phone_id
            and isinstance(phone.get("phone_number"), str)
        ):
            return phone["phone_number"]
    if phone_numbers:
        phone = phone_numbers[0]
        if isinstance(phone, dict) and isinstance(phone.get("phone_number"), str):
            return phone["phone_number"]
    return f"clerk:{profile['id']}"


def read_user_profile(conn: Any, user_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """SELECT u.id, u.role, u.helper_type, u.name, u.language, u.contact,
                  fp.market_toggle, COALESCE(fp.default_share_consent, 0) AS default_share_consent
           FROM users u
           LEFT JOIN farmer_prefs fp ON fp.user_id = u.id
           WHERE u.id = ?""",
        (user_id,),
    ).fetchone()
    return dict(row) if row else None


def _sync_clerk_user(clerk_user_id: str) -> dict:
    if not settings.clerk_secret_key:
        raise AppError(
            "AUTH_CONFIGURATION",
            "CLERK_SECRET_KEY is required to provision the user profile",
            status=503,
        )

    try:
        response = httpx.get(
            f"https://api.clerk.com/v1/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise AppError(
                "UNAUTHENTICATED",
                "The Clerk account associated with this session no longer exists",
                status=401,
            ) from exc
        logger.exception("Could not retrieve Clerk profile for %s", clerk_user_id)
        raise AppError(
            "IDENTITY_PROVIDER_UNAVAILABLE",
            "Unable to retrieve the authenticated Clerk profile",
            status=503,
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("Could not retrieve Clerk profile for %s", clerk_user_id)
        raise AppError(
            "IDENTITY_PROVIDER_UNAVAILABLE",
            "Unable to retrieve the authenticated Clerk profile",
            status=503,
        ) from exc

    try:
        profile = response.json()
    except ValueError as exc:
        logger.exception("Clerk returned invalid profile JSON for %s", clerk_user_id)
        raise AppError(
            "IDENTITY_PROVIDER_UNAVAILABLE",
            "Clerk returned an invalid user profile",
            status=503,
        ) from exc
    if not isinstance(profile, dict) or profile.get("id") != clerk_user_id:
        logger.error("Clerk returned an invalid profile for %s", clerk_user_id)
        raise AppError(
            "IDENTITY_PROVIDER_UNAVAILABLE",
            "Clerk returned an invalid user profile",
            status=503,
        )

    public_metadata = profile.get("public_metadata") or {}
    unsafe_metadata = profile.get("unsafe_metadata") or {}
    if not isinstance(public_metadata, dict):
        public_metadata = {}
    if not isinstance(unsafe_metadata, dict):
        unsafe_metadata = {}
    role = public_metadata.get("role")
    role = role if isinstance(role, str) and role in VALID_ROLES else "farmer"
    helper_type = public_metadata.get("helper_type")
    helper_type = (
        helper_type
        if isinstance(helper_type, str) and helper_type in VALID_HELPER_TYPES
        else None
    )
    language = unsafe_metadata.get("language")
    language = (
        language if isinstance(language, str) and language in {"en", "ml"} else "en"
    )
    name = " ".join(
        part
        for part in (profile.get("first_name"), profile.get("last_name"))
        if isinstance(part, str) and part.strip()
    ).strip()
    username = profile.get("username")
    name = (
        name
        or (username if isinstance(username, str) else None)
        or _clerk_contact(profile)
    )
    contact = _clerk_contact(profile)

    try:
        with get_db() as conn:
            row = conn.execute(
                """INSERT INTO users (clerk_user_id, role, helper_type, name, language, contact)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT (clerk_user_id) DO UPDATE SET
                       name = EXCLUDED.name,
                       language = EXCLUDED.language,
                       contact = EXCLUDED.contact
                   RETURNING id""",
                (clerk_user_id, role, helper_type, name, language, contact),
            ).fetchone()
            if not row:
                raise RuntimeError("Could not provision the Clerk user profile")
            conn.execute(
                "INSERT INTO farmer_prefs (user_id) VALUES (?) ON CONFLICT (user_id) DO NOTHING",
                (row["id"],),
            )
            user = read_user_profile(conn, row["id"])
            if not user:
                raise RuntimeError("Could not read the provisioned user profile")
            return user
    except UniqueViolation as exc:
        logger.warning(
            "Clerk profile contact is already attached to another local account"
        )
        raise AppError(
            "ACCOUNT_CONFLICT",
            "This email or phone is already linked to another account",
            status=409,
        ) from exc


def current_user(authorization: str | None = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("UNAUTHENTICATED", "Authentication required", status=401)

    token = authorization[7:].strip()
    if not token:
        raise AppError("UNAUTHENTICATED", "Authentication required", status=401)

    try:
        claims = decode_clerk_token(token)
    except ClerkConfigurationError as exc:
        raise AppError("AUTH_CONFIGURATION", str(exc), status=503) from exc
    except PyJWKClientError as exc:
        if isinstance(exc, PyJWKClientConnectionError):
            logger.exception("Could not retrieve Clerk signing keys")
            raise AppError(
                "IDENTITY_PROVIDER_UNAVAILABLE",
                "Unable to verify the Clerk session",
                status=503,
            ) from exc
        raise AppError(
            "UNAUTHENTICATED", "Invalid or expired Clerk session", status=401
        ) from exc
    except jwt.PyJWTError as exc:
        raise AppError(
            "UNAUTHENTICATED", "Invalid or expired Clerk session", status=401
        ) from exc

    clerk_user_id = claims["sub"]
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE clerk_user_id = ?",
            (clerk_user_id,),
        ).fetchone()
        if row:
            conn.execute(
                "INSERT INTO farmer_prefs (user_id) VALUES (?) ON CONFLICT (user_id) DO NOTHING",
                (row["id"],),
            )
            user = read_user_profile(conn, row["id"])
            if not user:
                raise RuntimeError("Could not read the authenticated user profile")
            return user

    return _sync_clerk_user(clerk_user_id)


def require_role(*roles: str):
    def dependency(user: dict = Depends(current_user)):
        if user["role"] not in roles:
            raise AppError("FORBIDDEN", f"Access restricted to {roles}", status=403)
        return user

    return dependency


def own_field(field_id: int, user: dict = Depends(require_role("farmer"))):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM fields WHERE id = ?", (field_id,)).fetchone()
        if not row or row["farmer_id"] != user["id"]:
            raise AppError("NOT_FOUND", "Field not found", status=404)
        return dict(row)


def own_season(id: int, user: dict = Depends(require_role("farmer"))):
    with get_db() as conn:
        row = conn.execute(
            """SELECT s.* FROM seasons s
               JOIN fields f ON f.id = s.field_id
               WHERE s.id = ? AND f.farmer_id = ?""",
            (id, user["id"]),
        ).fetchone()
    if not row:
        raise AppError("NOT_FOUND", "Season not found", status=404)
    return dict(row)


def own_plan(id: int, user: dict = Depends(require_role("farmer"))):
    with get_db() as conn:
        row = conn.execute(
            """SELECT p.* FROM plans p
               JOIN fields f ON f.id = p.field_id
               WHERE p.id = ? AND f.farmer_id = ?""",
            (id, user["id"]),
        ).fetchone()
    if not row:
        raise AppError("NOT_FOUND", "Plan not found", status=404)
    return dict(row)


def reviewable_finding(id: int, user: dict = Depends(current_user)):
    if user["role"] not in {"farmer", "mentor", "officer"}:
        raise AppError("FORBIDDEN", "Access restricted to farmers and shared helpers", status=403)

    with get_db() as conn:
        row = conn.execute(
            """SELECT fi.*, s.field_id, f.farmer_id
               FROM findings fi
               JOIN seasons s ON s.id = fi.season_id
               JOIN fields f ON f.id = s.field_id
               WHERE fi.id = ?""",
            (id,),
        ).fetchone()
        if not row:
            raise AppError("NOT_FOUND", "Finding not found", status=404)

        if user["role"] == "farmer":
            if row["farmer_id"] != user["id"]:
                raise AppError("NOT_FOUND", "Finding not found", status=404)
            return dict(row)

        reports = conn.execute(
            """SELECT r.fields_shared, r.expires_at, r.revoked_at, r.status
               FROM reports r
               JOIN plans p ON p.id = r.plan_id
               JOIN fields f ON f.id = p.field_id
               WHERE r.shared_with = ? AND p.field_id = ?
                 AND r.created_by = f.farmer_id""",
            (user["id"], row["field_id"]),
        ).fetchall()
    for report in reports:
        if not report_is_active(report):
            continue
        try:
            shared_fields = json.loads(report["fields_shared"])
        except (TypeError, json.JSONDecodeError) as exc:
            logger.exception("Invalid consent fields stored for a report")
            raise AppError(
                "REPORT_INVALID",
                "Stored report consent is invalid",
                status=500,
            ) from exc
        if isinstance(shared_fields, list) and "findings" in shared_fields:
            return dict(row)
    raise AppError("NOT_FOUND", "Finding not found", status=404)
