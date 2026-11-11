# Speculara API (FastAPI)

Flow: profile URL -> SocialMonitor browser collector -> Python analytics -> optional Supabase persistence -> React results. Gemma (`gemma-4-31b-it`) answers chat questions from the analysis facts. Profile analysis makes no Google Search or other LLM research calls.

Endpoints: `GET /api/health`, `POST /api/analyze {url}`, `GET /api/sample`, `POST /api/upload` (csv/xlsx, in memory),
`POST /api/chat {message, facts}`, `GET /api/history`, `GET /api/analyses/{id}`,
`GET /api/collector/status`, `POST /api/collector/login {network}`,
`POST /api/collector/login/finish`, `POST /api/collector/cancel` (controls are localhost only).

## Run locally (Windows Git Bash / UCRT64)

Requires Python 3.12 and Node >=22.23.4 (Node 24 works). From `speculara`, install the collector once:

```bash
npm.cmd run collector:setup
# Optional fallback when Google Chrome is not installed:
npm.cmd run collector:browser
```

The actual upstream collectors are pinned and MIT-licensed; see [integration notes](../integrations/socialmonitor/UPSTREAM.md).

Install dependencies and start the backend:

```bash
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt

export GEMMA_API_KEY="your-google-ai-studio-key"
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-supabase-secret-key"
export CORS_ORIGINS="http://localhost:8443"

./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

Create a Google AI Studio API key at https://aistudio.google.com/apikey. The backend also accepts GEMINI_API_KEY for existing setups, but always calls a Gemma model. Keep keys in the backend environment; never put them in React or source control. You can copy env.example to .env in this directory to persist settings locally. The backend automatically loads .env; exported environment values take precedence. .env is ignored by Git. Replace any key that has been shared publicly.

The default chat model is `gemma-4-31b-it`. Set `GEMMA_MODEL` to use another compatible Gemma 4 model. AI credentials are optional for page analysis and sample data; chat falls back to factual templates if Gemma is unavailable. Google AI Studio quotas still apply to Gemma chat.

## Collecting real posts

Paste an Instagram, Facebook or TikTok **profile** link and click Analyze. The upstream collector reads up to 20 recent posts and 8 comments per post. For Instagram comment text or Facebook collection, choose the network under the input, click **Sign in for comments**, sign in yourself in the separate browser window, then click **Done signing in** in Speculara. Closing the sign-in tab also releases the browser. The app never enters passwords. Browser state is stored in ignored `backend/.socialmonitor/` and is not sent to Gemma or Supabase.

Collection displays live progress and elapsed time. **Cancel collection** requests a graceful browser shutdown. The collector has a 210-second overall deadline and the frontend request has a four-minute deadline. Optional Supabase calls run outside the request loop with five-second database timeouts; failures do not prevent displaying the analysis.

Instagram may require sign-in even for public profiles. Login walls/checkpoints and platform changes can interrupt collection. At least 5 valid dated posts are needed. TikTok uses the upstream signed-out collector. Unsupported networks/individual post URLs are rejected explicitly. Use `refresh: true` with POST /api/analyze to bypass the six-hour analysis cache.

Source links and data notes accompany results. Missing metrics are tracked separately; zero placeholders are used internally, with no invented view counts for collected posts. Missing-metric notes also travel with chat facts. Results may cover only the timeline returned by the platform, rather than the whole account history.

Supabase is optional: omit both Supabase exports to run without saving results. Open http://localhost:8000/api/health to check configuration. The `llm` and `database` flags indicate configuration is present, not that credentials have been validated against the services.

Leave the backend running. In a second terminal, from the `speculara` directory:

```bash
npm.cmd install
export VITE_API_URL="http://localhost:8000"
npm.cmd run dev
```

Open http://localhost:8443 and test an analysis. To run the backend tests from `backend`:

```bash
./.venv/Scripts/python.exe -m pytest
```

## Supabase
1. Create a project. 2. SQL Editor: run `supabase_schema.sql`.
3. Copy the Project URL from the Connect dialog and a backend secret key from Settings -> API Keys into the backend environment above. The variable remains named `SUPABASE_SERVICE_ROLE_KEY`; it also accepts the legacy `service_role` key. Never put this key in React.

## Deployment requirements
The original Python-only Dockerfile cannot run the local browser collector. Hosting requires a container with Python, Node, Playwright/Chromium and persistent browser storage. Interactive sign-in is available on the local computer only. Do not deploy the existing Render blueprint unchanged for this collector setup.

For a suitably configured server, New -> Blueprint (uses `render.yaml`), set `GEMMA_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `CORS_ORIGINS`. Set `CORS_ORIGINS` to your Netlify URL. `GEMMA_MODEL` is optional and defaults to `gemma-4-31b-it`.

## Deploy React (Netlify)
Build `npm run build`, publish `dist` (see `netlify.toml`). Site settings -> Environment variables:
`VITE_API_URL=https://speculara-api.onrender.com` then redeploy.

Results are cached per profile for 6 hours, including an in-memory cache of up to 100 profiles when Supabase is unavailable. The in-memory cache resets when the backend restarts. The cache accepts only SocialMonitor-sourced analyses, so older LLM research results are not reused. Test with `npm.cmd run collector:test` and `npm.cmd run test:api` from the root and `./.venv/Scripts/python.exe -m pytest` from backend.

## Analysis evidence and chat

Gemma receives the analysis sections, data-quality notes, and bounded post/comment evidence (up to 40 posts and 320 comment samples). The chat shows how much evidence it can read and renders source buttons for cited evidence. It cannot read comments the collector did not return or infer private sales metrics.

Sentiment uses collected comment text when available, otherwise explicitly labeled caption sentiment. Empty data produces an explanatory state. Demand measures questions and requests in sampled comments, independently of unavailable views, saves, or sales. Source buttons link to an exact comment URL when supplied by the collector; otherwise they explicitly link to the parent post or reel. Demo data has no external source links.

Saved analyses with stored posts are upgraded to the current evidence format when loaded. Refresh the frontend and run the analysis again to replace an older result still held in the browser. Run `npm.cmd run test:analysis` for panel rendering and evidence-filter checks.
