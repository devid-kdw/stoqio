# WMS — UI Specification: Warehouse

**Status**: Active document
**Version**: v1
**Audience**: AI coding agents
**Module**: Warehouse (`/warehouse`)
**Accessible by roles**: ADMIN (full), MANAGER (read-only)

---

## 1. Purpose

The Warehouse screen is the central view for stock levels and article master data management. It gives the ADMIN a real-time overview of all inventory, with visual indicators for reorder thresholds, and full access to article details including transaction history, batches, and suppliers.

---

## 2. Screen Layout

**Main screen** — searchable, filterable list of all active articles with stock levels.
**Article detail screen** — full article details, transaction history, batches, suppliers, and edit form.

---

## 3. Articles List Screen

### 3.1 Filters & Search

- **Search field** — searches by article number or article description. Debounced input.
- **Category filter** — dropdown to filter by article category. Default: all categories.
- **Show deactivated** — toggle (off by default). When enabled, deactivated articles appear in the list visually distinguished (greyed out).

### 3.2 List Columns

| Column | Notes |
|--------|-------|
| Article No. | Article number |
| Description | Article description |
| Category | Article category label (HR) |
| Stock | Current stock quantity + UOM |
| Surplus | Current surplus quantity + UOM. Show "—" if 0. |
| Threshold | Reorder threshold value + UOM |
| Status indicator | Colour dot — see threshold visualisation below |

### 3.3 Reorder Threshold Visualisation

Subtle colour indicator per row — not aggressive, just a soft visual cue:

| Zone | Condition | Indicator |
|------|-----------|-----------|
| Normal | `qty > threshold × 1.10` | No indicator |
| Yellow zone | `threshold < qty ≤ threshold × 1.10` | Subtle yellow highlight or dot |
| Red zone | `qty ≤ threshold` | Subtle red highlight or dot |

> The indicator should be understated — a small coloured dot or a very light row background tint. Not banners or bold warnings.

### 3.4 Actions on List Screen

- **"Novi artikl"** button — opens the article creation form.

### 3.5 Empty State

`"Nema pronađenih artikala."`

---

## 4. Creating a New Article

- Clicking "Novi artikl" opens a form (modal or separate page — implementation choice).
- Visible fields match the Article data model except `density` and `reorder_coverage_days`: article_no, description, category, base_uom, pack_size, pack_uom, has_batch, initial_average_price, reorder_threshold, manufacturer, manufacturer_art_number, is_active.
- In the v1 Croatian UI, `has_batch` is shown with the label `"Artikl sa šaržom"` rather than a process-oriented phrase such as `"Praćenje po šarži"`.
- `initial_average_price` is shown as `"Prosječna cijena"` and is available on create and edit.
- `density` remains a backend/master-data field but is hidden in the v1 Warehouse UI. Warehouse create/edit flows submit it as `1.0`.
- `reorder_coverage_days` remains a backend/planning field but is hidden in the v1 Warehouse UI until automated reorder-threshold logic is introduced in a later phase.
- On submit: POST to `/api/v1/articles`.
- On success: show success toast `"Artikl je kreiran."`, redirect to article detail screen.

---

## 5. Article Detail Screen

Accessible by clicking any row in the articles list.

### 5.1 Header Section

Displays all article master data fields relevant to the v1 Warehouse UI. `density` and `reorder_coverage_days` are not displayed. The visible label for `has_batch` remains `"Artikl sa šaržom"`. "Uredi" button allows inline editing of the visible fields directly on this screen.

`initial_average_price` is displayed as `"Prosječna cijena"`.

### 5.2 Stock & Surplus Section

Shows current stock and surplus quantities. If article has `has_batch = true`, displays a table of active batches:

| Column | Notes |
|--------|-------|
| Šarža | Šifra šarže |
| Expiry date | Date of expiry |
| Stock qty | Current stock quantity for this batch |
| Surplus qty | Current surplus quantity for this batch, or "—" if 0 |

