import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False, encoding="utf-8-sig")


def cors_origins(value: str, frontend_url: str = '') -> list[str]:
    origins=[]
    for item in (value+','+frontend_url).split(','):
        item=item.strip().strip('"\'').rstrip('/')
        try:
            url=urlsplit(item)
            if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.path or url.query or url.fragment:
                continue
            origin=f'{url.scheme}://{url.netloc.lower()}'
            if origin not in origins: origins.append(origin)
        except ValueError:
            continue
    return origins


class Settings:
    require_access_code: bool = os.getenv('SPECULARA_REQUIRE_AUTH','0')=='1'
    demo_access_token: str = os.getenv('DEMO_ACCESS_TOKEN','')
    operator_access_token: str = os.getenv('OPERATOR_ACCESS_TOKEN','')
    # GEMINI_API_KEY is also accepted for existing Google AI Studio setups.
    gemma_api_key: str = os.getenv("GEMMA_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    gemma_model: str = os.getenv("GEMMA_MODEL", "gemma-4-31b-it")
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    # Comma-separated list of allowed browser origins, e.g. https://speculara.netlify.app
    cors_origins: list[str] = cors_origins(os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8443"),os.getenv('FRONTEND_URL',''))
    # Also allow Netlify deploy previews like https://deploy-preview-3--speculara.netlify.app
    cors_origin_regex: str = os.getenv("CORS_ORIGIN_REGEX", r"https://.*\.netlify\.app")


@lru_cache
def get_settings() -> Settings:
    return Settings()
