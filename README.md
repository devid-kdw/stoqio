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