Batches ordered by expiry date ascending (earliest first — FEFO).

### 5.3 Suppliers Section

Lists all suppliers linked to this article (from ArticleSupplier):

| Column | Notes |
|--------|-------|
| Supplier name | |
| Supplier article code | Supplier's code for this article |
| Last price | Last known unit price |
| Preferred | Indicates preferred supplier |

### 5.4 Transaction History Section

Paginated list of all inventory transactions for this article, newest first.

| Column | Notes |
|--------|-------|
| Date & time | When the transaction occurred |
| Type | STOCK_RECEIPT / OUTBOUND / SURPLUS_CONSUMED / STOCK_CONSUMED / INVENTORY_ADJUSTMENT / PERSONAL_ISSUE |
| Quantity | Algebraic amount (negative = outbound) + UOM |
| Šarža | Šifra šarže, or "—" |
| Reference | Order number or delivery note number if available |
| User | Who performed the action |

### 5.5 Statistics Section (Statistika)

The Statistics section is lazy-loaded on first expand. It does not fetch data on page mount.

**Controls:**
- Period selector: 30 dana / 90 dana / 180 dana (default: 90 dana).
- Toggling the section open triggers the first fetch. Changing the period re-fetches.

**Layout — three mini-dashboard cards:**

| Card | Label | KPIs | Chart |
|------|-------|------|-------|
| Tjedni izlaz | TJEDNI IZLAZ | Ukupno izlaz + Aktivnih tjedana | Bar chart, weekly buckets |
| Tjedni ulaz | TJEDNI ULAZ | Ukupno ulaz + Aktivnih tjedana | Bar chart, weekly buckets |
| Povijest cijene | POVIJEST CIJENE | Zadnja cijena + Promjena (period) + Zapisa | Line chart, one point per receipt |

Each card uses a theme-aware background that works in both light and dark mode. Chart grid lines and tick labels adapt to the active colour scheme.

**Price history drill-in:**

Within the "Povijest cijene" card, a "Prikaži sve zapise" / "Sakrij zapise" toggle opens a compact table below the chart. The table lists all price points in reverse chronological order (newest first):

| Column | Notes |
|--------|-------|
| Datum primke | ISO date of the Receiving record, date portion only |
| Cijena / jed. | Unit price at that date |

**Empty state:** `"Nema dostupne povijesti transakcija."` when all three series are empty.

---

### 5.6 Article Actions

- **"Uredi"** — enables inline editing of all article master data fields on this screen.
- **"Deaktiviraj"** — deactivates the article. Shows confirmation: `"Deaktivirati ovaj artikl? Više se neće prikazivati na popisu aktivnih artikala."` Deactivated articles remain in the database and their history is preserved.
- Detail payload must include `has_pending_drafts` and `pending_draft_count` so the UI can render the open-drafts deactivation warning without an extra API call.
- **"Preuzmi PDF barkoda"** (ADMIN only) — calls `GET /api/v1/articles/{id}/barcode`; downloads a PDF barcode label directly in the browser.
- **"Ispis barkoda"** (ADMIN only) — calls `POST /api/v1/articles/{id}/barcode/print`; sends a ZPL label directly to the configured network label printer. Requires `label_printer_ip` to be configured in Settings. Shows an error toast if the printer is not reachable or not configured.

---

## 6. Editing an Article

- Admin clicks "Uredi" on the article detail screen.
- All fields become editable inline.
- `"Spremi"` / `"Odustani"` buttons appear.
- On save: PUT to `/api/v1/articles/{id}`.
- On success: show success toast `"Artikl je ažuriran."`, fields return to read-only display.
- On error: show inline errors or error toast.

---

## 7. Barcode Printing

Barcode actions are **ADMIN-only**. MANAGER role has no print actions.

### 7.1 PDF download

