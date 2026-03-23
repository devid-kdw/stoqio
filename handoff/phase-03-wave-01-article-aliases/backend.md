# Backend Handoff — Wave 1 Phase 3 Article Aliases

Reserved for backend agent entries. Append only.

---

## Session — 2026-03-23

### What was done

**Migration** — `backend/migrations/versions/a1b2c3d4e5f6_add_article_alias_unique_constraint.py`
- Added `UNIQUE (article_id, normalized)` constraint (`uq_article_alias_article_normalized`) to `article_alias`.
- Paired the constraint in the SQLAlchemy model (`backend/app/models/article_alias.py`) via `__table_args__`.

**Service layer** — `backend/app/services/article_service.py`
- `create_article_alias(article_id, payload)`: validates `alias` is non-blank, normalizes via `lower() + strip()`, checks for existing `(article_id, normalized)` row and raises `409 ALIAS_ALREADY_EXISTS` / `"Alias already exists."`, falls back to catching `IntegrityError` for race conditions, returns `_serialize_alias(alias_row)`.
- `delete_article_alias(article_id, alias_id)`: verifies the article exists via `_get_article`, queries `ArticleAlias` filtered by both `id` and `article_id` (scoped delete), raises `404 ALIAS_NOT_FOUND` if missing.

**Routes** — `backend/app/api/articles/routes.py`
- `POST /articles/<id>/aliases` — ADMIN only, returns `201` with created alias object.
- `DELETE /articles/<id>/aliases/<alias_id>` — ADMIN only, returns `204` on success.
- `GET /articles/<id>` unchanged — still returns `aliases[]` with `{id, alias, normalized}`.
- Identifier search unchanged — still queries `ArticleAlias.normalized` via the existing `outerjoin` path.

### Contract adherence

| Rule | Status |
|---|---|
| Normalization = `lower() + strip()` | ✅ |
| Uniqueness scoped per article, not globally | ✅ |
| `POST` returns `201` with alias object | ✅ |
| Duplicate → `409` + `"Alias already exists."` | ✅ |
| `DELETE` returns `204` | ✅ |
| Missing alias → `404` | ✅ |
| `GET` still includes `aliases[]` | ✅ |
| Identifier alias search preserved | ✅ |
| `POST`/`DELETE` ADMIN only | ✅ |

### Verification

```
backend/venv/bin/pytest backend/tests/test_articles.py -q
32 passed in 1.05s
```

No regressions. Dedicated alias test coverage delegated to the testing agent per `orchestrator.md`.
