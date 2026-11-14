import json
import time
from typing import Callable
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

def get_job_status(job_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        res = dict(row)
        res["steps"] = json.loads(res["steps_json"]) if res["steps_json"] else []
        if res["result_json"]:
            res["result"] = json.loads(res["result_json"])
        return res
