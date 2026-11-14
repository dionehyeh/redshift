import json
from datetime import datetime
from fastapi import APIRouter, Depends
from app.schemas.reports import (
    ReportCreateRequest,
    CommentCreateRequest,
    ReportResponse,
)
from app.deps import current_user, require_role
from app.db import get_db
from app.services.report_service import create_report_service
from app.errors import AppError

router = APIRouter(tags=["Consultation Reports"])

@router.post("/reports", status_code=201)
def create_report(body: ReportCreateRequest, user: dict = Depends(require_role("farmer"))):
    return create_report_service(
        farmer_id=user["id"],
        plan_id=body.plan_id,
        mentor_id=body.mentor_id,
        share_fields=body.share,
        expires_days=body.expires_days,
    )

@router.get("/reports/{id}")
def get_report(id: int, user: dict = Depends(current_user)):
    with get_db() as conn:
        report = conn.execute("SELECT * FROM reports WHERE id = ?", (id,)).fetchone()
        if not report:
            raise AppError("NOT_FOUND", "Report not found", status=404)
        
        # Access control check
        if user["role"] == "farmer" and report["created_by"] != user["id"]:
            raise AppError("FORBIDDEN", "Access denied", status=403)
        if user["role"] in ("mentor", "officer") and report["shared_with"] != user["id"]:
            raise AppError("FORBIDDEN", "Report not shared with your account", status=403)
        if report["revoked_at"] or report["expires_at"] < datetime.utcnow().isoformat():
            raise AppError("REPORT_UNAVAILABLE", "This report consultation has expired or been revoked", status=403)

        comments_rows = conn.execute("SELECT * FROM report_comments WHERE report_id = ? ORDER BY created_at ASC", (id,)).fetchall()
        comments = [
            {"id": c["id"], "author_label": c["author_label"], "body": c["body"], "created_at": c["created_at"]}
            for c in comments_rows
        ]

        # Audit view by mentor
        if user["role"] in ("mentor", "officer"):
            conn.execute(
                """INSERT INTO audit_log (user_id, action, object_type, object_id)
                   VALUES (?, 'VIEW_REPORT', 'report', ?)""",
                (user["id"], id),
            )
            conn.execute("UPDATE reports SET status = 'viewed' WHERE id = ? AND status = 'sent'", (id,))

        return {
            "id": report["id"],
            "status": report["status"],
            "share_token": report["share_token"],
            "shared_fields": json.loads(report["fields_shared"]),
            "snapshot": json.loads(report["snapshot_json"]),
            "expires_at": report["expires_at"],
            "revoked_at": report["revoked_at"],
            "comments": comments,
            "created_at": report["created_at"],
        }

@router.post("/reports/{id}/comments", status_code=201)
def add_comment(id: int, body: CommentCreateRequest, user: dict = Depends(require_role("mentor", "officer"))):
    with get_db() as conn:
        report = conn.execute("SELECT * FROM reports WHERE id = ?", (id,)).fetchone()
        if not report:
            raise AppError("NOT_FOUND", "Report not found", status=404)
        
        label = "Agricultural Extension Officer" if user["role"] == "officer" else "Student Mentor, not a certified advisor"
        cursor = conn.execute(
            """INSERT INTO report_comments (report_id, author_id, author_label, body)
               VALUES (?, ?, ?, ?) RETURNING id""",
            (id, user["id"], label, body.text),
        )
        comment_id = cursor.fetchone()["id"]
        conn.execute("UPDATE reports SET status = 'commented' WHERE id = ?", (id,))
        conn.execute(
            """INSERT INTO audit_log (user_id, action, object_type, object_id)
               VALUES (?, 'ADD_COMMENT', 'report', ?)""",
            (user["id"], id),
        )

        return {"id": comment_id, "author_label": label, "body": body.text, "created_at": datetime.utcnow().isoformat()}

@router.post("/reports/{id}/revoke")
def revoke_report(id: int, user: dict = Depends(require_role("farmer"))):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute("UPDATE reports SET status = 'revoked', revoked_at = ? WHERE id = ? AND created_by = ?", (now, id, user["id"]))
        conn.execute(
            """INSERT INTO audit_log (user_id, action, object_type, object_id)
               VALUES (?, 'REVOKE_REPORT', 'report', ?)""",
            (user["id"], id),
        )
    return {"status": "revoked"}

@router.get("/mentor/inbox")
def get_mentor_inbox(user: dict = Depends(require_role("mentor", "officer"))):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT r.id as report_id, u.name as farmer_name, r.created_at, r.status, r.expires_at 
               FROM reports r
               JOIN users u ON r.created_by = u.id
               WHERE r.shared_with = ? AND r.revoked_at IS NULL
               ORDER BY r.created_at DESC""",
            (user["id"],),
        ).fetchall()
        return {"items": [dict(r) for r in rows], "next_cursor": None}

@router.get("/helpers")
def list_helpers(type: str | None = None, user: dict = Depends(current_user)):
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, role, helper_type FROM users WHERE role IN ('mentor', 'officer')").fetchall()
        return {
            "items": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "role": r["role"],
                    "helper_type": r["helper_type"] or "student",
                    "label": f"{r['name']} ({r['helper_type'] or r['role']})",
                }
                for r in rows
            ]
        }
