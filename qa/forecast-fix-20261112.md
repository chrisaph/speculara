# Forecast correction - 12 November 2026

This update follows the original MVP package at commit `22c04ed`. The PDFs/ZIP in `outputs/speculara-mvp-20261112` describe that earlier implementation; the current forecast changes are documented here and in `backend/README.md`.

## Problem

A recent-post sample was resampled into weekly sums and calendar gaps became zeros. This measures the posting schedule of the collected sample as well as post performance. One-step training validation also chose models for a different task than the final multi-step holdout. The prominently displayed derived score hid all errors at or above 100% behind the same 0% label.

## Changes

- Default to a forecast of the next **posts**, preserving one observed metric per dated collected post. Do not insert artificial zero posts for empty weeks. Future values are labeled `Next post 1`, etc., without invented publication dates.
- Retain **Weekly totals** as an explicit separate view, with the sparse-coverage warning. Trend longevity continues to use weekly history rather than silently changing to post units.
- Select candidates using rolling **multi-step** folds within training data, matching the final holdout horizon. Compare simple recent-mean, median, full-training mean and last-value baselines, with damped smoothing eligible when the training folds are long enough.
- Keep the final holdout out of model selection. Display raw WAPE and the recent-average baseline on the same holdout. A poor result remains poor; no positive minimum score is imposed.
- Bump analysis version to 7 to invalidate old caches/recompute saved analyses when stored posts exist. Reload the frontend and run the analysis again to replace a result already held in browser memory.
- Preserve the established neumorphic components, post/comment evidence and other analysis features.

## Verification

- Final automated checks: 124 backend tests and 17 panel tests passed, along with TypeScript and the production build. The restarted live API returned analysis version 7 with per-post default/weekly alternative on the same 20 observed posts.
- Regression cases cover irregular posting gaps, multiple posts in one week, measured zero values, future dates, training-only multi-step model selection and genuinely poor holdouts.
- Stable per-post counts across irregular dates retain 12 real observations and a 100% derived holdout score, without calendar-gap zeros.
- A real 20-post MrBeast sample was compared on identical inputs. Comments changed from a zero weekly derived score to a 30% per-post score (70.3% WAPE). Likes remained poor at 130.0% WAPE. These results are disclosed rather than inflated.
- The frontend shows post versus week units, held-out post dates and baseline error, and prominently reports raw error with a low-reliability warning where appropriate.

## Remaining limits

Collected counts are snapshots. Older posts have had more time to gain engagement, and a sample of recent posts is not complete account history. Per-post estimates still do not represent performance at a fixed exposure age. Virality, distribution shifts and small holdouts can make any chosen model unreliable. The method change does not promise improved error for every account or metric.
