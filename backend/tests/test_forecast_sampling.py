"""Sparse publication dates must not turn stable per-post results into zero weeks."""
from datetime import datetime,timedelta
import numpy as np
from app import analytics,insights
from app.schemas import Post


def frame(days,values):
    return analytics.to_frame([Post(id=str(i),posted_at=datetime(2026,1,1)+timedelta(days=d),likes=v)
                               for i,(d,v) in enumerate(zip(days,values))])


def test_irregular_posting_does_not_insert_zero_performance_posts():
    df=frame([0,1,16,29,50,61,80,91,100,120,121,150],[100]*12)
    p=insights._forecast(df,'likes',8,as_of='2026-11-12',basis='post')
    assert len(p['history'])==12
    assert all(r['value']==100 for r in p['history'])
    assert p['accuracy']==100 and p['validation']['weighted_error_pct']==0
    assert p['validation']['test_posts']==3 and p['validation']['test_weeks']==0
    assert [r['date'] for r in p['forecast']]==[f'Next post {i}' for i in range(1,9)]


def test_many_posts_in_one_week_can_support_post_forecast_but_not_weekly_forecast():
    df=frame([0]*12,[100]*12)
    post=insights._forecast(df,'likes',8,as_of='2026-11-12',basis='post')
    weekly=insights._forecast(df,'likes',8,as_of='2026-11-12')
    assert post['accuracy']==100 and len(post['history'])==12
    assert len(weekly['history'])==1 and weekly['forecast']==[]


def test_post_forecast_excludes_future_dated_posts_and_preserves_observed_zero():
    df=frame([0,1,2,3,4,5,6,400],[100,100,100,100,100,0,100,999999])
    p=insights._forecast(df,'likes',8,as_of='2026-11-12',basis='post')
    assert len(p['history'])==7 and p['history'][5]['value']==0
    assert max(r['value'] for r in p['history'])==100


def test_selection_uses_multi_step_predictions_without_access_to_holdout(monkeypatch):
    calls=[]
    original=insights._fit
    def fit(y,horizon,method='damped'):
        calls.append((list(y),horizon));return original(y,horizon,method)
    monkeypatch.setattr(insights,'_fit',fit)
    train=np.arange(1,13,dtype=float)
    insights._choose_model(train,horizon=3)
    assert calls and all(h==3 for _,h in calls)
    assert all(len(y)<=len(train)-3 for y,_ in calls)


def test_recent_collapse_can_still_report_genuine_zero_backtest():
    p=insights._forecast(frame(list(range(12)),[100]*9+[1]*3),'likes',8,as_of='2026-11-12',basis='post')
    assert p['accuracy']==0 and p['validation']['weighted_error_pct']>=100
    assert p['validation']['actual_total']==3
    assert len(p['forecast'])==8 and p['forecast_supported'] is True
    assert p['reliability']=='low' and 'Exploratory estimate' in p['reason']
    assert all(0<=r['low']<=r['value']<=r['high'] for r in p['forecast'])
    assert len(p['history'])==12 and p['validation']['observations']


def test_default_prediction_and_weekly_trends_keep_separate_units():
    p=insights.predict(frame([7*i for i in range(16)],[100]*16))
    assert p['basis']=='post' and p['metrics']['likes']['basis']=='post'
    assert p['weekly_metrics']['likes']['basis']=='week'
    assert p['metrics']['likes']['forecast'][0]['date']=='Next post 1'
    assert p['weekly_metrics']['likes']['forecast'][0]['date'].startswith('2026-')


def test_zero_holdout_total_keeps_exploratory_estimate_without_percentage_score():
    p=insights._forecast(frame(list(range(12)),[100]*9+[0]*3),'likes',8,as_of='2026-11-12',basis='post')
    assert len(p['forecast'])==8 and p['reliability']=='unknown'
    assert p['validation']['weighted_error_pct'] is None and p['accuracy'] is None
    assert 'percentage error cannot be calculated' in p['reason']
