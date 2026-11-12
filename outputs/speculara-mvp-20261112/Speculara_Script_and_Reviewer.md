# Speculara presentation script and reviewer

12 November 2026. Ten slides total; slide 10 is the demo. Suggested timing: 6-8 minutes plus a 3-minute demo.

## Slide 1: Speculara

Speculara helps marketing teams understand their social media results. It brings six analysis views into one application and lets a Gemma assistant explain the evidence. Today I will show the working MVP, distinguish observed values from estimates, and finish with a short demonstration. Our demo uses clearly labeled synthetic data so everyone can reproduce the same workflow.

Sources: S1, S3

## Slide 2: The decision problem

A post can receive many comments for very different reasons. Some people praise it, others ask about price, and others complain. A single total cannot explain that distinction. Speculara combines observed counts with sampled text and keeps track of missing metrics. This is our product motivation, not a quantified market study or a claim about time saved. The goal is a clearer decision with evidence the presenter can inspect.

Sources: S2, S4, S7

## Slide 3: Data and provenance

There are two entry routes. A supported profile link starts the local SocialMonitor collector. The post-count selector controls the requested maximum, and the platform can return fewer records. Alternatively, CSV or Excel supplies a complete dataset. For an existing profile analysis, Import Metrics joins private counts by post ID or URL. Sales and private Insights values are never invented. Source buttons open an actual comment link where available, or its parent post.

Sources: S1, S4, S9

## Slide 4: Comparison and relationships

Charts display supplied values rather than generated chart data. Recommendations compare posts using caption TF-IDF, sampled-comment TF-IDF and normalized metric patterns, weighted 50, 30 and 20 percent. That percentage is similarity, not a probability of success. Correlation uses Spearman rank correlation, which measures whether two metrics tend to increase or decrease together. Each pair uses only posts with both values and enough variation. It does not establish causation.

Sources: S3, S12, S15, S16

## Slide 5: Forecasts and trend duration

Prediction groups supplied counts by posting week and excludes the current incomplete week from fitting. Model selection compares simple baselines and damped exponential smoothing using only training observations. The final holdout remains separate. The displayed score is 100 minus weighted absolute percentage error, floored at zero. Zero therefore means a poor backtest, not a broken button. The uncertainty band is approximate. Trend duration only uses completed comparable patterns within the same profile, so limited history may support no estimate.

Sources: S3, S13

## Slide 6: Sentiment and demand

Sentiment estimates tone using VADER with a Filipino vocabulary extension. Ganda is positive, while hindi maganda becomes negative through negation handling. This is a rule-based MVP, so sarcasm and mixed-language expressions still need human review. Demand identifies questions and requests in sampled comments. Magkano is an inquiry, while a compliment alone is not a request. A comment may match both categories, so their totals can overlap. These are interest signals, not measured purchases or a market-size forecast.

Sources: S2, S5, S14

## Slide 7: Gemma strategy and assistant

Gemma does not automatically browse a profile or know all private metrics. The backend sends structured analysis plus a bounded selection of collected evidence. Chat answers the current question from that context. Strategy can additionally retrieve a fixed allowlist of official Meta or TikTok guidance, then asks Gemma to distinguish observations from proposed experiments. This is not a comprehensive web search. Source buttons resolve IDs against supplied URLs. API quota or availability problems produce a labeled fallback, not a claim that Gemma generated the response.

Sources: S6, S7, S8, S11

## Slide 8: Technical stack

React manages the interface and TypeScript checks its types. Vite serves and builds it, while Tailwind and custom CSS create the neumorphic style. FastAPI exposes the analysis endpoints. Python libraries perform the numerical work, rather than asking an LLM to invent statistics. A Node and Playwright worker collects normal page data using a local saved session. Hosted Gemma provides language responses. Supabase can store analyses, but local analysis works without it. Static hosting alone cannot run this Python API or desktop-session collector.

Sources: S1, S3, S6, S9, S10

## Slide 9: MVP demo scope

The reproducible demo route uses the supplied synthetic file. We can demonstrate numerical views without waiting for external services. Live TikTok collection and Gemma calls have worked during testing, but the provider can still rate-limit or time out. The updated parser returned five dated posts from the supplied Facebook page. Coverage still depends on platform access and layout. Supabase is optional and is not configured in the local test environment. This is an MVP demonstration scope, not a production-readiness claim.

Sources: S21, S9

## Slide 10: Demo

I am opening the app and selecting Analyze CSV / Excel data. This file contains 40 synthetic posts, which I will identify explicitly. I will show the metric coverage first, then compare posts and inspect a correlation. Next I will open sentiment and show the positive Filipino example. Demand counts questions and requests, which differ from general engagement. I will inspect the forecast validation rather than promise a fixed accuracy. Finally I will ask the assistant about demand and generate strategy. If the API falls back, I will state that clearly. Synthetic rows have no real post URLs, so I will explain that source links appear only when genuine evidence exists.

Sources: S1, S2, S3, S7

## Reviewer: technology and tools

### Frontend

