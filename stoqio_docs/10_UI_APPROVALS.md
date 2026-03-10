# WMS — UI Specification: Approvals

**Status**: Active document
**Version**: v1
**Audience**: AI coding agents
**Module**: Approvals (`/approvals`)
**Accessible by roles**: ADMIN

---

## 1. Purpose

The Approvals screen is where the ADMIN reviews, corrects, and approves (or rejects) daily material consumption drafts submitted by operators. It replaces the manual process of collecting paper forms, aggregating quantities per article, and entering them into an ERP system.

The system automatically aggregates draft lines by article, so the ADMIN sees one row per article (with total quantity) instead of individual operator entries.

---

## 2. Screen Layout

The screen has two tabs or sections:

**Pending** (default view) — drafts waiting for approval.
**History** — all past drafts (approved, rejected, or older pending).

---

## 3. Pending View

### 3.1 Draft List

Displays one card or section per day, showing the operational date and total number of lines.

Each draft card expands to show the **aggregated lines table**.

### 3.2 Aggregated Lines Table

Lines are grouped by `article + batch`. Each row shows the sum of all operator entries for that article/batch combination on that day.

| Column | Notes |
|--------|-------|
| Article No. | Article number |
| Description | Article description |
| Batch | Batch code, or "—" if no batch |
| Total Quantity | Sum of all operator entries for this article/batch |
| UOM | Unit of measure |
| Actions | Edit quantity (pencil), Reject line (x icon), Approve line (checkmark) |

> **Important**: Different batches of the same article appear as separate rows.

### 3.3 Expanding a Row

Each aggregated row can be expanded to reveal the individual operator entries that make up the total:

| Column | Notes |
|--------|-------|
| Time | HH:MM when the line was entered |
| Operator | Username of the operator |
| Quantity | Individual quantity entered |
| Employee ID | If provided |
| Note | If provided |

This allows the ADMIN to trace exactly who entered what and when.

---

## 4. Approving

### 4.1 Approve a Single Line

- Click the checkmark icon on a row.
- System applies surplus-first logic: consumes surplus first, then stock.
- If stock would go below zero: block approval, show inline error `"Insufficient stock."`.
- If stock would fall below reorder threshold after approval: show warning toast `"Stock for [article] will fall below minimum after this approval."` — approval is still allowed.
- On success: row moves to approved state (greyed out or removed from pending view).

### 4.2 Approve All

- "Approve All" button at the top of the draft.
- Approves all pending lines in the draft at once.
- If any line has insufficient stock: that line is skipped and shown with an inline error. All other lines are approved.
- Reorder threshold warnings are shown as a summary toast after bulk approval.

---

## 5. Editing Before Approval

- ADMIN can edit the **quantity** of any pending aggregated line before approving.
- Click pencil icon → inline edit field appears for quantity.
- On save: PATCH to `/api/v1/approvals/{draft_group_id}/lines/{article_id}` with updated quantity.
- Editing the aggregated quantity overwrites the total — individual operator entries are preserved in history but the approved quantity reflects the ADMIN's correction.
- On success: updated quantity shown in the row.

---

## 6. Rejecting

### 6.1 Reject a Single Line

- Click the reject (x) icon on a row.
- A modal appears asking for a **reason** (required, free text, max 500 characters).
- On confirm: line is rejected. Stock is not affected.
- Rejected line is removed from pending view and visible in history.

### 6.2 Reject Entire Draft

- "Reject All" button at the top of the draft.
- A modal appears asking for a **reason** (required, free text, max 500 characters).
- On confirm: entire draft is rejected. Stock is not affected.
- Draft moves to history with status `REJECTED`.

---

## 7. History View

- Lists all past drafts ordered by date descending (newest first).
- Each draft shows: date, status (APPROVED / REJECTED / PARTIAL), total lines.
- Expandable — same detail view as pending, but all fields are read-only.
- No actions available in history — read-only.

---

## 8. API Endpoints Used

| Action | Method | Endpoint |
|--------|--------|----------|
| Get pending drafts | GET | `/api/v1/approvals?status=pending` |
| Get draft history | GET | `/api/v1/approvals?status=history` |
| Get draft detail (lines) | GET | `/api/v1/approvals/{draft_group_id}` |
| Edit aggregated line quantity | PATCH | `/api/v1/approvals/{draft_group_id}/lines/{line_id}` |
| Approve single line | POST | `/api/v1/approvals/{draft_group_id}/lines/{line_id}/approve` |
| Approve all lines | POST | `/api/v1/approvals/{draft_group_id}/approve` |
| Reject single line | POST | `/api/v1/approvals/{draft_group_id}/lines/{line_id}/reject` |
| Reject entire draft | POST | `/api/v1/approvals/{draft_group_id}/reject` |

---

## 9. Request / Response Shapes

### POST `.../approve` — Approve single line

**Response (200):**
```json
{
  "line_id": 12,
  "article_id": 42,
  "article_no": "BOJ-001",
  "approved_quantity": 5.0,
  "uom": "kg",
  "stock_after": 94.5,
  "surplus_consumed": 0.0,
  "stock_consumed": 5.0,
  "reorder_warning": false
}
```

### POST `.../reject` — Reject line or draft

**Request:**
```json
{
  "reason": "Quantity appears incorrect — please re-enter."
}
```

**Response (200):**
```json
{
  "status": "REJECTED",
  "reason": "Quantity appears incorrect — please re-enter."
}
```

---

## 10. Edge Cases

| Situation | Behaviour |
|-----------|-----------|
| Insufficient stock for approval | Block approval, show inline error `"Insufficient stock."` |
| Stock falls below reorder threshold after approval | Allow approval, show warning toast |
| Approving a line that was already approved | Return 409, show error toast `"This line has already been approved."` |
| Rejecting without entering a reason | Block submission, show inline error `"Reason is required."` |
| Draft has mix of approved and rejected lines | Draft status shown as `PARTIAL` in history |
| No pending drafts | Empty state: `"No pending drafts."` |
