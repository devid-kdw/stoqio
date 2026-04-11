# WMS — UI Specification: Identifier

**Status**: Active document
**Version**: v1
**Audience**: AI coding agents
**Module**: Identifier (`/identifier`)
**Accessible by roles**: ADMIN, MANAGER, WAREHOUSE_STAFF, VIEWER

---

## 1. Purpose

The Identifier screen is a fast article lookup tool. It solves the communication problem between departments that refer to the same article by different names. For example, a painter may know an article as "12.36-57" while the system stores it as "BOJ-001" (ALEXIT-FST Strukturlack 346-65). The Identifier connects all known names (article number, description, aliases, barcode) to the correct article record.

This is a new feature with no equivalent in the previous paper-based process.

---

## 2. Screen Layout

Single screen with two elements:

**Search field** — large, prominent input at the top. Auto-focuses on page load.

**Results area** — displays matching articles below the search field, or a "not found" state with a report option.

---

## 3. Search Behaviour

- Search activates in real-time as the user types (debounced).
- Searches across: article number, description, aliases, barcode.
- Results appear immediately below the search field.
- No "Search" button required — results update as user types.
- Minimum 2 characters before search activates.

### Search result card

Each matching article is displayed as a card showing:

| Field | Notes |
|-------|-------|
| Article No. | Article number |
| Description | Article description |
| Category | Category label (HR) |
| UOM | Base unit of measure |
| Stock | Depends on role — see section 4 |
| Is Ordered | Whether the article has outstanding open purchase-order lines |
| Ordered Quantity | Depends on role — see section 4 |
| Latest Purchase Price | Depends on role — see section 4 |
| Matched alias | If result was found via alias, show which alias matched (e.g. "Found via alias: 12.36-57") |

---

## 4. Stock & Order Visibility by Role (Wave 9 Phase 3)

| Role | Stock display | Ordered | Ordered Quantity | Latest Purchase Price |
|------|--------------|---------|------------------|-----------------------|
| ADMIN | Exact quantity (e.g. "42.50 kg") | Boolean | Exact quantity | Shown |
| MANAGER | Exact quantity | Boolean | Exact quantity | Shown |
| WAREHOUSE_STAFF | Availability only ("In stock" / "Out of stock") | Boolean | Hidden | Hidden |
| VIEWER | Availability only ("In stock" / "Out of stock") | Boolean | Hidden | Hidden |

### Ordered quantity definition

`ordered_quantity` = sum of `(ordered_qty − received_qty)` across all OPEN order lines on OPEN purchase orders for the article.

`is_ordered` = `true` when `ordered_quantity > 0`.

### Latest purchase price hierarchy

1. Most recent `Receiving.unit_price` (by `received_at` descending)
2. Preferred `ArticleSupplier.last_price`
3. Any `ArticleSupplier.last_price` (by `last_ordered_at` descending)

If none found, `latest_purchase_price` is `null`.

---

## 5. Empty State — Article Not Found

If no articles match the search term:

- Display message: `"No articles found for '[search term]'."`
- Display a **"Report missing article"** button below the message.

### Missing article report flow

1. User clicks "Report missing article".
2. A simple form appears with one field: **search term** (pre-filled with what the user typed, editable).
3. User confirms and submits.
4. POST to `/api/v1/identifier/reports`.
5. On success: show toast `"Report submitted. An admin will review it."`.
6. Duplicate reports (same normalized search term) are merged — the system increments a counter on the existing report rather than creating a new one.

---

## 6. Admin: Missing Article Report Queue

Accessible to ADMIN only — displayed as a separate section or tab within the Identifier screen (or in Reports module).

- Lists all open missing article reports ordered by date descending.
- Each row shows: search term, number of times reported, date first reported, status (OPEN / RESOLVED).
- Admin can resolve a report by clicking "Resolve" and optionally entering a note (e.g. "Article added as BOJ-042").
- Resolved reports move to a separate "Resolved" tab — not deleted.
- A report can only be closed by explicit admin action — it does not close automatically.

### Report queue columns

| Column | Notes |
|--------|-------|
| Search term | What the user searched for |
| Times reported | How many times this term was reported |
| First reported | Date of first report |
| Status | OPEN / RESOLVED |
| Actions | Resolve (with optional note) |

