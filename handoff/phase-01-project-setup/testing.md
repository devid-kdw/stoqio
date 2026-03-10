# Testing Handoff

Reserved for testing agent entries. Append only.

---

## 2026-03-10 16:34 Testing Agent — Phase 1 Verification

Status
- PARTIAL PASS - Backend and frontend startup verified; proxy blocked by macOS AirPlay Receiver

Scope
- Verify backend starts with `flask run`
- Verify frontend starts with `npm run dev`
- Verify proxy from frontend dev server to backend `/api/v1/health`

Docs Read
- `stoqio_docs/07_ARCHITECTURE.md` §5 (Pi deployment), §6 (development workflow)
- `handoff/README.md`
- `handoff/phase-01-project-setup/orchestrator.md`
- `handoff/phase-01-project-setup/backend.md`
- `handoff/phase-01-project-setup/frontend.md`

Files Changed
- None (testing agent does not modify product code)

Commands Run
```bash
# Backend verification
cd backend
pip install -r requirements.txt              # SUCCESS - all dependencies installed
source venv/bin/activate && FLASK_APP=app FLASK_ENV=development flask run --port 5000
                                             # SUCCESS - Flask starts on 127.0.0.1:5000
curl -s http://127.0.0.1:5000/api/v1/health  # SUCCESS - returns {"status":"ok"}

# Frontend verification
cd frontend
npm run dev -- --port 3000 --host 127.0.0.1  # SUCCESS - Vite starts on 127.0.0.1:3000
curl -s http://127.0.0.1:3000/               # SUCCESS - returns Vite HTML page

# Proxy verification
curl -s http://127.0.0.1:3000/api/v1/health  # FAILURE - returns 403 Forbidden from AirTunes
curl -s http://localhost:5000/api/v1/health  # FAILURE - returns 403 Forbidden from AirTunes
curl -s http://127.0.0.1:5000/api/v1/health  # SUCCESS - returns {"status":"ok"}
```

Tests
- Passed: Backend starts with `flask run`
- Passed: `/api/v1/health` returns `{"status":"ok"}` via direct IPv4 access (`127.0.0.1:5000`)
- Passed: Frontend starts with `npm run dev`
- Passed: Frontend serves index.html correctly
- **FAILED**: Proxy from frontend to backend blocked by macOS AirPlay Receiver

Open Issues / Risks

### BLOCKER: macOS AirPlay Receiver Intercepts `localhost:5000`

**Root cause**: macOS ControlCenter (AirPlay Receiver) binds to `*:5000` on both IPv4 and IPv6. When DNS resolves `localhost` to IPv6 `::1`, requests hit AirPlay instead of Flask.

**Evidence**:
```
$ lsof -i :5000
ControlCe  599 grzzi  11u  IPv4  TCP *:5000 (LISTEN)       # AirPlay on all interfaces
ControlCe  599 grzzi  12u  IPv6  TCP *:5000 (LISTEN)       # AirPlay on all interfaces
Python   14334 grzzi   4u  IPv4  TCP 127.0.0.1:5000 (LISTEN) # Flask on localhost only

$ curl -s http://127.0.0.1:5000/api/v1/health
{"status":"ok"}   # Flask responds

$ curl -s http://localhost:5000/api/v1/health
(empty, 403 Forbidden from AirTunes)  # AirPlay intercepts
```

**Vite config** (`frontend/vite.config.ts` line 10):
```ts
target: 'http://localhost:5000',  // resolves to IPv6, hits AirPlay
```

**Fix options** (requires orchestrator approval):
1. **Config fix**: Change Vite proxy target from `localhost` to `127.0.0.1`
   - File: `frontend/vite.config.ts` line 10
   - Change: `target: 'http://127.0.0.1:5000'`
2. **Environment fix**: Disable AirPlay Receiver in macOS System Settings → General → AirDrop & Handoff → AirPlay Receiver
3. **Port change**: Use a different port for Flask (e.g., 5050)

**Impact**: Proxy verification cannot complete on macOS machines with AirPlay Receiver enabled until one of the above fixes is applied.

### Minor: Backend venv needed pip install

Backend handoff noted that `pip install` failed during agent session. Testing agent successfully ran `pip install -r requirements.txt` in the venv, installing Flask 3.1.3 and all dependencies.

Next Recommended Step
- Orchestrator to approve one of the proxy fix options above
- After fix, re-run proxy verification: `curl http://127.0.0.1:3000/api/v1/health` should return `{"status":"ok"}`
- Proceed to Phase 2 once proxy verification passes

---

## 2026-03-10 16:47 Testing Follow-up — Post-Fix Reverification

Status
- completed

Scope
- Re-run Phase 1 verification after orchestrator-applied backend/frontend fixes.
- Confirm that the previous proxy blocker is resolved and that the Phase 1 acceptance criteria now pass.

Docs Read
- `handoff/phase-01-project-setup/testing.md`
- `handoff/phase-01-project-setup/backend.md`
- `handoff/phase-01-project-setup/frontend.md`
- `handoff/phase-01-project-setup/orchestrator.md`

Files Changed
- None (verification only)

Commands Run
```bash
backend/venv/bin/flask run --port 5000
npm run dev -- --host 127.0.0.1 --port 3000
curl -s http://127.0.0.1:5000/api/v1/health
curl -s http://127.0.0.1:3000/api/v1/health
backend/venv/bin/pytest backend/tests -v
cd frontend && npm run build && npm run lint -- --max-warnings=0
```

Tests
- Passed: direct backend health check returns `{"status":"ok"}` on `127.0.0.1:5000`
- Passed: frontend dev server starts on `127.0.0.1:3000`
- Passed: proxy health check through Vite returns `{"status":"ok"}` on `127.0.0.1:3000/api/v1/health`
- Passed: `backend/venv/bin/pytest backend/tests -v`
- Passed: `npm run build`
- Passed: `npm run lint -- --max-warnings=0`
- Failed: None
- Not run: manual browser interaction beyond HTTP smoke checks

Open Issues / Risks
- Previous `localhost:5000` proxy blocker is resolved by targeting `127.0.0.1:5000`.
- Development-server verification depends on local machine policy allowing binds to ports `5000` and `3000`.

Next Recommended Step
- Mark Phase 1 fully verified and proceed to Phase 2.
