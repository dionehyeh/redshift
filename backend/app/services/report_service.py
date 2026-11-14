import json
import time
from datetime import datetime, timedelta
from app.db import get_db
from app.security import new_share_token
from app.errors import AppError

def create_report_service(farmer_id: int, plan_id: int, mentor_id: int, share_fields: list[str], expires_days: int) -> dict:
    if not share_fields:
        raise AppError("CONSENT_REQUIRED", "Select at least one field to share", status=400)
    
    with get_db() as conn:
        plan_row = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not plan_row:
            raise AppError("NOT_FOUND", "Plan not found", status=404)
        
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
        now = datetime.utcnow()
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
