from fastapi import APIRouter, Depends

from app.config import settings
from app.deps import require_role
from app.errors import AppError
from app.jobs import get_owned_job_status
from app.schemas.system import HealthResponse, JobStatusResponse

router = APIRouter(tags=["System & Health"])

@router.get("/jobs/{id}", response_model=JobStatusResponse)
def get_job(id: str, user: dict = Depends(require_role("farmer"))):
    job = get_owned_job_status(id, user["id"])
    if not job:
        raise AppError("JOB_NOT_FOUND", "Background task not found", status=404)
    return {
        "job_id": job["id"],
        "status": job["status"],
        "step": job["step"],
        "progress": job["progress"],
        "steps": job.get("steps", []),
        "error": job.get("error"),
        "result": job.get("result"),
    }

@router.get("/health", response_model=HealthResponse)
def health_check():
    earth_engine_status = (
        "configured_not_checked" if settings.ee_project else "requires_ee_project"
    )
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "sources": {
            "power": "not_checked",
            "imerg": earth_engine_status,
            "modis": earth_engine_status,
            "soilgrids": "not_checked",
        },
        "llm": "active" if settings.llm_api_key else "off (templates)",
        "version": "0.1.0",
    }
