"""Small candidate family for fitted-history weekly forecasts.

Selection uses training MAPE, not a held-out forecast score. Trend complexity is
limited to two coefficients with six weeks, three with eight weeks.
"""
import numpy as np
from scipy.optimize import least_squares
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def fit_weekly(weekly, horizon):
    y = weekly.to_numpy(dtype=float)
    denominator = np.maximum(y, 1.0)
    if np.all(y == y[0]):
        return {"model": "Constant observed history", "training_mape": 0.0,
                "fitted": y.copy(), "values": np.repeat(y[0], horizon),
                "selection": "All observed weekly values are identical.",
                "fit_observations": len(y)}
    candidates = []

    def add(name, fitted, values):
        fitted, values = np.maximum(0, fitted), np.maximum(0, values)
        if np.isfinite(fitted).all() and np.isfinite(values).all():
            error = float(np.mean(np.abs(y - fitted) / denominator))
            candidates.append((error, name, fitted, values))

    # Scaling makes the optimizer independent of the size of engagement counts.
    scale = max(float(y.max()), 1.0)
    for trend in (None, "add"):
        try:
            model = ExponentialSmoothing(y / scale, trend=trend,
                                         damped_trend=trend is not None).fit()
            if model.mle_retvals and not model.mle_retvals.get("success", True):
                continue
            add("Damped exponential smoothing" if trend else "Level exponential smoothing",
                np.asarray(model.fittedvalues) * scale,
                np.asarray(model.forecast(horizon)) * scale)
        except (ValueError, ArithmeticError):
            continue

    # Use real calendar distances even when a week has no collected posts.
    elapsed = (weekly.index - weekly.index[0]).days.to_numpy(dtype=float) / 7
    span = max(float(elapsed[-1]), 1.0)
    t = elapsed / span
    upper = float(np.log1p(y.max()) + 5)
    for degree, minimum in ((1, 6), (2, 8)):
        if len(y) < minimum:
            continue
        design = np.vander(t, degree + 1, increasing=True)
        initial = np.linalg.lstsq(design, np.log1p(y), rcond=None)[0]

        def decode(z):
            return np.expm1(np.clip(z, -20, upper))

        def residual(coefficients):
            return (decode(design @ coefficients) - y) / denominator

        result = least_squares(residual, initial, loss="soft_l1", max_nfev=2000)
        if not result.success:
            continue
        coefficients = result.x
        fitted = decode(design @ coefficients)
        # A global curve's endpoint can sit far below the latest observation.
        # Forecast from the actual latest level and a robust recent calendar
        # slope instead of extending that curve's steep endpoint derivative.
        recent_t, recent_log = elapsed[-4:], np.log1p(y[-4:])
        slopes = [(recent_log[j] - recent_log[i]) / (recent_t[j] - recent_t[i])
                  for i in range(len(recent_t)) for j in range(i + 1, len(recent_t))]
        slope = float(np.median(slopes))
        steps = np.arange(1, horizon + 1)
        offsets = np.cumsum(0.8 ** steps)
        values = decode(np.log1p(y[-1]) + slope * offsets)
        add(f"Robust log {'linear' if degree == 1 else 'quadratic'} fit; recent damped forecast",
            fitted, values)

    # A finite baseline also covers genuine all-zero observed histories.
    add("Historical median", np.repeat(np.median(y), len(y)),
        np.repeat(np.median(y), horizon))
    error, name, fitted, values = min(candidates, key=lambda c: c[0])
    return {"model": name, "training_mape": error, "fitted": fitted, "values": values,
            "selection": "Lowest training MAPE among level/damped smoothing, eligible robust log trends and median.",
            "fit_observations": len(y)}
