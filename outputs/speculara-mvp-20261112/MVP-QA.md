# Speculara MVP verification - 12 November 2026

The repeatable local MVP demonstration is ready using the supplied synthetic CSV/XLSX or built-in sample. All three networks and both Gemma endpoints passed small live smoke tests. This is not a certification of every profile, production security, model accuracy or provider uptime.

## Automated checks

| Check | Final result |
|---|---|
| `cd backend` then `.venv/Scripts/python.exe -m pytest -q` | 118 passed |
| `npm.cmd run collector:test` | 15 passed |
| `npm.cmd run test:analysis` | 16 passed |
| `npm.cmd run test:api` | 4 passed |
| `npx.cmd tsc --noEmit` | Passed |
| `npm.cmd run build` | Passed |
| `git diff --check` | Passed |
| PDF page/layout checks | 10-slide deck, 20-page guide, 9-page reviewer; no text outside page bounds |

Statsmodels emits numerical/convergence warnings on some synthetic or constant histories. The implementation rejects failed smoothing fits and uses simple baseline candidates where appropriate. Forecast results retain their validation limitations. Vite emits an advisory about its future native config loader; the current build succeeds.

## Live checks against localhost

| Case | Result and limits |
|---|---|
| Backend health | `ok=true`, `llm=true`, `database=false`; key configuration alone does not verify generation |
| CSV and XLSX standalone analysis | Both load 40 synthetic posts, all six metrics and all 15 pairwise correlations |
| CSV and XLSX metrics merge | Both match 40 built-in sample IDs and preserve the active evidence |
| Filipino classification | `Ang ganda!` scores positive in both uploaded datasets |
| Validation | Bad post limit and malformed upload reject with HTTP 422 |
| CORS | localhost:8443 allowed |
| Branding | Served and built title is `Speculara | Social Media Analysis`; new favicon URL and uploaded logo asset verified |
| Instagram `mrbeast`, limit 5 | HTTP 200; 5 dated posts, 40 comment samples, likes and comment counts. Views/shares/saves/sales unavailable in this response |
| Facebook `joanquizonmakeup`, limit 5 | HTTP 200; 5 dated posts, 2 comment samples, likes/comment counts/shares and genuine post links. Views/saves/sales unavailable |
| TikTok `tiktok`, limit 5 | HTTP 200; 5 dated posts, 40 comment samples, views/likes/comments/shares/saves. Sales unavailable |
| Chat | HTTP 200, `engine=gemma`, 27.3 seconds |
| Strategy on sample | Earlier quota fallback; successful retry `engine=gemma`, 32.8 seconds. No official research claimed for a generic sample |
| Strategy on real Facebook analysis | HTTP 200, `engine=gemma`, 40.5 seconds, `research_status=retrieved`; supplied post URLs and official Meta reference resolved |

Exact captured results are in `live-verification.json`, `service-retest.json` and `final-smoke.json`. They contain public metric summaries and model answers, not keys, passwords or browser cookies. They preserve earlier failures rather than relabeling them as successful runs.

## Issues found and addressed

- The dev server retained the old branding configuration. Reloading its configuration applied the new title and cache-busted favicon. Verified served HTML and production output.
- Facebook initially missed posts embedded in the initial Relay payload. The adapter now reads those records as well as subsequent GraphQL, restricts posts to the requested profile, and deduplicates them. A live run verified real dates and post URLs.
- A repeated Facebook run stalled while reading comments. Optional comment reads now use an isolated page and a 30-second deadline. Failure retains already observed post metrics and stops further comment-text requests for that run. The final retest returned two comment samples.
- Parallel panel tests collided with Vite's live dependency cache on Windows. Each test process now gets its own ignored cache directory. The full panel suite passed afterward.
- Hosted Gemma returned a quota error during one strategy call. The UI kept its labeled local fallback. A later sample strategy and real-data strategy succeeded. No quota bypass or unlimited-availability claim is made.

## Demo boundaries

No desktop automation or approval handoffs were used during the final run. Collection ran headlessly using existing saved sessions. No sign-in window was opened. Browser clicks, drag behavior and final responsive pixel layout were not visually re-tested in a desktop browser. Panel rendering, numerical reconciliation and safe-source contracts were checked automatically.

Use the synthetic file for slide 10, identify it as fictional, and explain that its rows intentionally have no genuine social post URLs. Source buttons can be demonstrated on the current collected analysis. Keep the file route ready if an external platform or model fails.

Supabase persistence is unconfigured and was not live-tested. Public/collected metrics do not expose sales or guarantee private Insights. Small samples, caption-only sentiment when comments are absent, heuristic multilingual rules and approximate forecast bands remain documented limitations. The local MVP does not provide production multi-user authentication/session isolation.
