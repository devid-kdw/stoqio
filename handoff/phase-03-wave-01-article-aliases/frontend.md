# Frontend Handoff — Wave 1 Phase 3 Article Aliases

Reserved for frontend agent entries. Append only.

---

## Session — 2026-03-23

### What was done

**API layer** — `frontend/src/api/articles.ts`
- Added `createAlias(articleId, alias)`: `POST /articles/{id}/aliases` → returns `ArticleAliasItem`.
- Added `deleteAlias(articleId, aliasId)`: `DELETE /articles/{id}/aliases/{alias_id}` → `void`.
- No new interfaces needed; `ArticleAliasItem` (`id`, `alias`, `normalized`) was already present.

**Article detail page** — `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- Added Mantine imports: `ActionIcon`, `TextInput`.
- Added `@tabler/icons-react` import: `IconX`.
- Added `ArticleAliasItem` to the `articles` import.
- Added four state variables: `aliasInput`, `aliasSubmitting`, `aliasError`, `aliasDeletingId`.
- Added `handleAddAlias` callback:
  - POSTs to backend, updates `article.aliases` in local state on success, clears input.
  - On `409 ALIAS_ALREADY_EXISTS`: sets inline `aliasError` = `"Ovaj alternativni naziv već postoji."`.
  - On network/server error: sets `fatalError` (matches existing page error pattern).
  - Other API errors: `showErrorToast`.
- Added `handleDeleteAlias(aliasId)` callback:
  - DELETEs from backend, removes alias from `article.aliases` in local state on success.
  - Same error branching as add.
- Replaced the static read-only alias table with:
  - Aliases rendered as Mantine `Badge` pills (size lg, light variant).
  - ADMIN: each badge has a right-section `ActionIcon` (`IconX`, xs) that triggers delete; spinner shown while that alias is being deleted.
  - MANAGER: badges without delete affordance (same render path, `isAdmin` guard on `rightSection`).
  - Empty state text preserved.
  - Below aliases: ADMIN-only add row (`TextInput` + `Dodaj` button); error displayed inline via `error` prop on `TextInput`; Enter key triggers add.

### Contract adherence

| Rule | Status |
|---|---|
| Alias section visible in read mode (not behind edit toggle) | ✅ |
| ADMIN can add and delete inline | ✅ |
| MANAGER view is read-only | ✅ |
| 409 duplicate → inline error, not toast | ✅ |
| Add/delete success refreshes alias list without full reload | ✅ |
| Rest of article detail screen unchanged | ✅ |

### No backend contract gaps
Backend matches orchestrator spec exactly: `POST 201`, `DELETE 204`, `409 ALIAS_ALREADY_EXISTS`.

### Verification

```
cd frontend && npm run lint
# → no output (clean)

cd frontend && npm run build
# → ✓ built in 2.08s, 0 errors
```
