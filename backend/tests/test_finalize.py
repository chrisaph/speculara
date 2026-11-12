import io,json
from datetime import datetime,timedelta
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from app import analytics,main,insights,collector
from app.schemas import Post
from app.metric_import import merge_metrics
from app.metric_import import canonical


def dataset():
    posts=[Post(id=str(i),url=f'https://www.instagram.com/reel/final{i}/',posted_at=datetime(2026,1,1)+timedelta(weeks=i),caption=f'Observed {i}',likes=10+i,comments=20-i,comments_sample=['Where to buy? Please make more!'],unavailable_metrics=['views','saves','shares','sales']) for i in range(12)]
    result=analytics.analyze(posts);result['profile']={'platform':'Instagram','handle':'qa'}
    return result


def test_metric_import_unlocks_all_fifteen_pairs_and_preserves_evidence():
    before=dataset()
    csv='url,views,saves,shares,sales\n'+''.join(f'https://instagram.com/reel/final{i}/?utm=x,{100+i*10},{i*2},{i*3},{i}\n' for i in range(12))
    r=TestClient(main.app).post('/api/metrics',data={'analysis':json.dumps(before)},files={'file':('metrics.csv',csv.encode(),'text/csv')})
    assert r.status_code==200,r.text
    after=r.json()
    assert len(after['correlation']['pairs'])==15
    assert after['metric_import']=={'matched_posts':12,'updated_values':48,'source':'User-imported metrics'}
    assert after['metric_availability']['sales']['known_posts']==12
    assert after['metric_availability']['sales']['imported_posts']==12
    assert after['metric_availability']['sales']['total']==66
    assert after['evidence']['comments']==before['evidence']['comments']
    assert after['sentiment']['scored']==12 and after['demand']['summary']==before['demand']['summary']
    assert after['analysis_id'] is None  # Chat must not reload an older saved dataset.
    assert all(p['metric_sources']['sales']=='User-imported metrics' for p in after['evidence']['posts'])


def test_import_zero_is_observed_but_blank_keeps_metric_unknown():
    data=dataset()
    merged,summary=merge_metrics(data,b'id,views,sales\n0,0,\n','metrics.csv')
    assert merged[0].views==0 and 'views' not in merged[0].unavailable_metrics
    assert 'sales' in merged[0].unavailable_metrics and 'views' in merged[1].unavailable_metrics
    assert summary['updated_values']==1
    result=analytics.analyze(merged)
    assert result['metric_availability']['views']['total']==0
    assert result['metric_availability']['views']['known_posts']==1
    assert 'views' not in result['correlation']['matrix']


@pytest.mark.parametrize('csv',[b'id,views\nunknown,4\n',b'id,views\n0,-1\n',b'id,views\n0,1.5\n',b'id,views\n0,=2+2\n',b'id,views\n0,3\n0,4\n',b'id,url,views\n0,https://instagram.com/reel/final1/,4\n',b'id,views\n0,\n'])
def test_invalid_metric_import_is_atomic_and_actionable(csv):
    data=dataset();original=json.dumps(data)
    with pytest.raises(ValueError):merge_metrics(data,csv,'metrics.csv')
    assert json.dumps(data)==original


def test_xlsx_metrics_use_matching_urls_and_preserve_counts():
    w=Workbook();w.active.append(['post_url','saves','sales']);w.active.append(['https://www.instagram.com/reel/final0/',123,0])
    content=io.BytesIO();w.save(content)
    posts,summary=merge_metrics(dataset(),content.getvalue(),'metrics.xlsx')
    assert posts[0].saves==123 and posts[0].sales==0
    assert 'sales' not in posts[0].unavailable_metrics


def test_corrupt_workbook_returns_actionable_validation_error():
    r=TestClient(main.app).post('/api/metrics',data={'analysis':json.dumps(dataset())},files={'file':('broken.xlsx',b'not-a-workbook','application/octet-stream')})
    assert r.status_code==422 and 'readable XLSX' in r.json()['detail']


def test_facebook_query_post_ids_are_not_collapsed_during_matching():
    assert canonical('https://facebook.com/permalink.php?story_fbid=111&id=7')!=canonical('https://facebook.com/permalink.php?story_fbid=222&id=7')
    assert canonical('https://www.facebook.com/permalink.php?id=7&story_fbid=111&fbclid=tracking')==canonical('https://m.facebook.com/permalink.php?story_fbid=111&id=7')


def test_zero_score_exposes_error_instead_of_claiming_zero_activity():
    posts=[Post(id=str(i),posted_at=datetime(2026,1,1)+timedelta(weeks=i),likes=100 if i<9 else 1) for i in range(12)]
    result=insights._forecast(analytics.to_frame(posts),'likes',8,as_of='2026-11-12')
    assert result['accuracy']==0
    assert result['validation']['weighted_error_pct']>=100
    assert result['validation']['actual_total']==3
    assert all(r['actual']==1 for r in result['validation']['observations'])


def test_unfinished_week_is_not_used_for_model_selection_or_backtesting():
    posts=[Post(id=str(i),posted_at=datetime(2026,1,1)+timedelta(weeks=i),likes=100+i) for i in range(12)]
    result=insights._forecast(analytics.to_frame(posts),'likes',8,as_of='2026-03-06')
    assert result['partial_weeks']
    assert all(r['date']<'2026-03-06' for r in result['history'])
    assert result['validation']['end']<'2026-03-06'


def test_zero_holdout_total_has_no_percentage_score():
    posts=[Post(id=str(i),posted_at=datetime(2026,1,1)+timedelta(weeks=i),likes=100 if i<9 else 0) for i in range(12)]
    result=insights._forecast(analytics.to_frame(posts),'likes',8,as_of='2026-11-12')
    assert result['accuracy'] is None and result['validation']['weighted_error_pct'] is None
    assert result['validation']['actual_total']==0


def test_collector_keeps_observed_saves_shares_and_zero_views():
    raw={'posts':[{'ext_id':'1','posted_at':'2026-01-01T00:00:00Z','kind':'reel','likes':2,'comments_count':1,'views':0,'saves':4,'shares':5,'url':'https://instagram.com/reel/p/'}]}
    _,posts=collector.normalize(raw,'https://instagram.com/qa','Instagram','qa')
    assert posts[0].saves==4 and posts[0].shares==5 and posts[0].views==0
    assert posts[0].unavailable_metrics==['sales']
