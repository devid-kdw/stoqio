## Phase Summary

Phase
- Wave 9 - Phase 3 - Identifier Order Visibility

Objective
- Remediate W9-F-007:
  Identifier should stop surfacing surplus and instead show role-sensitive stock/order/purchase
  visibility.

Source Docs
- `handoff/README.md`
- `handoff/wave-09/README.md`
- `handoff/Findings/wave-09-user-feedback.md`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/14_UI_IDENTIFIER.md`
- `frontend/src/api/identifier.ts`
- `frontend/src/pages/identifier/IdentifierPage.tsx`
- `frontend/src/pages/identifier/identifierUtils.ts`
- `backend/app/services/article_service.py`
- `backend/tests/test_articles.py`
- `backend/tests/test_aliases.py`

Current Repo Reality
- Identifier currently returns `stock` + `surplus` to non-VIEWER roles and `in_stock` only to
  `VIEWER`.
- The Identifier result card shows `Na stanju` and `Višak`.
- There is no Identifier field for ordered status, ordered quantity, or latest purchase price.

Contract Locks / Clarifications
- Remove `Višak` from Identifier.
- Role visibility is now:
  - `ADMIN` and `MANAGER`: exact stock quantity, `je li naručeno`, `koliko je naručeno`,
    `zadnja nabavna cijena`
  - `WAREHOUSE_STAFF` and `VIEWER`: `je li na stanju`, `je li naručeno`
- `Koliko je naručeno` means the sum of still-outstanding quantities across all open purchase
  orders for the article. If the article appears on multiple open orders, the quantities must be
  summed.
- `Je li naručeno` is `true` when the summed outstanding ordered quantity is greater than zero.
- `Zadnja nabavna cijena` should align with the accepted pricing source hierarchy already used
  elsewhere; if a fallback beyond the latest relevant receiving price is needed, document it.

File Ownership
- `backend/app/services/article_service.py`
- `backend/tests/test_articles.py`
- `backend/tests/test_aliases.py` (only if identifier alias coverage is touched)
- `frontend/src/api/identifier.ts`
- `frontend/src/pages/identifier/IdentifierPage.tsx`
- `frontend/src/pages/identifier/identifierUtils.ts`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/14_UI_IDENTIFIER.md`
- `handoff/wave-09/phase-03-wave-09-identifier-order-visibility/backend.md`
- `handoff/wave-09/phase-03-wave-09-identifier-order-visibility/frontend.md`
- `handoff/wave-09/phase-03-wave-09-identifier-order-visibility/testing.md`

Delegation Plan
- Backend:
  - update Identifier serialization to be role-aware beyond the old VIEWER split
  - compute ordered visibility from open-order outstanding quantities
  - expose latest purchase price for ADMIN/MANAGER
  - extend tests for the new role matrix
- Frontend:
  - update Identifier result card layout to remove surplus and render the new fields
  - preserve good readability for both exact-quantity and boolean-only roles
  - localize any new labels/copy
- Testing:
  - verify role-sensitive result shapes and UI behavior

Acceptance Criteria
- Identifier no longer shows `Višak`.
- ADMIN and MANAGER see exact stock, ordered quantity, and latest purchase price.
- WAREHOUSE_STAFF and VIEWER see only in-stock and ordered booleans.
- Ordered quantity sums across multiple open orders for the same article.
- Docs and tests reflect the new Identifier contract.

Validation Notes
- 2026-04-11: Orchestrator opened Wave 9 Phase 3 from the finalized Wave 9 feedback intake.

Next Action
- Backend, frontend, and testing workers implement and record their handoffs.
