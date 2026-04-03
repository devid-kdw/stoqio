# WMS — UI Specification: Orders

**Status**: Active document
**Version**: v1
**Audience**: AI coding agents
**Module**: Orders (`/orders`)
**Accessible by roles**: ADMIN (full), MANAGER (read-only)

---

## 1. Purpose

The Orders screen is where the ADMIN creates and manages purchase orders sent to suppliers. The system generates a PDF of the order that can be emailed to the supplier. After the supplier sends an order confirmation, the ADMIN updates delivery dates per line. When goods arrive, receiving is handled in the Receiving module.

This replaces the SAP Bestellung process.

---

## 2. Screen Layout

**Main screen** — list of all orders (open on top, closed below).
**Order detail screen** — full order with all lines, actions, and history.

Client-rendered labels, validation messages, success toasts, warnings, and empty states follow the Croatian UI default from `08_SETUP_AND_GLOBALS.md` § 4.

---

## 3. Orders List Screen

### 3.1 List Layout

- Open orders displayed at the top, visually prominent.
- Closed orders displayed below, visually muted (greyed out) so it is clear they are inactive.
- Each row shows: order number, supplier name, date created, number of lines, total value, status.
- Clicking a row opens the Order Detail screen.

### 3.2 Actions on List Screen

- **"Nova narudžbenica"** button — opens a form to create a new order.

### 3.3 Empty State

`"Nema narudžbenica."`

---

## 4. Creating a New Order

### 4.1 Order Header Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Order number | Text input | Yes | Pre-filled with auto-generated number (e.g. `ORD-0001`). Admin can overwrite with a manual number (e.g. SAP number `260100`). Must be unique. |
| Supplier | Dropdown / search | Yes | Select from supplier master data. |
| Supplier confirmation number | Text input | No | Added after supplier sends order confirmation (e.g. `2485602`). Can be filled in later. |
| Note | Text input | No | General note on the order. Max 1000 characters. |

### 4.2 Order Lines

Admin adds one or more lines to the order. Each line has:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Article | Search input | Yes | Search by article number or description. |
| Supplier article code | Text input | No | Auto-populated from ArticleSupplier if exists. Editable. |
| Quantity | Numeric input | Yes | Positive only. |
| UOM | Display only | — | Auto-populated from article master data. |
| Unit price | Numeric input | Yes | Price per unit at time of order. |
| Delivery date | Date input | No | Expected delivery date. Can be filled in later after supplier confirmation. |
| Note | Text input | No | Line-level note. Max 1000 characters. |

### 4.3 Adding Lines

- "Dodaj stavku" button appends a new empty row.
- Admin fills in article, quantity, price per line.
- At least one line is required to save the order.

### 4.4 Submitting

- Submit button label: **"Kreiraj narudžbenicu"**
- On submit: POST to `/api/v1/orders`.
- On success: redirect to Order Detail screen, show success toast `"Narudžbenica je kreirana."`.
- On error: show inline errors or error toast.

---

## 5. Order Detail Screen

Displays full order details and all lines.

### 5.1 Header Section

Shows: order number, supplier, date, status, supplier confirmation number, note, total value (sum of all active lines).

### 5.2 Lines Table

| Column | Notes |
|--------|-------|
| Position | Line number (1, 2, 3...) |
| Article No. | Article number |
| Description | Article description |
| Supplier article code | Supplier's code for this article |
| Ordered qty | Quantity ordered |
| Received qty | Cumulative quantity received so far |
| UOM | Unit of measure |
| Unit price | Price per unit |
| Total price | Ordered qty × unit price |
| Delivery date | Expected delivery date |
| Status | OPEN / CLOSED / REMOVED |
| Actions | Edit (pencil), Remove (x) — only for OPEN lines |

### 5.3 Order Actions

- **"Uredi narudžbenicu"** — edit header fields (supplier confirmation number, note).
- **"Dodaj stavku"** — add a new line to an existing open order.
- **"Generiraj PDF"** — generate a PDF of the order for sending to supplier.

---

## 6. Editing an Order

