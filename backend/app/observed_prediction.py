"""Observed-data forecasts with historical fit and separate forecast checks."""
import numpy as np
import pandas as pd

from .forecast_check import check_posts, post_series
from .prediction_fit import fit_weekly

METRICS = ['views', 'likes', 'comments', 'shares', 'saves', 'sales']


def _points(series, groups):
    return [{'date': date.strftime('%Y-%m-%d'), 'value': int(value),
             'post_count': len(groups.loc[date]), 'post_ids': groups.loc[date]}
            for date, value in series.items()]


def _result(series, history, horizon=8, basis='week', fitted=None):
    result = {'history': history, 'forecast': [], 'accuracy': None, 'basis': basis,
              'score_basis': 'fitted_history', 'forecast_supported': False,
              'reason': 'At least four observed periods are needed for a forecast.'}
    if len(series) < 4:
        return result
    fit = fitted if fitted is not None else fit_weekly(series, horizon)
    values, predicted = series.to_numpy(dtype=float), fit['fitted']
    # Use count-space errors. Exponentiating a widening log residual produced
    # enormous bands that overwhelmed otherwise ordinary forecasts.
    absolute_errors = np.abs(values - predicted)
    error = float(np.mean(np.abs(values - predicted) / np.maximum(values, 1)))
    result.update(accuracy=int(np.clip(round(100 * (1 - error)), 0, 97)),
                  training_mape=error, model=fit['model'], fit_observations=len(values),
                  reason='', forecast_supported=True)
    if 'validation' in fit:
        result['validation'] = fit['validation']
    for i, value in enumerate(fit['values'], 1):
        band = float(np.quantile(absolute_errors, .9)) * np.sqrt(i)
        date = f'Next post {i}' if basis == 'post' else (
            series.index[-1] + pd.Timedelta(days=i if basis == 'day' else i * 7)
        ).strftime('%Y-%m-%d')
        result['forecast'].append({'date': date, 'value': max(0, round(float(value))),
            'low': max(0, round(float(value - band))),
            'high': max(0, round(float(value + band)))})
    result['range_basis'] = 'Training absolute-error spread; approximate, not a calibrated probability.'
    return result


def _linear(y, positions):
    if np.all(y == y[0]):
        return np.repeat(y[0], len(positions))
    slope, intercept = np.polyfit(np.arange(len(y)), y, 1)
    return np.maximum(0, intercept + slope * positions)


def _daily_upload(rows, metric):
    """Baseline comparison for complete daily uploads, not sparse scraped feeds.

    Inspired by mtfugin/Speculara backend/forecasting.py. The last three dates
    are excluded from candidate fitting. The winning baseline is refit on all
    dates; that holdout is a small model-selection sample, not an unbiased test.
    """
    if 'metric_sources' not in rows or not rows.metric_sources.map(lambda source: source.get(metric) == 'Uploaded file').all():
        return None
    grouped = rows.set_index('posted_at').groupby(lambda date: date.normalize())
    series = grouped[metric].sum(min_count=1).sort_index()
    if not 14 <= len(series) <= 365 or not series.index.equals(
            pd.date_range(series.index[0], periods=len(series), freq='D')):
        return None
    y = series.to_numpy(dtype=float)
    train, test = y[:-3], y[-3:]
    candidates = {'linear': _linear(train, np.arange(len(train), len(y))),
                  'last_value': np.repeat(train[-1], 3)}
    errors = {name: float(np.mean(np.abs(test - values))) for name, values in candidates.items()}
    method = 'linear' if errors['linear'] < errors['last_value'] else 'last_value'
    fitted = _linear(y, np.arange(len(y))) if method == 'linear' else np.r_[y[0], y[:-1]]
    future = _linear(y, np.arange(len(y), len(y) + 7)) if method == 'linear' else np.repeat(y[-1], 7)
    fit = {'fitted': fitted, 'values': future,
           'model': 'Daily linear trend' if method == 'linear' else 'Daily last-value baseline',
           'validation': {'method': 'Three-date baseline selection by MAE', 'scores': errors,
                          'holdout_dates': [d.strftime('%Y-%m-%d') for d in series.index[-3:]],
                          'train_days': len(train), 'selected_model': method,
                          'scope': 'Small selection holdout; not an independent performance test.'}}
    ids = grouped['id'].agg(lambda values: [str(v) for v in values])
    return _result(series, _points(series, ids), basis='day', fitted=fit)


