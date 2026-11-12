# Render backend + Netlify frontend

Netlify serves React; Render runs Python, Node, Chromium and a virtual display. This is a private, operator-led temporary demo. The checked-in Blueprint now selects **Render Free with no persistent disk**. Choose Netlify's Free plan too. These files do not provision cloud resources.

Render Free currently provides 512 MB RAM and 0.1 CPU, sleeps after 15 idle minutes, and can restart at any time. Files, saved social sign-ins and in-memory results can disappear on sleep, restart or redeploy. The collector plus desktop may exceed available memory; this configuration enables a trial, not a guarantee that live collection will work. Start with five posts and one visitor. CSV/Excel is the demo fallback, but also needs target-service verification. Provider quotas and hosting usage limits still apply.

## Backend

Create a Render **Blueprint** from this repository's `staging` branch using root `render.yaml`. Leave the root directory at the repository root. It builds `deploy/backend.Dockerfile`, including the collector dependencies; do not use the old Python-only service configuration. Keep one instance because collection and saved sessions are single-user resources.

Confirm the service shows **Free** and no disk before creating it. If you already created a paid service, this Git change does not cancel charges: select Free in Render and remove its disk there first. Export any needed files before deleting a disk; its contents are lost. A workspace's free plan alone does not make an individual paid service free.

Enter `GEMMA_API_KEY` and `CORS_ORIGINS`. The latter is your exact Netlify HTTPS origin. If unknown initially, temporarily use `http://localhost:8443`, then replace it after creating Netlify and redeploy Render. Leave `CORS_ORIGIN_REGEX` empty.

The Blueprint generates `DEMO_ACCESS_TOKEN` and `OPERATOR_ACCESS_TOKEN`. Find them in Render's Environment settings. Share only the demo token with trusted attendees. Keep the operator token private. Neither belongs in Netlify or any `VITE_` variable. Existing services must also receive these new settings when applying this configuration.

Supabase is optional. Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in Render and run `backend/supabase_schema.sql` to enable history. Otherwise `database:false` is expected.

Wait for the Docker build, then open `https://YOUR-SERVICE.onrender.com/api/health`. Expect `ok:true` and `llm:true`; this checks configuration, not provider quota. After idle sleep, open health and wait for it to finish waking before unlocking Netlify. Caddy listens on Render's public port; Python and the desktop use private loopback ports. The startup script initializes temporary storage, then runs the application and browser as UID 10001.

## Frontend

Import the repository and `staging` branch into Netlify. Base directory: repository root. `netlify.toml` selects Node 24, `npm run build:netlify`, and publish directory `dist`.

Before building, add this public variable in Netlify:

```ini
VITE_API_URL=https://YOUR-SERVICE.onrender.com
```

Use the origin without `/api`. The build rejects missing URLs, HTTP, localhost, credentials and paths. It enables the access-code screen and operator-managed collection. Redeploy Netlify whenever this build-time URL changes.

Set Render's `CORS_ORIGINS` to the exact resulting Netlify origin (plus your custom domain if used, comma-separated) and redeploy Render. Preview domains are excluded unless explicitly allowed.

Open Netlify and enter the demo token. It stays in tab memory and is sent as a Bearer header; refreshing requires re-entry. Never put API secrets in frontend environment variables. Requests go directly to Render: do not add a Netlify API proxy, whose documented 26-second timeout is too short for collection and some Gemma calls.

## Operator social sign-in

Visitors cannot open or cancel saved browser sessions. For Instagram/Facebook, the operator signs in separately. Platform challenges and rate limits can still block cloud collection; private Insights/sales metrics cannot be obtained from arbitrary profiles.

1. Set `ENABLE_REMOTE_DESKTOP=1` in Render and redeploy. It is off by default.
2. In local PowerShell at the repository root, load the operator token without printing it or placing it in command history:

```powershell
$operatorSecret = Read-Host 'Render operator key' -AsSecureString
$env:OPERATOR_ACCESS_TOKEN = [System.Net.NetworkCredential]::new('', $operatorSecret).Password
.\backend\.venv\Scripts\python.exe deploy/collector-admin.py login instagram --url https://YOUR-SERVICE.onrender.com
```

Use `facebook` instead of `instagram` when needed. The helper requires Python and `httpx`, included in backend requirements.

3. Open the protected desktop URL:

```text
https://YOUR-SERVICE.onrender.com/operator/desktop/vnc.html?path=operator%2Fdesktop%2Fwebsockify
```

Enter HTTP Basic username `operator` and the operator token as password. Connect the desktop, then sign in manually in the platform browser. Do not send social passwords to chat. Foreign browser origins are rejected; the desktop and WebSocket use the same protected origin.

4. Finish from PowerShell:

```powershell
.\backend\.venv\Scripts\python.exe deploy/collector-admin.py finish --url https://YOUR-SERVICE.onrender.com
.\backend\.venv\Scripts\python.exe deploy/collector-admin.py status --url https://YOUR-SERVICE.onrender.com
Remove-Item Env:OPERATOR_ACCESS_TOKEN
```

Use `cancel` only for a genuinely stuck collection. On **Free**, keep `ENABLE_REMOTE_DESKTOP=1` during your demo: changing it and redeploying after sign-in can erase the new session. The desktop remains protected by the private operator key. Finish the login with the helper, close the desktop tab, then test five posts from Netlify. Only one collection can run at a time. When the demo ends, disable the desktop and redeploy; expect to sign in again next time. Never share the operator key with attendees.

For durable sessions later, upgrade to a paid service and attach a disk at `/data`. Only with that disk can sessions survive redeploys; on that setup you can disable the desktop and redeploy after signing in without intentionally discarding storage. Free does not support persistent disks or SSH/shell access, so use the HTTPS helper above.

## Acceptance checks and limits

- Health responds; `/api/access` returns 401 without a token. Wrong demo codes fail; refreshing locks the UI.
- Upload the synthetic CSV/XLSX and inspect all six panels, coverage, evidence, correlations and honest forecast reliability.
- Ask Gemma a question and generate strategy. Confirm actual responses or clearly labeled provider/fallback errors; configured keys alone do not prove quota.
- Verify protected operator sign-in and a five-post live collection; check Render logs for memory-related restarts.
- A Render restart may discard sign-in on Free. Verify that repeating the operator sign-in recovers collection instead of expecting persistence.
- After the demo, disable the desktop and confirm its URL returns 404. Expect to repeat sign-in next time.

Local automated tests cover access separation, CORS, frontend gating, URL validation, gateway routing and builds. This machine has no Docker daemon: the Linux image build and real Render/Netlify/browser smoke checks must complete on the target services before calling the cloud deployment verified. No cloud service has been created by this change. Local development retains its existing desktop sign-in and does not require demo codes by default.

Sources: [Render web services](https://render.com/docs/web-services), [Blueprint fields](https://render.com/docs/blueprint-spec), [persistent disks](https://render.com/docs/disks), [pricing](https://render.com/pricing), [Netlify proxy timeout](https://docs.netlify.com/manage/routing/redirects/rewrites-proxies/), [Caddy authentication](https://caddyserver.com/docs/caddyfile/directives/basic_auth), [Playwright Docker](https://playwright.dev/docs/docker).

Free-tier limits: [Render Free](https://render.com/docs/free) and [compute plans](https://render.com/docs/compute-plans).

The [single-VPS guide](README.md) remains an alternative.
