# Speculara MVP documentation

## Scope

Speculara is a local social media analysis application for marketing teams. It combines six numerical/text analysis views with a Gemma assistant and a strategy generator. This guide documents the current staging implementation and a reproducible demonstration route as of 12 November 2026.

## Demo decision

Use the bundled synthetic CSV/Excel file as the primary demo dataset. Live connectors are supplementary. Facebook returned five dated posts from the supplied page after the parser fix. This does not guarantee every profile or comment is accessible. Gemma is an external dependency with variable latency and quota. Optional Supabase persistence is not configured in this local environment.

## What is in this package

A 10-slide PDF and standalone HTML presentation, speaker script, presentation reviewer, this user/technical guide, sample CSV and Excel, and a verification log. Slide 10 is the demonstration. Existing historical presentation PDFs are not the current demo deck.

## How to read the sources

Source IDs S1-S21 refer to the reference pages at the end. Repository links point to staging. Function names in the code guide locate the implementation. Library documentation explains a method, while Speculara source defines the application behavior.

# User guide: start locally

## Prerequisites

Use the existing Python 3.12 virtual environment, Node.js 24 and npm, and installed Chrome or Playwright Chromium. Run the backend under your normal Windows account so a manually requested sign-in window can appear. Keep both terminals running.

## Backend terminal

From speculara/backend, activate or call .venv/Scripts/python.exe directly. Install requirements.txt if this is a new setup. Put GEMMA_API_KEY in the ignored backend/.env, with optional GEMMA_MODEL=gemma-4-31b-it. Start: .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000. A restart is needed after Python code changes when reload is disabled.

## Frontend terminal

From speculara, run npm.cmd install once, then npm.cmd run dev. For Bash, export VITE_API_URL="http://localhost:8000" before starting Vite. Open http://localhost:8443. The API base defaults to localhost:8000.

## Health check

Open http://localhost:8000/api/health. ok=true means the route responds. llm=true means a key is configured, not that a live generation has succeeded. database=false is acceptable for a local demo and means saved history is unavailable. Confirm Gemma through a real chat/strategy request.

## Browser dependencies

From speculara run npm.cmd run collector:setup and, if no compatible browser is installed, npm.cmd run collector:browser. Do not paste keys into frontend code, commit .env, or share your saved browser profile.

# User guide: load and collect

## Reliable demo route

Choose Analyze CSV / Excel data, then select Speculara_Synthetic_Sample.csv or .xlsx from outputs/speculara-samples-20261112. Both contain the same 40 posts. They are fictional data for product demonstration and must not be described as a real brand analysis.

## Built-in sample

Try with sample data loads a deterministic demo dataset. Use this when you want a quick fallback. Loading an uploaded dataset or collecting a profile replaces the active analysis, so previously shown sample results should not remain mixed with the new result.

## Profile collection

Paste an Instagram, Facebook or TikTok profile URL, choose a maximum of 5, 10, 20, 30, 40 or 50 latest posts and click Analyze. At least five valid dated posts are needed. Platforms can return fewer posts than requested. Larger requests take longer. This is a recent sample, not a guaranteed complete history.

## Saved sessions

Instagram comment text and Facebook require a saved sign-in session. Select the network and choose Sign in for comments. Sign in manually in the separate window, then choose Done signing in. Only one login or collection can own the saved profile at a time. TikTok uses the logged-out collector.

## Known Facebook limitation

The updated parser reads initial embedded Relay data and later GraphQL payloads. The supplied Facebook page returned five dated posts with likes, comment counts, shares and real post links. Other pages can still fail. Zero collected posts is a connector coverage result, not evidence that the page has no posts. File import remains the stable demo route. No password entry, security-check solving or desktop actions are part of automated verification.

# User guide: files and provenance

## Standalone dataset

Include posted_at (or date/timestamp). Recommended columns are id, type, caption, url, views, likes, comments, shares, saves, sales and comments_sample. Separate comment samples with a vertical bar. Dates should be unambiguous ISO dates, numeric counts should be whole non-negative numbers, and a row represents one post. Use at least five valid rows. Maximum file size is 10 MB.

## Add private metrics to collected posts

