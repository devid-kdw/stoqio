# WMS — Architecture

**Status**: LOCKED — ne mijenjati bez eksplicitnog odobrenja vlasnika projekta
**Verzija**: v1

---

## 1. Folder struktura projekta

```
wms/
├── backend/
│   ├── app/
│   │   ├── __init__.py              ← create_app() factory
│   │   ├── extensions.py            ← db, jwt, migrate instance-i
│   │   ├── config.py                ← Config klase (Development, Production)
│   │   ├── models/                  ← SQLAlchemy modeli, jedan file po entitetu
│   │   │   ├── __init__.py
│   │   │   ├── article.py
│   │   │   ├── batch.py
│   │   │   ├── stock.py
│   │   │   ├── surplus.py
│   │   │   ├── draft.py
│   │   │   ├── draft_group.py
│   │   │   ├── approval_action.py
│   │   │   ├── receiving.py
│   │   │   ├── order.py
│   │   │   ├── order_line.py
│   │   │   ├── transaction.py
│   │   │   ├── inventory_count.py
│   │   │   ├── employee.py
│   │   │   ├── personal_issuance.py
│   │   │   ├── annual_quota.py
│   │   │   ├── supplier.py
│   │   │   ├── user.py
│   │   │   ├── location.py
│   │   │   ├── category.py
│   │   │   ├── uom_catalog.py
│   │   │   ├── missing_article_report.py
│   │   │   ├── system_config.py
│   │   │   └── role_display_name.py
│   │   ├── api/                     ← Flask blueprints po modulima
│   │   │   ├── __init__.py
│   │   │   ├── auth/
│   │   │   │   ├── __init__.py
│   │   │   │   └── routes.py
│   │   │   ├── articles/
│   │   │   │   ├── __init__.py
│   │   │   │   └── routes.py
│   │   │   ├── drafts/
│   │   │   │   ├── __init__.py
│   │   │   │   └── routes.py
│   │   │   ├── approvals/
│   │   │   │   ├── __init__.py
│   │   │   │   └── routes.py
│   │   │   ├── receiving/
│   │   │   │   ├── __init__.py
│   │   │   │   └── routes.py
│   │   │   ├── orders/
│   │   │   │   ├── __init__.py
│   │   │   │   └── routes.py
│   │   │   ├── warehouse/
│   │   │   │   ├── __init__.py
│   │   │   │   └── routes.py
│   │   │   ├── employees/
│   │   │   │   ├── __init__.py
│   │   │   │   └── routes.py
│   │   │   ├── inventory_count/
│   │   │   │   ├── __init__.py
│   │   │   │   └── routes.py
│   │   │   ├── reports/
│   │   │   │   ├── __init__.py
│   │   │   │   └── routes.py
│   │   │   └── settings/
│   │   │       ├── __init__.py
│   │   │       └── routes.py
│   │   ├── services/                ← business logika, odvojena od ruta
│   │   │   ├── approval_service.py  ← surplus-first logika, stock update
│   │   │   ├── receiving_service.py ← stock povećanje, avg price izračun
│   │   │   ├── inventory_service.py ← discrepancy handling
│   │   │   ├── barcode_service.py   ← generiranje i print barkodova
│   │   │   └── export_service.py    ← Excel export (SAP format)
│   │   └── utils/
│   │       ├── auth.py              ← JWT dekoratori, role check
│   │       ├── pagination.py        ← standardna pagination logika
│   │       └── validators.py        ← batch code regex, uom validacija
│   ├── migrations/                  ← Alembic migracije
│   ├── static/                      ← React build output (gitignored)
│   ├── tests/
│   │   ├── conftest.py              ← pytest fixtures, test DB setup
│   │   ├── test_auth.py
│   │   ├── test_articles.py
│   │   ├── test_drafts.py
│   │   ├── test_approvals.py        ← kritično: surplus-first, stock check
│   │   ├── test_receiving.py
│   │   ├── test_orders.py
│   │   ├── test_inventory_count.py
│   │   ├── test_employees.py
│   │   └── test_reports.py
│   ├── .env.example
│   ├── run.py                       ← entry point (development)
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── routes.tsx               ← centralna route config
│   │   ├── pages/
│   │   │   ├── auth/
│   │   │   │   └── LoginPage.tsx
│   │   │   ├── drafts/
│   │   │   │   └── DraftEntryPage.tsx
│   │   │   ├── approvals/
│   │   │   │   └── ApprovalsPage.tsx
│   │   │   ├── receiving/
│   │   │   │   └── ReceivingPage.tsx
│   │   │   ├── orders/
│   │   │   │   ├── OrdersPage.tsx
│   │   │   │   └── OrderDetailPage.tsx
│   │   │   ├── warehouse/
│   │   │   │   ├── WarehousePage.tsx
│   │   │   │   └── ArticleDetailPage.tsx
│   │   │   ├── identifier/
│   │   │   │   └── IdentifierPage.tsx
│   │   │   ├── employees/
│   │   │   │   ├── EmployeesPage.tsx
│   │   │   │   └── EmployeeDetailPage.tsx
│   │   │   ├── inventory/
│   │   │   │   └── InventoryCountPage.tsx
│   │   │   ├── reports/
│   │   │   │   └── ReportsPage.tsx
│   │   │   └── settings/
│   │   │       └── SettingsPage.tsx
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── AppShell.tsx     ← sidebar + content area
│   │   │   │   └── Sidebar.tsx      ← RBAC-aware navigacija
│   │   │   └── shared/              ← reusable UI komponente
│   │   ├── api/
│   │   │   ├── client.ts            ← axios instance + interceptori
│   │   │   ├── auth.ts              ← login, refresh, logout
│   │   │   ├── articles.ts          ← TanStack Query hooks
│   │   │   ├── drafts.ts
│   │   │   ├── approvals.ts
│   │   │   ├── receiving.ts
│   │   │   ├── orders.ts
│   │   │   ├── warehouse.ts
│   │   │   ├── employees.ts
│   │   │   ├── inventory.ts
│   │   │   └── reports.ts
│   │   ├── store/
│   │   │   └── authStore.ts         ← Zustand: korisnik, rola, token
│   │   ├── i18n/
│   │   │   ├── index.ts
│   │   │   └── locales/
│   │   │       ├── hr.json          ← puna podrška
│   │   │       ├── en.json          ← scaffold
│   │   │       ├── de.json          ← scaffold
│   │   │       └── hu.json          ← scaffold
│   │   └── utils/
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
│
├── scripts/
│   ├── build.sh                     ← npm build → kopiraj u backend/static/
│   └── deploy.sh                    ← git pull + build + restart systemd
│
├── .gitignore
└── README.md
```

