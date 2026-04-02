# Frontend Handoff — Wave 3 Phase 1: Runtime Language Switching & Locale Foundation

---

## Entry 1 — 2026-04-02

### Status

Complete. A shared localization foundation is now established. The frontend translates shell/sidebar components and formats dates/numbers according to `i18n.language` rather than defaulting to Croatian, and applies settings before AppShell routes.

### Scope

- Implement the shared locale-aware formatting helpers (`formatDate`, `formatDateTime`, `formatNumber`, `getActiveLocale`).
- Update `main.tsx` to apply initial language mapping (`GET /settings/shell`) during bootstrap.
- Migrate `Sidebar`, `AppShell`, and auth bootstrap states to use `useTranslation()`/`i18n.t()`.
- Populate `hr.json`, `en.json`, `de.json`, and `hu.json`.
- Replace hardcoded `hr-HR` locales in utility files with the `getActiveLocale` shared helper.

### Docs Read

- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md`
- `handoff/README.md`
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/orchestrator.md`

### Solution

**Bootstrap Integration:**
`main.tsx` was modified to explicitly `await useSettingsStore.getState().loadShellSettings()` _before_ calling `renderApp()` (but after hydration/`bootstrapAuth`). Because `loadShellSettings` fetches configuration and changes `i18n.language`, this guarantees the initial page load renders immediately in the correct default language without flashing Croatian or loading text while the `AppShell` component runs `useEffect`.

**Shared Locale Formatting:**
Created `frontend/src/utils/locale.ts` providing `getActiveLocale()`, mapping current `i18n.language` tag back to `BPC-47` compliant locale strings (`hr-HR`, `en-GB`, `de-DE`, `hu-HU`), and falling back to `hr-HR`. 

Date and number formatting in utils (`reportsUtils.ts`, `warehouseUtils.ts`, `orderUtils.ts`, `identifierUtils.ts`) now use the central `getActiveLocale()` ensuring dynamic runtime selection instead of hardcoded formats. Quantity precision specifics and timezone configurations correctly stay within the respective module functions or dependants.

**JSON Language Definitions:**
Populated layout translation keys for `nav`, `sidebar`, `shell`, and `auth`:
- `hr.json` populated with default Croatian translations.
- `en.json` populated with standard English translations.
- `de.json` and `hu.json` were initialized as empty `{}` objects per phase requirements.

**Layout & Utility Updates:**
- Mapped `SettingsPage`, `DraftGroupCard`, `ReceivingPage`, `InventoryCountPage`, and `EmployeeDetailPage` hardcoded format calls to the locale utility.
- `AppShell`, `Sidebar`, and `main.tsx` loading screens now render `i18n.t()` definitions dynamically.

### Files Changed

- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/i18n/locales/de.json`
- `frontend/src/i18n/locales/en.json`
- `frontend/src/i18n/locales/hr.json`
- `frontend/src/i18n/locales/hu.json`
- `frontend/src/main.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/employees/EmployeeDetailPage.tsx`
- `frontend/src/pages/identifier/identifierUtils.ts`
- `frontend/src/pages/inventory/InventoryCountPage.tsx`
- `frontend/src/pages/orders/orderUtils.ts`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/reports/reportsUtils.ts`
- `frontend/src/pages/settings/SettingsPage.tsx`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `frontend/src/utils/locale.test.ts` (NEW)
- `frontend/src/utils/locale.ts` (NEW)
