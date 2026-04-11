# WMS — UI Specification: Reports

**Status**: Active document
**Version**: v1
**Audience**: AI coding agents
**Module**: Reports (`/reports`)
**Accessible by roles**: ADMIN (full), MANAGER (read-only, no export)

---

## 1. Purpose

The Reports module provides data visibility and export capabilities for warehouse management decisions. It replaces manual SAP exports and Excel calculations. The primary use case is understanding current stock levels, identifying reorder needs, and reviewing material movement over time.

---

## 2. Screen Layout

The Reports screen is a single page with multiple report sections, each in its own tab or clearly separated section:

1. **Stock Overview** (Doseg zaliha) — default view
2. **Surplus List** (Viškovi)
3. **Transaction Log** (Transakcijski dnevnik)
4. **Statistics** (Statistike)

---

## 3. Report 1: Stock Overview (Doseg zaliha)

### 3.1 Purpose

Shows current stock levels per article with calculated consumption metrics, helping the admin decide what needs to be reordered.

### 3.2 Filters

| Filter | Type | Notes |
|--------|------|-------|
| Period — date from | Date input | Required. Start date for consumption calculation. |
| Period — date to | Date input | Required. End date for consumption calculation. Default: today. |
| Category | Dropdown | Filter by article category. Default: all. |
| Show only reorder zone | Toggle | When enabled, shows only articles in red or yellow zone. |

### 3.3 Table Columns

| Column | Notes |
|--------|-------|
| Article No. | Article number |
| Description | Article description |
| Supplier | Preferred supplier name |
| Stock | Current stock quantity + UOM |
| Surplus | Current surplus quantity + UOM. Show "—" if 0. |
| Total available | Stock + Surplus |
| Inbound (period) | Total received quantity in the selected period |
| Outbound (period) | Total consumed quantity in the selected period |
| Avg monthly consumption | Outbound ÷ number of months in selected period. Shown with 2 decimal places. |
| Coverage (months) | Total available ÷ avg monthly consumption. Shown with 1 decimal place. "∞" if consumption = 0. |
| Reorder threshold | Configured threshold value + UOM |
| Status | Colour indicator — red / yellow / none (same logic as Warehouse module) |

> **Coverage calculation**: `(stock + surplus) / (outbound / months_in_period)`. If outbound = 0 for the period, coverage is shown as "∞".

> **Months in period**: calculated as `(date_to - date_from)` in days / 30.44 (average days per month).

### 3.4 Actions

- **Export Excel** — exports the full table (all rows, all columns) as `.xlsx`.
- **Export PDF** — exports the full table as a printable PDF.

### 3.5 Empty State

`"No articles found for the selected filters."`

---

## 4. Report 2: Surplus List (Viškovi)

### 4.1 Purpose

Shows all current surplus quantities — material discovered during inventory counts that exceeds the system stock. Useful for identifying excess material that could be redistributed or written off.

### 4.2 Filters

- No filters in v1 — always shows all current surplus.

### 4.3 Table Columns

| Column | Notes |
|--------|-------|
| Article No. | Article number |
| Description | Article description |
| Batch | Batch code, or "—" if no batch |
| Expiry date | If batch exists, or "—" |
| Surplus qty | Current surplus quantity + UOM |
| Discovered | Date the surplus was added (from inventory count) |

### 4.4 Actions

- **Export Excel** — exports the surplus list as `.xlsx`.
- **Export PDF** — exports the surplus list as a printable PDF.

### 4.5 Empty State

`"No surplus on record."`

---

## 5. Report 3: Transaction Log (Transakcijski dnevnik)

### 5.1 Purpose

A full audit trail of all inventory movements. Can be viewed for a specific article or as a general log across all articles.

### 5.2 Filters

| Filter | Type | Notes |
|--------|------|-------|
| Article | Search input | Optional. If selected, shows only transactions for that article. |
| Date from | Date input | Optional. |
| Date to | Date input | Optional. Default: today. |
| Transaction type | Dropdown (multi-select) | STOCK_RECEIPT / OUTBOUND / SURPLUS_CONSUMED / STOCK_CONSUMED / INVENTORY_ADJUSTMENT / PERSONAL_ISSUE. Default: all. |

### 5.3 Table Columns

