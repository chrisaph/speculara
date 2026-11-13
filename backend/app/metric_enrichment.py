"""Bounded background reads of already-collected public Instagram posts."""
import asyncio
from copy import deepcopy
from hashlib import sha256
import json
from secrets import token_urlsafe
from time import monotonic

from . import analytics, collector
from .schemas import Post

jobs = {}
tasks = set()


def merge_observed(posts, records):
    updated = 0
    by_id = {p.id: p for p in posts}
    for record in records:
        post = by_id.get(str(record.get('id', '')))
        if not post:
            continue
        for metric, value in record.get('metrics', {}).items():
            if metric not in ('views', 'shares', 'saves', 'likes', 'comments') or metric not in post.unavailable_metrics:
                continue
            if type(value) is not int or not 0 <= value <= 10**15:
                continue
            setattr(post, metric, value)
            post.unavailable_metrics.remove(metric)
            post.metric_sources[metric] = 'Public post page (Playwright)'
            updated += 1
    return updated


async def _run(job, active, posts):
    job.update(status='running', message='Checking public post pages in the background…')
    try:
        extra = await collector.enrich_public_metrics(posts)
        updated = merge_observed(posts, extra.get('posts', []))
        result = await asyncio.to_thread(analytics.analyze, posts) if updated else deepcopy(active)
        profile = deepcopy(active.get('profile', {}))
        profile['unavailable_metrics'] = [m for m, value in result.get('metric_availability', {}).items() if not value['complete']]
        message = (f"Checked {extra.get('checked', 0)} public post pages; added {updated} supplied counts. "
                   'Counts not exposed by the page remain unavailable. Saves and sales may need an Insights or sales upload.')
        metadata = {'status': 'complete', 'updated_values': updated, 'message': message, 'notes': extra.get('notes', [])}
        if updated:
            profile['notes'] = message
            result['facts']['data_quality'] = {'source': 'SocialMonitor + public post pages',
                'unavailable_metrics': profile['unavailable_metrics'], 'notes': message}
        result = {**active, **result, 'profile': profile, 'metric_enrichment': metadata}
        # Enriched results are not saved under the old analysis ID.
        if updated:
            result['analysis_id'] = None
        job.update(status='complete', message=message, result=result)
    except asyncio.CancelledError:
        job.update(status='cancelled', message='Background check cancelled.')
        raise
    except Exception:
        job.update(status='failed', message='Public metrics could not be checked. Your existing results are unchanged; try again after signing in.')


def start(active, refresh=False):
    if active.get('profile', {}).get('collector') != 'socialmonitor':
        raise ValueError('Background checks require an existing live collection.')
    posts = [Post.model_validate(raw) for raw in active.get('evidence', {}).get('posts', [])]
    if not 5 <= len(posts) <= 50:
        raise ValueError('Use an analysis containing 5 to 50 collected posts.')
    # Validate the target domain and media path before launching a browser.
    from urllib.parse import urlsplit
    import re
    for p in posts:
        u = urlsplit(p.url)
        if u.scheme != 'https' or u.hostname not in ('instagram.com', 'www.instagram.com') or u.port or u.username or u.password or not re.fullmatch(r'/(p|reel)/[A-Za-z0-9_-]+/?', u.path):
            raise ValueError('Background checks currently support collected Instagram posts only.')
    fingerprint = sha256(json.dumps([p.model_dump(mode='json') for p in posts], sort_keys=True).encode()).hexdigest()
    now = monotonic()
    for key, job in list(jobs.items()):
        if now - job['created'] > 600 and job['status'] not in ('queued', 'running'):
            jobs.pop(key)
        elif job['fingerprint'] == fingerprint and (not refresh or job['status'] in ('queued', 'running')):
            return {'job_id': key, 'status': job['status']}
    if any(job['status'] in ('queued', 'running') for job in jobs.values()) or collector.status()['busy'] or collector.status()['login_open']:
        raise RuntimeError('The browser is busy. Finish the current collection or sign-in first.')
    if len(jobs) >= 20:
        raise RuntimeError('Too many recent background checks. Try again later.')
    key = token_urlsafe(24)
    jobs[key] = {'status': 'queued', 'message': 'Waiting to check public metrics…', 'created': now, 'fingerprint': fingerprint}
    task = asyncio.create_task(_run(jobs[key], deepcopy(active), posts))
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return {'job_id': key, 'status': 'queued'}


def status(key):
    job = jobs.get(key)
    if not job:
        return None
    result = {k: v for k, v in job.items() if k not in ('created', 'fingerprint')}
    state = collector.status()
    if job['status'] == 'running' and state['busy']:
        result['message'] = state.get('progress') or job['message']
    return result


async def shutdown():
    for task in list(tasks):
        task.cancel()
    if tasks:
        await asyncio.gather(*list(tasks), return_exceptions=True)
