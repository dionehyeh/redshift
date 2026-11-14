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
        
        # Build scrubbed snapshot strictly respecting farmer consent
        snapshot = {}
        if "field_profile" in share_fields:
            field_row = conn.execute(
                """SELECT elevation_m, flood_prone, drainage, soil_ph
                   FROM fields WHERE id = ?""",
                (plan_row["field_id"],),
            ).fetchone()
            if not field_row:
                raise AppError(
                    "NOT_FOUND",
                    "Field profile not found",
                    status=404,
                )
            snapshot["field"] = {
                "elevation_m": field_row["elevation_m"],
                "flood_prone": bool(field_row["flood_prone"]),
                "drainage": field_row["drainage"],
                "soil_ph": field_row["soil_ph"],
            }
        if "cards" in share_fields:
            cards_rows = conn.execute(
                """SELECT position, crop_id, verdict, total, factors_json
                   FROM plan_cards WHERE plan_id = ? ORDER BY position ASC""",
                (plan_id,),
            ).fetchall()
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
        if "history" in share_fields:
            history_rows = conn.execute(
                """SELECT c.name AS crop, s.start_date, s.end_date,
                          s.outcome, s.loss_percent
                   FROM seasons s
                   LEFT JOIN crops c ON c.id = s.crop_id
                   WHERE s.field_id = ? AND s.status = 'completed'
                   ORDER BY s.end_date DESC, s.id DESC""",
                (plan_row["field_id"],),
            ).fetchall()
            snapshot["history"] = [
                {
                    "crop": row["crop"],
                    "start_date": row["start_date"],
                    "end_date": row["end_date"],
                    "outcome": row["outcome"],
                    "loss_percent": row["loss_percent"],
                }
                for row in history_rows
            ]
        if "findings" in share_fields:
            finding_rows = conn.execute(
                """SELECT fi.kind, fi.week_from, fi.week_to, fi.deviation,
                          fi.unit, fi.crop_stage, fi.severity, fi.confidence,
                          fi.source, fi.resolution, fi.text_plain,
                          fi.explainer_key, fi.review_status
                   FROM findings fi
                   JOIN seasons s ON s.id = fi.season_id
                   WHERE s.field_id = ?
                   ORDER BY s.start_date DESC, fi.week_from, fi.id""",
                (plan_row["field_id"],),
            ).fetchall()
            snapshot["findings"] = [
                {
                    "kind": row["kind"],
                    "weeks": [row["week_from"], row["week_to"]],
                    "deviation": row["deviation"],
                    "unit": row["unit"],
                    "crop_stage": row["crop_stage"],
                    "severity": row["severity"],
                    "confidence": row["confidence"],
                    "source": row["source"],
                    "resolution": row["resolution"],
                    "text": row["text_plain"],
                    "explainer_key": row["explainer_key"],
                    "review_status": row["review_status"],
                }
                for row in finding_rows
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