In an active analysis use the metrics import control. Supply CSV or XLSX with id or url and one or more metric columns. Rows must identify posts already in the analysis. If both ID and URL are supplied, they must agree. Duplicate posts, negative/fractional counts and formulas are rejected. The app recomputes the views after a successful merge.

## Unknown is different from zero

The internal Post model uses numeric placeholders together with unavailable_metrics. Analysis excludes unavailable values for that metric. The interface displays Not supplied for completely missing metrics, and shows coverage for partially observed values. A measured zero remains valid data.

## Private metrics

Instagram may expose likes/comments and sometimes play counts. Public collection cannot guarantee views, saves or shares, and it does not provide sales. Supply your own Insights/export or sales counts to fill these gaps. TikTok can expose play/share/collect counts. The collector only preserves fields actually returned.

## Sample file safety

The supplied file labels captions as SYNTHETIC SAMPLE and data_origin=synthetic. URLs are blank to avoid fake sources. The sample IDs match built-in sample rows so a sample metrics-merge demonstration is possible. Never attach these fictional numbers to a real profile.

# User guide: charts and correlation

## Charts

Choose Charts and a metric. Review period totals, per-post values, title labels/tooltips and share comparisons. Counts use only observed values. Weekly/monthly groups use the post publication date. They represent current supplied lifetime counts grouped by posting date, not daily activity captured at that time.

## Correlation

Choose Correlation, inspect the relationship list, signed matrix and scatter plot. The selectable pair controls the scatter axes. Strong/negative filters describe calculated coefficients. At least three pairwise observed posts and variation in both metrics are needed.

## Interpretation

Spearman correlation ranges from -1 to +1 and measures rank association. A positive value means the two metrics tend to increase together in this sample. It does not demonstrate that one metric caused another. Small samples, selection effects and incomplete platform coverage can distort the result.

## Sources

Post titles and source buttons resolve supplied evidence URLs. A direct comment link is preferred when the collector provides one, otherwise a comment points to its parent post and labels that relationship. Missing URLs should not become fabricated links. Synthetic file rows have no real social source.

## Implementation

S3: charts() groups known rows and returns per-post values. correlation() applies known() for each pair, calls scipy.stats.spearmanr and returns sample sizes plus scatter evidence. S12 documents the underlying method.

# User guide: forecasts and trends

## Metric forecast

Open Prediction and choose an available metric. The backend aggregates observed rows into completed weeks, requires at least six completed weekly observations with a non-zero total, and compares last-week, recent-average and damped exponential-smoothing candidates. Sparse/unknown history produces a reason instead of a fabricated forecast.

## Validation score

Candidate selection uses rolling validation within training weeks only. A separate final holdout of two to four weeks calculates weighted absolute percentage error (WAPE). Displayed score = max(0, 100 - WAPE). The score measures the particular backtest, not a future guarantee or a universal model accuracy.

## Why a score can be zero

If weighted prediction error reaches or exceeds 100%, the floored score is zero. Review the actual-versus-predicted holdout observations and date range. Spiky posting schedules and few weeks can make forecasts weak. A numerical smoothing failure falls back to a simple baseline rather than making up a result.

## Uncertainty

The band uses 1.64 times holdout root-mean-square error times the square root of the forecast step. It is an approximate error band, not a calibrated probability guarantee. Counts grouped by post publication week can also change when old posts accumulate engagement.

## Trend longevity

The app compares normalized four-week patterns within this profile, keeps cosine matches at or above 0.97, and observes when earlier patterns drop below 80% of their peak. It takes the median duration of completed comparable windows. Overlapping windows are not independent trends. No completed match means no supported remaining-duration estimate. See S3 and S13.

# User guide: recommendations

## Find similar posts

Open Recommend and select an already-collected post by title or paste its post URL. Find compares that post against other collected posts. Results retain post titles and source links. It does not perform a global social-media search.

## Similarity method

The implementation uses 50% caption TF-IDF cosine similarity, 30% sampled-comment TF-IDF cosine similarity, and 20% normalized observed metric-pattern cosine similarity. Missing text contributes zero. Metric-pattern columns must be known on every post and have variation. The displayed score is a heuristic similarity, not predicted engagement or a sales probability.

## Basic next action

The deterministic recommendation identifies the strongest observed engagement per view if views are complete and positive, otherwise an observed engagement count. It uses only engagement metrics available across all compared posts. It explains the available metrics behind that choice.

