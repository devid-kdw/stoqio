# Wave 7 Handoffs

This folder stores all Wave 7 remediation handoff folders.

Use the existing `handoff/README.md` protocol and create one subfolder per phase in the format:

- `phase-NN-wave-07-*`

## Wave 7 Purpose

Wave 7 is the remediation wave for findings surfaced in the dual-agent post-Wave-6 code review
performed on 2026-04-08 (source documents: `handoff/Findings/wave-06-post-hardening-code-review-findings.md`
and `handoff/Findings/wave-06-second-opinion-review.md`).

It addresses all High, Medium, and selected Low/New severity findings across five ownership domains:
backend concurrency/transactional integrity, backend DB schema integrity, backend process and docs
cleanup, frontend auth and domain fixes, and infrastructure hardening.

This is not a feature wave. Every change must be traceable to a specific numbered finding from the
source documents. Scope creep is not permitted.

## Phases

| Phase | Owner | Primary Findings | Can run in parallel |
|-------|-------|-----------------|---------------------|
| `phase-01-wave-07-backend-concurrency-hardening` | Backend | H-1, H-2, H-3, H-4, N-1, M-3 | Yes |
| `phase-02-wave-07-backend-schema-integrity` | Backend | M-1, M-2, N-5 | Yes |
| `phase-03-wave-07-backend-process-and-docs` | Backend | M-8, L-1, N-4, L-3, L-4, L-5, L-6, L-7 | Yes |
| `phase-04-wave-07-frontend-auth-and-domain` | Frontend | M-5, M-6, N-6, H-5, L-2, M-4, M-9 | Yes |
| `phase-05-wave-07-infrastructure` | Backend + DevOps | M-7, N-3 | Yes |

All five phases touch non-overlapping files and can run simultaneously.

**File ownership per phase (no overlaps):**
- Phase 1: `approval_service.py`, `inventory_service.py`, `employee_service.py`
- Phase 2: `stock.py`, `surplus.py`, `batch.py`, `inventory_count.py` (model layer) + new Alembic migrations
- Phase 3: `seed.py`, `app/api/reports/routes.py`, `app/utils/auth.py`, `README.md`, `requirements.lock`, handoff Wave 6 docs
- Phase 4: `authStore.ts`, `client.ts`, `ProtectedRoute.tsx`, `SettingsPage.tsx`, `warehouseUtils.ts`, `WarehousePage.tsx`, `api/reports.ts`, `pages/reports/reportsUtils.ts`
- Phase 5: `scripts/deploy.sh`, `.github/workflows/ci.yml` (new)

## Finding Reference

Source: `handoff/Findings/wave-06-post-hardening-code-review-findings.md` (original agent)
         `handoff/Findings/wave-06-second-opinion-review.md` (second-opinion orchestrator)

| ID  | Description | Phase |
|-----|-------------|-------|
| H-1 | Approval quantities editable after approval/rejection | 1 |
| H-2 | Approval double-spend — intra-bucket race | 1 |
| H-3 | Inventory count start/complete race-prone | 1 |
| H-4 | Employee issuance can overspend stock | 1 |
| N-1 | approve_all() has no group-level lock | 1 |
| M-3 | Employee issuance accepts arbitrary client UOM | 1 |
| M-1 | Stock/surplus NULL batch_id uniqueness incomplete | 2 |
| M-2 | Batch lookup can create duplicates under race | 2 |
| N-5 | InventoryCountLine has no uniqueness constraint | 2 |
| M-8 | seed.py creates admin with pbkdf2 | 3 |
| L-1 | Report pagination malformed int returns 500 | 3 |
| N-4 | Transaction log pagination passes unparsed strings | 3 |
| L-3 | Stale pbkdf2 wording in auth.py | 3 |
| L-4 | Wave 6 frontend handoff stale about eslint-plugin-security | 3 |
| L-5 | Wave 6 verification notes conflict | 3 |
| L-6 | README revoked-token cleanup docs outdated | 3 |
| L-7 | requirements.lock contains stale python-barcode | 3 |
| M-5 | Refreshed tokens do not refresh frontend user/role state | 4 |
| M-6 | Settings self role edit leaves frontend auth state stale | 4 |
| N-6 | ProtectedRoute has no loading state | 4 |
| H-5 | Editing warehouse article overwrites density with 1 | 4 |
| L-2 | Warehouse article create does not refresh the list | 4 |
| M-4 | Reports pagination/export contract incomplete | 4 |
| M-9 | Report default dates use UTC not local | 4 |
| M-7 | Deploy has no real rollback path | 5 |
| N-3 | No CI/CD pipeline | 5 |
| N-2 | check_issuance dry-run not bound to create_issuance | documented only (Phase 1 backend.md) |
