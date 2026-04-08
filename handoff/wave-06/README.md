# Wave 6 Handoffs

This folder stores all Wave 6 follow-up handoff folders.

Use the existing `handoff/README.md` protocol and create one subfolder per phase in the format:

- `phase-NN-wave-06-*`

## Wave 6 Purpose

Wave 6 is the remediation wave for the deep multi-agent security code review performed on
2026-04-08. It addresses all Critical, High, and selected Medium severity findings from that
review across four ownership domains: backend security core, backend authorization/IDOR,
frontend token handling, and deployment infrastructure.

This is not a feature wave. Every change must be traceable to a specific numbered finding
from the 2026-04-08 review report. Scope creep beyond the listed findings is not permitted.

## Phases

| Phase | Owner | Primary Findings |
|-------|-------|-----------------|
| `phase-01-wave-06-backend-security-core` | Backend | K-1, K-3, K-4, V-3, V-5, V-7, S-1, S-2, S-3 |
| `phase-02-wave-06-backend-idor-authorization` | Backend | K-2, V-4, V-12, N-1 |
| `phase-03-wave-06-frontend-security` | Frontend | V-8, S-7, S-9, N-6 |
| `phase-04-wave-06-infrastructure-hardening` | Backend + Frontend | V-6, V-10, V-11, S-10, S-12, N-7, N-9 |

Phases 01, 02, 03 can run in parallel. Phase 04 can also run in parallel with the others.
