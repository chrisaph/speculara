"""Local bridge to the pinned SocialMonitor browser collectors. No LLM research."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
from urllib.parse import urlparse, parse_qs

from pydantic import ValidationError

from .schemas import Post, ProfileInfo, ResearchSource, CommentEvidence
from .evidence import safe_url

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "integrations" / "socialmonitor" / "worker.mjs"
DATA_DIR = ROOT / "backend" / ".socialmonitor"
_lock = threading.Lock()
_login_process: subprocess.Popen | None = None
_collection_process: subprocess.Popen | None = None
_login_tasks: set[asyncio.Task] = set()
_done = threading.Event()
_done.set()
_progress = "Ready to collect."
_cancel_version = 0


def cancellation_version() -> int:
    return _cancel_version


class CollectorError(RuntimeError):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


def profile_url(raw: str) -> tuple[str, str, str]:
    u = urlparse(raw.strip() if re.match(r"^https?://", raw.strip(), re.I) else "https://" + raw.strip())
    host = (u.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    network = {"instagram.com": "Instagram", "facebook.com": "Facebook", "tiktok.com": "TikTok"}.get(host)
    if not network or u.scheme not in ("http", "https") or u.username or u.password or u.port:
        raise ValueError("Use an Instagram, Facebook or TikTok profile URL.")
    handle = u.path.strip("/")
    if network == "TikTok":
        handle = handle.removeprefix("@")
    if network == "Facebook" and handle == "profile.php":
        handle = parse_qs(u.query).get("id", [""])[0]
    if not re.fullmatch(r"[\w.-]{1,100}", handle, flags=re.ASCII) or (network == "Instagram" and handle in {"p", "reel", "reels", "explore", "accounts"}):
        raise ValueError("Paste the profile link, rather than an individual post or login page.")
    path = f"@{handle}" if network == "TikTok" else f"profile.php?id={handle}" if network == "Facebook" and handle.isdigit() else handle
    return f"https://www.{host}/{path}", network, handle


def status() -> dict:
    return {"installed": bool(shutil.which("node") and (WORKER.parent / "node_modules/playwright/package.json").exists()),
            "login_open": _login_process is not None and _login_process.poll() is None,
            "busy": _lock.locked(), "progress": _progress, "networks": ["instagram", "facebook", "tiktok"]}


def _terminate_owned_worker(proc):
    if proc.poll() is not None:
        return
    # Target only this worker and its child browser, never other Chrome windows.
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
    else:
        proc.kill()
    proc.wait(timeout=10)


def _stop_sync(proc, action):
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.stdin.write(json.dumps({"action": action}) + "\n")
        proc.stdin.flush()
        proc.wait(timeout=12)
    except (BrokenPipeError, OSError, ValueError, subprocess.TimeoutExpired):
        _terminate_owned_worker(proc)


async def finish_login() -> dict:
    await asyncio.to_thread(_stop_sync, _login_process, "finish_login")
    if _login_tasks:
        await asyncio.gather(*list(_login_tasks))
    return {"closed": True, "message": "Sign-in window closed. You can now analyze the profile."}


async def cancel_collection() -> dict:
    global _cancel_version
    _cancel_version += 1
    await asyncio.to_thread(_stop_sync, _collection_process, "cancel")
    await asyncio.to_thread(_done.wait, 3)
    return {"cancelled": True}


def _process() -> subprocess.Popen:
    node = shutil.which("node")
    if not node or not status()["installed"]:
        raise CollectorError("SocialMonitor needs Node.js and its browser dependency. Run npm run collector:setup and npm run collector:browser from speculara.")
    # The browser worker has no use for AI/database credentials.
    env = {k: v for k, v in os.environ.items() if not any(word in k.upper() for word in ("API_KEY", "SECRET", "TOKEN", "SUPABASE", "ANTHROPIC", "OPENAI", "GEMINI", "GEMMA", "AWS_"))}
    env["SPECULARA_COLLECTOR_DATA_DIR"] = str(DATA_DIR)
    env['NODE_USE_SYSTEM_CA']='1'  # Trust managed Windows certificates without disabling TLS.
    return subprocess.Popen([node, str(WORKER)], cwd=WORKER.parent, env=env, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


def _invoke_sync(payload: dict) -> dict:
    global _collection_process, _progress
    if not _lock.acquire(blocking=False):
        raise CollectorError("The collector is busy. Finish signing in and close the sign-in window, or wait for the current collection.", 409)
    proc = None
    timer = None
    expired = threading.Event()
    _done.clear()
    try:
        proc = _process()
        _collection_process = proc
        _progress = "Opening the collection browser…"
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()
        def timeout():
            expired.set()
            _terminate_owned_worker(proc)
        deadline=max(210,30+int(payload.get('limit',20))*10)
        timer = threading.Timer(deadline, timeout)
        timer.daemon = True
        timer.start()
        result = None
        for line in proc.stdout:
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if message.get("event") == "progress":
                _progress = str(message.get("message", "Collecting…"))[:250]
            elif "ok" in message:
                result = message
        proc.wait(timeout=10)
        if expired.is_set():
            raise CollectorError(f"SocialMonitor collection timed out after {deadline//60} minutes. Try fewer posts or sign in again.")
        if result is None:
            raise CollectorError("SocialMonitor could not start. Check Node.js and run npm run collector:setup.")
        if not result.get("ok"):
            raise CollectorError(str(result.get("error") or "SocialMonitor could not read that profile."))
        return result["data"]
    finally:
        if timer:
            timer.cancel()
        if proc and proc.poll() is None:
            try:
                _terminate_owned_worker(proc)
            except (OSError, subprocess.TimeoutExpired):
                pass
        if proc:
            for stream in (proc.stdin, proc.stdout):
                try:
                    stream.close()
                except OSError:
                    pass
        _collection_process = None
        _progress = "Ready to collect."
        _lock.release()
        _done.set()


async def start_login(network: str) -> dict:
    global _login_process, _progress
    if network not in ("instagram", "facebook"):
        raise CollectorError("Choose Instagram or Facebook for sign-in. TikTok uses public pages.", 422)
    # Retrying sign-in is an explicit request to reopen its window. A hidden or
    # minimized login must not leave the user trapped behind a permanent 409.
    if _login_process is not None:
        await finish_login()
    if not _lock.acquire(blocking=False):
        raise CollectorError("The collector is busy. Cancel the current collection before opening sign-in.", 409)
    proc = None
    _done.clear()
    try:
        proc = _process()
        proc.stdin.write(json.dumps({"action": "login", "network": network}) + "\n")
        proc.stdin.flush()
        line = await asyncio.wait_for(asyncio.to_thread(proc.stdout.readline), timeout=25)
        result = json.loads(line)
        if result.get("event") != "login_ready":
            raise CollectorError(result.get("error", "Could not open the sign-in window."))
        _login_process = proc
        _progress = "Finish signing in, then click Done signing in."
    except BaseException:
        if proc and proc.poll() is None:
            try:
                _terminate_owned_worker(proc)
            except (OSError, subprocess.TimeoutExpired):
                pass
        _lock.release()
        _done.set()
        raise

    async def finish():
        global _login_process, _progress
        try:
            await asyncio.to_thread(proc.wait)
        finally:
            try:
                proc.stdout.close()
                proc.stdin.close()
            finally:
                _login_process = None
                _progress = "Ready to collect."
                _lock.release()
                _done.set()
    task = asyncio.create_task(finish())
    _login_tasks.add(task)
    task.add_done_callback(_login_tasks.discard)
    return {"opened": True, "message": "Sign in in the browser window, then click Done signing in here."}


def normalize(data: dict, canonical_url: str, network: str, handle: str) -> tuple[ProfileInfo, list[Post]]:
    posts: list[Post] = []
    missing: set[str] = set()
    seen: set[str] = set()
    skipped = 0
    sources = []
    types = {"photo": "Photo", "video": "Video", "reel": "Reel", "carousel": "Carousel", "text": "Text"}
    for raw in data.get("posts", []):
        try:
            pid = str(raw["ext_id"])
            if pid in seen:
                continue
            unavailable = [key for key, field in (("likes", "likes"), ("comments", "comments_count"), ("shares", "shares"), ("views", "views"), ("saves","saves")) if raw.get(field) is None] + ["sales"]
            url = safe_url(raw.get("url"))
            comment_rows = [c for c in (raw.get("comments") or []) if isinstance(c, dict) and c.get("text")][:8]
            p = Post(id=pid, posted_at=raw["posted_at"], type=types.get(raw.get("kind"), "Photo"),
                     caption=raw.get("caption") or "", likes=max(0, int(raw.get("likes") or 0)),
                     comments=max(0, int(raw.get("comments_count") or 0)), shares=max(0, int(raw.get("shares") or 0)),
                     views=max(0, int(raw.get("views") or 0)), saves=max(0,int(raw.get('saves') or 0)),
                     comments_sample=[str(c["text"]) for c in comment_rows], url=url,
                     comment_evidence=[CommentEvidence(id=str(c.get("ext_id", "")), text=str(c["text"]),
                        author=str(c.get("author") or ""), posted_at=c.get("posted_at"),
                        source_url=safe_url(c.get("url")) or url,
                        source_kind="comment" if safe_url(c.get("url")) else "post" if url else "none") for c in comment_rows],
                     unavailable_metrics=unavailable)
            posts.append(p)
            missing.update(unavailable)
            seen.add(pid)
            if url:
                sources.append(ResearchSource(title=f"{network} post {pid}", url=url))
        except (KeyError, TypeError, ValueError, ValidationError):
            skipped += 1
    notes = f"Collected {len(posts)} posts with SocialMonitor. Totals include only observed values."
    if missing: notes += f" Add your own Insights or sales counts for missing metrics: {', '.join(sorted(missing))}."
    if network == "Instagram" and not data.get("signed_in"):
        notes += " Sign in for comment text; public post counts can be available without signing in."
    if posts and not any(p.comments_sample for p in posts):
        notes += " No comment text was returned; sentiment and keywords reflect captions only."
    if skipped:
        notes += f" Skipped {skipped} posts with missing or invalid dates/data."
    if not sources:
        sources = [ResearchSource(title=f"{network} profile", url=canonical_url)]
    return ProfileInfo(platform=network, handle=handle, notes=notes, sources=sources, collector="socialmonitor", unavailable_metrics=sorted(missing)), posts


async def collect_profile(raw_url: str, limit: int = 20) -> tuple[ProfileInfo, list[Post]]:
    canonical, network, handle = profile_url(raw_url)
    if not 5<=limit<=50: raise CollectorError('Choose 5 to 50 posts.',422)
    result = await asyncio.to_thread(_invoke_sync, {"action": "collect", "url": canonical, "limit": limit})
    return normalize(result, canonical, network, handle)
