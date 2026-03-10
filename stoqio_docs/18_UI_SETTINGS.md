# WMS — UI Specification: Settings

**Status**: Active document
**Version**: v1
**Audience**: AI coding agents
**Module**: Settings (`/settings`)
**Accessible by roles**: ADMIN

---

## 1. Purpose

The Settings screen is where the ADMIN configures the system at installation and adjusts it over time. All settings are installation-specific — they adapt the software to each customer's business without changing the system's internal logic.

Settings are grouped into sections. Changes take effect immediately on save unless otherwise noted.

---

## 2. Screen Layout

Single page with clearly separated sections, each with its own Save button:

1. **General** — location name, language, timezone
2. **Roles** — display names for system roles
3. **UOM Catalog** — units of measure
4. **Article Categories** — category labels and personal issue flag
5. **Quotas** — annual quotas for personal issuances per job title
6. **Barcode** — barcode format and printer configuration
7. **Export** — SAP/Excel export format
8. **Suppliers** — supplier master data (create, edit, deactivate)
9. **Users** — user management (create, edit, deactivate system users)

---

## 3. Section: General

| Field | Type | Notes |
|-------|------|-------|
| Location name | Text input | Required. Max 100 characters. Displayed in the UI header. |
| Default UI language | Dropdown | Options: Hrvatski (hr), English (en), Deutsch (de), Magyar (hu). Default: hr. |
| Operational timezone | Dropdown | Used for day grouping in Approvals and timestamps. Default: Europe/Berlin. |

---

## 4. Section: Roles

Display names for each system role. The system role key never changes — only the label shown in the UI.

| System role | Display name field | Default |
|-------------|--------------------|---------|
| `ADMIN` | Text input | Admin |
| `MANAGER` | Text input | Menadžment |
| `WAREHOUSE_STAFF` | Text input | Administracija |
| `VIEWER` | Text input | Kontrola |
| `OPERATOR` | Text input | Operater |

- Max 50 characters per display name.
- Display names are shown everywhere in the UI where a role is mentioned (user list, login screen, etc.).

---

## 5. Section: UOM Catalog

Displays all current units of measure. Admin can add new units.

### 5.1 Existing Units Table

| Column | Notes |
|--------|-------|
| Code | Unit code (e.g. `kg`, `kom`) — not editable after creation |
| Label (HR) | Croatian label |
| Label (EN) | English label |
| Decimal display | Yes / No — controls quantity display format |

### 5.2 Adding a New Unit

- "Add unit" button opens an inline form: code, label_hr, label_en, decimal_display (toggle).
- Code must be unique.
- On save: POST to `/api/v1/settings/uom`.

> Units cannot be deleted once created — they may be referenced by existing articles and transactions.

---

## 6. Section: Article Categories

Displays all article categories. Admin can edit labels and configure the personal issue flag.

### 6.1 Categories Table

| Column | Notes |
|--------|-------|
| Key | System key (e.g. `safety_equipment`) — read-only, never changes |
| Label (HR) | Croatian label — editable |
| Label (EN) | English label — editable |
| Personal issue | Toggle — if enabled, articles in this category appear in the issuance form |
| Default annual quota | Numeric input + UOM — default quota for all employees in any job title |

> The system key is fixed and used in all internal logic. Only the display labels are editable.

---

## 7. Section: Quotas

Annual quota configuration for personal issuances. Quotas are defined per job title and category/article.

### 7.1 Purpose

Defines how much of a given article or category an employee with a specific job title can receive per year.

### 7.2 Quota Table

| Column | Notes |
|--------|-------|
| Job title | Free text — must match employee job_title exactly |
| Article / Category | Article or category this quota applies to |
| Quantity | Annual quota quantity |
| UOM | Unit of measure |
| Enforcement | WARN / BLOCK |
| Reset month | Month when quota resets (1 = January) |

### 7.3 Adding a Quota

- "Add quota" button opens a form.
- Fields: job title (text input), scope (dropdown: Category / Article), article or category selector, quantity, UOM, enforcement (WARN / BLOCK), reset month (1–12, default 1).
- On save: POST to `/api/v1/settings/quotas`.

### 7.4 Editing / Deleting a Quota

- Each row has Edit and Delete actions.
- Deleting a quota does not affect past issuance history — only future enforcement.

### 7.5 Quota Priority

The system applies quotas in this priority order (highest first):
1. Override per employee + article (set from employee detail screen)
2. Override per article (set here, applies to all employees)
3. Default per job title + category (set here)

---

## 8. Section: Barcode

| Field | Type | Notes |
|-------|------|-------|
| Barcode format | Dropdown | EAN-13 / Code128. Default: Code128. |
| Barcode printer | Text input | Printer name as configured in the operating system on the Raspberry Pi. Used when printing barcode PDFs. |

> Barcode printer field is free text — it must match the printer name exactly as it appears in the Pi's system printer list. No printer discovery UI in v1.

