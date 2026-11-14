import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Settings(BaseModel):
    demo_mode: bool = os.getenv("DEMO_MODE", "false").lower() in ("true", "1")
    database_url: str = os.getenv("DATABASE_URL", "")
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