---

## 2. API konvencije

### URL struktura

Svi endpointi počinju s `/api/v1/`.

```
GET    /api/v1/articles
GET    /api/v1/articles/{id}
POST   /api/v1/articles
PUT    /api/v1/articles/{id}
DELETE /api/v1/articles/{id}

GET    /api/v1/drafts
POST   /api/v1/drafts
POST   /api/v1/drafts/{id}/approve
POST   /api/v1/drafts/{id}/reject

GET    /api/v1/orders
POST   /api/v1/orders
GET    /api/v1/orders/{id}
POST   /api/v1/orders/{id}/lines
PUT    /api/v1/orders/{id}/lines/{line_id}
```

### Error format

Svaki error vraća isti oblik, neovisno o modulu:

```json
{
  "error": "BATCH_EXPIRY_MISMATCH",
  "message": "Batch 12345 already exists with different expiry date.",
  "details": {}
}
```

`error` — strojno čitljiv kod (konstanta, uvijek EN)
`message` — human-readable opis (uvijek EN)
`details` — dodatni kontekst (opcionalno, može biti prazan objekt)

### HTTP status kodovi

| Situacija | Status |
|-----------|--------|
| Uspješno dohvaćanje | 200 |
| Uspješno kreiranje | 201 |
| Validacijska greška | 400 |
| Nije autentificiran | 401 |
| Nema dozvole (pogrešna rola) | 403 |
| Resurs ne postoji | 404 |
| Konflikt (npr. batch expiry mismatch) | 409 |
| Greška servera | 500 |