| Column | Notes |
|--------|-------|
| Date & time | When the transaction occurred |
| Article No. | Article number |
| Description | Article description |
| Type | Transaction type label (human-readable) |
| Quantity | Algebraic amount + UOM. Negative = outbound, positive = inbound. |
| Batch | Batch code, or "—" |
| Reference | Order number or delivery note number if available, or "—" |
| User | Who performed the action |

Paginated — 50 rows per page.

### 5.4 Actions

- **Export Excel** — exports all rows matching current filters (not just current page) as `.xlsx`.
- **Export PDF** — exports all rows matching current filters as a printable PDF.

### 5.5 Empty State

`"No transactions found for the selected filters."`

---

## 6. Report 4: Statistics (Statistike)

### 6.1 Purpose

Visual overview of warehouse activity — consumption trends, top articles by usage, and reorder zone summary. Secondary: personal issuance tracking per employee.

### 6.2 Layout

Four visual sections on a single screen. No filters shared across sections — each section has its own period selector where applicable.

---

### 6.3 Section A: Top Articles by Consumption

- **Chart type**: Horizontal bar chart.
- **Shows**: Top 10 articles by outbound quantity in the selected period.
- **Period selector**: Week / Month / Year (default: Month).
- **X axis**: Total outbound quantity (in base UOM).
- **Y axis**: Article description.
- Clicking a bar navigates to that article's transaction log (pre-filtered).

---

### 6.4 Section B: Inbound / Outbound Over Time

- **Chart type**: Line chart (two lines — inbound and outbound).
- **Shows**: Total inbound and outbound quantities aggregated by week or month over the selected period.
- **Period selector**: Last 3 months / Last 6 months / Last 12 months (default: Last 6 months).
- **Filters** (optional, default: whole warehouse):
  - Exact article (search/select field); mutually exclusive with category filter.
  - Article category (dropdown).
- **X axis**: Time (weeks or months).
- **Y axis**: Quantity (summed across all articles, all UOMs — note: mixed UOMs mean this is an indicative trend view, not a precise total).
- A note is displayed below the chart in Croatian: `"Količine su zbrojene po svim mjernim jedinicama. Grafikon prikazuje trendove, a ne precizne ukupne iznose."`

---

### 6.5 Section C: Reorder Zone Summary

- **Chart type**: Simple summary widget (not a complex chart).
- **Shows**: Count of articles currently in each zone.
  - 🔴 Red zone: X articles
  - 🟡 Yellow zone: X articles
  - ✅ Normal: X articles
- Each zone count is clickable. Clicking opens a separate collapsible block within the Statistics tab that lists articles belonging to that zone. The user does **not** leave the Statistics tab.

---

### 6.6 Section E: Price Movement (Kretanje cijena)

Visible to **ADMIN** and **MANAGER** only.

- **Shows**: Warehouse-wide article price-change report, one row per active article.
- **Default sort**: Articles with the most recent actual price change appear first (most recent change date DESC). Articles whose price never changed appear next. Articles with no price history appear last.
- **"Actual price change"**: A real difference between consecutive Receiving unit prices. A newer Receiving row with the same price does not count as a change.

| Column | Notes |
|--------|-------|
| Article No. | Article number |
| Description | Article description |
| Category | Article category key |
| Latest price | Most recent known price from Receiving records |
| Previous price | Price before the most recent change; `—` if price never changed |
| Last change date | Date of the most recent actual price change; `—` if never changed |
| Delta | Absolute price difference (latest − previous); `—` if no change |
| Delta % | Percentage change; `—` if no change |

- No export in v1 — view only.
- No filter in v1 — always shows full active article set.

---

### 6.7 Section D: Personal Issuances (secondary)

Displayed below the main three sections — visually de-emphasised (smaller heading, less prominent placement).

- **Shows**: Table of personal issuances grouped by employee, for the current year.
- Columns: Employee name, Job title, Article, Quantity issued (this year), Quota, Remaining.
- No chart — plain table only.
- **Period**: Always current year — no period selector.
- **Export**: No export from this section in v1.

---

### 6.8 Layout Behaviour (Wave 9)

- All Statistics subsections start **collapsed** by default.
- The user opens only the section they want to inspect.
- Clicking a reorder zone count opens a drilldown block **within** the Statistics tab — no tab switch to Stock Overview.

