import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _read_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", "")
    demo_mode: bool = _read_bool_env("DEMO_MODE")
    clerk_secret_key: str = os.getenv("CLERK_SECRET_KEY", "")
    clerk_issuer: str = os.getenv("CLERK_ISSUER", "")
    clerk_jwks_url: str = os.getenv("CLERK_JWKS_URL", "")
    allowed_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]
    cache_dir: str = os.getenv("CACHE_DIR", "data/cache")

    earthdata_user: str | None = os.getenv("EARTHDATA_USER")
    earthdata_password: str | None = os.getenv("EARTHDATA_PASSWORD")
    ee_project: str | None = os.getenv("EE_PROJECT")

    llm_provider: str | None = os.getenv("LLM_PROVIDER")
    llm_api_key: str | None = os.getenv("LLM_API_KEY")
    llm_model: str | None = os.getenv("LLM_MODEL")

settings = Settings()
