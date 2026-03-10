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

- **"New Article"** button — opens the article creation form.

### 3.5 Empty State

`"No articles found."`

---

## 4. Creating a New Article

- Clicking "New Article" opens a form (modal or separate page — implementation choice).
- Fields match the Article data model: article_no, description, category, base_uom, pack_size, pack_uom, has_batch, reorder_threshold, reorder_coverage_days, density, manufacturer, manufacturer_art_number, is_active.
- On submit: POST to `/api/v1/articles`.
- On success: show success toast `"Article created."`, redirect to article detail screen.

---

## 5. Article Detail Screen

Accessible by clicking any row in the articles list.

### 5.1 Header Section

Displays all article master data fields. "Edit" button allows inline editing of all fields directly on this screen.

### 5.2 Stock & Surplus Section

Shows current stock and surplus quantities. If article has `has_batch = true`, displays a table of active batches:

| Column | Notes |
|--------|-------|
| Batch code | Batch identifier |
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
| Batch | Batch code, or "—" |
| Reference | Order number or delivery note number if available |
| User | Who performed the action |

### 5.5 Article Actions

- **"Edit"** — enables inline editing of all article master data fields on this screen.
- **"Deactivate"** — deactivates the article. Shows confirmation: `"Deactivate this article? It will no longer appear in the active article list."` Deactivated articles remain in the database and their history is preserved.
- **"Print barcode"** — generates and downloads a PDF barcode label for this article.

---

## 6. Editing an Article

- Admin clicks "Edit" on the article detail screen.
- All fields become editable inline.
- Save / Cancel buttons appear.
- On save: PUT to `/api/v1/articles/{id}`.
- On success: show success toast `"Article updated."`, fields return to read-only display.
- On error: show inline errors or error toast.

---

## 7. Barcode Printing

- "Print barcode" button on the article detail screen.
- Generates a PDF barcode label for the article.
- PDF is downloaded directly in the browser.
- Barcode format is configurable in Settings (EAN-13 or Code128).
- For articles with `has_batch = true`, the admin can also print batch-level barcodes from the batch table (one label per batch).

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
| Print barcode | GET | `/api/v1/articles/{id}/barcode` |
| Print batch barcode | GET | `/api/v1/batches/{id}/barcode` |

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
  "reorder_threshold": 20.0,
  "reorder_coverage_days": 30,
  "density": 1.2,
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
| Article number already exists | Inline error: `"Article number already exists."` |
| Deactivating article with open drafts | Show warning: `"This article has pending drafts. Deactivating will not affect existing drafts."` Allow deactivation. |
| Deactivating article with stock > 0 | Show warning: `"This article still has stock on hand."` Allow deactivation. |
| No transactions for article | Empty state in transaction history: `"No transactions found."` |
| No batches for article | Batch section not shown if `has_batch = false`. |
| Search returns no results | Empty state: `"No articles found."` |
