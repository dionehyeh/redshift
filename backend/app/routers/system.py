from fastapi import APIRouter
from app.jobs import get_job_status
from app.config import settings
from app.errors import AppError

router = APIRouter(tags=["System & Health"])

@router.get("/jobs/{id}")
def get_job(id: str):
    job = get_job_status(id)
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

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "sources": {
            "power": "ok",
            "imerg": "ok" if not settings.demo_mode else "cached",
            "modis": "ok",
            "soilgrids": "cached",
        },
        "llm": "active" if settings.llm_api_key else "off (templates)",
        "version": "0.1.0",
    }
