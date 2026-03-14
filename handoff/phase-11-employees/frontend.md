# Phase 11 — Employees Frontend

## Status
COMPLETE

## Scope
Implemented the full Employees UI for ADMIN and WAREHOUSE_STAFF:
- `frontend/src/api/employees.ts` — all 10 API methods with TypeScript types
- `frontend/src/pages/employees/EmployeesPage.tsx` — list page
- `frontend/src/pages/employees/EmployeeDetailPage.tsx` — detail page with quota overview, issuance history, issuance form
- `frontend/src/routes.tsx` — replaced placeholder routes with real lazy-loaded pages

## Docs Read
- stoqio_docs/15_UI_EMPLOYEES.md
- stoqio_docs/03_RBAC.md
- stoqio_docs/08_SETUP_AND_GLOBALS.md (§4, §5)
- handoff/README.md
- handoff/decisions/decision-log.md (DEC-EMP-001, DEC-EMP-002, DEC-BE-003)
- handoff/phase-11-employees/backend.md

## Files Changed
| File | Action |
|------|--------|
| frontend/src/api/employees.ts | Created — all types + employeesApi (10 methods) |
| frontend/src/pages/employees/EmployeesPage.tsx | Created — list, search, pagination, create modal |
| frontend/src/pages/employees/EmployeeDetailPage.tsx | Created — detail, edit, deactivate, quotas, issuances, issuance form |
| frontend/src/routes.tsx | Updated — lazy imports + Suspense for /employees and /employees/:id |

## Commands Run
```
cd frontend && npm run lint -- --max-warnings=0   # 0 errors, 0 warnings
cd frontend && npm run build                       # ✓ built in 1.93s
```

## Tests
No frontend unit tests added (not in scope per project baseline — other pages have no unit tests). Lint and build used as verification per task specification.

## Feature Summary

### EmployeesPage.tsx
- Debounced search (400ms) across employee_id, first_name, last_name
- "Prikaži neaktivne" checkbox toggle
- Paginated table (50/page): Šifra, Ime i prezime, Radno mjesto, Odjel, Status
- Row click navigates to `/employees/:id`
- ADMIN: "Novi zaposlenik" button opens create modal
- WAREHOUSE_STAFF: no create action visible
- Create form: employee_id (required), first_name (required), last_name (required), department, job_title, is_active
- Inline validation + 409 conflict handling for duplicate employee_id
- Full-page error on connection failure with retry

### EmployeeDetailPage.tsx
- Parallel initial load: employee + quotas + issuances (page 1)
- Full-page error on load failure; loading spinner while fetching
- Header: full name, status badge, Edit/Deactivate buttons (ADMIN only)
- Deactivate: inline confirmation alert before PATCH /deactivate
- Edit: inline form within page (not modal), pre-filled from current data
- Employee info card: employee_id, department, job_title, created_at
- Quota overview (prominent): table with Artikl/Kategorija, Kvota, Primljeno, Preostalo, Pravilo, Status
  - Category-level rows (article_id=null): show category_label_hr + "(kategorija)"
  - Status badges: U redu (green), Upozorenje (yellow), Prekoračeno (red)
  - Empty state for ADMIN: text + button to /settings; for WAREHOUSE_STAFF: text only
- Issuance history (paginated, 10/page, newest first): Datum, Artikl br., Opis, Količina, Serija, Izdao/la, Napomena
  - issued_by shown as username string (direct from backend, no extra lookup needed)
- Issuance form modal (ADMIN only):
  - Article search (debounced 400ms, dedicated /lookups/articles endpoint, personal-issue only)
  - Custom dropdown below TextInput (mousedown+blur handling)
  - Quantity: NumberInput with decimal_display-aware step/scale
  - Batch: conditional Select (FEFO-ordered batches from lookup result); inline error if no batches available
  - Note: Textarea, max 1000 chars
  - Check state machine: idle → checking → (blocked | warned | creating)
  - BLOCKED: Alert shown, submit disabled
  - WARNING: Alert shown, submit changes to "Potvrdi i izdaj"
  - On success: toast, close modal, refresh quotas + issuances

### RBAC
- WAREHOUSE_STAFF: sees list, detail, quota overview, issuance history only
- All create/edit/deactivate/issue actions gated behind `isAdmin` flag
- issuance lookup endpoint is ADMIN-only (enforced by backend; form not rendered for WAREHOUSE_STAFF)

## Open Issues / Risks
- Settings page is still a Placeholder — the "Upravljanje kvotama u Postavkama" button navigates to `/settings` which shows the scaffold. This is intentional per project state (Settings not yet implemented).
- No unit tests for frontend components (consistent with project baseline).

## Next Recommended Step
Testing agent: validate RBAC boundaries, issuance quota check flow, and WAREHOUSE_STAFF read-only behavior end-to-end.
