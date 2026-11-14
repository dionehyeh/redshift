from fastapi import APIRouter, Depends, BackgroundTasks
from app.schemas.seasons import (
    SeasonCreateRequest,
    SeasonPatchRequest,
    FindingReviewRequest,
    SeasonAnalysisResponse,
)
from app.deps import current_user, require_role, own_field
from app.db import get_db
from app.jobs import create_job
from app.services.analysis_service import analyze_season_task
from app.errors import AppError

router = APIRouter(tags=["Seasons & Diagnosis"])

@router.post("/fields/{field_id}/seasons", status_code=201)
def log_season(field_id: int, body: SeasonCreateRequest, user: dict = Depends(require_role("farmer")), field: dict = Depends(own_field)):
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO seasons (field_id, crop_id, status, start_date, end_date, outcome, loss_percent, suspected_cause, investment, revenue)
               VALUES (?, (SELECT id FROM crops WHERE name = ?), 'completed', ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            (
                field_id,
                body.crop,
                body.start_date,
                body.end_date,
                body.outcome,
                body.loss_percent,
                body.suspected_cause,
                body.investment,
                body.revenue,
            ),
        )
        season_id = cursor.fetchone()["id"]
        return {"id": season_id, "field_id": field_id, "status": "completed", "crop": body.crop}

@router.get("/seasons/{id}")
def get_season(id: int, user: dict = Depends(current_user)):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM seasons WHERE id = ?", (id,)).fetchone()
        if not row:
            raise AppError("NOT_FOUND", "Season record not found", status=404)
        return dict(row)

@router.patch("/seasons/{id}")
def patch_season(id: int, body: SeasonPatchRequest, user: dict = Depends(require_role("farmer"))):
    with get_db() as conn:
        conn.execute(
            """UPDATE seasons 
               SET outcome = COALESCE(?, outcome),
                   loss_percent = COALESCE(?, loss_percent),
                   suspected_cause = COALESCE(?, suspected_cause)
               WHERE id = ?""",
            (body.outcome, body.loss_percent, body.suspected_cause, id),
        )
    return {"status": "updated"}

@router.post("/seasons/{id}/analyze", status_code=202)
def analyze_season(id: int, tasks: BackgroundTasks, user: dict = Depends(require_role("farmer"))):
    job_id = f"job_analysis_{id}"
    create_job(job_id, "season_analysis", target_id=id, steps=["loading_season", "calculating_anomalies", "synthesizing_stress_flags"])
    tasks.add_task(analyze_season_task, job_id, id)
    return {"season_id": id, "job_id": job_id, "status": "queued"}

@router.get("/seasons/{id}/analysis")
def get_season_analysis(id: int, user: dict = Depends(current_user)):
    with get_db() as conn:
        season = conn.execute("SELECT * FROM seasons WHERE id = ?", (id,)).fetchone()
        if not season:
            raise AppError("NOT_FOUND", "Season not found", status=404)
        findings_rows = conn.execute("SELECT * FROM findings WHERE season_id = ?", (id,)).fetchall()
        
        findings_list = []
        for r in findings_rows:
            findings_list.append({
                "id": r["id"],
                "kind": r["kind"],
                "weeks": [r["week_from"], r["week_to"]],
                "deviation": f"{r['deviation']}%",
                "unit": r["unit"],
                "crop_stage": r["crop_stage"],
                "severity": r["severity"],
                "confidence": r["confidence"],
                "source": r["source"],
                "resolution": r["resolution"],
                "text": r["text_plain"],
                "explainer_key": r["explainer_key"],
                "review_status": r["review_status"],
            })
            
        return {
            "season_id": id,
            "approval_status": season["approval_status"],
            "comparison_years": "2005-2025 (20-year climatology)",
            "findings": findings_list,
            "gaps": [
                "Pests and diseases cannot be detected from satellite imagery",
                "Cloud cover prevented optical NDVI imaging in weeks 8 to 9",
            ],
            "followup_question": "Did you observe insect attack or water stagnation in the field?",
        }

@router.post("/findings/{id}/review")
def review_finding(id: int, body: FindingReviewRequest, user: dict = Depends(current_user)):
    with get_db() as conn:
        finding = conn.execute("SELECT * FROM findings WHERE id = ?", (id,)).fetchone()
        if not finding:
            raise AppError("NOT_FOUND", "Finding not found", status=404)
        
        verified_level = 1 if user["role"] == "mentor" else (2 if user["role"] == "officer" else 0)
        review_status = "confirmed" if body.action == "confirm" else ("rejected" if body.action == "reject" else "corrected")

        conn.execute("UPDATE findings SET review_status = ? WHERE id = ?", (review_status, id))
        conn.execute(
            """INSERT INTO corrections (finding_id, corrected_by, by_role, new_cause, note, verified)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (id, user["id"], user["role"], body.new_cause or finding["kind"], body.note, verified_level),
        )
        if body.action in ("confirm", "correct"):
            approved_cause = body.new_cause or "water_stress"
            conn.execute(
                """UPDATE seasons 
                   SET approved_cause = ?, approval_status = 'approved', approved_by = ?, approver_role = ?
                   WHERE id = ?""",
                (approved_cause, user["id"], user["role"], finding["season_id"]),
            )

    return {"finding_id": id, "review_status": review_status, "verified_level": verified_level}
