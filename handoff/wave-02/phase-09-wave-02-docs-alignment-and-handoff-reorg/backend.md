## [2026-04-02] Backend Agent — Phase 9 Wave 02: Docs Alignment and Handoff Reorg

### Status
Done

### Scope
Reorganized `handoff/` into cycle-based folders and updated owned documentation to align with the accepted auth/session model and local-host runtime direction.

### Docs Read
- `README.md`
- `memory/MEMORY.md`
- `docs/v1-recap.md`
- `docs/wave-01-recap.md`
- `stoqio_docs/01_PROJECT_OVERVIEW.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md`
- `stoqio_docs/19_IMPLEMENTATION_PLAN.md`
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-FE-006, DEC-BE-012, DEC-BE-013)
- `handoff/implementation/phase-16-v1-stabilization/orchestrator.md`
- `frontend/src/store/authStore.ts`
- `frontend/src/main.tsx`
- `frontend/src/api/client.ts`

### Files Changed

**Handoff structure — folder moves**
- Created `handoff/implementation/`, `handoff/wave-01/`, `handoff/wave-02/`
- Moved all V1 phases (phase-01 through phase-16, phase-06-1-*, phase-06-2-*) into `handoff/implementation/`
- Moved all wave-01 phases into `handoff/wave-01/`
- Moved all wave-02 phases into `handoff/wave-02/`
- Created `handoff/wave-02/phase-09-wave-02-docs-alignment-and-handoff-reorg/` (this phase)

**Updated files**
- `handoff/README.md` — updated folder layout example and guidance to reflect cycle-based structure
- `README.md` — removed Pi-only framing; updated backend description from "future static asset serving" to actual behavior; deployment description now includes mini PC, local server examples
- `memory/MEMORY.md` — replaced Pi-only project overview with local server framing (Pi as valid option); replaced stale "in-memory Zustand (not localStorage)" auth line with full accepted persisted-refresh-token model (DEC-FE-006)
- `stoqio_docs/01_PROJECT_OVERVIEW.md` — updated business model, deployment diagram, tech stack table to reflect local server targets; Pi retained as valid/historical option
- `stoqio_docs/07_ARCHITECTURE.md` — updated: token storage section, state management comment, Section 5 heading/text from Pi-specific to local server, git workflow Pi references, code splitting note, summary table rows for auth/token/deployment
- `stoqio_docs/19_IMPLEMENTATION_PLAN.md` — updated Pi deployment reference in Phase 1 prompt and final checklist
- `docs/v1-recap.md` — updated deployment context sentence; updated handoff path references to nested paths; updated Val 2 smoke test item
- `docs/wave-01-recap.md` — updated path reference to final wave-01 phase orchestrator
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` — updated three handoff path evidence citations to new nested paths

### Commands Run
None (docs-only phase, no product code touched)

### Tests
Not applicable — no product code changed.

### Open Issues / Risks
- `stoqio_docs/18_UI_SETTINGS.md` line 147 still says "Raspberry Pi" in the barcode printer description. This is a frontend-owned file and was not touched per ownership rules.
- `stoqio_docs/06_SESSION_NOTES.md` contains Pi references as historical session context. These are session notes rather than active guidance docs and were not in scope.
- Phase-level historical docs in `handoff/implementation/` and `handoff/decisions/decision-log.md` retain original Pi wording as historical truth. This is correct — those records document what was decided at the time.

### Remaining Pi references verdict
All remaining "Raspberry Pi" hits in the grep output fall into one of:
1. **Frontend-owned files** (`stoqio_docs/18_UI_SETTINGS.md`) — not in scope.
2. **Historical session notes** (`stoqio_docs/06_SESSION_NOTES.md`) — not active guidance.
3. **Updated files** where Pi is now correctly listed as one valid option among others (not the only target).
4. **Immutable historical records** (decision log entries, historical phase handoff docs) — preserved as truth about what was in scope at the time.

### Next Recommended Step
Frontend agent to update the frontend-owned docs listed in the phase brief (`stoqio_docs/02_DOMAIN_KNOWLEDGE.md`, `stoqio_docs/04_FEATURE_SPEC.md`, `stoqio_docs/13_UI_WAREHOUSE.md`, `stoqio_docs/18_UI_SETTINGS.md`) per their portion of this phase scope.
