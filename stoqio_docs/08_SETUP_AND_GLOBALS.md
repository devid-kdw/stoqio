# WMS — Setup, Validation & Global UI Rules

**Status**: Active document
**Version**: v1
**Audience**: AI coding agents

---

## 1. Seed Data

The following data must be inserted on first run (via a seed script executed after `alembic upgrade head`).

### 1.1 Admin User

| Field | Value |
|-------|-------|
| `username` | `admin` |
| `password` | `admin123` |
| `role` | `ADMIN` |
| `is_active` | `true` |

> No forced password change on first login. Admin uses this credential as-is until manually changed.

### 1.2 UOM Catalog

Seed the following units. The catalog is open — admins can add more via Settings.

| Code | Label (HR) | Label (EN) | Decimal display |
|------|------------|------------|-----------------|
| `kg` | kilogram | kilogram | 2 decimals |
| `l` | litra | litre | 2 decimals |
| `kom` | komad | piece | integer |
| `pak` | pakiranje | package | integer |
| `m` | metar | metre | 2 decimals |
| `m²` | četvorni metar | square metre | 2 decimals |
| `pár` | par | pair | integer |
| `g` | gram | gram | 2 decimals |
| `ml` | mililitar | millilitre | 2 decimals |
| `t` | tona | tonne | 2 decimals |

### 1.3 Article Categories

Seed all 12 categories. The `key` is the internal system identifier (never changes). `label_hr` and `label_en` are required. `label_de` and `label_hu` are nullable — seeded as NULL (scaffold for future localization).

| key | label_hr | label_en | is_personal_issue |
|-----|----------|----------|-------------------|
| `equipment_installations` | Oprema i instalacije | Equipment & Installations | false |
| `safety_equipment` | Zaštitna oprema | Safety Equipment | true |
| `operational_supplies` | Operativni potrošni materijal | Operational Supplies | false |
| `spare_parts_small_parts` | Rezervni dijelovi | Spare Parts | false |
| `auxiliary_operating_materials` | Pomoćna sredstva | Auxiliary Materials | false |
| `assembly_material` | Montažni materijal | Assembly Material | false |
| `raw_material` | Sirovine | Raw Material | false |
| `packaging_material` | Ambalažni materijal | Packaging Material | false |
| `goods_merchandise` | Roba za prodaju | Goods & Merchandise | false |
| `maintenance_material` | Materijal za održavanje | Maintenance Material | false |
| `tools_small_equipment` | Alati i sitna oprema | Tools & Small Equipment | true |
| `accessories_small_machines` | Pribor za strojeve | Machine Accessories | false |

### 1.4 SystemConfig

Seed the following key-value pairs on first run:

| key | value |
|-----|-------|
| `default_language` | `hr` |
| `barcode_format` | `Code128` |
| `barcode_printer` | `""` |
| `export_format` | `generic` |

### 1.5 RoleDisplayName

Seed one row per system role with default display names:

| role | display_name |
|------|-------------|
| `ADMIN` | Admin |
| `MANAGER` | Menadžment |
| `WAREHOUSE_STAFF` | Administracija |
| `VIEWER` | Kontrola |
| `OPERATOR` | Operater |

### 1.6 Location

**No location is seeded.** The first ADMIN user must create the location via the first-run setup screen before accessing any other part of the application.

---

## 2. First-Run Setup Flow

On first login (detected by absence of any `Location` record in the database):

1. After successful login, redirect ADMIN to `/setup` instead of the normal home route.
2. Display a single form with two fields:
   - **Location name** (required, max 100 characters) — e.g. "Skladište Tvornica d.o.o."
   - **Timezone** (required, dropdown) — default pre-selected: `Europe/Berlin`
3. On submit, create the `Location` record and redirect to `/approvals` (ADMIN home).
4. As long as no `Location` record exists, any route other than `/login` and `/setup` redirects to `/setup`.
5. If a non-ADMIN user logs in before setup is complete, the frontend must block access, show an error message, and return the user to `/login`. This avoids an ADMIN-only `/setup` redirect loop while initialization is still pending.

**Security**: POST `/api/v1/setup` is **not a public endpoint** — it requires a valid admin JWT token. The frontend sends the token obtained at login. This prevents anyone on the local network from creating the initial location without first authenticating as admin.

