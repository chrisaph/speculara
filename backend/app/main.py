from __future__ import annotations

import logging
import re
import asyncio
import json
from time import monotonic

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware

from . import analytics, db, collector
from .config import get_settings
from .llm import chat_answer
from .sample import sample_posts
from .schemas import AnalyzeRequest, ChatRequest, CollectorLoginRequest
from .evidence import ANALYSIS_VERSION, restore_posts
from .chat_context import build_chat_context, cited_sources
from .strategy import generate_strategy
from .metric_import import merge_metrics

log = logging.getLogger("speculara")
s = get_settings()
_analysis_cache: dict[str, tuple[float, dict]] = {}


async def _optional_storage(function, *args):
    try:
        return await asyncio.wait_for(asyncio.to_thread(function, *args), timeout=8)
    except (Exception, TimeoutError):
        log.warning("Optional storage operation did not complete: %s", function.__name__)
        return None


app = FastAPI(title="Speculara API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_origin_regex=s.cors_origin_regex,
                   allow_methods=["*"], allow_headers=["*"])


def _row_response(row: dict) -> dict | None:
    profile = row.get("profile") or {}
    result = row.get("result") or {}
    if result.get("analysis_version") != ANALYSIS_VERSION:
        if not row.get("posts"):
            return None
        result = analytics.analyze(restore_posts(row["posts"], profile))
        result["facts"]["data_quality"] = {"source": profile.get("collector", "Saved analysis"),
            "unavailable_metrics": profile.get("unavailable_metrics", []), "notes": profile.get("notes", "")}
    return {"analysis_id": row.get("id"), "profile": profile, **result}


@app.get("/api/health")
def health():
    return {"ok": True, "llm": bool(s.gemma_api_key), "database": db.enabled()}


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    try:
        url, platform, username = collector.profile_url(req.url)
        handle = f"{platform.lower()}:{username}"
    except ValueError as e:
        raise HTTPException(422, str(e))

    saved = _analysis_cache.get(handle)
    if not req.refresh and saved and saved[1].get('analysis_version') == ANALYSIS_VERSION and monotonic() - saved[0] < 6 * 3600:
        return {**saved[1], "cached": True}
    if collector.status()["login_open"]:
        raise HTTPException(409, "Finish signing in, then click Done signing in before analyzing.")
    cancel_version = collector.cancellation_version()
    cached = await _optional_storage(db.find_cached, handle) if not req.refresh else None
    if cancel_version != collector.cancellation_version():
        raise HTTPException(409, "Analysis cancelled.")
    if cached and cached.get("profile", {}).get("collector") == "socialmonitor":
        restored = await asyncio.to_thread(_row_response, cached)
        if restored:
            _analysis_cache[handle] = (monotonic(), restored)
            return {**restored, "cached": True}

    try:
        profile, posts = await collector.collect_profile(url)
    except collector.CollectorError as e:
        raise HTTPException(e.status_code, str(e))
    except Exception as e:
        log.exception("collection failed")
        raise HTTPException(502, "Could not collect that profile. Check the local collector and try again.")
    try:
        result = await asyncio.to_thread(analytics.analyze, posts)
    except ValueError as e:
        raise HTTPException(422, f"{e} {profile.notes}".strip())

    result["facts"]["data_quality"] = {"source": "SocialMonitor", "unavailable_metrics": profile.unavailable_metrics, "notes": profile.notes}

    aid = await _optional_storage(db.save_analysis, url, profile.platform, handle, profile.model_dump(), [p.model_dump(mode="json") for p in posts], result)
    response = {"analysis_id": aid, "cached": False, "profile": profile.model_dump(), **result}
    if len(_analysis_cache) >= 100:
        _analysis_cache.pop(next(iter(_analysis_cache)))
    _analysis_cache[handle] = (monotonic(), response)
    return response


@app.get("/api/collector/status")
def collector_status():
    return collector.status()


@app.post("/api/collector/login")
async def collector_login(req: CollectorLoginRequest, request: Request):
    _require_local(request)
    try:
        return await collector.start_login(req.network)
    except collector.CollectorError as e:
        raise HTTPException(e.status_code, str(e))
    except (TimeoutError, ValueError):
        raise HTTPException(503, "The sign-in browser did not open. Check browser setup and try again.")


def _require_local(request: Request):
    # Opening a desktop window is a local action, available only to this machine.
    if not request.client or request.client.host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(403, "Collector sign-in is available only on the local computer.")
    origin = request.headers.get("origin")
    if origin and origin not in {"http://localhost:8443", "http://127.0.0.1:8443"}:
        raise HTTPException(403, "Open the local Speculara app to sign in.")


@app.post("/api/collector/login/finish")
async def collector_login_finish(request: Request):
    _require_local(request)
    return await collector.finish_login()


@app.post("/api/collector/cancel")
async def collector_cancel(request: Request):
    _require_local(request)
    return await collector.cancel_collection()