- **"Preuzmi PDF barkoda"** button on the article detail screen.
- Calls `GET /api/v1/articles/{id}/barcode`.
- Generates a PDF barcode label and downloads it directly in the browser.
- Barcode format (EAN-13 or Code128) is set in Settings → Barcode.
- For articles with `has_batch = true`, the admin can download batch-level PDF barcodes from the batch table (`GET /api/v1/batches/{id}/barcode`), one label per batch.

### 7.2 Direct host printing

- **"Ispis barkoda"** button triggers a direct network print (`POST /api/v1/articles/{id}/barcode/print`).
- No PDF is generated. The ZPL label is sent directly to the configured network label printer over TCP.
- Requires `label_printer_ip` (and optionally `label_printer_port`, `label_printer_model`) to be configured in Settings → Barcode.
- If the printer is not configured or not reachable, the backend returns an error and the UI shows an error toast.
- For batch-level direct printing: `POST /api/v1/batches/{id}/barcode/print`.

### 7.3 Future: raw-label printer mode

A future raw-label printer mode (e.g., browser-direct, without server mediation) is **not implemented**. Do not surface this as a current feature.

---

## 8. MANAGER Read-only View

- MANAGER role can view the articles list and article detail screens.
- No create, edit, deactivate, or print actions are available.
- Transaction history is visible.

---

## 9. API Endpoints Used

| Action | Method | Endpoint |
|--------|--------|----------|
| Get articles list | GET | `/api/v1/articles?page=1&per_page=50&q={query}&category={key}&include_inactive={bool}` |
| Get article detail | GET | `/api/v1/articles/{id}` |
| Create article | POST | `/api/v1/articles` |
| Edit article | PUT | `/api/v1/articles/{id}` |
| Deactivate article | PATCH | `/api/v1/articles/{id}/deactivate` |
| Get article transactions | GET | `/api/v1/articles/{id}/transactions?page=1&per_page=50` |
| Download article barcode PDF | GET | `/api/v1/articles/{id}/barcode` |
| Download batch barcode PDF | GET | `/api/v1/batches/{id}/barcode` |
| Direct-print article label | POST | `/api/v1/articles/{id}/barcode/print` |
| Direct-print batch label | POST | `/api/v1/batches/{id}/barcode/print` |

---

## 10. Request / Response Shapes

### POST `/api/v1/articles` — Create article

**Request:**
```json
{
  "article_no": "BOJ-001",
  "description": "Epoxy paint RAL 7035",
  "category_id": 2,
  "base_uom": "kg",
  "pack_size": 4.0,
  "pack_uom": "kom",
  "has_batch": true,
  "initial_average_price": 12.5,
  "reorder_threshold": 20.0,
  "reorder_coverage_days": 30,
  "density": 1.0,
  "is_active": true
}
```

**Response (201):**
```json
{
  "id": 42,
  "article_no": "BOJ-001",
  "description": "Epoxy paint RAL 7035",
  "category": "safety_equipment",
  "base_uom": "kg",
  "initial_average_price": 12.5,
  "stock": 0.0,
  "surplus": 0.0,
  "is_active": true,
  "created_at": "2026-03-10T10:00:00Z"
}
```

---

## 11. Edge Cases

| Situation | Behaviour |
|-----------|-----------|
| Article number already exists | Inline error: `"Broj artikla već postoji."` |
| Deactivating article with open drafts | Show warning: `"Ovaj artikl ima otvorene draftove. Deaktivacija neće utjecati na postojeće draftove."` Allow deactivation. |
| Deactivating article with stock > 0 | Show warning: `"Ovaj artikl još uvijek ima zalihu na stanju."` Allow deactivation. |
| No transactions for article | Empty state in transaction history: `"Nema pronađenih transakcija."` |
| No batches for article | Batch section not shown if `has_batch = false`. |
| Search returns no results | Empty state: `"Nema pronađenih artikala."` |
