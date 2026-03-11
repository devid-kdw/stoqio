# WMS — UI Specification: Draft Entry

**Status**: Active document
**Version**: v1
**Audience**: AI coding agents
**Module**: Draft Entry (`/drafts`)
**Accessible by roles**: OPERATOR, ADMIN

---

## 1. Purpose

The Draft Entry screen is where operators record material consumption throughout the day. Each entry is a line item on a shared daily draft. The draft is reviewed and approved by an ADMIN at the end of the day or the next morning.

This screen replaces the paper-based *Material Consumption Sheet* used in manual workflows.

---

## 2. Draft Lifecycle

- One draft exists per operational day per location.
- The system automatically creates a new draft for today if one does not exist when the first line is submitted.
- The draft automatically closes at midnight (based on the location's configured timezone).
- After closing, the draft becomes visible in the Approvals module for ADMIN review.
- Operators cannot manually submit or close a draft — it closes automatically.

---

## 3. Shared Draft

- All operators share the same draft for the current day.
- All lines entered by any operator on the current day are visible to all operators on this screen.
- Each line records which user created it (`created_by`).

---

## 4. Screen Layout

The screen has two sections:

**Top section — Entry form**: fields for adding a new line to today's draft.

**Bottom section — Today's draft**: the shared draft for the current operational day, including an optional draft-level note and a table of all lines entered today (by all operators), with options to edit or delete each line.

---

## 5. Entry Form Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Article number | Text input | Yes | Operator types or scans barcode. On valid input, article description is displayed below the field automatically. |
| Article description | Display only | — | Auto-populated from article master data after article number is resolved. Not editable. |
| Quantity | Numeric input | Yes | Positive numbers only. Decimal display depends on UOM (see globals). |
| UOM | Display only | — | Auto-populated from article master data. Not editable. |
| Batch | Dropdown / Text input | Conditional | Shown only if article has `has_batch = true`. Required if shown. Displays available batches for the article ordered by expiry date (FEFO). |
| Employee ID | Text input | No | Optional. ID of the employee receiving the material (from Employee master data). Free text — no lookup validation in v1. |

### Draft-level note

- The current day's shared draft has a single optional note.
- This note applies to the entire daily draft (`DraftGroup`), not to individual lines.
- Max length: 1000 characters.
- The note is displayed and edited in the **Today's draft** section, not inside each table row.
- If no draft exists yet, the entered draft note is saved with the first successful line submission.
- After the day's draft exists, the draft note can be updated without adding a new line.

### Article number lookup behaviour

1. Operator types article number (or scans barcode).
2. On input change (debounced) or on blur: system looks up the article.
3. If found: display article description below the field. Populate UOM. Show batch field if `has_batch = true`.
4. If not found: show inline error `"Article not found."` below the field.
5. Operator cannot submit the form if article is not resolved.

### Batch field behaviour

- Shown only when article has `has_batch = true`.
- Displays a dropdown of existing batches for the article, ordered by expiry date ascending (earliest first — FEFO).
- Operator selects a batch from the dropdown.
- If no batches exist for the article: show inline error `"No batches available for this article."` and block submission.

---

## 6. Submitting a Line

- Submit button label: **"Add"**
- On submit:
  1. Validate all required fields (inline errors if missing).
  2. POST to `/api/v1/drafts` with the line data.
  3. On success: clear the form (keep article number field focused for fast repeated entry), append new line to the bottom table.
  4. On error: show toast with error message.
- The submit button is disabled and shows a spinner while the request is in flight.

If a draft-level note has been entered before the first line of the day, that note is included with the first successful line submission so the newly created daily draft stores it immediately.

---

## 7. Today's Draft

The bottom section represents the current operational day's shared draft (`DraftGroup`).

It contains:
- the draft status badge (`OPEN`)
- an optional draft-level note for the whole day
- a table of individual draft lines, newest first

Daily drafts are persisted and remain available for later review in the Approvals module history.

### 7.1 Draft-level note

- Label: **"Napomena za današnji draft"**
- Optional free text
- Applies to the whole daily draft, not to a single line
- Saved on the draft group (`DraftGroup.description`)

### 7.2 Today's Lines Table

Displays all draft lines for today's draft, newest first.

### Columns

| Column | Notes |
|--------|-------|
| Time | Time the line was created (HH:MM format, local timezone) |
| Article No. | Article number |
| Description | Article description |
| Quantity | Formatted per UOM decimal rules |
| UOM | Unit of measure |
| Batch | Batch code, or "—" if article has no batch |
| Created by | Username of the operator who entered the line |
| Actions | Edit (pencil icon), Delete (trash icon) |

### Empty state

`"No entries for today yet."`

---

## 8. Editing a Line

- Clicking the edit (pencil) icon on a line opens an inline edit form within the table row (or a modal — implementation choice).
- **Only the Quantity field is editable.** All other fields are read-only after creation.
- On save: PATCH to `/api/v1/drafts/{id}` with updated quantity.
- On success: update the row in the table, show success toast `"Entry updated."`.
- On error: show error toast.

---

## 9. Deleting a Line

- Clicking the delete (trash) icon shows a confirmation prompt: `"Delete this entry? This cannot be undone."`
- On confirm: DELETE to `/api/v1/drafts/{id}`.
- On success: remove the row from the table, show success toast `"Entry deleted."`.
- On error: show error toast.
- Confirmation can be a simple inline confirm (two buttons: Confirm / Cancel) — no modal required.

---

## 10. Restrictions

- Operators **cannot** change the date or time of an entry — always uses current timestamp.
- Operators **cannot** edit or delete lines that have already been approved (status `APPROVED`). These lines are read-only.
- Operators **cannot** submit a line with quantity 0 or negative.
- Operators **can** edit or delete lines with status `DRAFT` only.

---

## 11. Draft Status Indicator

- Display a status badge at the top of the screen showing the current draft status: **OPEN** (today's draft is active).
- If today's draft does not exist yet (no lines entered today): show the empty state in the table and allow adding the first line (which triggers draft creation).

---

## 12. API Endpoints Used

| Action | Method | Endpoint |
|--------|--------|----------|
| Get today's draft lines | GET | `/api/v1/drafts?date=today` |
| Add a line | POST | `/api/v1/drafts` |
| Update today's draft note | PATCH | `/api/v1/drafts/group` |
| Edit a line (quantity) | PATCH | `/api/v1/drafts/{id}` |
| Delete a line | DELETE | `/api/v1/drafts/{id}` |
| Lookup article by number/barcode | GET | `/api/v1/articles?q={query}` |

---

## 13. Request / Response Shapes

### POST `/api/v1/drafts` — Add line

**Request:**
```json
{
  "article_id": 42,
  "batch_id": 7,
  "quantity": 2.5,
  "uom": "kg",
  "employee_id_ref": "EMP-042",
  "draft_note": "Lakirnica - dnevni izlaz za drugu smjenu",
  "source": "manual",
  "client_event_id": "uuid-generated-by-frontend"
}
```

**Response (201):**
```json
{
  "id": 101,
  "draft_group_id": 5,
  "article_id": 42,
  "article_no": "BOJ-001",
  "description": "Epoxy paint RAL 7035",
  "batch_id": 7,
  "batch_code": "24001",
  "quantity": 2.5,
  "uom": "kg",
  "employee_id_ref": "EMP-042",
  "status": "DRAFT",
  "source": "manual",
  "created_by": "operator1",
  "created_at": "2026-03-10T08:42:00Z"
}
```

### PATCH `/api/v1/drafts/group` — Update today's draft note

**Request:**
```json
{
  "draft_note": "Lakirnica - dnevni izlaz za drugu smjenu"
}
```

**Response (200):**
```json
{
  "id": 5,
  "group_number": "IZL-0005",
  "status": "PENDING",
  "operational_date": "2026-03-10",
  "draft_note": "Lakirnica - dnevni izlaz za drugu smjenu"
}
```

### PATCH `/api/v1/drafts/{id}` — Edit quantity

**Request:**
```json
{
  "quantity": 3.0
}
```

**Response (200):** updated draft line object (same shape as above).

---

## 14. Edge Cases

| Situation | Behaviour |
|-----------|-----------|
| Article number not found | Inline error below field: `"Article not found."` Block submission. |
| Article has batches but none exist | Inline error: `"No batches available for this article."` Block submission. |
| Draft for today does not exist | System creates it automatically on first line submission. No action required from operator. |
| Draft note entered before the first line exists | The note is saved together with the first successful line submission. |
| Operator tries to edit an APPROVED line | Edit and delete buttons are hidden/disabled for approved lines. |
| Two operators submit simultaneously | Backend handles concurrency. Each line is independent — no conflict. |
| Midnight cutoff reached while operator has unsaved form | Form submission after midnight creates a line on the new day's draft. No warning needed. |
