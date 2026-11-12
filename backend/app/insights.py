"""Observed-data forecasts, comparisons and correlations; no generated demo values."""
from itertools import combinations
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from statsmodels.tsa.holtwinters import ExponentialSmoothing

METRICS = ['views', 'likes', 'comments', 'shares', 'saves', 'sales']


def known(df, metric):
    return df[~df.unavailable_metrics.map(lambda missing: metric in missing)]


def availability(df):
    return {m: {'known_posts': len(known(df, m)), 'total_posts': len(df),
                'imported_posts':int(known(df,m).metric_sources.map(lambda sources: m in sources).sum()) if 'metric_sources' in df else 0,
                'total': int(known(df, m)[m].sum()) if len(known(df, m)) else None,
                'complete': len(known(df, m)) == len(df)} for m in METRICS}


def _fit(y, horizon, method='damped'):
    if method=='last': return np.repeat(y[-1],horizon)
    if method=='mean': return np.repeat(np.mean(y[-4:]),horizon)
    if method=='median': return np.repeat(np.median(y[-5:]),horizon)
    if method=='average': return np.repeat(np.mean(y),horizon)
    fitted=ExponentialSmoothing(y,trend='add',damped_trend=True,initialization_method='estimated').fit(optimized=True)
    if fitted.mle_retvals is not None and not fitted.mle_retvals.get('success',True):
        raise ValueError('Smoothing model did not converge')
    return np.asarray(fitted.forecast(horizon))


def _choose_model(train, horizon=1):
    # Evaluate the same multi-step task as the final holdout, using training only.
    origins=list(range(2,len(train)-horizon+1))[-4:]
    methods=['mean','median','average','last']
    if origins and min(origins)>=4: methods.append('damped')
    losses={}
    for method in methods:
        try:
            errors=[float(np.abs(train[i:i+horizon]-np.maximum(0,_fit(train[:i],horizon,method))).mean()) for i in origins]
            if errors and np.all(np.isfinite(errors)): losses[method]=np.mean(errors)
        except (ValueError,ArithmeticError): continue
    return min(losses,key=losses.get) if losses else 'mean'