React 19 = interface/state. TypeScript = type checks. Vite 8 = local server/build. Tailwind 4 + custom CSS = palette and neumorphic surfaces. Native SVG = chart drawing. Sora/Manrope = interface fonts.

### Backend

Python 3.12 and FastAPI/Uvicorn = API. Pydantic = contracts. pandas/NumPy = tabular calculations. SciPy = Spearman. scikit-learn = TF-IDF/cosine. statsmodels = forecasting. VADER = rule-based tone with Filipino extension.

### Data and AI

Node.js + Playwright + adapted SocialMonitor = local collection. CSV/Excel + openpyxl/xlrd = file data. httpx = network requests. Gemma 4 31B through Google hosted API = explanation/strategy. Optional Supabase PostgreSQL = saved analyses.

### Development and verification tools

VS Code and Git/GitHub support development/versioning. pytest covers Python behavior. Node test runner covers the API client and collectors. React server rendering checks output contracts. tsc checks types and Vite checks the production bundle. ReportLab creates the presentation/manual PDFs; pypdf and PyMuPDF check pages and rendering. These artifact tools are not app runtime dependencies.

### One-sentence architecture

The frontend sends data requests to FastAPI, Python computes the analysis, and Gemma explains a bounded evidence context. The Node worker only collects normal page data. Keys stay in the backend.

## Reviewer: important code map

### Routes and contracts

backend/app/main.py: analyze(), upload(), import_metrics(), chat(), strategy(). schemas.py: Post and AnalyzeRequest. Read these first to explain inputs, active-result replacement and errors.

### Feature calculations

backend/app/insights.py: known(), availability(), _forecast(), _choose_model(), predict(), recommend(), charts(), correlation(). analytics.py: analyze(), sentiment(), demand(). These functions calculate the actual outputs.

### Evidence and AI

evidence.py: build_evidence()/safe_url(). chat_context.py: model_context()/cited_sources(). llm.py: _generate()/chat_answer(). strategy.py: research()/generate_strategy(). They determine what Gemma sees and how links resolve.

### Collector and interface

collector.py owns worker/session locks and normalization. integrations/socialmonitor/worker.mjs routes network requests. App.tsx owns the active analysis. AnalysisPanels/InsightPanels render views. MetricCoverage and SuggestionStrip cover missing counts and scrolling prompts.

### The numbers to remember

Post request: 5-50. Minimum valid posts: 5. Comment cap: 8 per collected post. Recommendation weights: 50/30/20. Spearman minimum: 3 pairwise observed varying rows. Forecast minimum: 6 completed nonzero-total weeks. Final holdout: 2-4 weeks. AI evidence context: about 16,000 characters.

## Reviewer: likely panel questions

### Is sentiment generated by Gemma?

No. The numerical sentiment view uses VADER plus Filipino vocabulary and negation rules. Gemma explains the results. The extension handles examples such as ganda, but does not prove comprehensive Filipino accuracy.

### Does higher comment count mean more demand?

Not by itself. Demand means sampled questions and requests. A popular joke may attract reactions without buying interest. Demand here is a proxy for interest, not sales.

### Can you collect saves and sales from Instagram?

Only values the page actually returns can be preserved. Private saves/shares/Insights coverage is not guaranteed. Sales need supplied export/order data. Unknown values remain unavailable until imported.

### Why can prediction show 0%?

The held-out error was at least 100%, so the score is floored at zero. Show the holdout table and explain limited/spiky history. Do not call it a forecast guarantee.

### Are recommendations success probabilities?

No. They are heuristic similarities based on text and metric patterns within this dataset. The best observed post can inspire a test, but its success does not prove the same outcome will repeat.

### Does Gemma browse the internet?

The backend supplies collected data. Strategy can additionally retrieve a fixed allowlist of official references. This is not unrestricted live web research. The response exposes research status and citations.

## Reviewer: limitations and demo recovery

### Does Facebook work now?

Yes for the tested supplied page: five dated posts with observed likes, comment counts, shares and source links. This is a small live smoke test, not complete Facebook coverage. Comment text can still be absent, and private metrics remain unavailable.

### What if Gemma fails during the demo?

Check the engine/notice label. Explain that fallback is deterministic and is not a Gemma response. Continue with charts, sentiment, demand, similarity and correlation, which compute locally.

### What is stored and where?

The active analysis is in memory and optional Supabase can persist history. Collector cookies stay in an ignored local browser profile. AI requests transmit a bounded analysis context to Google. This MVP is not a public multi-user security design.

### Is Netlify enough?

It can host static frontend assets. The Python API and local browser collector need separate infrastructure and session design. The current demonstration uses localhost.

### Demo checklist

Before presenting, confirm the two servers and preload the synthetic CSV. Show all six views. Keep the 10th slide as the switch to the app. Allow time for the model call. Explicitly label synthetic data, unavailable counts, approximate forecasts and AI-generated suggestions.

### Close

Speculara makes observed social-media results easier to inspect and discuss. Its MVP value is a connected workflow with transparent methods and evidence. The next engineering priority is reliable connector coverage and production isolation, not claiming access to hidden platform metrics.