---

## 7. Aliases

- Aliases are managed by ADMIN from the Article detail screen in the Warehouse module — not from the Identifier screen.
- Each article can have multiple aliases.
- Aliases are normalised on save (lowercased, trimmed) for search matching.
- Duplicates are rejected at the DB level.

---

## 8. API Endpoints Used

| Action | Method | Endpoint |
|--------|--------|----------|
| Search articles | GET | `/api/v1/identifier?q={query}` |
| Submit missing article report | POST | `/api/v1/identifier/reports` |
| Get report queue (ADMIN) | GET | `/api/v1/identifier/reports?status=open` |
| Resolve report (ADMIN) | POST | `/api/v1/identifier/reports/{id}/resolve` |

---

## 9. Request / Response Shapes

### GET `/api/v1/identifier?q=12.36` — Search

**Response (200) — ADMIN / MANAGER:**
```json
{
  "items": [
    {
      "id": 42,
      "article_no": "BOJ-001",
      "description": "ALEXIT-FST Strukturlack 346-65",
      "category_label_hr": "Operativni potrošni materijal",
      "base_uom": "kg",
      "decimal_display": true,
      "stock": 42.50,
      "is_ordered": true,
      "ordered_quantity": 15.0,
      "latest_purchase_price": 4.30,
      "matched_via": "alias",
      "matched_alias": "12.36-57"
    }
  ],
  "total": 1
}
```

**Response (200) — WAREHOUSE_STAFF / VIEWER:**
```json
{
  "items": [
    {
      "id": 42,
      "article_no": "BOJ-001",
      "description": "ALEXIT-FST Strukturlack 346-65",
      "category_label_hr": "Operativni potrošni materijal",
      "base_uom": "kg",
      "decimal_display": true,
      "in_stock": true,
      "is_ordered": true,
      "matched_via": "alias",
      "matched_alias": "12.36-57"
    }
  ],
  "total": 1
}
```

> `decimal_display` follows the base UOM catalog entry so the client can format exact quantities without guessing from the UOM code.

### POST `/api/v1/identifier/reports` — Submit report

**Request:**
```json
{
  "search_term": "12.36-57"
}
```

**Response (201):**
```json
{
  "id": 5,
  "search_term": "12.36-57",
  "report_count": 1,
  "status": "OPEN",
  "created_at": "2026-03-10T09:00:00Z"
}
```

> If an OPEN report with the same lowercase-trimmed `normalized_term` already exists, the backend returns `200` and increments `report_count` on that existing row instead of creating a duplicate.

### GET `/api/v1/identifier/reports?status=open` — Admin queue

**Response (200):**
```json
{
  "items": [
    {
      "id": 5,
      "search_term": "12.36-57",
      "report_count": 3,
      "status": "OPEN",
      "created_at": "2026-03-10T09:00:00Z",
      "resolution_note": null,
      "resolved_at": null
    }
  ],
  "total": 1
}
```

### POST `/api/v1/identifier/reports/{id}/resolve` — Resolve report

**Request:**
```json
{
  "resolution_note": "Article added as BOJ-042."
}
```

**Response (200):**
```json
{
  "id": 5,
  "status": "RESOLVED",
  "resolution_note": "Article added as BOJ-042.",
  "resolved_at": "2026-03-10T10:00:00Z"
}
```

---

## 10. Edge Cases

| Situation | Behaviour |
|-----------|-----------|
| Search term less than 2 characters | Frontend does not trigger search. If the endpoint is called anyway, backend returns `200` with an empty `items[]` payload. |
| Multiple articles match | All matching articles shown as cards. |
| Same search term reported multiple times | Report counter incremented, no duplicate record created. |
| VIEWER tries to see exact stock | Stock shown as "In stock" or "Out of stock" only. `ordered_quantity` and `latest_purchase_price` are hidden. |
| WAREHOUSE_STAFF tries to see exact stock | Same boolean-only visibility as VIEWER. |
| Article found via barcode scan | Barcode input works as plain text in the search field — scanner acts as keyboard input. |
| No search term entered | Results area is empty, no empty state shown. |
