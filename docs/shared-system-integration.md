# Shared Speculara integration

## Purpose

Use `chrisaph/speculara` as the shared repository and `integration/shared-system` as the integration branch. Open a draft PR into `main` to review progress. This starter adds a plan only; the two applications are not combined yet.

## Preserved starting points

- Teammate version: `chrisaph/speculara@21e855773b2dc4a9e5e986ce824961ddeafa9fd9`.
- Decision-first MVP: `AK-Lmn/Speculara@ab9e9ee63fccc447bf1749c3240d56f9465b5400`.
- The repositories have unrelated Git histories. Port deliberate changes in reviewable commits; do not replace either version wholesale or mark an unimplemented merge as complete.

## Proposed combined system

Keep the decision-first interface, six modules, upload preview, experiment cards, accessible chat and explicit synthetic labels. Adapt the teammate's comment evidence, source links, optional collection and optional Gemma chat into that interface. Supabase history remains optional; upload analysis must work without it or an LLM key.

Collection is an optional source, not proof that all platform metrics are available. Missing sales, saves and views remain unknown. Do not estimate views from likes, report training-fit error as validated prediction accuracy, discard correlation direction, or promise experiment uplift.

## Integration sequence

1. Agree on one response contract. Preserve schema 2 measured results and add optional post/comment evidence and source metadata. Document mappings from the teammate's `facts`, `evidence` and `post_count` fields.
2. Separate upload and profile collection routes. The current `/api/analyze` contracts conflict: one accepts file bytes, the other JSON containing a profile URL. Add adapters and API contract tests before switching the interface.
3. Port Decision Brief, independent funnel counts, experiment measurements, preview and the existing mobile/keyboard fixes. Keep observed values unchanged and technical evidence expandable.
4. Port comment samples, source buttons and deterministic citations. Distinguish comment sentiment from caption sentiment and question entries from numeric comment totals.
5. Add collection and Gemma as optional capabilities with clear unavailable/error states. Preserve deterministic answers when credentials or services are absent. Do not imply an official platform integration.
6. Reconcile deployment and dependencies. The current teammate Dockerfile copies only the Python app; collection also needs Node, browser dependencies and the collector files. Local interactive sign-in cannot be assumed to work on Render.
7. Run combined Python, frontend, TypeScript, build and browser checks before marking the draft ready. Cover missing versus zero, opposite relationships, text-only uploads, preview cancellation, failed requests, citations, downloads, mobile and keyboard access.

## Team workflow

- Add `AK-Lmn` as a collaborator with write access and accept the invitation.
- Both developers fetch `chrisaph/speculara` and start feature branches from `integration/shared-system`.
- Open small PRs targeting `integration/shared-system`; pull its latest changes before starting new work.
- Coordinate edits to `src/App.tsx`, the analysis contract and API routes. Assign an owner before overlapping work.
- Keep the integration-to-main PR in draft until the combined system passes verification. No force pushes, automatic deployment or direct replacement of `main`.