## Generate strategy

The separate Generate Strategy action invokes Gemma using the dataset context and optional retrieved official guidance. It proposes experiments and should distinguish a supplied statistic from a suggestion. The basic deterministic recommendation remains available when Gemma is unavailable.

## Limits

TF-IDF captures word overlap rather than deep semantic meaning. English stop words and a small dataset can reduce useful multilingual comparisons. There is no collaborative filtering, co-purchase model, influencer discovery network or guaranteed reach lift. See S3, S8, S15 and S16.

# User guide: sentiment and demand

## Sentiment

Open Sentiment and inspect the scored sample count, basis, keywords and comment examples. The backend uses collected comment text when present. If no comments were returned it explicitly scores captions instead. Caption sentiment must not be described as audience sentiment.

## Filipino extension

text_sentiment.py adds positive words such as ganda, maganda, sulit and galing, and negative terms such as pangit and palpak. It preprocesses hindi/di and related negation before VADER scoring. Verified examples include Ang ganda as positive, hindi maganda as negative and hindi pangit as positive. This is a small vocabulary/rule extension, not a validated multilingual model.

## Thresholds

Compound sentiment scores at least +0.05 are positive, at most -0.05 negative, and the remainder neutral. Keyword polarity reflects the average tone of samples containing that keyword, not an independent meaning for the word. Sarcasm, context, spelling and code-switching can cause mistakes.

## Demand explained simply

More comments do not automatically mean more demand. Demand here means people asking questions or requesting something, for example Magkano?, Saan mabibili?, or Please restock. Nice post alone is engagement. A complaint might contain a question, so review examples before taking action. These signals do not prove a purchase.

## Counting detail

The rules can match a comment as both a question and a request. The unique demand-comment total counts it once, while question/request subtotals can overlap. Only sampled comments are counted, not every comment on the platform. At most eight comment texts per collected post are retained. S2, S5 and S14 define the rules.

# User guide: Gemma and strategy

## Assistant

Open Ask Speculara after an analysis. Ask a specific question about the current results, such as Explain demand or Why is forecast accuracy low? Suggestions scroll horizontally and support navigation controls. The request includes structured statistics and bounded evidence, with a coverage report.

## Context

model_context() removes repeated charts/matrices/history and caps serialized context around 16,000 characters by removing whole evidence records. Full-dataset summaries remain, while only a selection of posts/comments enters the model. A coverage label reports included versus collected records. Gemma cannot claim it read every original comment.

## Strategy research

The backend fetches fixed official Meta or TikTok URLs with TLS verification and bounded downloads/timeouts. It inserts retrieved article excerpts into the prompt as W sources. This is an allowlisted reference lookup, not live search across the web. Sources can be old or temporarily unavailable, which the response must disclose.

## Sources and trust

Post, comment and web IDs resolve through source_index. The response instructs Gemma to treat user text as untrusted evidence and to avoid inventing counts, rules or citations. Source buttons show only supplied safe URLs. Citations support inspection but do not prove the interpretation is correct.

## Service behavior

The configured model is gemma-4-31b-it through Google hosted Gemma. A transient request can retry once. Calls can take about a minute and the backend bounds total generation time. The UI distinguishes engine=gemma from engine=fallback and displays a sanitized notice for quota, access or timeout errors. Numerical views continue working without a successful LLM call. See S6-S8 and S11.

# Architecture and technology

## Frontend

React 19 manages state and rendering. TypeScript checks contracts. Vite 8 serves localhost:8443 and builds static assets. Tailwind CSS 4 and custom theme classes style the interface. Charts use native React/SVG, not an external paid dashboard service. Source: package.json and src/components/InsightPanels.tsx.

## API and analytics

Python 3.12 with FastAPI/Uvicorn serves localhost:8000. Pydantic validates request/post models. pandas and NumPy structure and aggregate data. SciPy computes Spearman coefficients, scikit-learn builds TF-IDF and cosine similarities, statsmodels supplies smoothing, and vaderSentiment scores text. openpyxl/xlrd read spreadsheets.

## Collection

A Node.js worker imports the pinned SocialMonitor collectors and Playwright. Python communicates through JSON lines over standard streams, with a global ownership lock, progress and cancellation. The local saved browser profile contains session cookies and stays ignored by Git. Worker environment filtering excludes AI/database credentials.

