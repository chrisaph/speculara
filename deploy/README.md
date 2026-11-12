# Hosting decision: one private MVP server

Use one **Ubuntu 24.04 x86-64 VPS with Docker Compose**, a domain and a password-protected site. The same server runs the static frontend, FastAPI and the real Node/Playwright collector. Supabase stays optional. A 4 GB RAM server is a starting sizing estimate, not a measured capacity guarantee. Keep one backend replica and one simultaneous collection.

This matches the current application's shared saved browser profile, in-memory cache and global collection lock. It is an operator-run demo for trusted viewers, not a multi-user SaaS with isolated social accounts. Do not enable public signup or invite unrelated tenants into this shared environment.

## Why the previous files were insufficient

| Existing file/behavior | Hosting consequence |
|---|---|
| `netlify.toml` builds and publishes `dist` | Hosts the UI, not the API/collector |
| `backend/Dockerfile` installs Python only and copies `app` | Does not include Node, collector source, Playwright or Chromium |
| `render.yaml` uses the backend-only context | Cannot build the complete collector without changing that context |
| Manual login opens a desktop browser | A normal headless web host cannot show that window to its visitor |
| One browser profile and Python lock | Keep one backend process/replica; do not load-balance separate workers against it |
| Relative API fallback is localhost:8000 | The hosted frontend needs a same-origin API base, not each visitor's localhost |

The new `compose.yaml` and `deploy/*` prepare the complete route. Legacy Netlify/Render files remain for the separate file-upload-only scenario. There is no requirement to buy both a VPS and separate frontend hosting for this private MVP.

## Components

- **web** builds the real frontend using the existing pnpm lockfile, then Caddy serves it, proxies `/api/*`, provides HTTPS and checks a demo username/password on both UI and API.
- **backend** contains Python 3.12, Node 24, the pinned Playwright package/browser and collector source. It runs as a non-root user, one Uvicorn worker and a private virtual display. Browser sessions persist in the `collector-data` volume.
- **operator desktop** starts only when `ENABLE_REMOTE_DESKTOP=1`. Its host port binds to `127.0.0.1:6080`, never all interfaces. Access it through SSH for manual sign-in. Do not expose it through a domain, reverse proxy or public firewall rule.
- **hosted UI** explains that sessions belong to the operator and hides local-only sign-in/cancel controls. The local app retains its existing sign-in flow.

## 1. Prepare a server and domain

Create the VPS with an SSH key. Point the domain's A record to its public IP. Add an AAAA record only if IPv6 actually reaches the server. Allow inbound SSH, TCP 80/443 and optionally UDP 443. Do not open 6080, 5900 or 8000 publicly.

Install Docker Engine and the Compose plugin using the [official Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/). These files have not created a server, bought a domain, changed DNS or deployed an external service.

Run Docker commands as an authorized server administrator. Use `sudo docker ...` if your SSH user does not have Docker access.

## 2. Get the current staging code

```bash
git clone --branch staging https://github.com/chrisaph/speculara.git
cd speculara
cp deploy/hosting.env.example deploy/.env
chmod 600 deploy/.env
```

The runtime build does not need the PDFs or Git LFS artifacts. The Docker context allowlist excludes reports, local `.env` files and saved Windows sessions. Keep the real deployment environment only on the server. Do not copy your Windows browser profile into Linux; sign in afresh on the server.

## 3. Set the deployment environment

Generate a password hash interactively without putting the password in command history:

```bash
docker run --rm -it caddy:2-alpine caddy hash-password
```

Edit `deploy/.env` with a server editor. Set `DOMAIN` to the hostname only (for example `demo.example.com`, without `https://`), choose `SITE_USER`, and paste the generated hash into `SITE_PASSWORD_HASH` **inside single quotes**. This keeps the hash's dollar signs literal in Compose interpolation. Set `GEMMA_API_KEY`; leave optional Supabase values empty if saved history is not needed. Keep `ENABLE_REMOTE_DESKTOP=0` for ordinary operation.

