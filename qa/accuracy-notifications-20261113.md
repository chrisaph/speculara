# Accuracy presentation and collection completion — 2026-11-13

## Historical check

- `21e8557` displayed `Accuracy: {f.acc}%`, but its `facts` helper could fall back to `mockFacts`. That fallback returned 88 for sample seeds or a seeded random 84–91 score for other seeds. This cannot establish real Instagram forecast accuracy.
- `09b3f55` rendered `Held-out accuracy: {data.accuracy}%` from Python's observed-data forecast. Its Python calculation was `round(max(0, 100 * (1 - absolute_error / actual_total)))`, with the final observations excluded from fitting.
- `cf2f0319854a666c1b2d1b770d436ae70c86d961` retained the held-out calculation and error evidence. Later work changed sampling and model selection; this UI update does not restore old zero-filled weekly sampling or modify the current model.

Commit source proves how scores were calculated/displayed, not a specific historical Instagram result. No archived live profile payload was used to claim a positive score. A 465.3% error still produces a genuine 0% score; the UI does not fabricate a better value.

## Final behavior

The main forecast label is `Accuracy: X%`, taking the finite 0–100 value directly from Python. Missing/invalid scores stay unavailable. A short caption identifies it as a historical held-out score, not a future success probability. Low reliability is noted briefly. Raw error, holdout dates, model, baseline, actual/predicted table and score formula are inside closed-by-default **Backtest details and evidence**. Model limits remain available separately.

Older cached results containing the retired withholding message ask the user to analyze again instead of displaying contradictory forecast messaging. Current exploratory estimates retain their real warnings in the details; no forecast values are invented by the UI.

All successful collection/sample/upload responses use the shared completion handler. It counts returned posts, not the entire account's total. A small neumorphic popup prompts the user to scroll up/choose a question and expires after six seconds, with an optional dismiss button. A separate permanent notice sits above **Scroll and choose** and remains while changing analyses. It updates only when a new successful dataset replaces the active analysis. Failed collection keeps the previous dataset and does not show success. Timers are cleaned up on replacement/unmount.

## Verification

Panel tests cover Python scores of 0, 57 and 100, unavailable scores, collapsed raw evidence and stale-result messaging. A real headless Chrome test with a synthetic Python-generated analysis verifies successful notification, placement above the heading, sticky-header visibility, choice switching, six-second expiry, manual dismissal, failed-request behavior and mobile horizontal overflow. This test does not claim live Instagram access. Temporary screenshots are kept in ignored `.tmp-ui-ready` for visual inspection. No desktop interaction or user credentials are used by the test.