## AI and storage

httpx calls hosted Gemma and retrieves approved reference pages. Optional Supabase PostgreSQL stores analysis history using a backend-only service key. If unconfigured or unavailable, the app still analyzes and chats from the active result. A six-hour in-memory profile cache is separate from durable storage.

## Deployment

This MVP runs locally with two services and a local browser collector. Netlify can serve the frontend build but cannot alone run this Python backend and saved desktop browser session. A hosted multi-user collector, authentication, session isolation, abuse limits and operational monitoring are future production work.

# Brand, palette and neumorphism

## Name

For presentation, describe Speculara as a coined name inspired by specular, meaning mirror-like or relating to a mirror. The product reflects social media evidence back to its user. This is a proposed brand interpretation, not a documented founder etymology. S18 supports the meaning of specular, not the invented product name.

## Logo

The supplied circular mark combines aperture-like blades, a central lens/highlight and clock-like perimeter ticks. Suggested interpretation: focus, reflection and observation over time. This describes visible features of the supplied artwork rather than claiming a historical design brief. Preserve the original SVG proportions and colors. Use PNG for favicon compatibility.

## Palette

Ink #29348F: primary headings/actions. Dark ink #1E2761: readable body text and unavailable-value labels. Mist #F1F5F9: canvas/surfaces. Sky #38BDF8: chart accents/highlights. Wine #8F2934: warnings/negative emphasis. Cream #F9F5F1: warm logo detail. Shadow #CBD3DD and white #FFFFFF create depth.

## Neumorphism

The interface uses a shared pale surface, soft opposing light/dark shadows, raised controls and inset fields. .neu creates large raised panels, .neu-sm smaller controls, .neu-in inset fields and .neu-btn primary buttons. Sora is the display font, Manrope the UI font with system fallback. S10 is the source of truth.

## Accessibility and assets

Depth alone should not communicate state. Keep text labels, visible focus, readable dark text and standard controls. Reduced-motion CSS disables transitions for users requesting it. public/speculara-logo.svg renders in the site header, public/favicon.png supplies the browser icon, and .figma/make/site.json sets the tab title and description.

# Important code: ingestion and evidence

## Input validation

schemas.AnalyzeRequest defines post_limit as a strict integer between 5 and 50. main.analyze() normalizes the profile URL, distinguishes cache entries by requested limit and calls collector.collect_profile(). It rejects analysis while a sign-in window still owns the saved profile.

## Known values

insights.known() removes rows listing a metric in unavailable_metrics. availability() reports known-post coverage and returns total=None when no count is known. This prevents missing views/sales from silently becoming measured zeros in charts, correlation and forecasts.

## File merge

metric_import.merge_metrics() restores the current post evidence, matches IDs/URLs, validates non-negative whole counts and sets metric_sources to User-imported metrics. main.import_metrics() runs analytics.analyze() again so the charts and relationships reflect the imported values.

## Evidence IDs

evidence.build_evidence() retains actual post/comment URLs and metadata. chat_context.build_chat_context() assigns P/C source IDs. cited_sources() recognizes single/grouped bracket IDs and returns only supplied safe links. Captions and comments remain data, not executable instructions.

## Reading map

Start with backend/app/main.py for routes, schemas.py for contracts, collector.py for session/process control, metric_import.py for import behavior and evidence.py for provenance. These are application-specific sources S1, S4, S7 and S9.

# Important code: feature calculations

## Forecast

insights._forecast() resamples known values, excludes partial weeks, selects a candidate on training data and computes a separate holdout. _choose_model() tests rolling one-step errors. predict() adds within-profile comparable windows and qualified duration estimates.

## Recommendations

insights.recommend() constructs caption/comment TF-IDF similarities and complete metric-pattern similarities. score = .5*caption + .3*comments + .2*patterns. Its action list describes an observed post, not a generated reach-lift estimate.

## Correlation and charts

insights.correlation() uses pairwise known rows and scipy.stats.spearmanr. It includes sample sizes and source-bearing scatter points. charts() returns weekly/monthly totals and per-post labels/values.

## Sentiment

analytics.sentiment() chooses comment or caption basis and calls text_sentiment.score_text(). Compound thresholds produce positive/neutral/negative labels. Evidence samples retain source metadata so a reviewer can inspect a classification.

