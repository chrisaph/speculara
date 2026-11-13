# Prediction implementation

The prediction panel retains metric pills, an actual-data line chart with a blue
forecast band, an Accuracy label, documentation, and the lifecycle illustration.
The illustration is labelled; it is not a fabricated account history.

## Data selection

- Missing metrics are excluded, not fitted as zero placeholders.
- Weekly posting totals omit weeks without collected posts.
- At least four observed weeks enable a calendar forecast. Shorter date ranges
  fall back to post-sequence forecasts. Selection never chooses the higher score.
- Complete CSV uploads with 14–365 consecutive daily dates can use daily
  posting-total forecasts. Every row must supply the selected metric.
- Historical-fit accuracy is `clip(round(100 * (1 - training MAPE)), 0, 97)`.
  It is not a measured future success probability and has no 50% floor.
- Approximate residual bands are not calibrated confidence probabilities.
- Snapshot counts have different post ages. Fixed-age performance needs repeated
  observations at a consistent age after publication.

## Linked repository review

Reviewed https://github.com/mtfugin/Speculara, particularly
`backend/forecasting.py`, its tests, the collector and Instagram payload adapter.
The daily adapter in `app/observed_prediction.py` follows its baseline-comparison
approach: fit linear and last-value baselines without the last three dates,
compare MAE on those dates, select a baseline, then refit on all dates. This is a
small selection holdout, not independent validation. The separate next-post
checks remain in the backend response and do not replace historical-fit accuracy.

The current Playwright adapter already preserves additional supplied view, share
and save fields and keeps metrics from earlier responses when later responses
omit them. It was retained instead of replacing it with the linked, narrower
adapter. Collector fixture tests pass; no new live social collection was performed
as part of this change. Public pages may still omit private metrics.

## Verification data

The exported 20-post dataset reproduces 53% weekly historical fit for likes and
81% for comments. Views remain unavailable. Other datasets can score below 50%.
`../demo/speculara-sample-20-posts.csv` is explicitly synthetic, contains all six
metrics, and exercises the daily upload path. It does not establish live accuracy.


## Chart ranges and background public metrics

Count-space empirical absolute errors replace exponentiated log residual bands.
For post forecasts, rolling next-post errors are used when available; other
series use fitting residuals. The range widens with the square root of horizon.
It is approximate, not a calibrated coverage probability. The chart keeps every
range value and automatically labels a log scale when uncertainty exceeds the
central data scale by more than four times. Exact values remain available.

Short date ranges can show post-sequence phase and pattern evidence separately
from weekly phase. Durations are shown in posts for that basis, never relabelled
as weeks. A duration requires a completed comparable pattern; there is no invented
four-week fallback.

Instagram live analyses automatically start a bounded background pass over up to
20 already-collected public post pages. The Playwright worker reads matching
post JSON, preserves zero as a measured value, and fills only unavailable fields.
Existing measured/imported values are not overwritten. Sales are never inferred.
Jobs use opaque IDs, are deduplicated, and are bounded to one running browser and
20 recent jobs; completed jobs expire from the cache after ten minutes on the
next job start. The UI polls for completion and refreshes all analysis panels.
Retry is explicit. Browser login/challenge failures leave current results intact.

SerpApi's documented Instagram Profile response lists profile and post metadata,
not the required private metric counts: https://serpapi.com/instagram-profile-api.
No paid third-party requests were added. Unsupported/private counts remain
unavailable and can be supplied through the existing Insights/sales upload.
Worker, parser and HTTP job tests use fixtures; successful live extraction still
depends on the actual public page and saved session.
