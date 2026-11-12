import asyncio
import json
import io
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import collector, analytics, main
from app.sample import sample_posts


@pytest.mark.parametrize("raw, platform, handle", [
    ("instagram.com/mrbeast/", "Instagram", "mrbeast"),
    ("https://m.facebook.com/profile.php?id=123", "Facebook", "123"),
    ("https://www.tiktok.com/@example", "TikTok", "example"),
])
def test_profile_normalization(raw, platform, handle):
    canonical, actual, username = collector.profile_url(raw)
    assert actual == platform and username == handle
    assert canonical.startswith("https://www.")


@pytest.mark.parametrize("raw", ["http://localhost/a", "instagram.com.evil.test/a", "https://x:y@instagram.com/brand", "instagram.com/p/123", "https://instagram.com:123/a", "tiktok.com/@a/video/1", "instagram.com/accounts/login/", "example.com/brand"])
def test_unsupported_urls_rejected(raw):
    with pytest.raises(ValueError):
        collector.profile_url(raw)


def test_collector_fields_and_unavailable_metrics_are_preserved():
    data = {"signed_in": False, "posts": [
        {"ext_id": "1", "posted_at": "2026-11-01T12:00:00Z", "kind": "reel", "likes": 7,
         "comments_count": 3, "views": None, "shares": None, "caption": "Real caption",
         "comments": [{"text": "Real public comment"}], "url": "https://www.instagram.com/p/test/"},
        {"ext_id": "bad", "posted_at": None},
        {"ext_id": "1", "posted_at": "2026-11-01T12:00:00Z"},
    ]}
    profile, posts = collector.normalize(data, "https://www.instagram.com/brand", "Instagram", "brand")
    assert len(posts) == 1 and posts[0].type == "Reel" and posts[0].likes == 7
    assert posts[0].comments == 3 and posts[0].comments_sample == ["Real public comment"]
    assert "views" in posts[0].unavailable_metrics
    assert "saves" in profile.unavailable_metrics and profile.collector == "socialmonitor"
    assert "Sign in" in profile.notes and "Skipped 1" in profile.notes
    assert profile.sources[0].url.endswith("/p/test/")
    assert analytics.to_frame(posts)["views"].sum() == 0  # no fabricated view counts


def test_analysis_does_not_require_ai_key_or_call_gemma(monkeypatch):
    monkeypatch.setattr(main.db, "find_cached", lambda _: None)
    monkeypatch.setattr(main.db, "save_analysis", lambda *args: "saved-id")
    async def collect(url):
        return collector.ProfileInfo(platform="Instagram", handle="brand", collector="socialmonitor"), sample_posts(12)
    async def forbidden(*args, **kwargs):
        raise AssertionError("The page analysis must not call Gemma")
    from app import llm
    monkeypatch.setattr(main.collector, "collect_profile", collect)
    monkeypatch.setattr(llm, "_generate", forbidden)
    response = TestClient(main.app).post("/api/analyze", json={"url": "instagram.com/brand"})
    assert response.status_code == 200
    assert response.json()["post_count"] == 12 and response.json()["analysis_id"] == "saved-id"


def test_old_llm_cache_is_not_reused(monkeypatch):
    monkeypatch.setattr(main.db, "find_cached", lambda _: {"profile": {"collector": ""}})
    async def unavailable(url):
        raise collector.CollectorError("Sign in first", 409)
    monkeypatch.setattr(main.collector, "collect_profile", unavailable)
    response = TestClient(main.app).post("/api/analyze", json={"url": "instagram.com/brand"})
    assert response.status_code == 409 and response.json()["detail"] == "Sign in first"


def test_worker_lock_released_on_failure(monkeypatch):
    def fail():
        raise collector.CollectorError("Not installed")
    monkeypatch.setattr(collector, "_process", fail)
    with pytest.raises(collector.CollectorError, match="Not installed"):
        collector._invoke_sync({"action": "status"})
    assert not collector._lock.locked()


