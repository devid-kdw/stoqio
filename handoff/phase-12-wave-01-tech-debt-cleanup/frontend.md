# Frontend Agent — Phase 12 Wave 1 Tech Debt Cleanup

## Status

Done — all acceptance criteria met. Lint and build pass with zero warnings.

## Scope

- Centralized the integer-UOM list to a single shared source (`frontend/src/utils/uom.ts`).
- Replaced all 7 duplicate literal definitions across the frontend with imports from the shared source.
- Added `Accept-Language` header to every API request via the axios request interceptor in `client.ts`, using the currently active i18n language, normalized to supported app languages (`hr`, `en`, `de`, `hu`).

## Docs Read

- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-I18N-001)
- `handoff/phase-12-wave-01-tech-debt-cleanup/orchestrator.md`
- `frontend/src/api/client.ts`
- `frontend/src/i18n/index.ts`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/orders/orderUtils.ts`
- `frontend/src/pages/employees/EmployeeDetailPage.tsx`
- `frontend/src/pages/reports/reportsUtils.ts`
- `frontend/src/pages/warehouse/warehouseUtils.ts`

## Files Changed

### New

- `frontend/src/utils/uom.ts` — exports `INTEGER_UOMS: string[] = ["kom", "pak", "pár"]` as the single source of truth.

### Modified

- `frontend/src/api/client.ts` — added `import i18n`, `getAcceptLanguage()` helper (normalizes active i18n language to supported tag, falls back to `hr`), and sets `Accept-Language` header in the request interceptor. Auth/refresh/401 semantics unchanged.
- `frontend/src/pages/drafts/DraftEntryPage.tsx` — removed local `const INTEGER_UOMS = new Set([...])`, added import from shared util, changed `.has()` → `.includes()`.
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx` — same pattern.
- `frontend/src/pages/receiving/ReceivingPage.tsx` — same pattern.
- `frontend/src/pages/orders/orderUtils.ts` — removed `export const INTEGER_UOMS = new Set([...])`, added import from shared util, changed `.has()` → `.includes()`. Nothing imports `INTEGER_UOMS` from this module (verified by grep), so removing the export is safe.
- `frontend/src/pages/employees/EmployeeDetailPage.tsx` — same pattern.
- `frontend/src/pages/reports/reportsUtils.ts` — removed `const FALLBACK_INTEGER_UOMS = new Set([...])`, added import from shared util, changed `FALLBACK_INTEGER_UOMS.has(uom)` → `INTEGER_UOMS.includes(uom)`.
- `frontend/src/pages/warehouse/warehouseUtils.ts` — same as reportsUtils pattern.

## Commands Run

```
cd frontend && npm run lint -- --max-warnings=0   # PASS — no warnings
cd frontend && npm run build                       # PASS — clean build, 0 errors
```

## Tests

No frontend test suite exists in this repo. Verification was done by:
1. Lint: `npm run lint -- --max-warnings=0` — passes.
2. Build: `npm run build` — passes with TypeScript strict checks (tsc -b).
3. Code search: `grep -r "new Set.*kom\|pak\|pár"` on `frontend/src` — zero matches confirming no duplicate literals remain.
4. Code search: `grep -r "INTEGER_UOMS"` on `frontend/src` — all 7 consumer files import from `../../utils/uom` or `../../../utils/uom`; single definition in `utils/uom.ts`.
5. Reasoning: `getAcceptLanguage()` reads `i18n.language` at request time — since `settingsStore` calls `i18n.changeLanguage()` when loading or saving settings, language changes are reflected automatically on the next API call without any additional wiring.

## Open Issues / Risks

- None. The `Accept-Language` header is always sent, including on unauthenticated requests (login, refresh). This is intentional: the backend needs the language context to localize any error messages it may return on those paths too.
- The `INTEGER_UOMS` array export was previously a `Set` in `orderUtils.ts`. No other module imported it (confirmed by grep). The change is safe.

## Next Recommended Step

Backend agent should verify that `Accept-Language: hr` and other supported language tags are being parsed correctly from incoming requests and that the localized error messages are returned as expected per DEC-I18N-001.
