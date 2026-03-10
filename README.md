# WMS

Warehouse Management System monorepo for Raspberry Pi deployment.

## Structure

- `backend/` - Flask API and future static asset serving
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
flask run
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```
