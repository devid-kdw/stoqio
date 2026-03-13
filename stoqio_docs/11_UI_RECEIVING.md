# WMS — UI Specification: Receiving

**Status**: Active document
**Version**: v1
**Audience**: AI coding agents
**Module**: Receiving (`/receiving`)
**Accessible by roles**: ADMIN

---

## 1. Purpose

The Receiving screen is where the ADMIN records incoming goods and increases stock. It replaces the manual SAP Wareneingang process. A single purchase order can have multiple partial receipts (as shown in the SAP Verknüpfungsplan — one Bestellung linked to multiple Wareneingang entries).

---

## 2. Screen Layout

The screen has two sections:

**Top section — New receipt form**: find an order and record incoming goods.
**Bottom section — Receipt history**: a separate view (not on the same screen) accessible via a History tab or link.

---

## 3. Starting a Receipt

### 3.1 Linked to a Purchase Order (standard flow)

1. Admin types the order number in a search field.
2. System looks up the order and displays its open lines.
3. Admin enters received quantities for each line.
4. Admin enters the delivery note number.
5. Admin submits — stock increases for each received line.

### 3.2 Ad-hoc Receipt (no purchase order)

- A separate "Ad-hoc receipt" option is available.
- Admin selects article, enters quantity, UOM, delivery note number, and a mandatory explanatory note.
- No order line is linked.
- Stock increases immediately on submit.

---

## 4. Receipt Form Fields

### 4.1 Order Search

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Order number | Text input | Yes (for linked receipt) | Admin types order number. System displays order details and open lines on match. |

### 4.2 Per Order Line

Each open order line is displayed as a row. Admin fills in:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Received quantity | Numeric input | Yes | Can be less than, equal to, or more than ordered quantity. Positive only. |
| UOM | Display only | — | Auto-populated from order line. Not editable. |
| Batch code | Text input | Conditional | Required if article has `has_batch = true`. Validated against regex `^\d{4,5}$|^\d{9,12}$`. |
| Expiry date | Date input | Conditional | Required if article has `has_batch = true`. |
| Skip line | Checkbox | No | If checked, this line is not received in this receipt. Line remains open for future receipt. |

### 4.3 Receipt Header Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Delivery note number | Text input | Yes | Max 100 characters. Must be provided for every receipt. |
| Note | Text input | Conditional | Required for ad-hoc receipts. Optional for order-linked receipts. Max 1000 characters. |

---

## 5. Submitting a Receipt

- Submit button label: **"Confirm Receipt"**
- On submit:
  1. Validate all required fields (inline errors if missing).
  2. POST to `/api/v1/receiving` with receipt data.
  3. On success: show success toast `"Receipt recorded."`, clear the form.
  4. On error: show error toast.
- The submit button is disabled and shows a spinner while the request is in flight.

### Stock update rules

- Receiving increases **stock only** (never surplus).
- If article has `has_batch = true`: a Batch record is created (or matched if batch code already exists).
- If batch already exists with a different expiry date: block submission, show inline error `"Batch [code] already exists with a different expiry date."` (409).

---

## 6. Partial Receipt

- Admin can skip individual order lines by checking the "Skip" checkbox.
- Skipped lines remain `OPEN` on the order and can be received in a future receipt.
- An order line is automatically set to `CLOSED` when its cumulative received quantity equals or exceeds the ordered quantity.
- The order itself is automatically set to `CLOSED` when all active lines are `CLOSED`.

---

## 7. Ad-hoc Receipt

- Available as a separate option on the Receiving screen (e.g. a tab or button "Ad-hoc receipt").
- Fields: article number, quantity, UOM, batch code (if applicable), expiry date (if applicable), delivery note number, note (required).
- No order line is linked (`order_line_id` is NULL).
- Otherwise identical to standard receipt in terms of stock update logic.

---

## 8. Receipt History

- Accessible via a separate History tab or page — not displayed on the same screen as the receipt form.
- Lists all past receipts ordered by date descending (newest first).
- Each row shows: date, order number (or "Ad-hoc"), article, quantity, UOM, batch, delivery note number, received by.
- Read-only — no actions available.

---

## 9. API Endpoints Used

| Action | Method | Endpoint |
|--------|--------|----------|
| Look up order by number | GET | `/api/v1/orders?q={order_number}` |
| Get order detail (lines) | GET | `/api/v1/orders/{id}` |
| Submit receipt | POST | `/api/v1/receiving` |
| Get receipt history | GET | `/api/v1/receiving?page=1&per_page=50` |

---