---

## 9. Section: Export

| Field | Type | Notes |
|-------|------|-------|
| Excel column format | Dropdown | SAP-compatible / Generic. Default: Generic. When SAP-compatible is selected, exported Excel files use SAP column names and format. |

---

## 10. Section: Suppliers

Supplier master data management. Suppliers are referenced in Orders — they must exist before an order can be created.

### 10.1 Suppliers Table

| Column | Notes |
|--------|-------|
| Internal code | Unique supplier identifier |
| Name | Supplier name |
| Contact person | Contact name, or "—" |
| Phone | Phone number, or "—" |
| Status | Active / Inactive |
| Actions | Edit, Deactivate |

- Search field at the top — searches by internal code or name. Debounced.
- Inactive suppliers shown only when "Show inactive" toggle is enabled (off by default).

### 10.2 Creating a New Supplier

- "New supplier" button opens a form.
- Fields: internal_code (required, unique), name (required), contact_person, phone, email, address, iban, note.
- On save: POST to `/api/v1/settings/suppliers`.
- On success: show success toast `"Supplier created."`.

### 10.3 Editing a Supplier

- All fields editable except `internal_code` (immutable after creation).
- On save: PUT to `/api/v1/settings/suppliers/{id}`.

### 10.4 Deactivating a Supplier

- Deactivated suppliers are hidden from order creation dropdowns.
- Their history (past orders, receiving) is preserved.
- Confirmation: `"Deactivate this supplier? They will no longer appear in order forms."`

---

## 11. Section: Users

User management for system accounts (not employees — these are login users).

### 11.1 Users Table

| Column | Notes |
|--------|-------|
| Username | Login username |
| Role | System role (display name shown) |
| Status | Active / Inactive |
| Created | Date created |
| Actions | Edit, Deactivate |

### 11.2 Creating a New User

- "New user" button opens a form.
- Fields: username, password, role (dropdown), is_active.
- Username must be unique.
- Password: minimum 4 characters.
- On save: POST to `/api/v1/settings/users`.
- On success: show success toast `"User created."`.

### 11.3 Editing a User

- Admin can change: role, is_active status.
- Admin can reset password (sets a new password — no old password required).
- Username cannot be changed after creation.
- On save: PUT to `/api/v1/settings/users/{id}`.

### 11.4 Deactivating a User

- Deactivated users cannot log in.
- Their history (drafts, approvals, transactions) is preserved.
- Confirmation: `"Deactivate this user? They will no longer be able to log in."`

> Admin cannot deactivate their own account.

---

## 12. API Endpoints Used

| Action | Method | Endpoint |
|--------|--------|----------|
| Get all settings | GET | `/api/v1/settings` |
| Save general settings | PUT | `/api/v1/settings/general` |
| Save role display names | PUT | `/api/v1/settings/roles` |
| Get UOM catalog | GET | `/api/v1/settings/uom` |
| Add UOM | POST | `/api/v1/settings/uom` |
| Get categories | GET | `/api/v1/settings/categories` |
| Update category | PUT | `/api/v1/settings/categories/{id}` |
| Get quotas | GET | `/api/v1/settings/quotas` |
| Add quota | POST | `/api/v1/settings/quotas` |
| Edit quota | PUT | `/api/v1/settings/quotas/{id}` |
| Delete quota | DELETE | `/api/v1/settings/quotas/{id}` |
| Save barcode settings | PUT | `/api/v1/settings/barcode` |
| Save export settings | PUT | `/api/v1/settings/export` |
| Get suppliers | GET | `/api/v1/settings/suppliers` |
| Create supplier | POST | `/api/v1/settings/suppliers` |
| Edit supplier | PUT | `/api/v1/settings/suppliers/{id}` |
| Deactivate supplier | PATCH | `/api/v1/settings/suppliers/{id}/deactivate` |
| Get users | GET | `/api/v1/settings/users` |
| Create user | POST | `/api/v1/settings/users` |
| Edit user | PUT | `/api/v1/settings/users/{id}` |
| Deactivate user | PATCH | `/api/v1/settings/users/{id}/deactivate` |

---

## 13. Edge Cases

| Situation | Behaviour |
|-----------|-----------|
| Saving general settings with empty location name | Inline error: `"Location name is required."` |
| Adding UOM with existing code | Inline error: `"Unit code already exists."` |
| Deleting a quota with active employees | Quota deleted. Past issuance history unaffected. Future enforcement removed. |
| Creating supplier with existing internal code | Inline error: `"Supplier code already exists."` |
| Creating user with existing username | Inline error: `"Username already exists."` |
| Admin tries to deactivate own account | Action blocked. Show inline error: `"You cannot deactivate your own account."` |
| Barcode printer name does not match system printer | No validation in UI — admin must ensure the name is correct. Incorrect name will cause print errors at print time. |
| Changing timezone | Takes effect immediately. Existing draft groupings are not retroactively recalculated. |
