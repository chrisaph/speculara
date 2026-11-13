import asyncio

import pytest

from app import analytics, collector, metric_enrichment
from app.sample import sample_posts


def active():
    posts = sample_posts(6)
    for i, post in enumerate(posts):
        post.url = f'https://www.instagram.com/reel/fixture{i}/'
        post.views = post.saves = post.shares = post.sales = 0
        post.unavailable_metrics = ['views', 'saves', 'shares', 'sales']
    return {**analytics.analyze(posts), 'analysis_id': 'saved',
            'profile': {'platform': 'Instagram', 'collector': 'socialmonitor', 'handle': 'fixture'}}, posts


def test_public_merge_keeps_imported_and_known_counts_and_never_infers_sales():
    _, posts = active()
    likes = posts[0].likes
    changed = metric_enrichment.merge_observed(posts, [{'id': posts[0].id, 'metrics': {
        'views': 0, 'likes': 999999, 'sales': 50, 'shares': -1, 'saves': True}}])
    assert changed == 1
    assert posts[0].views == 0 and 'views' not in posts[0].unavailable_metrics
    assert posts[0].likes == likes
    assert 'sales' in posts[0].unavailable_metrics
    assert 'shares' in posts[0].unavailable_metrics
    assert 'saves' in posts[0].unavailable_metrics


def test_background_result_reanalyzes_without_blocking_the_initial_response(monkeypatch):
    data, posts = active()

    async def read(_):
        await asyncio.sleep(0)
        return {'checked': 1, 'posts': [{'id': posts[0].id, 'metrics': {'views': 1234}}]}

    monkeypatch.setattr(collector, 'enrich_public_metrics', read)
    monkeypatch.setattr(collector, 'status', lambda: {'busy': False, 'login_open': False})

    async def run():
        metric_enrichment.jobs.clear()
        response = metric_enrichment.start(data)
        assert response['status'] == 'queued'
        assert metric_enrichment.start(data)['job_id'] == response['job_id']
        await asyncio.gather(*list(metric_enrichment.tasks))
        state = metric_enrichment.status(response['job_id'])
        assert state['status'] == 'complete'
        assert state['result']['metric_availability']['views']['known_posts'] == 1
        assert state['result']['metric_availability']['views']['total'] == 1234
        assert state['result']['analysis_id'] is None
        assert 'fingerprint' not in state
        assert data['metric_availability']['views']['known_posts'] == 0
        metric_enrichment.jobs.clear()

    asyncio.run(run())


def test_rejects_arbitrary_urls_before_launching_browser():
    data, _ = active()
    data['evidence']['posts'][0]['url'] = 'https://127.0.0.1/private'
    with pytest.raises(ValueError, match='Instagram'):
        metric_enrichment.start(data)


def test_background_http_routes_return_a_completed_result(monkeypatch):
    import time
    from fastapi.testclient import TestClient
    from app.main import app
    data, posts = active()

    async def read(_):
        return {'checked': 1, 'posts': [{'id': posts[0].id, 'metrics': {'shares': 7}}]}

    monkeypatch.setattr(collector, 'enrich_public_metrics', read)
    monkeypatch.setattr(collector, 'status', lambda: {'busy': False, 'login_open': False})
    metric_enrichment.jobs.clear()
    with TestClient(app) as client:
        response = client.post('/api/enrichment/start', json={'analysis': data})
        assert response.status_code == 200
        key = response.json()['job_id']
        state = {}
        for _ in range(100):
            state = client.get('/api/enrichment/' + key).json()
            if state['status'] == 'complete':
                break
            time.sleep(.01)
        assert state['status'] == 'complete'
        assert state['result']['metric_availability']['shares']['total'] == 7
        assert state['result']['metric_enrichment']['updated_values'] == 1
        assert client.get('/api/enrichment/not-a-job').status_code == 404
    metric_enrichment.jobs.clear()
