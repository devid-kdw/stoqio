# Frontend — Phase 11 Wave 1: Warehouse Form UX Fixes

## Status
DONE

## Scope
Two targeted UX fixes in the Warehouse article form flow:
1. New-article post-save redirect: after `articlesApi.create(...)` succeeds, redirect to `/warehouse` (not to the article detail page).
2. Switch hit areas: wrap each Switch in a `width: fit-content` container so clicking empty right-side space in the grid cell does not toggle the switch.

## Docs Read
- `handoff/README.md`
- `handoff/phase-11-wave-01-warehouse-form-ux-fixes/orchestrator.md`
- `frontend/src/pages/warehouse/WarehousePage.tsx` (read before editing)
- `frontend/src/pages/warehouse/WarehouseArticleForm.tsx` (read before editing)
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx` (read; no changes needed)

## Files Changed

### `frontend/src/pages/warehouse/WarehousePage.tsx`
- Line ~280: removed assignment of `createdArticle` (no longer needed for redirect).
- Changed `navigate(`/warehouse/articles/${createdArticle.id}`)` → `navigate('/warehouse')`.
- Success toast and `handleCloseCreate()` call retained unchanged.

### `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
- Lines 211-225: wrapped each `Switch` in `<div style={{ width: 'fit-content' }}>`.
- Labels `Artikl sa šaržom` and `Aktivan artikl` unchanged.
- No other form behavior touched.

## Commands Run
```
cd frontend && npm run lint -- --max-warnings=0   → 0 warnings, exit 0
cd frontend && npm run build                       → tsc + vite, exit 0
```

## Tests

Manual verification (browser):
- Create new article → save → lands on `/warehouse`. ✓
- Edit existing article → save → remains on article detail page. ✓ (ArticleDetailPage.tsx not modified; `applyArticleState` + `showSuccessToast` flow unchanged.)
- Clicking empty space to the right of `Artikl sa šaržom` switch: does NOT toggle. ✓
- Clicking directly on `Artikl sa šaržom` switch label/toggle: toggles normally. ✓
- Clicking empty space to the right of `Aktivan artikl` switch: does NOT toggle. ✓
- Clicking directly on `Aktivan artikl` switch label/toggle: toggles normally. ✓

## Open Issues / Risks
None. No backend contract changes. No hidden dependencies discovered.

## Next Recommended Step
Orchestrator validation and phase close-out.
