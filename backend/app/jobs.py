import json
import time

from app.db import get_db


def create_job(job_id: str, kind: str, target_id: int | None = None, steps: list[str] | None = None) -> None:
    steps_list = steps or []
    with get_db() as conn:
        conn.execute(
            """INSERT INTO jobs (id, kind, target_id, status, step, progress, steps_json)
               VALUES (?, ?, ?, 'queued', 'queued', 0, ?)""",
            (job_id, kind, target_id, json.dumps(steps_list)),
        )

def update_job_step(job_id: str, step: str, progress: int) -> None:
    with get_db() as conn:
        conn.execute(
            """UPDATE jobs SET status = 'running', step = ?, progress = ? WHERE id = ?""",
            (step, progress, job_id),
        )

def complete_job(job_id: str, status: str = "done", result: dict | None = None) -> None:
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.execute(
            """UPDATE jobs SET status = ?, step = 'done', progress = 100, result_json = ?, finished_at = ? WHERE id = ?""",
            (status, json.dumps(result or {}), now, job_id),
        )

def fail_job(job_id: str, error_message: str) -> None:
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.execute(
            """UPDATE jobs SET status = 'failed', error = ?, finished_at = ? WHERE id = ?""",
            (error_message, now, job_id),
        )

def get_owned_job_status(job_id: str, farmer_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """SELECT j.* FROM jobs j
               LEFT JOIN fields onboarding_field
                 ON j.kind = 'field_onboarding'
                AND onboarding_field.id = j.target_id
               LEFT JOIN seasons analysis_season
                 ON j.kind = 'season_analysis'
                AND analysis_season.id = j.target_id
               LEFT JOIN fields analysis_field
                 ON analysis_field.id = analysis_season.field_id
               WHERE j.id = ?
                 AND (
                     onboarding_field.farmer_id = ?
                     OR analysis_field.farmer_id = ?
                 )""",
            (job_id, farmer_id, farmer_id),
        ).fetchone()
        if not row:
            return None

        result = dict(row)
        result["steps"] = json.loads(result["steps_json"]) if result["steps_json"] else []
        if result["result_json"]:
            result["result"] = json.loads(result["result_json"])
        return result
