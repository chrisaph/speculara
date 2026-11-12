# Hosting preparation validation

Local checks completed on 12 November 2026:

| Check | Result |
|---|---|
| Backend tests including persistent-path configuration and shutdown cleanup | 126 passed |
| Existing panel rendering tests | 18 passed |
| Hosted/local UI mode and same-origin upload tests | 2 passed (`npm.cmd run test:hosting`) |
| TypeScript | Passed |
| Hosted production frontend build | Passed; bundled API calls have no localhost:8000 fallback |
| Official Compose CLI schema/environment validation | Passed with placeholder example environment, without a Docker daemon |
| Official Caddy config validation and loopback HTTP checks | Passed: UI/API require authentication, SPA fallback works, API preserves paths and strips gateway credentials, operator endpoints reject public requests |
| Operator CLI Python syntax | Passed |
| Frontend manifest versus frozen pnpm lockfile | Dependency specs match |

The Caddy and Compose validators were downloaded from their official GitHub releases, checked against published release checksums, and kept only under an ignored temporary directory. No host service or browser window was installed or opened for this work. Loopback HTTP tests used a dummy backend and dummy credentials, not a public deployment.

Repeat the gateway checks with `python deploy/check-gateway.py --caddy /path/to/caddy` after installing the application's Python requirements. The test starts temporary loopback servers and stops them afterward. It does not require Docker or real login credentials.

## Required acceptance on the VPS

Docker Engine and a Linux browser runtime are unavailable on this development machine. The container image itself, virtual desktop, named-volume permissions, cloud-platform collection and real HTTPS provisioning remain **unverified until the first server build/start**. The entrypoint has not been executed under a Linux shell here.

Before sharing the site, follow `deploy/README.md` and check:

1. `docker compose --env-file deploy/.env build` completes on the target server.
2. Both services are running, the backend is healthy and the frontend is reachable only after the gateway login.
3. On the authenticated domain, `/api/health`, sample data, CSV/XLSX upload, all six panels, chat and strategy work. Verify a real Gemma response rather than only the health flag.
4. While no collection/sign-in is active, run a collector browser smoke test on the server:

   ```bash
   printf '%s\n' '{"action":"smoke"}' | docker compose --env-file deploy/.env exec -T backend node /srv/integrations/socialmonitor/worker.mjs
   ```

5. Connect operator sessions using the SSH-only desktop procedure. Use a dedicated operator account appropriate for a trusted shared demo; the saved session can access what that account can access.
6. Collect five actual posts from each desired platform. Datacenter networking or changed social-page layouts may behave differently than the laptop.
7. Recreate the backend, then confirm its saved sessions remain available and the operator desktop is disabled/unreachable afterward.
8. Confirm only SSH and web ports are externally reachable; ports 8000, 5900 and 6080 must not be public. Confirm the public session-control endpoints reject requests.
9. Finish or cancel active collection before updating. Confirm container shutdown closes browser tasks cleanly, then restart with the same persistent volumes.

Do not call the full hosted collector validated until those target-server checks pass. The existing local app and its previously tested workflow remain available while hosting is prepared.
