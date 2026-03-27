## 2026-03-27 17:42:54 CET

### Status
Complete

### Scope
Croatian-first copy cleanup for the owned login/setup/fatal-state/auth-bootstrap frontend surfaces, plus convergence of the shared connection-error baseline used by those screens.

### Docs Read
- `handoff/README.md`
- `handoff/phase-03-wave-02-croatian-first-localization/orchestrator.md`

### Files Changed
- `frontend/src/utils/http.ts`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/orders/OrderDetailPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`

### Commands Run
- `npm exec eslint src/utils/http.ts src/pages/auth/LoginPage.tsx src/components/layout/SetupGuard.tsx src/pages/drafts/DraftEntryPage.tsx src/pages/approvals/ApprovalsPage.tsx src/pages/receiving/ReceivingPage.tsx src/pages/orders/OrderDetailPage.tsx src/pages/auth/SetupPage.tsx`
- `date '+%Y-%m-%d %H:%M:%S %Z'`

### Tests
- Passed: targeted ESLint run on the edited frontend files.

### Open Issues / Risks
- None observed in the edited surfaces. The shared `CONNECTION_ERROR_MESSAGE` update will also affect any other existing consumer of that constant.

### Next Recommended Step
- Wait for backend/testing handoffs, then do a quick browser smoke check of login, setup, and the fatal-state pages if needed.
