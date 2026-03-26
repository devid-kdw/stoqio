# STOQIO Wave 1 Recap

**Date closed:** 2026-03-26  
**Status:** Closed  
**Scope:** short recap of the first post-V1 improvement wave

## 1. What Wave 1 was

Wave 1 was not a new product baseline from scratch. It was a focused follow-up wave on top of the already delivered V1, aimed at removing real workflow friction, tightening UI/API contracts, and landing a few targeted additive features without broad module rewrites.

## 2. Main outcomes

- Operator/admin workflows were polished across Draft Entry, Approvals, Receiving, Inventory, and related status visibility flows.
- Warehouse and Reports received additive improvements instead of redesigns:
- better dropdown preload/search behavior
- stock overview value visibility
- Warehouse create/edit UX fixes
- article-level statistics on Warehouse detail
- Cross-cutting frontend/backend cleanup landed:
- shared integer-UOM source
- localized backend API `message` strings
- auth reload persistence
- system-wide dark-mode baseline
- Wave 1 kept building on the existing docs-first + handoff-first process, so important contract changes and remediations remain discoverable for future agents.

## 3. Final phase in the wave

Wave 1 ended with **Phase 13 Wave 1 - Article Statistics + Dark Mode**:

- added `GET /api/v1/articles/{id}/stats`
- added lazy article statistics UI on Warehouse article detail
- added persisted light/dark color-scheme toggle
- remediated the first-pass drift so the final article-stats contract matches the delegated shape

## 4. Important baseline shifts future agents should remember

- Wave folders are follow-up phases on top of the original numbered phases; they are not replacements for the original phase folders.
- Handoff + decision log take precedence over older docs when there is proven drift.
- The final Wave 1 closeout for the last phase is recorded in:
- `handoff/phase-13-wave-01-article-stats-dark-mode/orchestrator.md`

## 5. Final verification snapshot

At Wave 1 closeout:

- backend targeted article tests -> `40 passed`
- backend full suite -> `343 passed`
- frontend lint -> passed
- frontend production build -> passed

## 6. Closeout

Wave 1 is complete and should now be treated as part of the active baseline for any future bugfix or feature work.
