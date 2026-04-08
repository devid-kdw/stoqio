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
FLASK_ENV=development venv/bin/python seed.py
flask run
```

> **Local development only.** `backend/seed.py` is a local development
> bootstrap tool. It generates a one-time random admin password and prints it
> once after a successful seed run. **Never run `seed.py` on a production or
> shared instance.** The authenticated first-run setup flow creates only the
> initial `Location`; it does **not** create the first admin account. This repo
> does not automate production/shared bootstrap of the initial admin user. On
> those installs, provision the first `ADMIN` account through a separate
> trusted operator process, then complete authenticated first-run setup and
> supply a strong `JWT_SECRET_KEY` and a valid `DATABASE_URL` in the
> environment.

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

The command deletes only `revoked_token` rows whose `expires_at` is already in the past. It does not remove active revocations and does not touch `expires_at IS NULL` rows.

Automatic cleanup also runs via a `before_request` hook registered in `app/__init__.py`. It executes at most once per hour (guarded by a process-level timestamp) and removes the same expired rows. This means the table self-cleans on active instances without any operator intervention. The manual CLI command remains useful for immediate cleanup or for instances that receive infrequent traffic.

Run it after the deploy that introduces this phase and then on a periodic local-server schedule if the instance keeps long-lived refresh-token history. The standard `./scripts/deploy.sh` flow already applies backend migrations; if you deploy manually, apply backend migrations before the first cleanup run.

## Deployment

`./scripts/build.sh` now installs frontend dependencies from `frontend/package-lock.json` with `npm ci` before building. `./scripts/deploy.sh` expects a backend virtualenv interpreter, defaults to `backend/venv/bin/python`, and allows overrides via `BACKEND_VENV_DIR` or `BACKEND_PYTHON` when needed.

Typical local-host deploy flow:

```bash
./scripts/deploy.sh
```

If the backend virtualenv does not live at `backend/venv`, set `BACKEND_PYTHON` explicitly before running the deploy script.
