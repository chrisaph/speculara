"""Reproductions from the 12 Nov Speculara QA review, using known-input fixtures."""
from datetime import datetime, timedelta
import io
import asyncio
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app import analytics, main, strategy
from app.schemas import Post


def posts(n=12):
    return [Post(id=str(i), posted_at=datetime(2026,1,1)+timedelta(weeks=i),
                 caption=f'Banana recipe tutorial {i}' if i%2 else f'Garden tools review {i}',
                 comments_sample=['Please make more recipes!'] if i%2 else ['How much is that tool?'],
                 likes=(i+1)*10,comments=(n-i)*2,views=(i+1)*100,
                 url=f'https://www.instagram.com/reel/qa{i}/') for i in range(n)]


def test_signed_correlation_and_actual_scatter():
    result=analytics.analyze(posts())['correlation']
    pair=next(p for p in result['pairs'] if {p['a'],p['b']}=={'Likes','Comments'})
    assert pair['v']==-1 and pair['n']==12
    assert result['matrix']['likes']['comments']==-1
    assert result['scatter']['likes|comments'][0]['x']==10
    assert result['scatter']['likes|comments'][0]['y']==24


def test_pairwise_missing_metrics_are_excluded():
    data=posts()
    for p in data[:10]: p.unavailable_metrics=['views']
    result=analytics.analyze(data)
    assert 'views' not in result['correlation']['matrix']
    assert result['metric_availability']['views']['known_posts']==2
    assert result['charts']['views']['month'][0]['value']==2300


def test_all_missing_metrics_never_get_estimated():
    data=posts()
    for p in data: p.views=0; p.unavailable_metrics=['views','saves','sales']
    result=analytics.analyze(data)
    assert result['metric_availability']['views']['total'] is None
    assert result['predict']['metrics']['views']['forecast']==[]
    assert result['predict']['metrics']['views']['history']==[]
    assert result['charts']['views']['month']==[]
    assert result['predict']['trend_metric']=='likes'


@pytest.mark.parametrize('caption',['the and of','!!!','','你好','a'])
def test_empty_tfidf_vocabulary_does_not_crash(caption):
    data=posts(6)
    for p in data: p.caption=caption; p.comments_sample=[]
    result=analytics.analyze(data)
    assert len(result['recommend']['comparisons']['0'])==5
    assert all(np.isfinite(r['score']) for r in result['recommend']['comparisons']['0'])


def test_similarity_uses_text_comments_and_is_selected_post_specific():
    data=posts(6)
    result=analytics.analyze(data)['recommend']
    rows=result['comparisons']['1']
    assert all(r['id']!='1' for r in rows)
    assert rows[0]['id'] in {'3','5'}
    assert rows[0]['caption_similarity']>0 and rows[0]['comment_similarity']>0
    assert result['comparisons']['0'][0]['id'] in {'2','4'}
    assert all(r['url'].endswith('/') for r in rows)


def test_forecast_uses_separate_holdout_and_metric_values():
    result=analytics.analyze(posts(16))['predict']
    for metric in ['likes','comments','views']:
        f=result['metrics'][metric]
        assert len(f['history'])==16 and len(f['forecast'])==8
        assert f['validation']['train_weeks']+f['validation']['test_weeks']==16
        assert f['validation']['test_weeks']>=2
        assert f['history'][0]['value']==getattr(posts(16)[0],metric)
        assert all(r['low']<=r['value']<=r['high'] for r in f['forecast'])
    assert result['metrics']['views']['forecast'][0]['value'] > result['metrics']['likes']['forecast'][0]['value']


def test_no_longevity_estimate_without_completed_matches():
    result=analytics.analyze(posts(6))['predict']
    assert result['weeks_left'] is None and result['similar_windows']==[]


def test_matching_windows_have_traceable_actual_posts():
    data=posts(20)
    for i,p in enumerate(data): p.views=100+(i%4)*5
    p=analytics.analyze(data)['predict']
    assert p['similar']==len(p['similar_windows'])>0
    for w in p['similar_windows']:
        assert w['start']<=w['end']<p['history'][-4]['date']
        assert len(w['history'])==4 and w['posts']
        assert all(x['url'].startswith('https://www.instagram.com/reel/qa') for x in w['posts'])


def test_chart_totals_and_all_post_comparisons():
    data=posts()
    result=analytics.analyze(data)['charts']['likes']
    assert sum(r['value'] for r in result['month'])==780
    assert sum(r['value'] for r in result['week'])==780
    assert len(result['posts'])==12
    assert sum(r['value'] for r in result['posts'])==780


def test_upload_marks_missing_columns_and_preserves_urls():
    data='date,caption,likes,url\n'+''.join(f'2026-01-{i+1:02d},Post {i},{i},https://www.instagram.com/p/qa{i}/\n' for i in range(6))
    result=analytics.posts_from_file(data.encode(),'qa.csv')
    assert all(set(p.unavailable_metrics)=={'comments','shares','saves','views','sales'} for p in result)
    assert result[0].url=='https://www.instagram.com/p/qa0/'
    assert analytics.analyze(result)['metric_availability']['views']['total'] is None


def test_negative_upload_rejected_and_analysis_survives_storage_failure(monkeypatch):
    client=TestClient(main.app)
    r=client.post('/api/upload',files={'file':('qa.csv',b'date,likes\n2026-01-01,-1','text/csv')})
    assert r.status_code==422
    def fail(*args): raise RuntimeError('Database unavailable')
    monkeypatch.setattr(main.db,'recent',fail)
    r=client.get('/api/history')
    assert r.status_code==200 and r.json()=={'items':[],'storage_available':False}


def test_strategy_cites_retrieved_references_and_statistics(monkeypatch):
    a=analytics.analyze(posts()); a['profile']={'platform':'Instagram'}
    async def docs(platform): return [{'id':'W1','title':'Official guide','url':'https://about.fb.com/guide','text':'Guidance text','retrieved_at':'2026-11-12'}]
    async def generate(instructions,prompt):
        assert 'online_research' in prompt and 'metric_availability' in prompt
        assert 'do not invent' in instructions.lower()
        return {'finishReason':'STOP','content':{'parts':[{'text':'Test a follow-up based on comments [P1] and official guidance [W1].'}]}}
    monkeypatch.setattr(strategy,'research',docs); monkeypatch.setattr(strategy,'_generate',generate)
    r=TestClient(main.app).post('/api/strategy',json={'message':'strategy','analysis':a}).json()
    assert r['engine']=='gemma' and r['research_status']=='retrieved'
    assert {s['id'] for s in r['sources']}=={'P1','W1'}


def test_strategy_provider_failure_is_labeled_fallback(monkeypatch):
    async def docs(platform): return []
    async def fail(*args): raise strategy.LLMUnavailable('Provider unavailable')
    monkeypatch.setattr(strategy,'research',docs); monkeypatch.setattr(strategy,'_generate',fail)
    a=analytics.analyze(posts())
    r=asyncio.run(strategy.generate_strategy(a))
    assert r['engine']=='fallback' and r['research_status']=='unavailable'
    assert r['notice']=='Provider unavailable'
    assert 'reach' not in r['answer'].lower() and r['sources']
