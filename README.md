# Speculara

Local social media analysis with forecasts, post similarity, charts, correlation, sentiment, demand signals and a Gemma assistant.

## Run

For the demo using the laptop's browser and saved sessions with the existing Netlify site, use the [protected laptop + Netlify launcher](deploy/laptop-netlify.md). It avoids running Instagram collection from Render's network.

For the hosted private MVP, follow the [Render Free backend + Netlify frontend setup](deploy/render-netlify.md). It includes separate operator sign-in and a demo access code. Browser collection is experimental on Free's limited memory; saved sessions are temporary and can disappear on sleep, restart or redeploy. A [single-VPS deployment](deploy/README.md) is also available.

See [backend setup](backend/README.md). Keep the Python API at `http://localhost:8000` and run `npm.cmd run dev` from this directory for the frontend at `http://localhost:8443`.

Gemma keys remain in ignored `backend/.env`. Supabase is optional. Profile collection uses an adapted, MIT-licensed SocialMonitor worker with a local saved browser session. Public collection cannot guarantee private Insights or sales metrics.

## MVP presentation and guide

- [10-slide presentation PDF](outputs/speculara-mvp-20261112/Speculara_MVP_10_Slides.pdf), with slide 10 dedicated to the demo
- [Standalone HTML presentation with notes](outputs/speculara-mvp-20261112/Speculara_MVP_10_Slides.html)
- [Presenter script and reviewer](outputs/speculara-mvp-20261112/Speculara_Presenter_Script_and_Reviewer.pdf)
- [Complete documentation PDF](outputs/speculara-mvp-20261112/Speculara_Documentation.pdf)
- [Important feature-code excerpts](outputs/speculara-mvp-20261112/Speculara_Feature_Code.md)
- [Synthetic CSV/Excel sample files](outputs/speculara-samples-20261112/README.md)
- [Final MVP verification and limits](outputs/speculara-mvp-20261112/MVP-QA.md)

Use **Analyze CSV / Excel data** to demonstrate the supplied 40 fictional posts. Collected profiles request 5-50 recent posts and retain only observed metrics. Source buttons require genuine supplied URLs.

Prediction now defaults to **Per post**, with **Weekly totals** as a separate view. It shows raw held-out error and baseline comparison. See [forecast correction notes](qa/forecast-fix-20261112.md) for the change since the original demo package.

Computed forecasts with poor or undefined percentage backtests remain visible as **exploratory estimates**, with their actual error, warning and uncertainty band. Missing metrics and insufficient histories remain unavailable; no minimum accuracy is invented. Analysis version 9 upgrades saved results from stored posts. See [prediction and hosted-access verification](qa/prediction-access-20261113.md).

## Checks

From the repository root run `npm.cmd run collector:test`, `npm.cmd run test:api`, `npm.cmd run test:analysis`, `npx.cmd tsc --noEmit` and `npm.cmd run build`. From `backend`, run `.venv/Scripts/python.exe -m pytest -q`.

The final headless smoke tests verified small Instagram, Facebook and TikTok collections plus live Gemma chat/strategy. Review the verification record for partial coverage, provider quota behavior and untested production/desktop UI boundaries.
