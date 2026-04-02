# STOQIO Wave 2 Recap

**Date closed:** 2026-04-02  
**Status:** Closed  
**Scope:** short recap of the second post-V1 hardening and alignment wave

## 1. What Wave 2 was

Wave 2 was a targeted hardening wave on top of the accepted V1 + Wave 1 baseline. Its purpose was not broad feature expansion, but closing real review findings, tightening runtime and migration contracts, improving operator-facing reliability, and bringing documentation back into line with the accepted code path.

An important process detail: multiple Wave 2 phases only reached the final accepted baseline after orchestrator review and, in a few cases, orchestrator direct fixes. Future agents should treat the accepted repo state plus the final orchestrator notes as the source of truth, not the first agent handoff in isolation.

## 2. Main outcomes

- Approvals now persist `DraftGroup.status = PARTIAL` as a real database state, with migration coverage that works on fresh SQLite and PostgreSQL upgrade paths.
- Frontend download/error handling was standardized around the shared HTTP utility layer, and the repo now has a lightweight frontend test harness with Wave 2 coverage in place.
- Login/setup/fatal-state UX was pushed to a Croatian-first baseline, including missing localized order-line domain errors.
- Startup/auth hardening landed:
- Production now fails fast on missing or blank `DATABASE_URL`
- the nonexistent-user login path no longer relies on a route-local dummy hash literal
- Inventory shortage linkage is now explicit through `Draft.inventory_count_id` instead of hidden `client_event_id LIKE ...` conventions, and shared query validators now replace multiple duplicated route helpers.
- The obsolete `backend/seed_location.py` path was retired. Fresh installs are now clearly documented as:
- migrations
- `backend/seed.py` for reference/admin seed data
- authenticated `/setup` for the single supported location
- Installation-wide shell branding now applies to all authenticated roles, not just `ADMIN`.
- Barcode handling now has two accepted runtime paths:
- PDF barcode download remains supported
- direct host printing to a configured network label printer is supported for article and batch labels
- Documentation was realigned to the accepted auth/session model, the local-host deployment baseline, and the barcode PDF + direct-print split.
- `handoff/` is now cycle-organized into `implementation/`, `wave-01/`, and `wave-02/`.

## 3. Final phase in the wave

Wave 2 ended with **Phase 9 - Docs Alignment + Handoff Reorg**:

- aligned auth-storage docs to the accepted memory-access-token + persisted-refresh-token model
- updated deployment wording from Raspberry-Pi-only assumptions to the broader local-host/server baseline
- clarified barcode docs around generation, PDF fallback, direct host printing, and future raw-label mode
- reorganized `handoff/` by delivery cycle and updated markdown references to the new structure

## 4. Important baseline shifts future agents should remember

- Auth storage baseline:
- access token is memory-only
- refresh token is persisted in browser `localStorage` under `stoqio_refresh_token`
- app bootstrap silently refreshes auth and loads `/auth/me` before protected routes render
- Deployment baseline:
- STOQIO is a local host/server product inside the customer network
- mini PC, local Linux server, local Windows server, and Raspberry Pi are all valid examples
- Barcode baseline:
- barcode generation exists
- PDF download exists
- direct host printing exists
- future raw-label/browser-direct mode is not implemented
- Handoff baseline:
- original numbered phases live under `handoff/implementation/`
- Wave 1 phases live under `handoff/wave-01/`
- Wave 2 phases live under `handoff/wave-02/`

## 5. Final verification snapshot

At Wave 2 closeout:

- backend full suite -> `440 passed in 35.24s`
- frontend tests -> `5 files passed, 19 tests passed`
- frontend lint -> passed
- frontend production build -> passed
- Phase 9 doc-layout verification -> no remaining markdown hits for `handoff/phase-`

## 6. Residual notes

- Real hardware smoke testing for the direct-printer flow is still an operator-side follow-up. The accepted software contract is in place, but label stock/layout verification on the actual Zebra hardware remains outside repo-only validation.
- Older review notes and historical handoff files may still mention past problems or earlier Raspberry Pi assumptions as historical context. Those are part of the project record and should not be mistaken for the active baseline when newer orchestrator closeout notes supersede them.

## 7. Closeout

Wave 2 is complete and should now be treated as part of the active STOQIO baseline. The current repo state reflects not just the initial agent deliveries, but the final accepted result after review, validation, and documented follow-up corrections.
