from pydantic import BaseModel

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    step: str
    progress: int
    steps: list[str] = []
    error: str | None = None
    result: dict | None = None

class HealthResponse(BaseModel):
    status: str
    demo_mode: bool
    sources: dict[str, str]
    llm: str
    version: str
