# WMS — UI Specification: Inventory Count

**Status**: Active document
**Version**: v1
**Audience**: AI coding agents
**Module**: Inventory Count (`/inventory`)
**Accessible by roles**: ADMIN

---

## 1. Purpose

The Inventory Count screen is where the ADMIN conducts periodic stock counts and reconciles discrepancies between the physical count and the system state. It replaces the paper-based inventory list (printed, filled in by hand, archived by date).

A count is done by one person, going article by article in warehouse order, entering the physically counted quantity for each. The system automatically handles discrepancies.

---

## 2. Inventory Count Lifecycle

```
(no active count)
       ↓ Admin starts new count
  IN_PROGRESS
       ↓ Admin completes count
   COMPLETED
```

- Only one inventory count can be `IN_PROGRESS` at a time.
- A count cannot be deleted — it is a permanent record.
- A completed count is read-only.

---

## 3. Screen Layout

**Main screen** — shows either:
- The active count (if one is `IN_PROGRESS`), or
- The history of past counts (if no active count exists).

These two states occupy the same screen — no tabs needed. The presence or absence of an active count determines what is shown.

---

## 4. No Active Count — History View

When no count is `IN_PROGRESS`, the screen shows:

- **"Start New Count"** button at the top.
- List of all past completed counts, ordered by date descending (newest first).

### History List Columns

| Column | Notes |
|--------|-------|
| Date | Date the count was started |
| Started by | Admin username |
| Total lines | Number of articles counted |
| Discrepancies | Number of lines where counted ≠ system quantity |
| Status | COMPLETED |

- Clicking a row opens the completed count detail (read-only).

### Empty State

`"No inventory counts recorded yet."`

---

## 5. Starting a New Count

- Admin clicks **"Start New Count"**.
- System creates a new `InventoryCount` record with status `IN_PROGRESS`.
- System automatically generates one `InventoryCountLine` per active article (and per batch if `has_batch = true`), capturing the current system quantity as `system_quantity` at that moment.
- Admin is immediately taken to the active count screen.

> **Note**: `system_quantity` is captured at the moment the count is started and does not change during the count. Any approvals or receipts that happen during the count do not affect `system_quantity` for this count.

---

## 6. Active Count Screen

Displayed when a count is `IN_PROGRESS`.

### 6.1 Header

Shows: date started, started by, progress indicator (e.g. "47 / 120 counted").

**"Complete Count"** button — visible but disabled until all lines have a `counted_quantity` entered. When all lines are filled: button becomes active.

### 6.2 Count Lines Table

One row per article (and per batch for batch-tracked articles).

| Column | Notes |
|--------|-------|
| Article No. | Article number |
| Description | Article description |
| Batch | Batch code, or "—" if no batch |
| Expiry date | Expiry date if batch exists, or "—" |
| System qty | Quantity recorded in the system at count start |
| UOM | Unit of measure |
| Counted qty | Numeric input — admin enters physically counted quantity |
| Difference | Calculated: `counted - system`. Shown once counted qty is entered. Positive = surplus, negative = shortage. |
| Resolution | Shown after count is completed — see section 8. |

### 6.3 Entering Counted Quantities

- Admin clicks into the "Counted qty" field of a row and types the physically counted quantity.
- Input must be ≥ 0 (zero is valid — article was not found).
- Field accepts decimal input for decimal UOM articles; integer only for integer UOM articles.
- As admin types, the "Difference" column updates in real time.
- No save button per row — values are saved automatically on blur (field loses focus).
- PATCH to `/api/v1/inventory/{count_id}/lines/{line_id}` on each blur.

### 6.4 Visual Indicators on Rows

- Row with no counted qty entered: neutral (default).
- Row where `counted = system`: subtle green indicator — no discrepancy.
- Row where `counted > system`: subtle blue indicator — surplus found.
- Row where `counted < system`: subtle yellow indicator — shortage found.
- Row not yet counted (counted qty is NULL): no colour.

### 6.5 Filtering