## Demand

analytics.demand() applies QUESTION_RE and REQUEST_RE to each sampled comment. It counts the union separately and produces per-post rankings/time groups. Do not interpret question/request totals as purchases. The optional demand projection remains a rough sampled-comment estimate.

# Important code: AI, UI and controls

## Gemma request

llm._generate() validates that the configured model ID starts with gemma-, sends the API key in x-goog-api-key, uses a plaintext contents request and TLS verification, bounds time and retries one transient failure. Error bodies and secrets are not returned to the browser.

## Context preparation

chat_context.model_context() preserves aggregate statistics, removes repeated payload sections and trims complete evidence records. main.chat() returns the engine label, notice, resolved sources and evidence coverage. A fallback uses observed facts and never impersonates a successful model call.

## Strategy

strategy.research() downloads bounded excerpts from fixed official URLs. generate_strategy() adds W citations to context and asks for three concrete experiments tied to observations. Its fallback uses deterministic recommendations and labels the engine.

## UI

App.tsx owns the active analysis and loading/cancellation flow. InsightPanels.tsx renders prediction, recommendations, charts and correlation. AnalysisPanels.tsx renders sentiment/demand and sources. MetricCoverage.tsx distinguishes missing/zero/imported values. SuggestionStrip.tsx gives the chat prompts horizontal navigation.

## Security boundary

Keys stay in backend/.env and are excluded from Git. The local-only login endpoints check client/origin. Collector subprocesses do not receive API/database secrets. This does not make the app a secure public multi-user SaaS: the current API still needs production authentication, resource limits and session isolation before internet exposure.

# MVP testing and demonstration runbook

## Verified scope

Backend regression tests, collector unit tests, API-client tests, server-rendered panel tests, TypeScript checks, production build and live localhost API tests cover the demo. The accompanying verification JSON and MVP-QA.md record exact results. Browser click/drag behavior was not desktop-tested in the final run, per the user instruction.

## Pre-demo

Keep both servers running. Confirm /api/health. Load the sample CSV/XLSX once and check 40 posts and all metric coverage. Open the 10-slide deck in fullscreen or PDF presentation mode. Keep this guide and the presenter reviewer available. Do not display keys, cookie files or unrelated personal tabs.

## Live demonstration

On slide 10 switch to localhost:8443. Upload the synthetic file and explicitly identify it as fictional. Inspect all six tabs, one recommendation, a correlation pair, a Filipino comment, demand sample counts and forecast holdout detail. Then ask chat a demand question and generate strategy, checking the engine/notice labels.

## Fallback plan

If Gemma is unavailable, show the labeled fallback and explain the calculations still work. If a network connector fails, use file import and disclose the connector status. Synthetic data has no genuine source URL, so show source-link behavior only on a previously collected real analysis, without mixing datasets.

## Release limits

The local demo does not certify all Facebook profiles, production deployment, complete Instagram Insights, purchased conversions, semantic multilingual accuracy, causal inference or calibrated forecasting. Supabase persistence is optional/unconfigured. Treat all AI suggestions as experiments to validate.

# Troubleshooting and maintenance log

## Cannot reach service

Check backend port 8000, VITE_API_URL and the backend terminal. Restart the backend after Python updates. A successful frontend page load does not prove the API is reachable. Keep the app origin in CORS_ORIGINS.

## Collector busy / zero posts

Only one saved-session task can run. Finish sign-in with Done signing in or cancel collection. Zero posts can mean platform layout/access incompatibility. It does not imply that the account is empty. The parser fixed the tested Facebook page, but other layouts and restricted profiles can still return zero.

## Gemma error / slow response

A configured key is not a live-service test. Quota, model availability and provider failures can produce fallback. Retry later rather than repeatedly clicking. API calls are bounded and the active analysis remains usable.

## 12 November 2026 change log

Added configurable 5-50 post requests, synthetic CSV/XLSX samples and standalone upload control. Improved Filipino sentiment/negation. Preserved TikTok save counts when returned. Compacted Gemma context and added clearer service notices/citations. Darkened Not supplied text. Applied the supplied site logo, favicon and browser title. Limited file reads at the size boundary. Added presentation, reviewer/script and documentation with a documented demo fallback.

