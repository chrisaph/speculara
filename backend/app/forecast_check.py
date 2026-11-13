"""One-step checks on recorded post counts, using earlier posts only."""
import numpy as np
import pandas as pd

from .prediction_fit import fit_weekly


def post_series(values):
    # Equally spaced sequence positions: future publication dates are unknown.
    return pd.Series(np.asarray(values, dtype=float),
                     index=pd.date_range('2000-01-02', periods=len(values), freq='W'))


def check_posts(rows, metric, tolerance=0.30):
    values = rows[metric].to_numpy(dtype=float)
    series = post_series(values)
    observations = []
    for i in range(max(10, len(values) - 10), len(values)):
        # Selection, preprocessing and fitting see only this training prefix.
        model = fit_weekly(series.iloc[:i], 1)
        predicted = max(0, round(float(model['values'][0])))
        actual = int(values[i])
        baseline = max(0, round(float(np.mean(values[max(0, i - 4):i]))))
        allowed_error = tolerance * max(actual, 1)
        observations.append({
            'post_id': str(rows.iloc[i]['id']),
            'date': rows.iloc[i]['posted_at'].strftime('%Y-%m-%d'),
            'train_posts': i, 'actual': actual, 'predicted': predicted,
            'within_tolerance': abs(actual - predicted) <= allowed_error,
            'baseline_predicted': baseline,
            'baseline_within_tolerance': abs(actual - baseline) <= allowed_error,
            'model': model['model'],
        })
    count = len(observations)
    hits = sum(o['within_tolerance'] for o in observations)
    baseline_hits = sum(o['baseline_within_tolerance'] for o in observations)
    return {'score': round(100 * hits / count) if count else None,
            'checks': count, 'hits': hits, 'tolerance_pct': round(100 * tolerance),
            'baseline_score': round(100 * baseline_hits / count) if count else None,
            'baseline_hits': baseline_hits, 'observations': observations,
            'basis': 'post', 'evidence': 'Limited evidence',
            'scope': 'Recorded snapshot counts; posts may have different ages. Not a fixed-age performance test.',
            'reason': '' if count else 'At least 11 posts with this metric are needed for an automatic check.'}