---

## 3. Validation Rules

### 3.1 Article Number (`article_no`)

| Rule | Value |
|------|-------|
| Allowed characters | Letters, digits, hyphen (`-`) only. No spaces, no special characters. |
| Max length | 50 characters |
| Case sensitivity | Case-insensitive. `ABC123` and `abc123` are treated as the same article. Store normalized as uppercase. |
| Uniqueness | Must be unique across all articles (enforced at DB level). |

### 3.2 Article Description (`description`)

| Rule | Value |
|------|-------|
| Max length | 500 characters |
| Required | Yes |

### 3.3 Quantities

| Rule | Value |
|------|-------|
| User input | Always positive numbers only. Negative values are rejected. |
| Minimum value | Greater than 0 (0 is not a valid quantity for any input). |
| Decimal display | Depends on UOM — see UOM catalog above. UOM with integer display still store 3 decimal places in DB. |
| DB storage | Always `Numeric(14, 3)` regardless of display format. |

### 3.4 Passwords

| Rule | Value |
|------|-------|
| Minimum length | 4 characters |
| Character requirements | None — any combination of characters is valid. |
| Forced change on first login | No. |

### 3.5 Batch Code

Regex: `^\d{4,5}$|^\d{9,12}$`

Valid examples: `1234`, `12345`, `123456789`, `123456789012`

### 3.6 General Text Fields

| Field | Max length |
|-------|------------|
| Username | 50 characters |
| Supplier name | 200 characters |
| Delivery note number | 100 characters |
| Notes / free text fields | 1000 characters |
| Location name | 100 characters |

---

## 4. Global UI Rules

### 4.1 Language

- All UI copy: **Croatian (HR)** as default.
- Client-rendered validation, warning, success, and empty-state copy: **Croatian (HR)** by default.
- Raw backend/API business-error messages may remain **English** when surfaced directly.
- All internal code, API error codes, enum values: **English**.
- i18n keys exist for EN, DE, HU but are scaffold only in v1.

### 4.2 Error Display

| Situation | Display method |
|-----------|---------------|
| Form field validation (missing required, wrong format, etc.) | Inline — red text below the offending field |
| Server-side business logic errors (e.g. insufficient stock) | Toast |
| Successful actions (save, approve, delete) | Toast |
| Server unreachable / network error | Full-page error screen (after 1 automatic retry) |

### 4.3 Toast Behaviour

- Auto-dismiss after **4 seconds**.
- Success toasts: green.
- Error toasts: red.
- Maximum 1 toast visible at a time — new toast replaces existing.

### 4.4 Network Error & Retry

- On any failed API call due to network/server error: automatically retry **once**.
- If retry also fails: replace current page content with a full-page error screen.
- Error screen message: `"Connection error. Please check that the server is running and try again."`
- Error screen includes a **"Try again"** button that reloads the current page.

### 4.5 Loading States

Every async API call must show a loading indicator while in flight:
- Forms / buttons: disable the submit button and show a spinner inside it.
- Page-level data fetching: show a centered spinner in the content area.
- Never show stale data without indicating a refresh is in progress.

### 4.6 Empty States

Every list or table must have a human-readable empty state when there are no records:
- Example: `"No articles found."`, `"No pending drafts."`
- Empty state must be displayed in the same area as the list, not a separate screen.

### 4.7 Quantity Display

Quantities are displayed according to UOM type:
- **Integer UOM** (kom, pak, pár): display as whole number — `5 kom`, `12 pak`
- **Decimal UOM** (kg, l, m, m², g, ml, t): display with 2 decimal places — `10.50 kg`, `2.75 l`
- UOM type (integer vs decimal) is a property of the UOM catalog entry.

### 4.8 Responsive Layout

- Primary targets: **tablet** and **desktop**.
- Mobile is not a supported target in v1.
- Content area uses full available width — no narrow centered containers.
- Sidebar is always visible on tablet and desktop.

---

## 5. UOM Decimal Classification

The UOM catalog entry includes a `decimal_display` flag:
- `false` = integer display (kom, pak, pár)
- `true` = 2 decimal places (kg, l, m, m², g, ml, t)

When rendering any quantity in the UI, look up this flag from the UOM catalog and format accordingly. The DB always stores 3 decimal places regardless.
