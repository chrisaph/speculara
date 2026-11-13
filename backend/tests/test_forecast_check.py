import pandas as pd

from app.forecast_check import check_posts


def rows(values):
    return pd.DataFrame({'id': [str(i) for i in range(len(values))],
                         'posted_at': pd.date_range('2025-01-01', periods=len(values)),
                         'likes': values})


def test_twenty_posts_give_ten_checks_and_score_is_hit_rate():
    result = check_posts(rows([100] * 20), 'likes')
    assert result['checks'] == 10
    assert result['hits'] == 10
    assert result['score'] == 100
    assert [o['train_posts'] for o in result['observations']] == list(range(10, 20))


def test_held_out_value_cannot_change_its_own_prediction():
    normal = check_posts(rows([100] * 11), 'likes')
    shock = check_posts(rows([100] * 10 + [10000]), 'likes')
    assert normal['observations'][0]['predicted'] == shock['observations'][0]['predicted'] == 100
    assert shock['score'] == 0


def test_measured_zero_and_missing_evidence():
    assert check_posts(rows([0] * 11), 'likes')['score'] == 100
    result = check_posts(rows([100] * 10), 'likes')
    assert result['score'] is None
    assert result['checks'] == 0