- Order header (supplier confirmation number, note) can be edited at any time while order is OPEN.
- Order lines can be edited (quantity, price, delivery date) while line status is OPEN.
- Lines can be removed (status → REMOVED) while line status is OPEN.
- Adding new lines is allowed while order status is OPEN.
- A CLOSED order cannot be edited.

---

## 7. Order & Line Status Logic

### Order status

| Status | Condition |
|--------|-----------|
| `OPEN` | At least one active line is not yet fully received |
| `CLOSED` | All active (non-REMOVED) lines are CLOSED |

Order status is recalculated automatically after every change to a line.

### Line status

| Status | Condition |
|--------|-----------|
| `OPEN` | Received qty < ordered qty |
| `CLOSED` | Received qty ≥ ordered qty |
| `REMOVED` | Admin manually removed the line |

---

## 8. PDF Generation

- "Generiraj PDF" button on the Order Detail screen.
- Generates a professional PDF of the order containing:
  - Order number, date
  - Supplier name and address
  - Lines: position, article description, supplier article code, quantity, UOM, unit price, total price, delivery date
  - Order totals: subtotal, VAT (if applicable), grand total
  - Note (if present)
- PDF is downloaded directly in the browser or opened in a new tab.
- PDF does not include company logo or company-specific branding — it is generic and universally applicable.

---

## 9. MANAGER Read-only View

- MANAGER role can view the orders list and order detail.
- No create, edit, or delete actions are available.
- "Generiraj PDF" button is visible and usable for MANAGER.

---

## 10. API Endpoints Used

| Action | Method | Endpoint |
|--------|--------|----------|
| Supplier lookup for order form | GET | `/api/v1/orders/lookups/suppliers?q={query}` |
| Article lookup for order form | GET | `/api/v1/orders/lookups/articles?q={query}&supplier_id={supplier_id}` |
| Get orders list | GET | `/api/v1/orders?page=1&per_page=50` |
| Get order detail | GET | `/api/v1/orders/{id}` |
| Create order | POST | `/api/v1/orders` |
| Edit order header | PATCH | `/api/v1/orders/{id}` |
| Add line to order | POST | `/api/v1/orders/{id}/lines` |
| Edit order line | PATCH | `/api/v1/orders/{id}/lines/{line_id}` |
| Remove order line | DELETE | `/api/v1/orders/{id}/lines/{line_id}` |
| Generate PDF | GET | `/api/v1/orders/{id}/pdf` |

> Compatibility note: `GET /api/v1/orders?q={order_number}` is intentionally reserved for the Receiving module's exact-match lookup flow. The Orders module itself uses the paginated list mode (`page` / `per_page`) and the full-detail mode documented here.

---

## 11. Request / Response Shapes

### GET `/api/v1/orders/lookups/suppliers?q={query}` — Supplier lookup

- Search active suppliers by name or internal code.
- Used by the Orders create/edit flow.

**Response (200):**
```json
{
  "items": [
    {
      "id": 5,
      "internal_code": "MAN-001",
      "name": "Mankiewicz Gebr. & Co."
    }
  ]
}
```

### GET `/api/v1/orders/lookups/articles?q={query}&supplier_id={supplier_id}` — Article lookup for order entry

- Search active articles by article number or description.
- If `supplier_id` is provided and an `ArticleSupplier` link exists, return `supplier_article_code` and `last_price` for that supplier.

**Response (200):**
```json
{
  "items": [
    {
      "article_id": 42,
      "article_no": "BOJ-001",
      "description": "Blue paint",
      "uom": "kg",
      "supplier_article_code": "34665.5414.7.171",
      "last_price": 60.10
    }
  ]
}
```

### GET `/api/v1/orders?page=1&per_page=50` — Orders list

- Default Orders list mode.
- Open orders appear first. Closed orders follow below them.

**Response (200):**
```json
{
  "items": [
    {
      "id": 12,
      "order_number": "ORD-0042",
      "supplier_id": 5,
      "supplier_name": "Mankiewicz Gebr. & Co.",
      "status": "OPEN",
      "line_count": 3,
      "total_value": 480.80,
      "created_at": "2026-02-23T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 50
}
```

### GET `/api/v1/orders/{id}` — Full order detail

