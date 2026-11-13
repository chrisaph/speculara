# Forecast history audit and numerical fix

Reviewed all reachable prediction history on local/remote main and staging after fetching origin. Changes are confined to staging. No UI source, scoring definition or holdout selection was changed.

## Same-data replay

An existing archived SocialMonitor analysis contains 20 observed MrBeast posts with likes/comments and unavailable views. It is analysis version 6, not a newly collected snapshot. Every distinct historical `insights.py` version was executed against the same restored posts with an as-of date of 2026-11-13 where supported. The original predictor in `21e8557` was also replayed. Aggregate output and the input hash are in [the machine-readable report](forecast-history-review-20261113.json); raw posts, comments and local credentials are not included.

| Version | Basis | Likes score | Comments score | Relevant behavior |
|---|---|---:|---:|---|
| `21e8557` | Weekly views only | Not independently scored | Not independently scored | Returned 97 for unavailable views represented as zeros; fitted-training error and 40–97 clipping |
| `09b3f55` | Weekly | 0 | 0 | Actual metric-specific holdout scoring |
| `cf2f031` | Completed weeks | 0 | 0 | Training-only model selection and excluded incomplete weeks |
| `ed28ea9` | Per post | 0 | 30 | Matching multi-step training folds and no artificial zero posts for publication gaps |
| `0cc6b7b` | Per post | 0 | 30 | Hid the poor likes forecast |
| `a97d419` | Per post | 0 | 30 | Restored explicitly exploratory projections |
| Numerical fix | Per post | 0 | 30 | Same genuine archive scores; stable smoothing for large count units |

Weekly and per-post models have different targets, so their scores are not interchangeable. The old 97% was not evidence of a flawless likes forecast. The earliest UI additionally had a seeded 84–91% fallback when live facts were missing. Neither behavior was restored.

## Confirmed bug and fix

The current exponential-smoothing optimizer received raw counts. For an identical spiky series, merely multiplying all counts by a million changed the relative four-step forecast from approximately `[15.94, 15.95, 15.95, 15.96]` to `[8.71, 7.20, 5.71, 4.24]` after dividing the result back by a million. Its maximum relative discrepancy was 73.4%, even though the fit reported success.

The model now fits dimensionless counts using a scale obtained from that fit's training data, then restores the original count units. Forecast shape is invariant to the count-unit multiplier in the regression fixture. This is numerical conditioning, not altered accuracy scoring. Held-out observations remain excluded from model selection. Missing metrics, zero-denominator rules, model selection and 0–100 scoring remain intact.

Analysis version is now 10 so stored analyses can be recomputed from their preserved posts. An already-running Python backend needs a restart to load the new code. No active collector/browser session was interrupted as part of this audit.

## Validation and limits

The new count-unit invariance test failed on the original code and passed after the fix. A second regression verifies predictions return in original count units. All 155 backend tests passed. Existing AIC/log-of-zero warnings on degenerate fixtures remain; the forecast selection does not use those AIC values. The archived likes holdout still legitimately scores 0%; this patch makes no claim of improved performance on that snapshot or future posts. No interface files changed.