def test_browser_worker_has_no_ai_or_database_credentials(monkeypatch):
    captured = {}
    monkeypatch.setenv("GEMMA_API_KEY", "private-ai-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "private-db-key")
    monkeypatch.setattr(collector.shutil, "which", lambda _: "node")
    monkeypatch.setattr(collector, "status", lambda: {"installed": True})
    def spawn(args, **kwargs):
        captured.update(kwargs)
        assert args == ["node", str(collector.WORKER)]
        return SimpleNamespace()
    monkeypatch.setattr(collector.subprocess, "Popen", spawn)
    collector._process()
    assert "GEMMA_API_KEY" not in captured["env"]
    assert "SUPABASE_SERVICE_ROLE_KEY" not in captured["env"]
    assert captured["env"]["SPECULARA_COLLECTOR_DATA_DIR"] == str(collector.DATA_DIR)
    assert not captured.get("shell")


def test_busy_collector_does_not_start_another_browser():
    collector._lock.acquire()
    try:
        with pytest.raises(collector.CollectorError) as error:
            collector._invoke_sync({"action": "status"})
        assert error.value.status_code == 409
    finally:
        collector._lock.release()


def test_login_rejects_remote_origins_without_opening_browser(monkeypatch):
    async def forbidden(network):
        raise AssertionError("Must not open a browser")
    monkeypatch.setattr(collector, "start_login", forbidden)
    response = TestClient(main.app).post("/api/collector/login", json={"network": "instagram"}, headers={"Origin": "https://example.com"})
    assert response.status_code == 403


def test_login_returns_instructions(monkeypatch):
    async def start(network):
        assert network == "instagram"
        return {"opened": True, "message": "Close the window when finished."}
    monkeypatch.setattr(collector, "start_login", start)
    response = TestClient(main.app).post("/api/collector/login", json={"network": "instagram"}, headers={"Origin": "http://localhost:8443"})
    assert response.status_code == 200 and response.json()["opened"]


def test_login_releases_browser_lock_when_window_closes(monkeypatch):
    proc = SimpleNamespace(stdin=io.StringIO(), stdout=io.StringIO('{"event":"login_ready"}\n'), wait=lambda: 0, poll=lambda: 0)
    monkeypatch.setattr(collector, "_process", lambda: proc)
    async def run():
        result = await collector.start_login("instagram")
        assert result["opened"] and collector._lock.locked()
        await asyncio.gather(*collector._login_tasks)
    asyncio.run(run())
    assert not collector._lock.locked() and collector._login_process is None


def test_retry_login_closes_existing_session_before_reopening(monkeypatch):
    calls = []
    monkeypatch.setattr(collector, '_login_process', SimpleNamespace(poll=lambda: None))
    collector._lock.acquire()
    async def finish():
        calls.append('close existing')
        collector._login_process = None
        collector._lock.release()
    monkeypatch.setattr(collector, 'finish_login', finish)
    proc = SimpleNamespace(stdin=io.StringIO(), stdout=io.StringIO('{"event":"login_ready"}\n'), wait=lambda: 0, poll=lambda: 0)
    def process():
        calls.append('open new')
        return proc
    monkeypatch.setattr(collector, '_process', process)
    async def run():
        assert (await collector.start_login('instagram'))['opened']
        await asyncio.gather(*collector._login_tasks)
    asyncio.run(run())
    assert calls == ['close existing', 'open new']
    assert not collector._lock.locked()


def test_login_does_not_replace_an_active_collection(monkeypatch):
    monkeypatch.setattr(collector, '_login_process', None)
    collector._lock.acquire()
    try:
        with pytest.raises(collector.CollectorError) as error:
            asyncio.run(collector.start_login('instagram'))
        assert error.value.status_code == 409
        assert 'Cancel' in str(error.value)
    finally:
        collector._lock.release()


def test_analysis_is_cached_locally_even_without_storage(monkeypatch):
    calls = []
    monkeypatch.setattr(main.db, "find_cached", lambda _: None)
    monkeypatch.setattr(main.db, "save_analysis", lambda *args: None)
    async def collect(url):
        calls.append(url)
        return collector.ProfileInfo(platform="Instagram", collector="socialmonitor"), sample_posts(12)
    monkeypatch.setattr(collector, "collect_profile", collect)
    client = TestClient(main.app)
    first = client.post("/api/analyze", json={"url": "instagram.com/brand"})
    second = client.post("/api/analyze", json={"url": "instagram.com/brand"})
    assert first.status_code == second.status_code == 200
    assert len(calls) == 1 and second.json()["cached"]


def test_optional_storage_failure_does_not_block_results(monkeypatch):
    def fail(*args):
        raise RuntimeError("Storage unavailable")
    monkeypatch.setattr(main.db, "find_cached", fail)
    monkeypatch.setattr(main.db, "save_analysis", fail)
    async def collect(url):
        return collector.ProfileInfo(platform="Instagram", collector="socialmonitor"), sample_posts(12)
    monkeypatch.setattr(collector, "collect_profile", collect)
    response = TestClient(main.app).post("/api/analyze", json={"url": "instagram.com/brand"})
    assert response.status_code == 200 and response.json()["analysis_id"] is None


def test_cancel_during_cache_lookup_prevents_browser_start(monkeypatch):
    def cache(_):
        collector._cancel_version += 1
        return None
    async def forbidden(url):
        raise AssertionError("Cancelled analysis must not start a browser")
    monkeypatch.setattr(main.db, "find_cached", cache)
    monkeypatch.setattr(collector, "collect_profile", forbidden)
    response = TestClient(main.app).post("/api/analyze", json={"url": "instagram.com/brand"})
    assert response.status_code == 409 and "cancelled" in response.json()["detail"]


def test_finish_sends_graceful_control_message():
    proc = SimpleNamespace(stdin=io.StringIO(), poll=lambda: None, wait=lambda timeout: 0)
    collector._stop_sync(proc, "finish_login")
    assert json.loads(proc.stdin.getvalue()) == {"action": "finish_login"}


def test_collection_progress_stream_is_read_before_results(monkeypatch):
    class Output:
        def __iter__(self):
            yield '{"event":"progress","message":"Reading post 2 of 20"}\n'
            assert collector.status()["progress"] == "Reading post 2 of 20"
            yield '{"ok":true,"data":{"posts":[]}}\n'
        def close(self): pass
    proc = SimpleNamespace(stdin=io.StringIO(), stdout=Output(), poll=lambda: 0, wait=lambda timeout: 0)
    monkeypatch.setattr(collector, "_process", lambda: proc)
    assert collector._invoke_sync({"action": "collect"}) == {"posts": []}
    assert not collector._lock.locked()