## Maintenance

Keep the upstream MIT license and pinned commit record. Platform response formats can change independently of this app. Re-run automated checks and a small live collection after collector updates. Keep sample outputs synthetic and keep .env, saved sessions, logs and temporary builds out of commits.

# Verification record and limits

## Automated checks

118 Python backend tests, 15 collector tests, 16 server-rendered panel tests and four API-client tests passed. TypeScript type checking and the Vite production build passed. The panel tests use isolated caches to avoid a Windows file-lock collision with the running dev server.

## Live connectors

Final headless API smoke tests returned five dated posts each for Instagram, Facebook and TikTok. Instagram returned 40 comment samples with likes/comment counts. Facebook returned two comment samples plus likes, comment counts, shares and source URLs. TikTok returned 40 samples plus views, likes, comments, shares and saves. Sales were unavailable on all three.

## Gemma

A live chat request returned engine=gemma in 27.3 seconds. A sample strategy retry succeeded in 32.8 seconds after an earlier quota fallback. A strategy on real Facebook data succeeded in 40.5 seconds with research_status=retrieved and valid post/official Meta reference links. These are successful smoke tests, not an uptime guarantee.

## Imports and branding

Both synthetic files loaded 40 posts, all six supplied metrics and 15 correlation pairs through the live API. Matching metric imports, invalid limits, malformed files and localhost CORS behaved as expected. The served/built page title, favicon URL and logo asset were verified after reloading Vite configuration.

## Final-run boundary

No desktop UI interaction or manual login occurred in the final run. Existing saved sessions powered headless connector tests. Server-rendered component checks do not prove browser clicks, touch, drag or final pixel layout. The file route remains the repeatable demo path. See MVP-QA.md and the JSON logs for details.

# Sources and implementation references

## S1  Speculara API and input routes

https://github.com/chrisaph/speculara/blob/staging/backend/app/main.py

## S2  Analytics, sentiment and demand rules

https://github.com/chrisaph/speculara/blob/staging/backend/app/analytics.py

## S3  Forecasts, recommendations, charts and correlations

https://github.com/chrisaph/speculara/blob/staging/backend/app/insights.py

## S4  Metric import validation

https://github.com/chrisaph/speculara/blob/staging/backend/app/metric_import.py

## S5  Filipino sentiment extension

https://github.com/chrisaph/speculara/blob/staging/backend/app/text_sentiment.py

## S6  Gemma REST client

https://github.com/chrisaph/speculara/blob/staging/backend/app/llm.py

## S7  Bounded chatbot evidence and citations

https://github.com/chrisaph/speculara/blob/staging/backend/app/chat_context.py

# Sources and implementation references

## S8  Strategy and official-reference retrieval

https://github.com/chrisaph/speculara/blob/staging/backend/app/strategy.py

## S9  Collector integration and upstream pin

https://github.com/chrisaph/speculara/blob/staging/integrations/socialmonitor/UPSTREAM.md

## S10  Neumorphic theme and palette

https://github.com/chrisaph/speculara/blob/staging/src/index.css

## S11  Google hosted Gemma documentation

https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api

## S12  SciPy Spearman correlation

https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html

## S13  Statsmodels exponential smoothing

https://www.statsmodels.org/stable/generated/statsmodels.tsa.holtwinters.ExponentialSmoothing.html

## S14  VADER implementation

https://github.com/cjhutto/vaderSentiment

# Sources and implementation references

## S15  scikit-learn TF-IDF

https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html

## S16  scikit-learn cosine similarity

https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html

## S17  SocialMonitor upstream

https://github.com/Shades-Media-Group/SocialMonitor/tree/53302c9704a50dd3aea2518df08c35637d0e2b2b

## S18  Specular dictionary meaning

https://www.merriam-webster.com/dictionary/specular

## S19  Meta ranking guidance used by strategy

https://about.fb.com/news/2023/06/how-ai-ranks-content-on-facebook-and-instagram/

## S21  MVP verification record

https://github.com/chrisaph/speculara/blob/staging/outputs/speculara-mvp-20261112/MVP-QA.md

## S20  TikTok recommendation guidance used by strategy

https://support.tiktok.com/en/using-tiktok/exploring-videos/how-tiktok-recommends-content