def _trend(history, rows=None):
    y = np.asarray([p['value'] for p in history], dtype=float)
    result = {'phase': 'Insufficient weekly history', 'growth': None,
              'weeks_left': None, 'similar': 0, 'similar_windows': []}
    if len(y) >= 6 and y[-6:-3].mean() > 0:
        ratio = float(y[-3:].mean() / y[-6:-3].mean())
        result.update(growth=round(100 * (ratio - 1)),
                      phase='Rising' if ratio > 1.12 else 'Declining' if ratio < .88 else 'Peaking')
    if len(y) < 10 or not np.any(y[-4:]):
        return result
    lengths = []
    by_id = {str(r['id']): r for r in rows.to_dict('records')} if rows is not None else {}
    for start in range(len(y) - 8):
        past = y[start:start + 4]
        denominator = np.linalg.norm(past) * np.linalg.norm(y[-4:])
        similarity = float(np.dot(past, y[-4:]) / denominator) if denominator else 0
        if similarity < .97:
            continue
        follow = y[start + 4:len(y) - 4]
        duration = next((i for i, v in enumerate(follow) if v < .8 * past.max()), len(follow))
        censored = duration == len(follow)
        if not censored:
            lengths.append(duration)
        result['similar_windows'].append({'start': history[start]['date'],
            'end': history[start + 3]['date'], 'similarity': round(similarity, 3),
            'weeks_observed_after': duration, 'censored': censored,
            'history': history[start:start + 4],
            'posts': [{'id': pid, 'title': by_id[pid].get('caption') or by_id[pid].get('type', 'Post'),
                       'url': by_id[pid].get('url', ''), 'type': by_id[pid].get('type', 'Post')}
                      for pid in dict.fromkeys(pid for point in history[start:start + 4]
                          for pid in (point.get('post_ids') or [point.get('post_id')])) if pid in by_id]})
    result['similar'] = len(result['similar_windows'])
    result['weeks_left'] = max(1, round(float(np.median(lengths)))) if lengths else None
    return result


def predict(df, horizon_weeks=8):
    metrics, weekly_metrics, daily_metrics, post_trends = {}, {}, {}, {}
    for metric in METRICS:
        rows = df[~df.unavailable_metrics.map(lambda missing: metric in missing)].sort_values('posted_at', kind='stable')
        common = {'metric': metric, 'total_posts': len(df), 'known_posts': len(rows),
                  'score_basis': 'fitted_history', 'coverage': f'{len(rows)} of {len(df)} posts have this metric.'}
        if rows.empty:
            missing = {**common, 'history': [], 'forecast': [], 'accuracy': None,
                       'forecast_supported': False, 'reason': f'No observed {metric} values were supplied.'}
            metrics[metric], weekly_metrics[metric] = {**missing, 'basis': 'post'}, {**missing, 'basis': 'week'}
            continue
        grouped = rows.set_index('posted_at').resample('W')
        series = grouped[metric].sum(min_count=1).dropna()
        ids = grouped['id'].agg(lambda values: [str(v) for v in values])
        history = _points(series, ids)
        weekly = _result(series, history, horizon_weeks)
        if not weekly['forecast_supported']:
            weekly['reason'] = f'Only {len(series)} observed weeks are available; a weekly forecast needs at least four.'
        weekly_metrics[metric] = {**weekly, **common, **_trend(history, rows)}
        history = [{'date': row.posted_at.strftime('%Y-%m-%d'), 'value': int(getattr(row, metric)),
                    'post_id': str(row.id)} for row in rows.itertuples()]
        post_trend = _trend(history, rows)
        post_trend['posts_left'] = post_trend.pop('weeks_left')
        post_trend['basis'] = 'post'
        post_trends[metric] = post_trend
        metrics[metric] = {**_result(post_series(rows[metric]), history, horizon_weeks, 'post'),
                           **common, 'forecast_check': check_posts(rows, metric)}
        checks = metrics[metric]['forecast_check']['observations']
        if checks:
            actual_total = sum(p['actual'] for p in checks)
            absolute_error = sum(abs(p['actual'] - p['predicted']) for p in checks)
            metrics[metric]['validation'] = {
                'method': 'Expanding-prefix next-post checks; no future posts used in fitting',
                'score_basis': 'rolling_next_post', 'train_observations': len(rows) - len(checks),
                'test_posts': len(checks), 'weighted_error_pct': 100 * absolute_error / actual_total if actual_total else None,
                'observations': checks}
            radius = float(np.quantile([abs(p['actual'] - p['predicted']) for p in checks], .9))
            for i, point in enumerate(metrics[metric]['forecast'], 1):
                band = radius * np.sqrt(i)
                point.update(low=max(0, round(point['value'] - band)), high=round(point['value'] + band))
            metrics[metric]['range_basis'] = 'Rolling next-post absolute-error spread; approximate, not a calibrated probability.'
        daily = _daily_upload(rows, metric) if len(rows) == len(df) else None
        if daily:
            daily_metrics[metric] = {**daily, **common}
    primary_metric = next((m for m in ['views', 'likes', 'comments', 'shares', 'saves', 'sales'] if metrics[m]['history']), 'views')
    primary = daily_metrics.get(primary_metric) or (weekly_metrics[primary_metric]
        if weekly_metrics[primary_metric]['forecast'] else metrics[primary_metric])
    return {'phase': 'Insufficient weekly history', 'growth': None, 'weeks_left': None, 'similar': 0,
            **primary, **{k: v for k, v in weekly_metrics[primary_metric].items() if k in ('phase', 'growth', 'weeks_left', 'similar', 'similar_windows')}, 'trend_metric': primary_metric,
            'metrics': metrics, 'weekly_metrics': weekly_metrics, 'daily_metrics': daily_metrics, 'post_trends': post_trends}
