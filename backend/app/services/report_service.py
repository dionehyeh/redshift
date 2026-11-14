import json
import logging
from datetime import datetime, timedelta, timezone

from app.db import get_db
from app.errors import AppError
from app.security import new_share_token

logger = logging.getLogger(__name__)


def report_is_active(report: dict) -> bool:
    if report.get("revoked_at") or report.get("status") == "revoked":
        return False
    try:
        expiry = datetime.fromisoformat(str(report["expires_at"]))
    except (KeyError, TypeError, ValueError) as exc:
        logger.exception("Invalid report expiration stored in the database")
        raise AppError(
            "REPORT_INVALID",
            "Stored report expiration is invalid",
            status=500,
        ) from exc
    now = datetime.now(timezone.utc)
    if expiry.tzinfo is None:
        now = now.replace(tzinfo=None)
    else:
        now = now.astimezone(expiry.tzinfo)
    return expiry > now


def create_report_service(farmer_id: int, plan_id: int, mentor_id: int, share_fields: list[str], expires_days: int) -> dict:
    allowed_fields = {"field_profile", "history", "cards", "findings"}
    if not share_fields or not set(share_fields).issubset(allowed_fields):
        raise AppError("CONSENT_REQUIRED", "Select at least one field to share", status=400)
    
    with get_db() as conn:
        plan_row = conn.execute(
            """SELECT p.* FROM plans p
               JOIN fields f ON f.id = p.field_id
               WHERE p.id = ? AND f.farmer_id = ?""",
            (plan_id, farmer_id),
        ).fetchone()
        if not plan_row:
            raise AppError("NOT_FOUND", "Plan not found", status=404)
        helper = conn.execute(
            "SELECT id FROM users WHERE id = ? AND role IN ('mentor', 'officer')",
            (mentor_id,),
        ).fetchone()
        if not helper:
            raise AppError("NOT_FOUND", "Consultation helper not found", status=404)
        
        field_row = conn.execute("SELECT * FROM fields WHERE id = ?", (plan_row["field_id"],)).fetchone()
        cards_rows = conn.execute("SELECT * FROM plan_cards WHERE plan_id = ?", (plan_id,)).fetchall()
        
        # Build scrubbed snapshot strictly respecting farmer consent
        snapshot = {}
        if "field_profile" in share_fields:
            snapshot["field"] = {
                "elevation_m": field_row["elevation_m"],
                "flood_prone": bool(field_row["flood_prone"]),
                "drainage": field_row["drainage"],
                "soil_ph": field_row["soil_ph"],
            }
        if "cards" in share_fields:
            snapshot["cards"] = [
                {
                    "position": c["position"],
                    "crop_id": c["crop_id"],
                    "verdict": c["verdict"],
                    "total": c["total"],
                    "factors": json.loads(c["factors_json"]),
                }
                for c in cards_rows
            ]

        token = new_share_token()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        expires_at = (now + timedelta(days=expires_days)).isoformat()

        cursor = conn.execute(
            """INSERT INTO reports (plan_id, created_by, share_token, shared_with, fields_shared, snapshot_json, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            (
                plan_id,
                farmer_id,
                token,
                mentor_id,
                json.dumps(share_fields),
                json.dumps(snapshot),
                expires_at,
            ),
        )
        report_id = cursor.fetchone()["id"]

        # Audit log
        conn.execute(
            """INSERT INTO audit_log (user_id, action, object_type, object_id)
               VALUES (?, 'CREATE_REPORT', 'report', ?)""",
            (farmer_id, report_id),
        )

    return {
        "id": report_id,
        "status": "sent",
        "share_token": token,
        "shared_fields": share_fields,
        "snapshot": snapshot,
        "expires_at": expires_at,
        "created_at": now.isoformat(),
    }