### Pagination

Sve liste koje mogu rasti (artikli, transakcije, draftovi) vraćaju paginirani odgovor:

```json
{
  "items": [...],
  "total": 142,
  "page": 1,
  "per_page": 50
}
```

Query parametri: `?page=1&per_page=50`

---

## 3. Auth flow

### Access + Refresh token model

Login vraća dva tokena:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ..."
}
```

| Token | Trajanje po roli |
|-------|-----------------|
| Access token (sve role) | 15 minuta |
| Refresh token — OPERATOR | 30 dana |
| Refresh token — sve ostale role | 8 sati |

### Token storage

Oba tokena se pohranjuju u Zustand store (in-memory). Ne u localStorage — nema persisted storage u browser-u.

Posljedica: zatvaranjem taba / refreshanjem stranice korisnik se mora ponovo prijaviti (osim ako postoji httpOnly cookie pristup — nije u v1 scope).

### Refresh flow

```
Frontend → API poziv s access tokenom
         ← 401 Unauthorized (token istekao)
Frontend → POST /api/v1/auth/refresh s refresh tokenom
         ← novi access token
Frontend → ponovi originalni API poziv s novim tokenom
```

Interceptor u `api/client.ts` (axios) automatski hvata 401 i radi refresh. Korisnik ne vidi ništa.

Ako refresh token istekne → automatski logout + redirect na `/login`.

### Endpoints

```
POST /api/v1/auth/login      ← username + password → access + refresh token
POST /api/v1/auth/refresh    ← refresh token → novi access token
POST /api/v1/auth/logout     ← invalidacija refresh tokena (server-side blacklist)
```

---

## 4. Frontend routing

### Biblioteka

React Router v6, centralna konfiguracija u `src/routes.tsx`.

### Struktura ruta

```
/login                         ← javna ruta (jedina bez auth)

/                              ← redirect na home po roli
/drafts                        ← OPERATOR, ADMIN
/approvals                     ← ADMIN
/receiving                     ← ADMIN
/orders                        ← ADMIN, MANAGER (read-only)
/orders/:id                    ← ADMIN, MANAGER (read-only)
/warehouse                     ← ADMIN, MANAGER (read-only)
/warehouse/articles/:id        ← ADMIN, MANAGER (read-only)
/identifier                    ← ADMIN, MANAGER, WAREHOUSE_STAFF, VIEWER
/employees                     ← ADMIN, WAREHOUSE_STAFF (read-only)
/employees/:id                 ← ADMIN, WAREHOUSE_STAFF (read-only)
/inventory                     ← ADMIN
/reports                       ← ADMIN, MANAGER
/settings                      ← ADMIN
```

### Home po roli (redirect s `/`)

| Rola | Home ruta |
|------|-----------|
| ADMIN | `/approvals` |
| MANAGER | `/warehouse` |
| WAREHOUSE_STAFF | `/identifier` |
| VIEWER | `/identifier` |
| OPERATOR | `/drafts` |

### RBAC zaštita ruta

Svaka zaštićena ruta ima `ProtectedRoute` wrapper koji provjerava rolu iz Zustand storea. Neovlašteni pristup → redirect na korisnikovu home rutu (ne na login, korisnik je prijavljen).

### Code splitting

Nema lazy loadanja — svi moduli učitavaju se odjednom pri prvom otvaranju. Opravdano jer je deployment na lokalnoj mreži (Pi → browser terminal).

### State management

Zustand store (`src/store/authStore.ts`) drži:

```typescript
{
  user: { id, username, role } | null,
  accessToken: string | null,
  refreshToken: string | null,
  isAuthenticated: boolean
}
```

---

## 5. Pi deployment

### Systemd servis

WMS se pokreće kao systemd servis koji automatski starta pri boot-u Pi-a.

```
/etc/systemd/system/wms.service
```

Servis pokreće Flask (Gunicorn) koji servira i API i React build s jednog porta (5000).

### Update proces

```bash
# Na Pi-u (ili preko SSH):
cd /home/wms/wms
git pull origin main
./scripts/deploy.sh
```

`deploy.sh` radi:
1. `git pull`
2. `pip install -r backend/requirements.txt`
3. `npm ci && npm run build` (u frontend/)
4. Kopira build u `backend/static/`
5. `alembic upgrade head` (migracije)
6. `sudo systemctl restart wms`

### Konfiguracija

Sve osjetljive vrijednosti (JWT secret, DB connection string) u `.env` fajlu na Pi-u — nikad u git repozitoriju.

```
# .env (samo na Pi-u, nikad u gitu)
FLASK_ENV=production
DATABASE_URL=postgresql://wms:password@localhost/wms
JWT_SECRET_KEY=<strong-random-key>
```

---

## 6. Development workflow

### Lokalni setup

Preduvjeti: Python 3.11+, Node 20+, PostgreSQL

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # popuni lokalne vrijednosti
alembic upgrade head
flask run                     # pokreće se na :5000

# Frontend (drugi terminal)
cd frontend
npm install
npm run dev                   # pokreće se na :5173 (Vite)
```

