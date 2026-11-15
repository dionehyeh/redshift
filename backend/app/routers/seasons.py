import json
from datetime import date
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends

from app.analysis.core import CAUSE_MAP
from app.db import get_db
from app.deps import (
    current_user,
    own_field,
    own_season,
    require_role,
    reviewable_finding,
)
from app.errors import AppError
from app.jobs import create_job
from app.schemas.seasons import (
    FindingReviewRequest,
    SeasonAnalysisResponse,
    SeasonCreateRequest,
    SeasonPatchRequest,
    SeasonResponse,
)
from app.services.analysis_service import analyze_season_task

router = APIRouter(tags=["Seasons & Diagnosis"])


@router.post("/fields/{field_id}/seasons", status_code=201)
def log_season(
    field_id: int,
    body: SeasonCreateRequest,
    user: dict = Depends(require_role("farmer")),
    field: dict = Depends(own_field),
):
    with get_db() as conn:
        crop = conn.execute(
            "SELECT id, name FROM crops WHERE LOWER(name) = LOWER(?)",
            (body.crop.strip(),),
        ).fetchone()
        if not crop:
            raise AppError(
                "VALIDATION",
                "Crop must match an entry in the crop catalog",
                status=422,
                details={"crop": body.crop},
            )
        cursor = conn.execute(
            """INSERT INTO seasons (
                   field_id, crop_id, status, start_date, end_date, outcome,
                   loss_percent, suspected_cause, investment, revenue
               )
               VALUES (?, ?, 'completed', ?, ?, ?, ?, ?, ?, ?)
               RETURNING id""",
            (
                field_id,
                crop["id"],
                body.start_date.isoformat(),
                body.end_date.isoformat(),
                body.outcome,
                body.loss_percent,
                body.suspected_cause,
                body.investment,
                body.revenue,
            ),
        )
        season_id = cursor.fetchone()["id"]
    return {
        "id": season_id,
        "field_id": field_id,
        "status": "completed",
        "crop": crop["name"],
        "approval_status": "pending_review",
    }


@router.get("/seasons/{id}", response_model=SeasonResponse)
def get_season(id: int, season: dict = Depends(own_season)):
    return {
        **season,
        "crop": season.get("crop_name"),
    }


@router.patch("/seasons/{id}")
def patch_season(
    id: int,
    body: SeasonPatchRequest,
    season: dict = Depends(own_season),
):
    updates = body.model_dump(exclude_unset=True)
    if "start_date" in updates:
        updates["start_date"] = updates["start_date"].isoformat()
    if "end_date" in updates:
        updates["end_date"] = updates["end_date"].isoformat()

    start_date = body.start_date or season.get("start_date")
    end_date = body.end_date or season.get("end_date")
    if start_date and end_date:
        if body.start_date is None:
            start_date = date.fromisoformat(str(start_date))
        if body.end_date is None:
            end_date = date.fromisoformat(str(end_date))
        if end_date < start_date:
            raise AppError(
                "VALIDATION",
                "end_date must be on or after start_date",
                status=422,
            )

    crop_name = updates.pop("crop", None)
    with get_db() as conn:
        if crop_name is not None:
            crop = conn.execute(
                "SELECT id FROM crops WHERE LOWER(name) = LOWER(?)",
                (crop_name.strip(),),
            ).fetchone()
            if not crop:
                raise AppError(
                    "VALIDATION",
                    "Crop must match an entry in the crop catalog",
                    status=422,
                    details={"crop": crop_name},
                )
            updates["crop_id"] = crop["id"]

        if updates:
            assignments = ", ".join(f"{column} = ?" for column in updates)
            conn.execute(
                f"UPDATE seasons SET {assignments} WHERE id = ?",
                (*updates.values(), id),
            )
    return {"status": "updated", "id": id}


@router.post("/seasons/{id}/analyze", status_code=202)
def analyze_season(
    id: int,
    tasks: BackgroundTasks,
    season: dict = Depends(own_season),
):
    job_id = f"job_analysis_{id}_{uuid4().hex[:12]}"
    create_job(
        job_id,
        "season_analysis",
        target_id=id,
        steps=["loading_season", "calculating_anomalies", "synthesizing_stress_flags"],
    )
    tasks.add_task(analyze_season_task, job_id, id)
    return {"season_id": id, "job_id": job_id, "status": "queued"}


