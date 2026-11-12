# SocialMonitor collector integration

Source: https://github.com/Shades-Media-Group/SocialMonitor

Pinned commit: `53302c9704a50dd3aea2518df08c35637d0e2b2b` (downloaded 2026-11-12).

The files in `vendor/collect/` and `vendor/types.ts` are copied from
`apps/app/src/core/` at that commit. The original MIT license is preserved in
`LICENSE`. No upstream dashboard, branding assets, AI provider, or SQLite store
is bundled. `vendor/db.ts` is a Speculara adapter exporting only `DATA_DIR`,
which is the browser helper's sole database-module dependency. The collector
source files include these Speculara changes: `collect/instagram.ts`, `collect/facebook.ts`, `collect/tiktok.ts`, `collect/tiktok-public.ts` and the optional `saves` field in `types.ts`. Speculara captures the
normal profile feed and embedded Relay data before trying the legacy profile
endpoint, which can return HTTP 404. `instagram-data.mjs` maps current and legacy
timeline records into the upstream format. If comment retrieval fails, observed
post metrics are retained and further comment requests stop for that run.
The adapter also preserves supplied Instagram play/share/save counts across sparse feed payloads. Missing counts remain unknown; no extra private-insights endpoint is assumed.

The Facebook adapter reads both embedded initial Relay records and later GraphQL responses, filters post URLs to the requested profile, and bounds optional comment-thread reads to retain observed metrics if a thread fails. TikTok maps a supplied `collectCount` to saves; absent save counts remain unknown. The original MIT license remains unchanged.

`worker.mjs` adapts those collectors to a line-delimited JSON stdin/stdout protocol with progress events and graceful finish/cancel controls. Python
starts it without a shell. Browser cookies stay in `backend/.socialmonitor/`,
which is ignored by Git. The worker receives no Gemma or Supabase credentials.
Only the explicit login action opens a visible browser. It never enters a
password, posts, likes, follows, or sends messages.

Collection requests 5-50 recent posts (default 20), with at most 8 comment samples per post in Speculara.
Instagram's upstream profile endpoint may return fewer posts and does not page
through the entire profile history. Comments need an Instagram session;
Facebook needs a session. TikTok uses the upstream logged-out collector.
Login walls/checkpoints are surfaced to the user. Platform changes may break
collection. No guarantee of complete historical data is made.

## Local setup

Use Node >=22.23.4 (Node 24 works). From the Speculara root:

```bash
npm.cmd run collector:setup
# Uses installed Google Chrome when available. Install Chromium as a fallback:
npm.cmd run collector:browser
npm.cmd run collector:test
```

Restart the Python backend and frontend as usual. Paste a supported profile
URL and click Analyze. To include Instagram comment text, choose Instagram and
click Sign in for comments; sign in manually, click Done signing in in Speculara, then Analyze.
The same control handles Facebook. A CLI equivalent is:

```bash
npm.cmd run collector:login -- instagram
```

On a server, both Python and Node plus a browser runtime are required. The
original Python-only Dockerfile does not provide the collector runtime. The
interactive sign-in endpoint is restricted to requests from this computer.