@app.get("/api/sample")
def sample():
    result = analytics.analyze(sample_posts())
    return {"analysis_id": None, "cached": False, "profile": {"platform": "Sample", "handle": "sample", "notes": "Demo data"}, **result}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 10_000_000:
        raise HTTPException(413, "File too large (10 MB max).")
    try:
        posts = analytics.posts_from_file(content, file.filename or "")
        result = analytics.analyze(posts)
    except (ValueError, TypeError, OverflowError) as e:
        raise HTTPException(422, str(e))
    return {"analysis_id": None, "cached": False, "profile": {"platform": "Upload", "handle": file.filename}, **result}


@app.post('/api/strategy')
async def strategy(req: ChatRequest):
    if not req.analysis or not req.analysis.get('evidence', {}).get('posts'):
        raise HTTPException(422, 'Run an analysis first.')
    return await generate_strategy(req.analysis)


@app.post('/api/metrics')
async def import_metrics(file: UploadFile = File(...), analysis: str = Form(...)):
    content=await file.read(10_000_001)
    if len(content)>10_000_000 or len(analysis)>2_000_000:
        raise HTTPException(413,'Metrics file or analysis is too large (10 MB file maximum).')
    try:
        active=json.loads(analysis)
        if not isinstance(active,dict): raise ValueError('A current analysis is required.')
        posts,summary=await asyncio.to_thread(merge_metrics,active,content,file.filename or '')
        result=await asyncio.to_thread(analytics.analyze,posts)
    except (ValueError,TypeError,KeyError) as error:
        raise HTTPException(422,str(error))
    profile={**(active.get('profile') or {})}
    profile['unavailable_metrics']=[m for m,c in result['metric_availability'].items() if not c['complete']]
    profile['notes']=f"{len(posts)} posts analyzed. Imported {summary['updated_values']} counts for {summary['matched_posts']} matching posts. Public and user-imported metrics are labeled separately."
    result['facts']['data_quality']={'source':'Collected posts + user-imported metrics','unavailable_metrics':profile['unavailable_metrics'],'notes':profile['notes']}
    return {'analysis_id':None,'cached':False,'profile':profile,'metric_import':summary,**result}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    analysis = req.analysis
    if req.analysis_id:
        row = await _optional_storage(db.get_analysis, req.analysis_id)
        if row:
            restored = await asyncio.to_thread(_row_response, row)
            if restored:
                analysis = restored
    if not analysis and req.facts:
        analysis = {"facts": req.facts}
    if not analysis:
        raise HTTPException(422, "Run an analysis first.")
    context = build_chat_context(analysis)
    try:
        answer = await chat_answer(req.message, context)
        engine = "gemma"
    except Exception:
        summary = analysis.get("demand", {}).get("summary", {})
        if re.search(r"demand|ask|question", req.message, re.I) and summary:
            answer = (f"The {summary.get('sampled_comments', 0)} sampled comments contain {summary.get('questions', 0)} questions "
                      f"and {summary.get('requests', 0)} requests. These are comment-based demand signals, not sales figures.")
        else:
            answer = _fallback_answer(req.message, analysis.get("facts") or {})
        engine = "fallback"
    return {"answer": answer, "sources": cited_sources(answer, context), "engine": engine,
            "context": context.get("evidence_coverage", {})}


def _fallback_answer(q: str, f: dict) -> str:
    q = q.lower()
    if re.search(r"longev|last|trend", q) and all(k in f for k in ("phase", "weeks", "similar")):
        if f['weeks'] is None:
            return f"The observed trend is {f['phase'].lower()}. No completed comparable historical windows support an estimate of remaining weeks."
        return f"The observed trend is {f['phase'].lower()}. The estimate is about {f['weeks']} more weeks from matching windows within this profile, not global trends."
    if re.search(r"keyword|word|comment", q) and f.get("keywords"):
        return f"The top keyword is \"{f['keywords'][0]['w']}\" with {f['keywords'][0]['n']} mentions."
    if re.search(r"sentiment|feel", q) and all(k in f for k in ("pos", "neu", "neg")):
        return f"{f['pos']}% positive, {f['neu']}% neutral, {f['neg']}% negative."
    if re.search(r"demand|ask|question", q) and f.get("posts"):
        return f"\"{f['posts'][0]['p']}\" has the most demand."
    if re.search(r"correl", q) and f.get("pairs"):
        return f"Strongest link: {f['pairs'][0]['a']} and {f['pairs'][0]['b']} ({f['pairs'][0]['v']}). Correlation is not causation."
    return "I can explain forecast accuracy, trend longevity, keywords, sentiment, demand, correlation or strategy."


@app.get("/api/history")
async def history():
    rows = await _optional_storage(db.recent)
    return {"items": rows or [], "storage_available": db.enabled() and rows is not None}


@app.get("/api/analyses/{analysis_id}")
async def get_one(analysis_id: str):
    row = await _optional_storage(db.get_analysis, analysis_id)
    if not row:
        raise HTTPException(404, "Not found")
    return _row_response(row) or {"analysis_id": row["id"], "profile": row["profile"], **row["result"]}