## 10. Request / Response Shapes

### GET `/api/v1/orders?q={order_number}` — Look up order by number

- Exact order-number match only (case-insensitive).
- Response is a single summary object, not an array.
- If no order matches: `404 ORDER_NOT_FOUND`.

**Response (200):**
```json
{
  "id": 91,
  "order_number": "ORD-0042",
  "status": "OPEN",
  "supplier_id": 7,
  "supplier_name": "ACME Supplies",
  "open_line_count": 3,
  "created_at": "2026-03-13T08:15:00+00:00"
}
```

### GET `/api/v1/orders/{id}` — Get receiving-oriented order detail

- Returns order header data plus only receiving-eligible lines:
  - `status = OPEN`
  - not `REMOVED`
- Closed or removed lines are omitted from `lines[]`.

**Response (200):**
```json
{
  "id": 91,
  "order_number": "ORD-0042",
  "status": "OPEN",
  "supplier_id": 7,
  "supplier_name": "ACME Supplies",
  "supplier_confirmation_number": "SUP-7781",
  "note": "Deliver in two batches.",
  "created_at": "2026-03-13T08:15:00+00:00",
  "lines": [
    {
      "id": 12,
      "article_id": 42,
      "article_no": "BOJ-001",
      "description": "Blue paint",
      "has_batch": true,
      "ordered_qty": 25.0,
      "received_qty": 10.0,
      "remaining_qty": 15.0,
      "status": "OPEN",
      "is_open": true,
      "uom": "kg",
      "unit_price": 3.45,
      "delivery_date": "2026-03-20"
    }
  ]
}
```

### POST `/api/v1/receiving` — Submit receipt

**Request (order-linked):**
```json
{
  "delivery_note_number": "LS12606198",
  "note": null,
  "lines": [
    {
      "order_line_id": 12,
      "article_id": 42,
      "quantity": 25.0,
      "uom": "kg",
      "batch_code": "24001",
      "expiry_date": "2026-12-31"
    },
    {
      "order_line_id": 13,
      "article_id": 55,
      "quantity": 10.0,
      "uom": "kom",
      "batch_code": null,
      "expiry_date": null
    }
  ]
}
```

**Request (ad-hoc):**
```json
{
  "delivery_note_number": "LS12606200",
  "note": "Urgent delivery, no order placed.",
  "lines": [
    {
      "order_line_id": null,
      "article_id": 42,
      "quantity": 10.0,
      "uom": "kg",
      "batch_code": "24002",
      "expiry_date": "2027-06-30"
    }
  ]
}
```

**Response (201):**
```json
{
  "receiving_ids": [201, 202],
  "stock_updated": [
    { "article_id": 42, "article_no": "BOJ-001", "quantity_added": 25.0, "uom": "kg" },
    { "article_id": 55, "article_no": "RUK-012", "quantity_added": 10.0, "uom": "kom" }
  ]
}
```

### GET `/api/v1/receiving?page=1&per_page=50` — Receipt history

**Response (200):**
```json
{
  "items": [
    {
      "id": 201,
      "received_at": "2026-03-13T10:21:00+00:00",
      "order_number": "ORD-0042",
      "article_id": 42,
      "article_no": "BOJ-001",
      "description": "Blue paint",
      "quantity": 25.0,
      "uom": "kg",
      "batch_code": "24001",
      "delivery_note_number": "LS12606198",
      "received_by": "admin"
    },
    {
      "id": 202,
      "received_at": "2026-03-13T10:24:00+00:00",
      "order_number": "Ad-hoc",
      "article_id": 55,
      "article_no": "RUK-012",
      "description": "Work gloves",
      "quantity": 10.0,
      "uom": "kom",
      "batch_code": null,
      "delivery_note_number": "LS12606200",
      "received_by": "admin"
    }
  ],
  "total": 2,
  "page": 1,
  "per_page": 50
}
```

---

## 11. Edge Cases

| Situation | Behaviour |
|-----------|-----------|
| Order number not found | Inline error: `"Order not found."` |
| Order is already CLOSED | Show warning: `"This order is already closed."` Prevent receipt. |
| Batch exists with different expiry date | Block submission, inline error: `"Batch [code] already exists with a different expiry date."` |
| All lines skipped | Block submission, inline error: `"At least one line must be received."` |
| Delivery note number missing | Inline error: `"Delivery note number is required."` |
| Ad-hoc receipt without note | Inline error: `"A note is required for ad-hoc receipts."` |
| Received quantity is 0 | Inline error: `"Quantity must be greater than 0."` |
