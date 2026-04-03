# WMS

Warehouse Management System monorepo. Designed for local host/server deployment inside the customer network (mini PC, local Linux server, local Windows server, or similar local hardware).

## Structure

- `backend/` - Flask API and React build serving
- `frontend/` - React + Vite web application
- `scripts/` - build and deployment helpers
- `stoqio_docs/` - product, architecture, and implementation documentation
- `handoff/` - inter-agent coordination and delivery trace

## Development

Backend:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
venv/bin/alembic upgrade head
venv/bin/python seed.py
flask run
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Local-host maintenance

The repository now ships a safe operator diagnostic helper and hardened deployment scripts:

```bash
cd backend
venv/bin/python diagnostic.py
```

`backend/diagnostic.py` reports only non-sensitive operational status. It does not print password hashes, password verification results, or other credential-sensitive data.

Expired revoked refresh-token rows can be cleaned up explicitly from the backend app:

```bash
cd backend
venv/bin/flask purge-revoked-tokens --dry-run
venv/bin/flask purge-revoked-tokens
```

The command deletes only `revoked_token` rows whose `expires_at` is already in the past. It does not remove active revocations, does not touch `expires_at IS NULL` rows, and is never run automatically on requests, startup, or logout.

Run it after the deploy that introduces this phase and then on a periodic local-server schedule if the instance keeps long-lived refresh-token history. The standard `./scripts/deploy.sh` flow already applies backend migrations; if you deploy manually, apply backend migrations before the first cleanup run.

## Deployment

`./scripts/build.sh` now installs frontend dependencies from `frontend/package-lock.json` with `npm ci` before building. `./scripts/deploy.sh` expects a backend virtualenv interpreter, defaults to `backend/venv/bin/python`, and allows overrides via `BACKEND_VENV_DIR` or `BACKEND_PYTHON` when needed.

Typical local-host deploy flow:

```bash
./scripts/deploy.sh
```

If the backend virtualenv does not live at `backend/venv`, set `BACKEND_PYTHON` explicitly before running the deploy script.
