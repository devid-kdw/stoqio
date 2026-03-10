# Decision Log

## Entry Template

- Date:
- Phase:
- Source:
- Decision:
- Impact:
- Docs update required: yes | no

---

## DEC-FE-002

- Date: 2026-03-10
- Phase: phase-01-project-setup
- Source: Testing feedback reviewed by orchestrator during Phase 1 reverification
- Decision: For local frontend-to-backend development proxying, use `http://127.0.0.1:5000` instead of `http://localhost:5000` as the default Vite proxy target.
- Impact: Avoids macOS AirPlay Receiver conflicts on port `5000` when `localhost` resolves to IPv6/`::1`; makes Phase 1 proxy verification reliable on affected machines.
- Docs update required: yes

---

## DEC-FE-001

- Date: 2026-03-10
- Phase: phase-01-project-setup
- Source: Frontend agent observation during scaffolding
- Decision: `npm install` and `npx` commands that hit the npm registry must be run directly in the user's terminal, not via agent tooling. The agent execution sandbox does not have socket bind permission for DNS resolution (macOS `isc_socket_bind: Operation not permitted`), causing all npm registry requests to fail with `ENOTFOUND`. This is an environment constraint, not a project constraint.
- Impact: All future frontend phases requiring new npm packages must instruct the user to run `npm install <pkg>` themselves, or the command must be listed in the handoff "Commands Run" section for manual execution.
- Docs update required: no

---