Napomena: `backend/migrations/env.py` treba defensivno guardati `fileConfig(config.config_file_name)` i provjeriti da config file postoji prije poziva. U nekim Python 3.9/macOS/Xcode okruženjima Alembic logging parser inače može srušiti `flask db upgrade` s `KeyError: 'formatters'`.

Frontend dev server (Vite, port 5173) proksira API pozive na Flask (port 5000) via Vite proxy config. Defaultni proxy target za lokalni development treba biti `http://127.0.0.1:5000`, ne `http://localhost:5000`, kako bi se izbjegli konflikti na macOS-u gdje AirPlay Receiver može preuzeti `localhost:5000` preko IPv6 rezolucije. HMR (hot module replacement) radi — promjena u React kodu = automatski refresh u browseru.

### Git workflow

`main` branch je uvijek stabilan i deployabilan na Pi. Novi feature ili bugfix = novi branch.

```bash
git checkout -b feature/approvals-bulk-action
# ... rad ...
git push origin feature/approvals-bulk-action
# merge u main kad gotovo
```

Na Pi-u uvijek ide samo `main`:
```bash
git pull origin main
```

### Testovi

```bash
cd backend
pytest tests/ -v
```

Integration testovi koriste zasebnu test bazu (konfigurabilna u `conftest.py`). Svaki test se izvodi u transakciji koja se rollbacka — testovi su izolirani i brzi.

---

## 7. Ključne arhitekturalne odluke (sažetak)

| Tema | Odluka | Razlog |
|------|--------|--------|
| Struktura projekta | Monorepo, Flask servira React build | Jedan proces, jedan port, jednostavan Pi deployment |
| Services layer | Odvojen od ruta (`app/services/`) | Čišći kod, lakše testirati business logiku |
| API versioning | `/api/v1/` od početka | Forward compatible, nema later refactoring |
| Pagination | Od početka, standardni format | Sprema za tisuće artikala |
| Auth model | Access (15 min) + Refresh token | Bolji UX, sesija traje bez vidljivog prekida |
| Token storage | Zustand in-memory | Sigurnije od localStorage |
| UI library | Mantine | Komponente prilagođene tabletu, dobra dokumentacija |
| Router | React Router v6 | Standard, odlična dokumentacija |
| Route config | Centralna (`routes.tsx`) | Pregledno, RBAC na jednom mjestu |
| Code splitting | Nema (sve odjednom) | Lokalna mreža, nema razloga za kompleksnost |
| State management | Zustand | Manje koda od Reduxa, vanjske ovisnosti minimalne |
| Testovi | Integration tests sve backend rute | Pokrivaju i API kontrakt i business logiku |
| DB (dev i prod) | PostgreSQL svugdje | Nema iznenađenja između okruženja |
| Deployment | Git pull + systemd autostart | Jednostavno, pouzdano, Pi-friendly |
| Dev workflow | Flask + Vite dev server (2 terminala) | HMR radi, brži razvoj frontenada |
| Git branching | Feature branches, main uvijek stabilan | Siguran deploy, čista historija |
