# Speculara QA — 12 Nov 2026

Baseline: `main` commit `21e8557`. Fixes and reports are on `staging` only.

The two workbooks in `outputs/speculara-qa-20261112` use only the supplied template's `1111 - Test` tab. They preserve its ID, Module, Result, Test / Finding, Remarks layout, column widths, header style and frozen header rows. Descriptions and remarks wrap with fitted row heights. The user's “11/11” label refers to this existing tab; Excel does not allow `/` in worksheet names. The original CAR workbook was read as a formatting reference and was not changed or uploaded.

`results.json` retains the same 33 IDs and acceptance tests before and after the fixes. Baseline findings came from code inspection, known-input reproductions, existing regression tests, and live local API checks. Render tests verify generated React markup and data transformations; they are not interactive browser or responsive-layout passes.

Known-input fixtures cover oppositely ranked metrics, missing/constant metrics, stopword-only/empty/non-English captions, selected post URLs, held-out forecasting, real historical-window provenance, numeric chart reconciliation, missing upload columns, negative counts, storage failures and model/source failure handling. Model success and citation plumbing are tested with explicit mocks. This is distinguished from live provider checks in the report.

Commands:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ..
npm.cmd run test:analysis
npm.cmd run test:api
npm.cmd run collector:test
.\node_modules\.bin\tsc.cmd --noEmit
npm.cmd run build
```

External limits are not marked as passed: Google Gemma returned a quota error in the live strategy test. Browser access initially failed, and native Computer Use later disconnected, so the final interactive/visual acceptance check remains blocked. Official Meta reference retrieval was separately verified successfully with TLS certificate validation enabled. No new live social-media collection or authenticated commenting was represented as a completed QA pass.

An additional private-storage QA probe used a harmless marker file, not cookies. The baseline server served it over HTTP; the fix denies `.socialmonitor` and `.venv` paths and excludes backend/output/temp folders from frontend watching. The temporary marker was removed after both probes.
