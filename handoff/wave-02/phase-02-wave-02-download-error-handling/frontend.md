# Frontend Agent Handoff — Wave 2 Phase 2

## Status

Done. All delegated tasks completed. Lint and build pass.

## Scope

- Standardize blob-download error handling to `await getApiErrorBodyAsync(error)` on all frontend blob-download failure paths.
- Converge duplicated local `isNetworkOrServerError`, `getApiErrorBody`, `runWithRetry`, and `CONNECTION_ERROR_MESSAGE` helpers onto the shared `frontend/src/utils/http.ts` layer for the delegated pages.

## Docs Read

- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (F-028, F-032)
- `stoqio_docs/17_UI_REPORTS.md`
- `stoqio_docs/12_UI_ORDERS.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/wave-02/phase-02-wave-02-download-error-handling/orchestrator.md`
- `frontend/src/utils/http.ts`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx` (reference implementation)
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/pages/orders/OrderDetailPage.tsx`
- `frontend/src/api/reports.ts`
- `frontend/src/api/orders.ts`
- `frontend/src/api/articles.ts`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`

## Files Changed

### Blob-download async error parser fixes

**`frontend/src/pages/reports/ReportsPage.tsx`**
- Added `getApiErrorBodyAsync` to the import from `../../utils/http`.
- `handleStockExport` catch: replaced `getApiErrorBody(error)?.message` with `(await getApiErrorBodyAsync(error))?.message`.
- `handleSurplusExport` catch: same.
- `handleTransactionsExport` catch: same.
- Non-blob error paths (`getApiErrorBody`) left unchanged.

**`frontend/src/pages/orders/OrderDetailPage.tsx`**
- Added `getApiErrorBodyAsync` to the import from `../../utils/http`.
- `handleDownloadPdf` catch: replaced `getApiErrorBody(error)?.message` with `(await getApiErrorBodyAsync(error))?.message`.
- Non-blob error paths left unchanged.

### Helper convergence

**`frontend/src/pages/drafts/DraftEntryPage.tsx`**
- Removed local `CONNECTION_ERROR_MESSAGE` constant (was identical to shared).
- Removed local `isNetworkOrServerError` function (was equivalent to shared).
- Added import `{ CONNECTION_ERROR_MESSAGE, isNetworkOrServerError }` from `../../utils/http`.
- Kept `import axios from 'axios'`: still needed for inline `axios.isAxiosError` message extraction in several catch blocks (not a duplicate of any shared helper — custom inline pattern).

**`frontend/src/pages/approvals/ApprovalsPage.tsx`**
- Removed local `CONNECTION_ERROR_MESSAGE` constant (was identical to shared).
- Removed local `isNetworkOrServerError` function (was equivalent to shared).
- Removed `import axios from 'axios'` (no longer needed after helper removal).
- Added import `{ CONNECTION_ERROR_MESSAGE, isNetworkOrServerError }` from `../../utils/http`.

**`frontend/src/pages/approvals/components/DraftGroupCard.tsx`**
- Removed local `isNetworkOrServerError` function (was equivalent to shared).
- Removed local `runWithRetry` `useCallback` (was a hook-wrapped duplicate of the module-level shared function; closed over no component state).
- Removed `runWithRetry` from the `fetchDetail` useCallback dependency array (module-level imports are not valid deps per `react-hooks/exhaustive-deps`).
- Added import `{ isNetworkOrServerError, runWithRetry }` from `../../../utils/http`.
- Kept `import axios from 'axios'`: still needed for inline `axios.isAxiosError` error message extraction in catch blocks.

**`frontend/src/pages/receiving/ReceivingPage.tsx`**
- Removed local `isNetworkOrServerError` function (was equivalent to shared).
- Removed local `getApiErrorBody` function (was equivalent to shared).
- Removed local `ApiErrorBody` interface (duplicate of shared; the specific `ApiErrorDetails` sub-interface was also removed as it was only used by the local `ApiErrorBody`).
- Removed local `runWithRetry` `useCallback` (was a hook-wrapped duplicate of the module-level shared function).
- Removed `runWithRetry` from all five useCallback dependency arrays where it appeared.
- Added import `{ getApiErrorBody, isNetworkOrServerError, runWithRetry }` from `../../utils/http`.
- Kept `import axios from 'axios'`: still needed at line `const notFound = axios.isAxiosError(error) && error.response?.status === 404` in `resolveArticle`.
- Kept local `CONNECTION_ERROR_MESSAGE`: **intentionally not converged** — wording differs from shared English message (`'Greška povezivanja...'` vs `'Connection error...'`). Converging would change user-facing Croatian copy, which is out of scope for this phase.

**`frontend/src/components/layout/SetupGuard.tsx`**
- Removed local `CONNECTION_ERROR_MESSAGE` constant (was identical to shared).
- Added import `{ CONNECTION_ERROR_MESSAGE }` from `../../utils/http`.

**`frontend/src/pages/auth/SetupPage.tsx`**
- Removed local `CONNECTION_ERROR_MESSAGE` constant (was identical to shared).
- Added import `{ CONNECTION_ERROR_MESSAGE }` from `../../utils/http`.
- No other changes: error handling uses `isRetryableSetupRequestError` from `setup.ts` and inline `axios.isAxiosError` — these are custom setup-flow patterns, not duplicates of the shared HTTP helpers.

## Blob-Download Flows Audited

All `responseType: 'blob'` call sites found via codebase search:

| File | Blob call | Error handler fixed? |
|---|---|---|
| `frontend/src/api/reports.ts` — `downloadReport()` | `client.get(..., { responseType: 'blob' })` | No handler at API layer; error propagates to callers |
| `ReportsPage.tsx` — `handleStockExport` | calls `reportsApi.exportStockOverview` | Yes — now `await getApiErrorBodyAsync` |
| `ReportsPage.tsx` — `handleSurplusExport` | calls `reportsApi.exportSurplus` | Yes — now `await getApiErrorBodyAsync` |
| `ReportsPage.tsx` — `handleTransactionsExport` | calls `reportsApi.exportTransactions` | Yes — now `await getApiErrorBodyAsync` |
| `frontend/src/api/orders.ts` — `downloadPdf()` | `client.get(..., { responseType: 'blob' })` | No handler at API layer; error propagates |
| `OrderDetailPage.tsx` — `handleDownloadPdf` | calls `ordersApi.downloadPdf` | Yes — now `await getApiErrorBodyAsync` |
| `frontend/src/api/articles.ts` — `downloadBarcode()` | `client.get(..., { responseType: 'blob' })` | Already correct in `ArticleDetailPage.tsx` (reference) |
| `frontend/src/api/articles.ts` — `downloadBatchBarcode()` | `client.get(..., { responseType: 'blob' })` | Already correct in `ArticleDetailPage.tsx` (reference) |

No additional blob-download flows discovered beyond the above.

## Commands Run

```
cd /Users/grzzi/Desktop/STOQIO/frontend && npm run lint -- --max-warnings=0
# Result: 0 errors, 0 warnings — exit 0

