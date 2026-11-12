# Render / Netlify preparation checks — 2026-11-13

Passed locally without desktop automation or cloud provisioning:

- Full Python suite: 133 passed before adding one more operator-positive test; focused final access suite: 8 passed. Existing statsmodels convergence/numerical warnings remain.
- Frontend API: 5 passed; hosted/local UI and Netlify URL guard: 4 passed.
- All analysis panels: 18 passed; SocialMonitor adapter/worker: 15 passed.
- TypeScript `tsc --noEmit`, guarded Netlify production build with a fixture HTTPS Render origin, and ordinary local production build passed.
- Caddy Render configuration validation and 8 loopback checks passed: preserved Bearer header, desktop disabled, Basic authentication, authenticated path stripping, rejected foreign Origin and accepted same Origin.
- Existing VPS Caddy validation and 8 loopback checks passed. Docker Compose configuration validation passed with placeholder environment values.

The fixtures use dummy upstreams and dummy tokens. They do not prove a real cloud browser/WebSocket session, live platform collection, Gemma quota or production capacity. No Docker daemon is available locally, so no Linux container build was run. Complete the target-service acceptance checks in [the setup guide](render-netlify.md) after provisioning. No paid cloud resources were created.
