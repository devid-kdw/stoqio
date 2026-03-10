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
| Surplus | Depends on role — see section 4 |
| Matched alias | If result was found via alias, show which alias matched (e.g. "Found via alias: 12.36-57") |

---

## 4. Stock Visibility by Role

| Role | Stock display |
|------|--------------|
| ADMIN | Exact quantity (e.g. "42.50 kg") |
| MANAGER | Exact quantity |
| WAREHOUSE_STAFF | Exact quantity |
| VIEWER | Availability only ("In stock" / "Out of stock") |

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

**Response (200):**
```json
{
  "items": [
    {
      "id": 42,
      "article_no": "BOJ-001",
      "description": "ALEXIT-FST Strukturlack 346-65",
      "category": "operational_supplies",
      "base_uom": "kg",
      "stock": 42.50,
      "surplus": 0.0,
      "matched_via": "alias",
      "matched_alias": "12.36-57"
    }
  ],
  "total": 1
}
```

> For VIEWER role, `stock` is replaced with `in_stock: true/false` and `surplus` is omitted.

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
  "status": "OPEN",
  "created_at": "2026-03-10T09:00:00Z"
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
| Search term less than 2 characters | No search triggered. Results area is empty. |
| Multiple articles match | All matching articles shown as cards. |
| Same search term reported multiple times | Report counter incremented, no duplicate record created. |
| VIEWER tries to see exact stock | Stock shown as "In stock" or "Out of stock" only. |
| Article found via barcode scan | Barcode input works as plain text in the search field — scanner acts as keyboard input. |
| No search term entered | Results area is empty, no empty state shown. |