cd /Users/grzzi/Desktop/STOQIO/frontend && npm run build
# Result: tsc + vite build — exit 0, 27 chunks generated
```

## Tests

None. No frontend test harness exists in this repo. Per orchestrator.md, the Testing Agent is responsible for adding minimal automated coverage for the blob-download failure scenarios. This agent's verification was code-path review plus lint/build.

## Open Issues / Risks

- **ReceivingPage `CONNECTION_ERROR_MESSAGE`** (intentionally skipped): The local message is in Croatian; the shared constant is English. Converging would change user-visible copy. Logged here per handoff rules. If the shared constant is localized in a future phase, this page should be revisited.
- **Inline `axios.isAxiosError` error extraction in DraftEntryPage and DraftGroupCard**: These catch blocks extract `err.response?.data?.message` directly without going through `getApiErrorBody`. This is not a blob-download flow and is not duplicating any shared helper — it's a custom inline pattern. Out of scope for this phase. The Testing Agent should be aware these handlers exist and are not covered by the shared helper convergence.
- **SetupPage inline axios usage**: Error extraction at submit uses `axios.isAxiosError` directly with field-specific branching. Not a duplicate of shared helpers. Left unchanged.

## Next Recommended Step

Delegate to Testing Agent to add minimal automated coverage for:
1. Reports export blob-error failure → correct toast message
2. Order PDF download blob-error failure → correct toast message
3. Regression smoke for retry/error behavior on touched pages