- Returns the full Orders-module detail contract with all lines.
- Receiving uses the separate compatibility mode documented in `11_UI_RECEIVING.md`.

**Response (200):**
```json
{
  "id": 12,
  "order_number": "ORD-0042",
  "supplier_id": 5,
  "supplier_name": "Mankiewicz Gebr. & Co.",
  "supplier_address": "Example address 1",
  "supplier_confirmation_number": "2485602",
  "status": "OPEN",
  "note": "Delivery in two batches confirmed.",
  "total_value": 480.80,
  "created_at": "2026-02-23T10:00:00Z",
  "updated_at": "2026-02-24T08:15:00Z",
  "lines": [
    {
      "id": 31,
      "position": 1,
      "article_id": 42,
      "article_no": "BOJ-001",
      "description": "Blue paint",
      "supplier_article_code": "34665.5414.7.171",
      "ordered_qty": 8.0,
      "received_qty": 0.0,
      "uom": "kg",
      "unit_price": 60.10,
      "total_price": 480.80,
      "delivery_date": null,
      "status": "OPEN",
      "note": null
    }
  ]
}
```

### POST `/api/v1/orders` — Create order

**Request:**
```json
{
  "order_number": "260100",
  "supplier_id": 5,
  "supplier_confirmation_number": null,
  "note": null,
  "lines": [
    {
      "article_id": 42,
      "supplier_article_code": "34665.5414.7.171",
      "ordered_qty": 8.0,
      "uom": "kg",
      "unit_price": 60.10,
      "delivery_date": null
    }
  ]
}
```

**Response (201):**
```json
{
  "id": 12,
  "order_number": "260100",
  "supplier_id": 5,
  "supplier_name": "Mankiewicz Gebr. & Co.",
  "status": "OPEN",
  "total_value": 480.80,
  "created_at": "2026-02-23T10:00:00Z"
}
```

### PATCH `/api/v1/orders/{id}` — Edit order header

**Request:**
```json
{
  "supplier_confirmation_number": "2485602",
  "note": "Delivery in two batches confirmed."
}
```

**Success response (200):**

- Returns the canonical full order-detail contract documented under `GET /api/v1/orders/{id}`.

### POST `/api/v1/orders/{id}/lines` — Add line to open order

**Request:**
```json
{
  "article_id": 42,
  "supplier_article_code": "34665.5414.7.171",
  "ordered_qty": 8.0,
  "uom": "kg",
  "unit_price": 60.10,
  "delivery_date": null,
  "note": null
}
```

**Success response (200):**

- Returns the canonical full order-detail contract documented under `GET /api/v1/orders/{id}`.

### PATCH `/api/v1/orders/{id}/lines/{line_id}` — Edit open line

**Request:**
```json
{
  "supplier_article_code": "34665.5414.7.171",
  "ordered_qty": 10.0,
  "unit_price": 61.25,
  "delivery_date": "2026-03-01",
  "note": "Confirmed with supplier."
}
```

**Success response (200):**

- Returns the canonical full order-detail contract documented under `GET /api/v1/orders/{id}`.

### DELETE `/api/v1/orders/{id}/lines/{line_id}` — Remove open line

- Soft-delete behavior only: the line remains in detail/history with `status = REMOVED`.
- Success response (200) returns the canonical full order-detail contract documented under `GET /api/v1/orders/{id}`.

### GET `/api/v1/orders/{id}/pdf` — Generate PDF

- Returns `application/pdf`.
- Browser downloads or opens the generated PDF directly.

---

## 12. Edge Cases

| Situation | Behaviour |
|-----------|-----------|
| Order number already exists | Inline error: `"Order number already exists."` |
| No lines on order | Block submission, inline error: `"At least one line is required."` |
| Editing a CLOSED order | Edit actions are hidden/disabled. If a closed-order mutation is called directly, backend returns `400 ORDER_CLOSED`. |
| Removing last active line | Order status automatically becomes CLOSED. |
| Line received qty exceeds ordered qty | Line status becomes CLOSED. Order recalculates. |
| MANAGER tries to create/edit | Actions are not visible — read-only view only. |
