"""Supabase persistence. If Supabase is not configured the API still works (results just are not saved)."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any, Optional

from .config import get_settings

log = logging.getLogger("speculara.db")


@lru_cache
def _client():
    s = get_settings()
    if not (s.supabase_url and s.supabase_service_key):
        return None
    from supabase import create_client, ClientOptions

    return create_client(s.supabase_url, s.supabase_service_key,
                         options=ClientOptions(postgrest_client_timeout=5, postgrest_client_retry=False))


def enabled() -> bool:
    try:
        return _client() is not None
    except Exception:
        return False


def save_analysis(url: str, platform: str, handle: str, profile: dict, posts: list[dict], result: dict) -> Optional[str]:
    c = _client()
    if not c:
        return None
    try:
        row = {"url": url, "platform": platform, "handle": handle, "profile": profile, "posts": posts, "result": result}
        res = c.table("analyses").insert(json.loads(json.dumps(row, default=str))).execute()
        return res.data[0]["id"]
    except Exception as e:  # never fail the user's analysis because storage failed
        log.warning("save_analysis failed: %s", e)
        return None


def get_analysis(analysis_id: str) -> Optional[dict[str, Any]]:
    c = _client()
    if not c:
        return None
    res = c.table("analyses").select("*").eq("id", analysis_id).limit(1).execute()
    return res.data[0] if res.data else None


def recent(limit: int = 20) -> list[dict]:
    c = _client()
    if not c:
        return []
    res = c.table("analyses").select("id,url,platform,handle,created_at").order("created_at", desc=True).limit(limit).execute()
    return res.data


def find_cached(url_key: str, max_age_hours: int = 6) -> Optional[dict]:
    c = _client()
    if not c:
        return None
    from datetime import datetime, timedelta, timezone

    since = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
    try:
        res = c.table("analyses").select("*").eq("handle", url_key).gte("created_at", since).order("created_at", desc=True).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None
