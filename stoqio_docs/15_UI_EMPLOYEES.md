# WMS — UI Specification: Employees

**Status**: Active document
**Version**: v1
**Audience**: AI coding agents
**Module**: Employees (`/employees`)
**Accessible by roles**: ADMIN (full), WAREHOUSE_STAFF (read-only)

---

## 1. Purpose

The Employees module tracks personal issuances of articles (protective equipment, tools, work clothing) to individual employees. It maintains a history of what each employee has received and tracks annual quota consumption per job title.

Employees are evidence records only — they do not have login accounts in v1.

---

## 2. Screen Layout

**Main screen** — searchable list of all active employees.
**Employee detail screen** — full employee profile with quota overview and issuance history.

---

## 3. Employees List Screen

### 3.1 Filters & Search

- **Search field** — searches by employee ID, first name, or last name. Debounced input.
- **Show inactive** — toggle (off by default). When enabled, inactive employees appear visually distinguished (greyed out).

### 3.2 List Columns

| Column | Notes |
|--------|-------|
| Employee ID | Internal HR number |
| Full name | First name + last name |
| Job title | Employee's role/position |
| Department | Department name |
| Status | Active / Inactive |

### 3.3 Actions on List Screen

- **"New Employee"** button — opens the employee creation form. ADMIN only.

### 3.4 Empty State

`"No employees found."`

---

## 4. Creating a New Employee

- Fields: employee_id, first_name, last_name, department, job_title, is_active.
- `employee_id` must be unique.
- On submit: POST to `/api/v1/employees`.
- On success: redirect to employee detail screen, show success toast `"Employee created."`.

---

## 5. Employee Detail Screen

### 5.1 Header Section

Displays: employee ID, full name, job title, department, status (active/inactive).

ADMIN can click **"Edit"** to edit all fields inline. On save: PUT to `/api/v1/employees/{id}`.

**"Deactivate"** button — shows confirmation: `"Deactivate this employee? Their history will be preserved."` ADMIN only.

### 5.2 Annual Quota Overview Section

Displays quota consumption for the **current year** for this employee.

One row per article/category that has a quota applicable to this employee's job title (or a personal override).

| Column | Notes |
|--------|-------|
| Article / Category | Article description, or category label if quota is category-level |
| Quota | Annual quota quantity + UOM |
| Received (this year) | Total quantity issued to this employee in the current year |
| Remaining | Quota minus received. Shown in red if 0 or negative. |
| Status | OK / Warning / Exceeded |

**Status logic:**

| Status | Condition |
|--------|-----------|
| OK | Received < quota |
| Warning | Received ≥ quota × 0.80 (within 20% of limit) |
| Exceeded | Received ≥ quota |

If no quotas are defined for this employee's job title: show message `"No quotas configured for this job title."` with a link to Settings.

### 5.3 Issuance History Section

Paginated list of all personal issuances for this employee, newest first.

| Column | Notes |
|--------|-------|
| Date | When issued |
| Article No. | Article number |
| Description | Article description |
| Quantity | Quantity + UOM |
| Batch | Batch code, or "—" |
| Issued by | Admin username |
| Note | If provided, or "—" |

Empty state: `"No issuances recorded for this employee."`

### 5.4 New Issuance Button

**"Issue article"** button — ADMIN only. Opens the issuance form (see section 6).

---

## 6. Issuing an Article

Issuance is always to a single employee. Access via the **"Issue article"** button on the employee detail screen.

### 6.1 Issuance Form Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Article | Search input | Yes | Search by article number or description. Only articles whose category has `is_personal_issue = true` are shown. |
| Quantity | Numeric input | Yes | Positive only. |
| UOM | Display only | — | Auto-populated from article master data. |
| Batch | Dropdown | Conditional | Shown only if article has `has_batch = true`. Lists available batches ordered by expiry date (FEFO). |
| Note | Text input | No | Optional. Max 1000 characters. |

### 6.2 Quota Check on Submit

Before submitting, the system checks whether issuing this quantity would exceed the employee's annual quota for this article/category.