def _forecast(df, metric, horizon, as_of=None, basis='week'):
    rows = known(df, metric)
    empty = {'metric': metric, 'basis':basis, 'history': [], 'forecast': [], 'forecast_supported':False, 'accuracy': None,
             'validation': {'method': 'Held-out weighted absolute percentage error', 'test_weeks': 0},
             'reason': f'No observed {metric} values were supplied.'}
    if not len(rows):
        return empty
    now=pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.now(tz='UTC').tz_localize(None)
    today=now.normalize()
    if basis=='post':
        observed=rows[rows.posted_at<=now].sort_values('posted_at',kind='stable')
        weekly=pd.Series(observed[metric].to_numpy(dtype=float),index=observed.posted_at)
        partial=pd.Series(dtype=float)
    else:
        weekly = rows.set_index('posted_at')[metric].resample('W').sum()
        partial=weekly[weekly.index>=today]
        weekly=weekly[weekly.index<today]
    y = weekly.to_numpy(dtype=float)
    history = [{'date': d.strftime('%Y-%m-%d'), 'value': int(v)} for d, v in weekly.items()]
    result = {**empty, 'history': history, 'reason': '', 'basis':basis,
              'coverage': f'{len(rows)} of {len(df)} posts have this metric.',
              'partial_weeks':[{'date':d.strftime('%Y-%m-%d'),'value':int(v)} for d,v in partial.items()]}
    if len(y) < 6 or not np.any(y):
        result['reason'] = ('At least six dated posts' if basis=='post' else 'At least six completed weekly observations')+' with a non-zero total are needed for a forecast.'
        return result
    try:
        # A separate holdout fit prevents training data from becoming claimed accuracy.
        ntest = max(2, min(4, len(y) // 4))
        test = y[-ntest:]
        method=_choose_model(y[:-ntest],ntest)
        try:
            fc = np.maximum(0, _fit(y,horizon,method))
            validation = np.maximum(0, _fit(y[:-ntest],ntest,method))
        except (ValueError,ArithmeticError):
            method='mean'  # Keep a usable baseline if a numerical fit fails.
            fc=np.maximum(0,_fit(y,horizon,method));validation=np.maximum(0,_fit(y[:-ntest],ntest,method))
        if not np.isfinite(fc).all() or not np.isfinite(validation).all(): raise ValueError('Non-finite forecast')
        denom = float(np.abs(test).sum())
        absolute_error=float(np.abs(test-validation).sum())
        wape=100*absolute_error/denom if denom else None
        accuracy = round(max(0,100-wape)) if wape is not None else None
        error = float(np.sqrt(np.mean((test-validation)**2)))
        result['accuracy'] = accuracy
        result['validation'].update(test_weeks=ntest if basis=='week' else 0,
                                    test_posts=ntest if basis=='post' else 0,
                                    train_observations=len(y)-ntest, train_weeks=len(y)-ntest if basis=='week' else 0,
                                    start=weekly.index[-ntest].strftime('%Y-%m-%d'), end=weekly.index[-1].strftime('%Y-%m-%d'),
                                    weighted_error_pct=round(wape,1) if wape is not None else None,
                                    absolute_error=round(absolute_error,1),actual_total=int(denom),
                                    observations=[{'date':weekly.index[-ntest+i].strftime('%Y-%m-%d'),'actual':int(v),'predicted':round(float(validation[i]))} for i,v in enumerate(test)])
        unit='posts' if basis=='post' else 'weeks'
        result['model']={'last':'Last observed value','mean':f'Recent four-{unit[:-1]} average','median':f'Recent five-{unit[:-1]} median','average':'Training-history average','damped':'Damped exponential smoothing'}[method]
        baseline=_fit(y[:-ntest],ntest,'mean')
        result['validation']['baseline_weighted_error_pct']=round(100*float(np.abs(test-baseline).sum())/denom,1) if denom else None
        result['validation']['baseline_model']=f'Recent four-{unit[:-1]} average'
        result['validation']['selection']='Rolling multi-step validation on training data using the holdout horizon; final holdout excluded from model selection.'
        if wape is None or round(wape,1)>=100:
            result['reason']='Forecast withheld: the held-out predictions were not reliable enough. Observed history is still shown. Collect more representative posts or use the charts to compare actual results.'
            return result
        result['forecast_supported']=True
        for i, v in enumerate(fc, 1):
            band = 1.64 * error * np.sqrt(i)
            result['forecast'].append({'date': f'Next post {i}' if basis=='post' else (weekly.index[-1]+pd.Timedelta(weeks=i)).strftime('%Y-%m-%d'),
                                       'value': round(float(v)), 'low': max(0, round(float(v-band))),
                                       'high': max(0, round(float(v+band)))})
    except (ValueError, ArithmeticError):
        result['reason'] = 'The model could not fit this history. No synthetic forecast was substituted.'
    return result


def predict(df, horizon_weeks=8):
    metrics = {m: _forecast(df, m, horizon_weeks,basis='post') for m in METRICS}
    weekly_metrics = {m: _forecast(df, m, horizon_weeks) for m in METRICS}
    metric = max(['views','likes','comments'],key=lambda m: len(known(df,m)))
    primary = metrics[metric]
    history = weekly_metrics[metric]['history']
    y = np.array([r['value'] for r in history], dtype=float)
    recent = float(y[-3:].mean()) if len(y) else 0
    prior = float(y[-6:-3].mean()) if len(y) >= 6 else 0
    growth = round(100*(recent/prior-1)) if prior else None
    phase = ('Rising' if growth > 12 else 'Declining' if growth < -12 else 'Peaking') if growth is not None else 'Insufficient history'
    windows = []
    if len(y) >= 10 and np.any(y[-4:]):
        cur = y[-4:] / max(y[-4:].mean(), 1)
        # Candidates precede the current window and need at least one observed follow-up week.
        for start in range(len(y)-8):
            end = start+4
            past = y[start:end]
            if not np.any(past): continue
            sim = float(cosine_similarity([cur], [past/max(past.mean(), 1)])[0,0])
            if sim < .97: continue
            follow = y[end:len(y)-4]
            length = next((i for i, v in enumerate(follow) if v < .8*past.max()), len(follow))
            censored = length == len(follow)
            lo, hi = history[start]['date'], history[end-1]['date']
            posts = df[(df.posted_at > pd.Timestamp(lo)-pd.Timedelta(days=7)) & (df.posted_at <= pd.Timestamp(hi)+pd.Timedelta(days=1)-pd.Timedelta(microseconds=1))]
            windows.append({'start': lo, 'end': hi, 'similarity': round(sim, 3), 'weeks_observed_after': length,
                            'censored': censored, 'history': history[start:end],
                            'posts': [{'id': r.id, 'title': r.caption or f'{r.type} {r.id}', 'url': r.url, 'type': r.type} for r in posts.itertuples()]})
    finished = [w['weeks_observed_after'] for w in windows if not w['censored']]
    weeks = max(1, round(float(np.median(finished)))) if finished else None
    return {**primary, 'metrics': metrics, 'weekly_metrics':weekly_metrics, 'phase': phase, 'growth': growth, 'weeks_left': weeks,
            'similar': len(windows), 'similar_windows': windows, 'trend_metric': metric,
            'trend_scope': 'Matching four-week patterns within this profile only. Overlapping windows are not independent trends.',
            'longevity_note': 'Median observed weeks until matching windows dropped below 80% of their peak. Unfinished windows are excluded.' if finished else 'No completed comparable window supports a remaining-duration estimate.'}


def correlation(df):
    cols = [m for m in METRICS if len(known(df,m)) >= 3 and known(df,m)[m].nunique() > 1]
    matrix = {m:{} for m in cols}; pairs=[]; scatter={}; sample_sizes={}
    for a in cols:
        matrix[a][a] = 1.0
    for a,b in combinations(cols,2):
        rows=known(known(df,a),b)
        valid=len(rows)>=3 and rows[a].nunique()>1 and rows[b].nunique()>1
        value=round(float(stats.spearmanr(rows[a],rows[b]).statistic),3) if valid else None
        matrix[a][b]=matrix[b][a]=value
        if value is not None and np.isfinite(value):
            pairs.append({'a':a.capitalize(),'b':b.capitalize(),'v':value,'n':len(rows)})
            scatter[f'{a}|{b}']=[{'x':int(r[a]),'y':int(r[b]),'id':r['id'],'title':r['caption'] or r['type'],'url':r['url']} for _,r in rows.iterrows()]
        sample_sizes[f'{a}|{b}']=len(rows)
    pairs.sort(key=lambda p:-abs(p['v']))
    return {'pairs':pairs,'matrix':matrix,'scatter':scatter,'sample_sizes':sample_sizes,'method':'Spearman rank correlation',
            'notes':'Pairwise observed values only. At least three posts and variation in both metrics are required. Association is not causation.'}


def charts(df):
    out={}
    for m in METRICS:
        rows=known(df,m)
        def periods(freq):
            return [{'label': str(k.start_time.date()) if freq=='W' else str(k), 'value':int(v)} for k,v in rows.groupby(rows.posted_at.dt.to_period(freq))[m].sum().items()]
        out[m]={'month':periods('M'),'week':periods('W'),
                'posts':[{'id':r.id,'title':r.caption or f'{r.type} {r.id}','url':r.url,'type':r.type,'date':r.posted_at.strftime('%Y-%m-%d'),'value':int(getattr(r,m))} for r in rows.itertuples()]}
    out['post_type_share']=[{'type':k,'pct':round(100*v/len(df),1)} for k,v in df.type.value_counts().items()]
    return out


def _text_similarity(texts):
    try:
        vectors=TfidfVectorizer(stop_words='english',max_features=1200).fit_transform(texts)
        return cosine_similarity(vectors)
    except ValueError:
        return np.zeros((len(texts),len(texts)))


def recommend(df):
    captions=_text_similarity(df.caption.fillna('').tolist())
    comments=_text_similarity([' '.join(x) for x in df.comments_sample])
    cols=[m for m in METRICS if len(known(df,m))==len(df) and df[m].nunique()>1]
    if cols:
        values=np.log1p(df[cols].to_numpy(dtype=float))
        values=(values-values.min(axis=0))/(values.max(axis=0)-values.min(axis=0))
        patterns=cosine_similarity(values)
    else: patterns=np.zeros_like(captions)
    comparisons={}
    for i,row in enumerate(df.itertuples()):
        ranked=[]
        for j,other in enumerate(df.itertuples()):
            if i==j: continue
            score=.5*captions[i,j]+.3*comments[i,j]+.2*patterns[i,j]
            ranked.append({'id':other.id,'title':other.caption or f'{other.type} {other.id}','url':other.url,'type':other.type,
                           'score':round(100*float(score),1),'caption_similarity':round(float(captions[i,j]),3),
                           'comment_similarity':round(float(comments[i,j]),3),'metric_similarity':round(float(patterns[i,j]),3)})
        comparisons[str(row.id)]=sorted(ranked,key=lambda r:-r['score'])
    # The score describes similarity, not a success probability or sales relationship.
    engagement_cols=[m for m in ['likes','comments','shares','saves'] if len(known(df,m))==len(df)]
    engagement=df[engagement_cols].sum(axis=1)
    view_rows=known(df,'views')
    use_rate=len(view_rows)==len(df) and (df.views>0).all()
    score=engagement/df.views if use_rate else engagement
    best=int(np.argmax(score.to_numpy()))
    post=df.iloc[best]
    actions=[{'rank':1,'action':f"Build on {post.caption[:70] or post['type']}",
              'why':f"This post has the highest {'observed engagement per view' if use_rate else 'observed engagement count'} in the collected posts ({float(score.iloc[best]):.2f}), using {', '.join(engagement_cols)} available on every post.",
              'post_id':post.id,'url':post.url,'basis':'Collected statistics'}] if engagement_cols else []
    return {'comparisons':comparisons,'actions':actions,'best_type':{},'theme':None,
            'method':'50% caption TF-IDF cosine, 30% sampled-comment TF-IDF cosine, 20% normalized observed metric-pattern cosine. Missing text contributes zero. No sales co-purchase inference.'}
