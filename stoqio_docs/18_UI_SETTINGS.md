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

1. **Općenito** — location name, language, timezone
2. **Role** — display names for system roles
3. **Katalog jedinica mjere** — units of measure
4. **Kategorije artikala** — category labels and personal issue flag
5. **Kvote** — annual quotas for personal issuances per job title
6. **Barkodovi** — barcode format and printer configuration
7. **Izvoz** — SAP/Excel export format
8. **Dobavljači** — supplier master data (create, edit, deactivate)
9. **Korisnici** — user management (create, edit, deactivate system users)

---

## 3. Section: Općenito

| Field | Type | Notes |
|-------|------|-------|
| Location name | Text input | Required. Max 100 characters. Displayed in the UI header. |
| Default UI language | Dropdown | Options: Hrvatski (hr), English (en), Deutsch (de), Magyar (hu). Default: hr. |
| Operational timezone | Dropdown | Used for day grouping in Approvals and timestamps. Default: Europe/Berlin. |

---

## 4. Section: Role

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

## 5. Section: Katalog jedinica mjere

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

## 6. Section: Kategorije artikala

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

## 7. Section: Kvote

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

## 8. Section: Barkodovi

Odjeljak Barkodovi kontrolira format barkoda i dva odvojena načina ispisa dostupna u sustavu.

### 8.1 Format barkoda

| Field | Type | Notes |
|-------|------|-------|
| Format barkoda | Dropdown | EAN-13 / Code128. Default: Code128. Applied when generating barcode images for articles and batches. |

### 8.2 Ispis kroz PDF preuzimanje (`barcode_printer`)

| Field | Type | Notes |
|-------|------|-------|
| Barkod printer | Text input | Optional. OS-level printer name configured on the host machine. Free-text field — must match the host OS printer name exactly. Used as a hint when the host OS triggers a print dialog after the PDF is downloaded. No printer discovery UI in v1. |

> The PDF download workflow (`GET /api/v1/articles/{id}/barcode`, `GET /api/v1/batches/{id}/barcode`) generates a PDF barcode label and downloads it directly in the browser. The `barcode_printer` field is stored as a configuration reference; it does not drive the current direct ZPL network-print path.

### 8.3 Direct host printing (`label_printer_ip`, `label_printer_port`, `label_printer_model`)

These fields configure the direct network-print path (`POST /api/v1/articles/{id}/barcode/print`, `POST /api/v1/batches/{id}/barcode/print`). ADMIN-only. No PDF is produced — the label is sent directly to the printer over TCP.

| Field | Type | Notes |
|-------|------|-------|
| Label printer IP | Text input | IPv4 address of the network label printer. Leave empty if direct printing is not configured. |
| Label printer port | Text input | TCP port. Default: 9100. |
| Label printer model | Dropdown | Printer protocol. Current accepted value: `zebra_zpl` (Zebra ZPL). |

> No printer discovery UI in v1. Admin must ensure the IP address and port are correct before using direct print actions.

### 8.4 Future: raw-label printer mode

A future raw-label printer mode (e.g., printing raw ZPL directly from the browser without server mediation) is **not implemented**. Do not document or surface this as a current feature.

---

## 9. Section: Izvoz

| Field | Type | Notes |
|-------|------|-------|
| Excel column format | Dropdown | SAP-compatible / Generic. Default: Generic. When SAP-compatible is selected, exported Excel files use SAP column names and format. |

---

## 10. Section: Dobavljači

Upravljanje podacima dobavljača. Dobavljači se koriste u Narudžbenicama i moraju postojati prije kreiranja narudžbe.

### 10.1 Tablica dobavljača

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

## 11. Section: Korisnici

User management for system accounts (not employees — these are login users).

### 11.1 Tablica korisnika

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
| Download article barcode PDF | GET | `/api/v1/articles/{id}/barcode` |
| Download batch barcode PDF | GET | `/api/v1/batches/{id}/barcode` |
| Direct-print article label | POST | `/api/v1/articles/{id}/barcode/print` |
| Direct-print batch label | POST | `/api/v1/batches/{id}/barcode/print` |
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
| Barcode printer name does not match host OS printer | No validation in UI — admin must ensure the name matches the host OS printer list exactly. Incorrect name will cause print errors at print time. |
| Direct print: printer IP not reachable | Backend returns a `PRINTER_CONNECTION_ERROR`. UI shows the error toast returned by the API. |
| Direct print: label_printer_ip is empty | Backend returns a `PRINTER_NOT_CONFIGURED` error. UI shows the error toast. |
| Changing timezone | Takes effect immediately. Existing draft groupings are not retroactively recalculated. |