- **Show only discrepancies** toggle — when enabled, shows only rows where counted ≠ system. Useful for review before completing.
- **Show only uncounted** toggle — when enabled, shows only rows where counted qty is still NULL.

---

## 7. Completing the Count

- Admin clicks **"Complete Count"** (only available when all lines have a counted qty).
- Confirmation prompt: `"Complete this inventory count? Discrepancies will be processed automatically. This cannot be undone."`
- On confirm: POST to `/api/v1/inventory/{count_id}/complete`.
- System processes all lines automatically (see section 8).
- Count status changes to `COMPLETED`.
- Admin is shown the completed count summary screen.

---

## 8. Discrepancy Processing (automatic on completion)

The system processes each line on completion:

| Situation | Action | Resolution label |
|-----------|--------|-----------------|
| `counted = system` | No change | `NO_CHANGE` |
| `counted > system` | Difference is added to Surplus automatically | `SURPLUS_ADDED` |
| `counted < system` | A shortage Draft is created (status `DRAFT`, type `INVENTORY_SHORTAGE`) for admin approval | `SHORTAGE_DRAFT_CREATED` |

> Shortage drafts created by inventory count follow the same approval workflow as regular outbound drafts. They appear in the Approvals module as pending items. The admin reviews and approves them there — this is intentional, as the shortage may need investigation before stock is reduced.

---

## 9. Completed Count Detail Screen

Read-only view of a completed count.

- Header: date, started by, completed at.
- Summary: total lines, lines with no change, surpluses added, shortage drafts created.
- Full lines table (same columns as active count, all read-only, with Resolution column filled in).
- Filter by resolution: All / NO_CHANGE / SURPLUS_ADDED / SHORTAGE_DRAFT_CREATED.

---

## 10. API Endpoints Used

| Action | Method | Endpoint |
|--------|--------|----------|
| Get count history | GET | `/api/v1/inventory?page=1&per_page=50` |
| Start new count | POST | `/api/v1/inventory` |
| Get active count | GET | `/api/v1/inventory/active` |
| Get count detail | GET | `/api/v1/inventory/{id}` |
| Update counted qty on a line | PATCH | `/api/v1/inventory/{id}/lines/{line_id}` |
| Complete count | POST | `/api/v1/inventory/{id}/complete` |

---

## 11. Request / Response Shapes

### POST `/api/v1/inventory` — Start new count

**Response (201):**
```json
{
  "id": 8,
  "status": "IN_PROGRESS",
  "started_by": "admin",
  "started_at": "2026-03-10T07:00:00Z",
  "total_lines": 120
}
```

### PATCH `/api/v1/inventory/{id}/lines/{line_id}` — Update counted qty

**Request:**
```json
{
  "counted_quantity": 47.50
}
```

**Response (200):**
```json
{
  "line_id": 34,
  "article_id": 42,
  "article_no": "BOJ-001",
  "system_quantity": 50.00,
  "counted_quantity": 47.50,
  "difference": -2.50,
  "uom": "kg"
}
```

### POST `/api/v1/inventory/{id}/complete` — Complete count

**Response (200):**
```json
{
  "id": 8,
  "status": "COMPLETED",
  "completed_at": "2026-03-10T09:30:00Z",
  "summary": {
    "total_lines": 120,
    "no_change": 98,
    "surplus_added": 14,
    "shortage_drafts_created": 8
  }
}
```

---

## 12. Edge Cases

| Situation | Behaviour |
|-----------|-----------|
| Admin tries to start a new count while one is already IN_PROGRESS | Block. Show inline error: `"An inventory count is already in progress."` |
| Admin tries to complete count with uncounted lines | "Complete Count" button remains disabled. Show tooltip: `"All lines must be counted before completing."` |
| Counted quantity is 0 | Valid. Difference = `0 - system_quantity` (shortage for entire stock). |
| New article added to system after count started | Not included in this count — it was not in the system when count lines were generated. |
| Article deactivated after count started | Its line remains in the count and must be counted. Deactivation does not remove it. |
| Approval of shortage drafts from inventory | Handled in the Approvals module — same flow as regular outbound drafts. |
