import asyncio,json
import pytest
from fastapi.testclient import TestClient
from app import analytics,main,collector,llm
from app.sample import sample_posts
from app.text_sentiment import score_text
from app.chat_context import model_context


@pytest.mark.parametrize('text',['ganda','Ang ganda!','sobrang maganda','gandaaaa','Sulit at ang galing!','hindi pangit'])
def test_filipino_positive(text):assert score_text(text)>=.05


@pytest.mark.parametrize('text',['hindi maganda','pangit','bulok at sira','Hindi ko gusto'])
def test_filipino_negative(text):assert score_text(text)<=-.05


def test_filipino_compliments_do_not_become_demand():
    posts=sample_posts(6)
    for p in posts:p.comments_sample=['Ang ganda!','Magkano po? Saan mabibili?','Pabili po!'];p.comment_evidence=[]
    result=analytics.analyze(posts)
    assert next(s for s in result['sentiment']['samples'] if s['text']=='Ang ganda!')['tone']=='pos'
    assert result['demand']['summary']['questions']==6
    assert result['demand']['summary']['requests']==6
    assert result['demand']['summary']['demand_comments']==12


def test_requested_post_limit_reaches_collector_and_cache_is_separate(monkeypatch):
    calls=[]
    async def collect(url,limit=20):
        calls.append(limit);return collector.ProfileInfo(platform='Instagram',handle='qa',collector='socialmonitor'),sample_posts(limit)
    monkeypatch.setattr(collector,'collect_profile',collect)
    monkeypatch.setattr(main.db,'find_cached',lambda *a:None);monkeypatch.setattr(main.db,'save_analysis',lambda *a:None)
    c=TestClient(main.app)
    for limit in (5,30,5):
        r=c.post('/api/analyze',json={'url':'instagram.com/qa','post_limit':limit})
        assert r.status_code==200,r.text
        assert r.json()['post_count']==limit and r.json()['requested_post_limit']==limit
    assert calls==[5,30]


@pytest.mark.parametrize('limit',[1,0,51,-1,True,'20'])
def test_invalid_limits_are_rejected(limit):
    assert TestClient(main.app).post('/api/analyze',json={'url':'instagram.com/qa','post_limit':limit}).status_code==422


def test_compact_gemma_context_keeps_valid_json_and_reports_coverage():
    full=analytics.analyze(sample_posts(50));compact=model_context(full)
    assert len(json.dumps(compact,separators=(',',':')))<24000
    assert compact['evidence_coverage']['collected_posts']==50
    assert compact['evidence_coverage']['posts_in_context']>0
    assert compact['demand']['summary']==full['demand']['summary']
    assert model_context(compact)==compact


def test_grouped_model_citations_resolve_only_supplied_safe_urls():
    from app.chat_context import cited_sources
    context={'source_index':{'P1':{'url':'https://example.com/post/1'},'P2':{'url':'https://example.com/post/2'},'P3':{'url':'javascript:alert(1)'}}}
    found=cited_sources('Compare [P1, P2], repeated [P1], unknown [P99] and unsafe [P3].',context)
    assert [s['url'] for s in found]==['https://example.com/post/1','https://example.com/post/2']
