# Phase 03 Verification Commands

Use these commands from the repo root if a local manual smoke check is needed after Phase 03.

## Backend - existing installation via SQLite

```bash
cd backend
export DATABASE_URL=sqlite:///phase3_manual_verify.db
export FLASK_ENV=development
export JWT_SECRET_KEY=test-secret

python -m alembic upgrade head
python seed.py
python seed_location.py
python diagnostic.py
```

Expected:
- `seed.py` reports admin/reference data created or skipped
- `seed_location.py` reports location created or skipped
- `diagnostic.py` shows user `admin` exists and `Password 'admin123' match: True`

## Backend - run dev server

```bash
cd backend
export DATABASE_URL=sqlite:///phase3_manual_verify.db
export FLASK_ENV=development
export JWT_SECRET_KEY=test-secret

python run.py
```

## Frontend - run dev server

```bash
cd frontend
npm install
npm run dev
```

## Manual browser checks

1. Open `http://127.0.0.1:5173/login`
2. Log in with `admin / admin123`
3. Confirm redirect to `/approvals`
4. Confirm sidebar shows ADMIN modules
5. Click `Logout` and confirm redirect to `/login`
6. Log in as a non-admin test user and confirm unauthorized routes redirect to that role's home route