- If quota is not exceeded: submit normally.
- If quota would be exceeded and enforcement is `WARN`: show a warning inline — `"This issuance will exceed the annual quota for [article/category]. Remaining quota: [X] [UOM]."` Admin can still proceed.
- If quota would be exceeded and enforcement is `BLOCK`: block submission, show inline error — `"Annual quota exceeded for [article/category]. Remaining quota: [X] [UOM]."` Admin cannot proceed.

### 6.3 Submitting

- Submit button label: **"Confirm Issuance"**
- On submit: POST to `/api/v1/employees/{id}/issuances`.
- On success: show success toast `"Issuance recorded."`, close form, refresh quota overview and issuance history.
- On error: show error toast.

---

## 7. Quota Configuration

Quotas are configured in the **Settings** module — not on the employee detail screen. The employee screen only displays and enforces them.

Quota priority (highest to lowest):
1. Override per employee + article
2. Override per article (applies to all employees)
3. Default per category (applies to all employees with matching job title)

---

## 8. WAREHOUSE_STAFF Read-only View

- WAREHOUSE_STAFF can view the employee list and employee detail screens.
- Quota overview and issuance history are visible.
- No create, edit, deactivate, or issue actions are available.

---

## 9. API Endpoints Used

| Action | Method | Endpoint |
|--------|--------|----------|
| Get employees list | GET | `/api/v1/employees?page=1&per_page=50&q={query}&include_inactive={bool}` |
| Get employee detail | GET | `/api/v1/employees/{id}` |
| Create employee | POST | `/api/v1/employees` |
| Edit employee | PUT | `/api/v1/employees/{id}` |
| Deactivate employee | PATCH | `/api/v1/employees/{id}/deactivate` |
| Get quota overview (current year) | GET | `/api/v1/employees/{id}/quotas` |
| Get issuance history | GET | `/api/v1/employees/{id}/issuances?page=1&per_page=50` |
| Issue article | POST | `/api/v1/employees/{id}/issuances` |

---

## 10. Request / Response Shapes

### POST `/api/v1/employees` — Create employee

**Request:**
```json
{
  "employee_id": "EMP-042",
  "first_name": "Sunil",
  "last_name": "Thapa",
  "department": "Lakiranje",
  "job_title": "Operater lakiranja",
  "is_active": true
}
```

**Response (201):**
```json
{
  "id": 7,
  "employee_id": "EMP-042",
  "first_name": "Sunil",
  "last_name": "Thapa",
  "department": "Lakiranje",
  "job_title": "Operater lakiranja",
  "is_active": true,
  "created_at": "2026-03-10T10:00:00Z"
}
```

### POST `/api/v1/employees/{id}/issuances` — Issue article

**Request:**
```json
{
  "article_id": 12,
  "batch_id": null,
  "quantity": 2.0,
  "uom": "kom",
  "note": null
}
```

**Response (201):**
```json
{
  "id": 55,
  "employee_id": 7,
  "article_id": 12,
  "article_no": "HLN-002",
  "description": "Antistatičke hlače vel. 44",
  "batch_id": null,
  "quantity": 2.0,
  "uom": "kom",
  "issued_by": "admin",
  "issued_at": "2026-03-10T10:30:00Z"
}
```

### GET `/api/v1/employees/{id}/quotas` — Quota overview

**Response (200):**
```json
{
  "year": 2026,
  "quotas": [
    {
      "article_id": 12,
      "article_no": "HLN-002",
      "description": "Antistatičke hlače",
      "quota": 2.0,
      "received": 1.0,
      "remaining": 1.0,
      "uom": "kom",
      "enforcement": "WARN",
      "status": "OK"
    }
  ]
}
```

---

## 11. Edge Cases

| Situation | Behaviour |
|-----------|-----------|
| Employee ID already exists | Inline error: `"Employee ID already exists."` |
| Article not in personal-issue category | Article not shown in issuance form search results. |
| No batches available for batch-tracked article | Inline error: `"No batches available for this article."` Block submission. |
| Quota exceeded, enforcement = WARN | Warning shown, admin can still proceed. |
| Quota exceeded, enforcement = BLOCK | Submission blocked, inline error shown. |
| No quotas configured for job title | Issuance proceeds without quota check. Message shown in quota section. |
| Deactivating employee with issuance history | Allowed. History preserved. |
| WAREHOUSE_STAFF tries to issue | Action button not visible. |
