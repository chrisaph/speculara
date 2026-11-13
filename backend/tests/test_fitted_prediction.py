import numpy as np
import pandas as pd

from app.analytics import predict
from app.observed_prediction import _daily_upload


def frame(values, missing=False):
    return pd.DataFrame({
        'id': [str(i) for i in range(len(values))],
        'posted_at': pd.date_range('2025-01-05', periods=len(values), freq='W'),
        'views': values, 'likes': values, 'comments': values,
        'shares': values, 'saves': values, 'sales': values,
        'engagement': values,
        'metric_sources': [{} for _ in values],
        'unavailable_metrics': [['views'] if missing else [] for _ in values],
    })


def test_unavailable_views_do_not_receive_a_placeholder_score():
    result = predict(frame([0] * 20, missing=True))
    assert result['metrics']['views']['accuracy'] is None
    assert result['metrics']['views']['forecast'] == []
    assert result['trend_metric'] == 'likes'


def test_empty_weeks_are_excluded_and_totals_reconcile():
    df = frame([0, 100, 200, 150, 120, 80, 40, 20])
    df['posted_at'] = pd.date_range('2025-01-05', periods=8, freq='2W')
    result = predict(df)['weekly_metrics']['likes']
    assert len(result['history']) == 8
    assert sum(p['post_count'] for p in result['history']) == 8
    assert sum(p['value'] for p in result['history']) == 710
    assert result['accuracy'] == int(np.clip(round(100 * (1 - result['training_mape'])), 0, 97))
    assert len(result['forecast']) == 8


def test_twenty_posts_in_three_weeks_still_get_ten_post_checks():
    df = frame([100] * 20)
    df['posted_at'] = pd.date_range('2026-11-02', periods=20, freq='20h')
    result = predict(df)
    assert result['basis'] == 'post'
    assert result['metrics']['likes']['forecast_check']['checks'] == 10
    assert len(result['weekly_metrics']['likes']['history']) == 3
    assert result['growth'] is None
    assert result['weeks_left'] is None
    assert result['post_trends']['likes']['phase'] == 'Peaking'
    assert result['post_trends']['likes']['basis'] == 'post'


def test_uncertainty_stays_in_count_units_instead_of_exponentially_exploding():
    result = predict(frame([10, 10000, 20, 30000, 40, 20000, 100, 5000]))
    metric = result['metrics']['likes']
    maximum = max(p['value'] for p in metric['history'])
    assert max(p['high'] for p in metric['forecast']) < maximum * 20
    assert all(0 <= p['low'] <= p['value'] <= p['high'] for p in metric['forecast'])
    assert 'absolute-error' in metric['range_basis']


def daily(values):
    df = frame(values)
    df['posted_at'] = pd.date_range('2026-01-01', periods=len(values), freq='D')
    df['metric_sources'] = [{'likes': 'Uploaded file'} for _ in values]
    return df


def test_daily_csv_baseline_selection_and_refit():
    result = _daily_upload(daily(list(range(1, 15))), 'likes')
    assert result['basis'] == 'day'
    assert result['validation']['selected_model'] == 'linear'
    assert result['validation']['train_days'] == 11
    assert result['validation']['scores']['linear'] < 1e-10
    assert [p['value'] for p in result['forecast']] == list(range(15, 22))
    assert result['accuracy'] == 97


def test_daily_holdout_does_not_leak_into_baseline_fit():
    result = _daily_upload(daily([10] * 11 + [0] * 3), 'likes')
    assert result['validation']['scores']['linear'] > 9.99
    assert result['validation']['scores']['last_value'] == 10


def test_sparse_or_incomplete_upload_is_not_a_daily_series():
    df = daily(list(range(14))).drop(index=5)
    assert _daily_upload(df, 'likes') is None
    df = daily(list(range(14)))
    df['metric_sources'] = [{}] * 14
    assert _daily_upload(df, 'likes') is None
