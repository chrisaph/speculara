import io
from types import SimpleNamespace
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.sample import sample_posts

c = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_external_services(monkeypatch):
    from app import db, llm, collector
    monkeypatch.setattr(db, "_client", lambda: None)
    monkeypatch.setattr(llm, "get_settings", lambda: SimpleNamespace(gemma_api_key="", gemma_model="gemma-4-31b-it"))
    async def unavailable(url,limit=20):
        raise collector.CollectorError("Collector not configured in this test.")
    monkeypatch.setattr(collector, "collect_profile", unavailable)


def test_health():
    assert c.get("/api/health").json()["ok"]


def test_sample_shape():
    j = c.get("/api/sample").json()
    f = j["facts"]
    assert f["pos"] + f["neg"] + f["neu"] == 100
    assert f["phase"] in ("Rising", "Peaking", "Declining")
    assert f["weeks"] is None or f["weeks"] >= 1
    assert len(f["keywords"]) > 0 and len(f["pairs"]) > 0 and f["counts"]["Views"] > 0
    assert len(j["predict"]["forecast"]) == 8 and j["recommend"]["actions"]


def test_upload_csv():
    df = pd.DataFrame([p.model_dump() for p in sample_posts()])
    df["comments_sample"] = df["comments_sample"].apply("|".join)
    r = c.post("/api/upload", files={"file": ("p.csv", df.to_csv(index=False).encode(), "text/csv")})
    assert r.status_code == 200, r.text
    assert r.json()["post_count"] == 40


def test_upload_bad():
    assert c.post("/api/upload", files={"file": ("p.txt", b"x", "text/plain")}).status_code == 422


def test_analyze_validation_and_collector_unavailable():
    assert c.post("/api/analyze", json={"url": "nodot"}).status_code == 422
    assert c.post("/api/analyze", json={"url": "instagram.com/brand"}).status_code == 503


def test_analyze_with_mocked_collector(monkeypatch):
    from app import main
    from app.schemas import ProfileInfo

    async def fake(url,limit=20):
        return ProfileInfo(platform="Instagram", handle="brand"), sample_posts(30)

    monkeypatch.setattr(main.collector, "collect_profile", fake)
    r = c.post("/api/analyze", json={"url": "https://www.instagram.com/brand/"})
    assert r.status_code == 200 and r.json()["profile"]["platform"] == "Instagram"


def test_too_few_posts(monkeypatch):
    from app import main
    from app.schemas import ProfileInfo

    async def fake(url,limit=20):
        return ProfileInfo(notes="private account"), sample_posts(3)

    monkeypatch.setattr(main.collector, "collect_profile", fake)
    r = c.post("/api/analyze", json={"url": "tiktok.com/@x"})
    assert r.status_code == 422 and "private" in r.json()["detail"]


def test_chat_fallback():
    f = c.get("/api/sample").json()["facts"]
    assert "weeks" in c.post("/api/chat", json={"message": "how long will the trend last", "facts": f}).json()["answer"]
