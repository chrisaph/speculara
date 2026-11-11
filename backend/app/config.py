import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False, encoding="utf-8-sig")


class Settings:
    # GEMINI_API_KEY is also accepted for existing Google AI Studio setups.
    gemma_api_key: str = os.getenv("GEMMA_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    gemma_model: str = os.getenv("GEMMA_MODEL", "gemma-4-31b-it")
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    # Comma-separated list of allowed browser origins, e.g. https://speculara.netlify.app
    cors_origins: list[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8443").split(",") if o.strip()]
    # Also allow Netlify deploy previews like https://deploy-preview-3--speculara.netlify.app
    cors_origin_regex: str = os.getenv("CORS_ORIGIN_REGEX", r"https://.*\.netlify\.app")


@lru_cache
def get_settings() -> Settings:
    return Settings()
