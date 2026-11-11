"""Exercise Gemma's REST integration with an offline HTTP transport."""
import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from app import llm


@pytest.fixture
def settings(monkeypatch):
    value = SimpleNamespace(gemma_api_key="test-key", gemma_model="gemma-4-31b-it")
    monkeypatch.setattr(llm, "get_settings", lambda: value)
    return value


@pytest.fixture
def transport(monkeypatch, settings):
    state = SimpleNamespace(requests=[], status=200, payload={"candidates": [{
        "finishReason": "STOP", "content": {"parts": [{"text": "Answer"}]},
        "groundingMetadata": {"webSearchQueries": ["brand public posts"]},
    }]}, hints=[])
    original_client = httpx.AsyncClient

    def handler(request):
        state.requests.append(request)
        return httpx.Response(state.status, json=state.payload)

    def client(**kwargs):
        return original_client(**kwargs, transport=httpx.MockTransport(handler))

    async def hint(url):
        state.hints.append(url)
        return "Public profile"

    monkeypatch.setattr(llm.httpx, "AsyncClient", client)
    monkeypatch.setattr(llm, "_page_hint", hint)
    return state


def candidate(state):
    return state.payload["candidates"][0]


def test_research_request_and_post_normalization(transport):
    candidate(transport)["content"]["parts"][0]["text"] = json.dumps({
        "profile": {"notes": "Public posts only"},
        "posts": [{"id": "real", "posted_at": "2026-11-01T12:00:00Z", "likes": "42",
                   "comments": None, "comments_sample": list(range(10))},
                  {"posted_at": "invalid"}, "malformed"],
    })
    profile, posts = asyncio.run(llm.research_page("instagram.com/brand"))
    assert profile.platform == "Instagram" and profile.handle == "instagram.com/brand"
    assert len(posts) == 1 and posts[0].likes == 42 and posts[0].comments == 0
    assert posts[0].comments_sample == [str(i) for i in range(8)]
    request, = transport.requests
    assert str(request.url) == "https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:generateContent"
    assert request.headers["x-goog-api-key"] == "test-key" and not request.url.query
    body = json.loads(request.content)
    assert body["tools"] == [{"googleSearch": {}}]
    assert body["systemInstruction"]["parts"][0]["text"] == llm.SYSTEM
    assert "Public profile" in body["contents"][0]["parts"][0]["text"]


def test_grounding_sources_deduplicated_and_safe(transport):
    c = candidate(transport)
    c["content"]["parts"][0]["text"] = '{"profile": {}, "posts": []}'
    web = {"web": {"uri": "https://example.com/post", "title": "Public post"}}
    c["groundingMetadata"]["groundingChunks"] = [web, web, {"web": {"uri": "javascript:alert(1)"}}]
    profile, posts = asyncio.run(llm.research_page("instagram.com/brand"))
    assert posts == []
    assert [s.model_dump() for s in profile.sources] == [{"url": "https://example.com/post", "title": "Public post"}]


def test_chat_uses_facts_without_search_and_omits_thoughts(transport):
    candidate(transport)["content"]["parts"] = [{"text": "Private thinking", "thought": True}, {"text": "  Rising.  "}]
    assert asyncio.run(llm.chat_answer("Trend?", {"phase": "Rising"})) == "Rising."
    body = json.loads(transport.requests[0].content)
    assert "tools" not in body
    assert '"phase": "Rising"' in body["contents"][0]["parts"][0]["text"]


def test_gemma_request_contains_complete_analysis_past_old_truncation_limit(transport):
    analysis = {"facts": {"padding": "x" * 7000}, "demand": {"summary": {"questions": 17, "requests": 9}},
                "evidence": {"posts": [{"id": "real", "caption": "The observed reel", "url": "https://example.com/reel"}],
                             "comments": [{"text": "Actual comment beyond the former cutoff", "source_url": "https://example.com/reel"}]}}
    asyncio.run(llm.chat_answer("Explain demand", analysis))
    content = json.loads(transport.requests[0].content)["contents"][0]["parts"][0]["text"]
    parsed = json.loads(content.split("Analysis JSON:\n", 1)[1].split("\n\nQuestion:", 1)[0])
    assert parsed["demand"]["summary"]["questions"] == 17
    assert parsed["evidence"]["comments"][0]["text"] == "Actual comment beyond the former cutoff"


@pytest.mark.parametrize("operation", ["research", "chat"])
def test_missing_key_fails_before_network(transport, settings, operation):
    settings.gemma_api_key = ""
    with pytest.raises(llm.LLMUnavailable, match="GEMMA_API_KEY"):
        asyncio.run(llm.research_page("instagram.com/brand") if operation == "research" else llm.chat_answer("?", {}))
    assert transport.requests == transport.hints == []


@pytest.mark.parametrize("reason", ["MAX_TOKENS", "SAFETY", "RECITATION"])
def test_incomplete_response_rejected(transport, reason):
    candidate(transport)["finishReason"] = reason
    with pytest.raises(ValueError, match="did not complete"):
        asyncio.run(llm.chat_answer("?", {}))


@pytest.mark.parametrize("text", ["", "  "])
def test_empty_response_rejected(transport, text):
    candidate(transport)["content"]["parts"][0]["text"] = text
    with pytest.raises(ValueError, match="text response"):
        asyncio.run(llm.chat_answer("?", {}))


def test_blocked_response_rejected(transport):
    transport.payload = {"promptFeedback": {"blockReason": "SAFETY"}}
    with pytest.raises(ValueError, match="candidate response"):
        asyncio.run(llm.chat_answer("?", {}))


def test_ungrounded_research_rejected(transport):
    candidate(transport).pop("groundingMetadata")
    with pytest.raises(ValueError, match="did not perform web research"):
        asyncio.run(llm.research_page("instagram.com/brand"))


@pytest.mark.parametrize("text", ["No data", '{"profile":', '{"profile": [], "posts": []}'])
def test_invalid_research_rejected(transport, text):
    candidate(transport)["content"]["parts"][0]["text"] = text
    with pytest.raises(ValueError):
        asyncio.run(llm.research_page("instagram.com/brand"))


@pytest.mark.parametrize("status", [400, 401, 403, 429, 500])
def test_provider_errors_are_sanitized(transport, status):
    transport.status = status
    transport.payload = {"error": {"message": "test-key private provider error"}}
    with pytest.raises(llm.LLMUnavailable) as exc:
        asyncio.run(llm.chat_answer("?", {}))
    assert "test-key" not in str(exc.value) and "private provider error" not in str(exc.value)


@pytest.mark.parametrize("key, expected", [("", False), ("test-key", True)])
def test_health_reports_gemma_key(monkeypatch, key, expected):
    from app import main
    monkeypatch.setattr(main, "s", SimpleNamespace(gemma_api_key=key))
    monkeypatch.setattr(main.db, "enabled", lambda: False)
    assert main.health() == {"ok": True, "llm": expected, "database": False}
