import asyncio
import json

from fastapi.testclient import TestClient

from app import analytics, collector, main
from app.chat_context import build_chat_context, cited_sources
from app.evidence import ANALYSIS_VERSION, restore_posts
from app.sample import sample_posts
from app.schemas import CommentEvidence


def observed_posts():
    posts = sample_posts(6)
    for index, post in enumerate(posts):
        post.url = f"https://www.instagram.com/reel/observed{index}/"
        post.unavailable_metrics = ["sales", "saves", "views"]
        post.comment_evidence = [CommentEvidence(id=f"comment-{index}", text=post.comments_sample[0],
            source_url=post.url, source_kind="post")]
        post.comments_sample = [post.comment_evidence[0].text]
    return posts


def test_sentiment_uses_real_comments_and_retains_each_source():
    posts = observed_posts()
    posts[0].comments_sample = ["Absolutely amazing banana challenge!"]
    posts[0].comment_evidence[0].text = posts[0].comments_sample[0]
    result = analytics.analyze(posts)
    assert result["sentiment"]["basis"] == "comments"
    assert result["sentiment"]["scored"] == 6
    sample = next(s for s in result["sentiment"]["samples"] if "banana" in s["text"])
    assert sample["source_url"] == posts[0].url
    assert sample["source_kind"] == "post" and sample["kind"] == "comment"
    assert any(k["w"] == "banana" for k in result["sentiment"]["keywords"])


def test_captions_are_identified_when_no_comments_are_collected():
    posts = observed_posts()
    for post in posts:
        post.comment_evidence = []
        post.comments_sample = []
    result = analytics.analyze(posts)
    assert result["sentiment"]["basis"] == "captions"
    assert all(s["kind"] == "caption" for s in result["sentiment"]["samples"])
    assert result["demand"]["basis"] == "none"
    assert result["demand"]["summary"]["sampled_comments"] == 0


def test_demand_is_measured_from_questions_and_requests_without_private_metrics():
    posts = observed_posts()
    for post in posts:
        post.comments_sample = ["Where can I buy this? Please restock!"]
        post.comment_evidence = [CommentEvidence(text=post.comments_sample[0], source_url=post.url, source_kind="post")]
        post.views = post.sales = post.saves = 0
    result = analytics.analyze(posts)
    summary = result["demand"]["summary"]
    assert summary["questions"] == summary["requests"] == summary["demand_comments"] == 6
    assert summary["request_rate_pct"] == 100
    assert sum(w["questions"] for w in result["demand"]["weekly"]) == 6
    assert result["demand"]["ranking"][0]["url"] == posts[0].url


def test_old_saved_posts_recover_parent_links_and_regenerate_analysis():
    posts = sample_posts(6)
    profile = {"collector": "socialmonitor", "sources": [{"title": f"Instagram post {p.id}", "url": f"https://www.instagram.com/p/old{p.id}/"} for p in posts]}
    raw = [p.model_dump(mode="json", exclude={"url", "comment_evidence"}) for p in posts]
    restored = restore_posts(raw, profile)
    assert restored[0].url.endswith("/old0/")
    row = main._row_response({"id": "old", "posts": raw, "profile": profile, "result": {"facts": {}}})
    assert row["analysis_version"] == ANALYSIS_VERSION
    assert row["sentiment"]["samples"][0]["source_url"]


def test_chat_context_keeps_demand_and_evidence_after_six_thousand_characters():
    analysis = analytics.analyze(observed_posts())
    analysis["facts"]["padding"] = "x" * 7000
    context = build_chat_context(analysis)
    encoded = json.dumps(context)
    assert len(encoded) > 6000
    assert context["demand"]["summary"]["sampled_comments"] == 6
    assert len(context["evidence"]["comments"]) == 6
    assert json.loads(encoded)["evidence"]["posts"][0]["url"]


def test_only_supplied_source_references_become_links():
    context = build_chat_context(analytics.analyze(observed_posts()))
    sources = cited_sources("This reel [P1] supports the finding. [P9999]", context)
    assert len(sources) == 1 and sources[0]["url"].endswith("/observed0/")


def test_chat_endpoint_passes_full_analysis_to_gemma_and_returns_source_buttons(monkeypatch):
    analysis = analytics.analyze(observed_posts())
    analysis["profile"] = {"platform": "Instagram", "handle": "brand"}
    async def reply(message, context):
        assert context["demand"]["summary"]["sampled_comments"] == 6
        assert context["sentiment"]["basis"] == "comments"
        assert len(context["evidence"]["posts"]) == 6
        return "The sampled comments show audience questions and requests [P1]."
    monkeypatch.setattr(main, "chat_answer", reply)
    response = TestClient(main.app).post("/api/chat", json={"message": "What about demand?", "analysis": analysis})
    assert response.status_code == 200
    assert response.json()["engine"] == "gemma"
    assert response.json()["sources"][0]["url"].endswith("/observed0/")
    assert response.json()["context"]["comments_in_context"] == 6