### 6.9 Actions

- No export from the Statistics tab in v1 — view only.

---

## 8. Export Format

### Excel (.xlsx)
- One sheet per export.
- Header row with column names.
- Data rows below.
- Column widths auto-fitted.
- Filename format: `wms_{report_type}_{date}.xlsx` — e.g. `wms_stock_overview_2026-03-10.xlsx`, `wms_surplus_2026-03-10.xlsx`, `wms_transactions_2026-03-10.xlsx`.

### PDF
- Clean tabular layout, A4 landscape for wide tables.
- Header: report name + date range (if applicable) + export timestamp.
- Filename format: `wms_{report_type}_{date}.pdf`.
- No company logo or branding — generic and universally applicable.

---

## 9. MANAGER Access

- MANAGER can view all three reports.
- MANAGER cannot export (no Export Excel / Export PDF buttons visible).

---

## 10. API Endpoints Used

| Action | Method | Endpoint |
|--------|--------|----------|
| Get stock overview | GET | `/api/v1/reports/stock-overview?date_from={}&date_to={}&category={}&reorder_only={bool}` |
| Get surplus list | GET | `/api/v1/reports/surplus` |
| Get transaction log | GET | `/api/v1/reports/transactions?article_id={}&date_from={}&date_to={}&tx_type={}&page=1&per_page=50` |
| Get top consumption | GET | `/api/v1/reports/statistics/top-consumption?period=week\|month\|year` |
| Get movement statistics | GET | `/api/v1/reports/statistics/movement?range=3m\|6m\|12m&article_id={}&category={}` |
| Get price movement | GET | `/api/v1/reports/statistics/price-movement` |
| Get reorder drilldown | GET | `/api/v1/reports/statistics/reorder-drilldown?status=RED\|YELLOW\|NORMAL` |
| Get reorder summary | GET | `/api/v1/reports/statistics/reorder-summary` |
| Get personal issuances | GET | `/api/v1/reports/statistics/personal-issuances` |
| Export stock overview Excel | GET | `/api/v1/reports/stock-overview/export?format=xlsx&date_from={}&date_to={}` |
| Export stock overview PDF | GET | `/api/v1/reports/stock-overview/export?format=pdf&date_from={}&date_to={}` |
| Export surplus Excel | GET | `/api/v1/reports/surplus/export?format=xlsx` |
| Export surplus PDF | GET | `/api/v1/reports/surplus/export?format=pdf` |
| Export transactions Excel | GET | `/api/v1/reports/transactions/export?format=xlsx&article_id={}&date_from={}&date_to={}&tx_type={}` |
| Export transactions PDF | GET | `/api/v1/reports/transactions/export?format=pdf&article_id={}&date_from={}&date_to={}&tx_type={}` |

---

## 11. Request / Response Shapes

### GET `/api/v1/reports/stock-overview` — Stock overview

**Response (200):**
```json
{
  "period": {
    "date_from": "2025-01-01",
    "date_to": "2026-01-01",
    "months": 12.0
  },
  "items": [
    {
      "article_id": 42,
      "article_no": "BOJ-001",
      "description": "ALEXIT-FST Strukturlack 346-65",
      "supplier_name": "Mankiewicz Gebr. & Co.",
      "stock": 50.0,
      "surplus": 5.0,
      "total_available": 55.0,
      "uom": "kg",
      "inbound": 120.0,
      "outbound": 96.0,
      "avg_monthly_consumption": 8.0,
      "coverage_months": 6.9,
      "reorder_threshold": 20.0,
      "reorder_status": "normal"
    }
  ],
  "total": 87
}
```

`reorder_status`: `"normal"` / `"yellow"` / `"red"`

---

## 12. Edge Cases

| Situation | Behaviour |
|-----------|-----------|
| Period with 0 outbound for an article | Coverage shown as "∞". Avg monthly consumption shown as "0". |
| Date from > date to | Inline error: `"Start date must be before end date."` |
| Export with active filters | Export includes all rows matching filters, not just the current page. |
| Transaction log with no article filter | Returns all transactions across all articles, paginated. |
| Very large export (thousands of rows) | Export button shows spinner while generating. File downloads when ready. |