def _analysis_result(result_json: str | dict | None) -> dict:
    if result_json is None:
        return {}
    try:
        result = json.loads(result_json) if isinstance(result_json, str) else result_json
    except json.JSONDecodeError as exc:
        raise AppError(
            "ANALYSIS_RESULT_INVALID",
            "Stored season analysis result is invalid",
            status=500,
        ) from exc
    if not isinstance(result, dict):
        raise AppError(
            "ANALYSIS_RESULT_INVALID",
            "Stored season analysis result is invalid",
            status=500,
        )
    return result


@router.get("/seasons/{id}/analysis", response_model=SeasonAnalysisResponse)
def get_season_analysis(id: int, season: dict = Depends(own_season)):
    with get_db() as conn:
        job = conn.execute(
            """SELECT id, status, result_json, error FROM jobs
               WHERE target_id = ? AND kind = 'season_analysis'
               ORDER BY created_at DESC, id DESC LIMIT 1""",
            (id,),
        ).fetchone()

        if not job:
            return {
                "season_id": id,
                "approval_status": season["approval_status"],
                "analysis_status": "not_started",
                "job_id": None,
                "comparison_years": None,
                "findings": [],
                "gaps": [],
                "likely_causes": None,
                "followup_question": None,
                "analysis_error": None,
            }

        job = dict(job)
        status = job["status"]
        response = {
            "season_id": id,
            "approval_status": season["approval_status"],
            "analysis_status": status,
            "job_id": job["id"],
            "comparison_years": None,
            "findings": [],
            "gaps": [],
            "likely_causes": None,
            "followup_question": None,
            "analysis_error": job.get("error") if status == "failed" else None,
        }
        if status not in {"done", "done_with_gaps"}:
            return response

        analysis_result = _analysis_result(job.get("result_json"))
        findings_rows = conn.execute(
            """SELECT id, kind, week_from, week_to, deviation, unit, crop_stage,
                      severity, confidence, source, resolution, text_plain,
                      explainer_key, review_status
               FROM findings WHERE season_id = ? ORDER BY id""",
            (id,),
        ).fetchall()
        if "finding_ids" in analysis_result:
            finding_ids = analysis_result["finding_ids"]
            if not isinstance(finding_ids, list) or any(
                isinstance(finding_id, bool) or not isinstance(finding_id, int)
                for finding_id in finding_ids
            ):
                raise AppError(
                    "ANALYSIS_RESULT_INVALID",
                    "Stored season analysis result is invalid",
                    status=500,
                )
            finding_ids = set(finding_ids)
            findings_rows = [
                row for row in findings_rows if row["id"] in finding_ids
            ]
        response.update(
            {
                "comparison_years": analysis_result.get("comparison_years"),
                "findings": [
                    {
                        "id": row["id"],
                        "kind": row["kind"],
                        "weeks": [row["week_from"], row["week_to"]],
                        "deviation": (
                            f"{float(row['deviation']):g}{row['unit'] or ''}"
                            if row["deviation"] is not None
                            else ""
                        ),
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
                    for row in findings_rows
                ],
                "gaps": analysis_result.get("gaps", []),
                "likely_causes": analysis_result.get("likely_causes"),
                "followup_question": (
                    "Did you observe insect attack or water stagnation in the field?"
                    if analysis_result.get("likely_causes")
                    else None
                ),
            }
        )
        return response


@router.post("/findings/{id}/review")
def review_finding(
    id: int,
    body: FindingReviewRequest,
    user: dict = Depends(current_user),
    finding: dict = Depends(reviewable_finding),
):
    verified_level = 1 if user["role"] == "mentor" else (2 if user["role"] == "officer" else 0)
    review_status = {
        "confirm": "confirmed",
        "correct": "corrected",
        "reject": "rejected",
    }[body.action]
    reviewed_cause = (
        body.new_cause
        if body.action == "correct"
        else CAUSE_MAP.get(finding["kind"])
        if body.action == "confirm"
        else None
    )

    with get_db() as conn:
        conn.execute("UPDATE findings SET review_status = ? WHERE id = ?", (review_status, id))
        conn.execute(
            """INSERT INTO corrections (finding_id, corrected_by, by_role, new_cause, note, verified)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (id, user["id"], user["role"], reviewed_cause, body.note, verified_level),
        )
        if body.action in {"confirm", "correct"}:
            approval_status = "corrected" if body.action == "correct" else "approved"
            conn.execute(
                """UPDATE seasons
                   SET approved_cause = ?, approval_status = ?, approved_by = ?, approver_role = ?
                   WHERE id = ?""",
                (
                    reviewed_cause,
                    approval_status,
                    user["id"],
                    user["role"],
                    finding["season_id"],
                ),
            )

    return {
        "finding_id": id,
        "review_status": review_status,
        "verified_level": verified_level,
        "approved_cause": reviewed_cause,
    }