Never put the Gemma key, service-role key or demo password in a `VITE_*` variable. The frontend uses an empty `VITE_API_URL`, so all API requests go to the same HTTPS origin. Its only other deployment flag is `VITE_COLLECTOR_MODE=operator`.

## 4. Build and start

```bash
docker compose --env-file deploy/.env config --quiet
docker compose --env-file deploy/.env build
docker compose --env-file deploy/.env up -d
docker compose --env-file deploy/.env ps
```

Do not run `docker compose config` without `--quiet` in a shared log or screenshot because expanded configuration includes server secrets. Check logs with:

```bash
docker compose --env-file deploy/.env logs --tail=50 backend web
```

Caddy obtains HTTPS after DNS points to the server and ports 80/443 are reachable. Open `https://YOUR_DOMAIN`, enter the demo credentials, then check `https://YOUR_DOMAIN/api/health`. `llm=true` only confirms configuration; test an actual chat. `database=false` is acceptable when Supabase is omitted.

For the first online check, upload the synthetic CSV/XLSX and test the six panels plus chat/strategy. Then verify TikTok or a public profile with five posts. Datacenter IPs can receive different login walls or rate limits than your laptop; local smoke tests do not guarantee cloud collection.

## 5. Connect the operator's Instagram/Facebook session

This is a private operator procedure. Site visitors do not submit their social passwords to Speculara.

1. Set `ENABLE_REMOTE_DESKTOP=1` in the server's `deploy/.env` and recreate only the backend:

   ```bash
   docker compose --env-file deploy/.env up -d --no-deps backend
   ```

2. From your computer, open the private tunnel and leave it running:

   ```bash
   ssh -N -L 6080:127.0.0.1:6080 YOUR_SSH_USER@YOUR_SERVER_IP
   ```

3. On the server, request login through the API's own loopback interface (not the publicly proxied endpoint):

   ```bash
   docker compose --env-file deploy/.env exec backend python /srv/collector-admin.py login instagram
   ```

4. Open `http://localhost:6080/vnc.html` on your computer. Connect and sign in manually in the displayed browser. Use the social network's normal login/security process. No credentials are entered automatically.

5. Finish through the same local API:

   ```bash
   docker compose --env-file deploy/.env exec backend python /srv/collector-admin.py finish
   docker compose --env-file deploy/.env exec backend python /srv/collector-admin.py status
   ```

   Repeat with `login facebook` if needed. The API lock prevents starting collection during sign-in. Use `cancel` to stop a stuck collection. Do not run the separate `collector:login` CLI alongside the API because it would bypass that lock.

6. Set `ENABLE_REMOTE_DESKTOP=0`, recreate the backend again and close the SSH tunnel. The saved session remains in the volume, and ordinary collection stays headless. Confirm the operator desktop is unreachable before sharing the site.

## Maintenance and limits

Update with `git pull --ff-only`, then repeat `build` and `up -d`. Keep the named volumes across redeploys. Do not use `docker compose down -v` unless you deliberately want to erase sessions/certificates. Treat browser storage backups as credentials and store them privately. Supabase, if configured, persists analyses separately.

The gateway password protects a small trusted demo and API quota from anonymous use. It is not per-user authentication or tenant isolation, and there is no distributed rate limiter/queue. The existing API has bounded requests, one collector lock and provider error handling. Add proper user authentication, account isolation and quotas before running an open public product. Shared saved history, sessions and cancellation belong to the operator.

The container packaging still needs its first Docker build/start on the target server. Docker is unavailable in the current development environment, so a Linux container/browser or HTTPS certificate test cannot be claimed here. See `validation.md` for checks that can be run locally and the remaining target-server acceptance steps.

## Primary references

- [Playwright Docker requirements](https://playwright.dev/docs/docker)
- [Caddy static site and API proxy patterns](https://caddyserver.com/docs/caddyfile/patterns)
- [Caddy HTTPS prerequisites](https://caddyserver.com/docs/automatic-https)
- [Caddy hashed-password authentication](https://caddyserver.com/docs/caddyfile/directives/basic_auth)
- [Compose environment interpolation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)
- [noVNC browser client](https://novnc.com/info.html)
