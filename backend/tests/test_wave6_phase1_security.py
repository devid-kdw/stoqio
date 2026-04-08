"""Wave 6 Phase 1 backend security regression tests.

Covers findings:
  K-1  JWT_ALGORITHM pinned to HS256 in both config classes
  K-3  Approval double-spend race: with_for_update() on draft read
  K-4  HSTS and Permissions-Policy response headers
  V-3  per_page capped at 200 in all paginated service functions
  V-5  sanitize_cell() applied to all user-controlled string fields in xlsx exports
  V-7  Surplus quantity >= 0 CHECK constraint (Alembic migration)
  S-1  Automatic revoked token cleanup (at most once per hour)
  S-2  _get_article() filters is_active=True; deactivate_article still works
  S-3  edit_aggregated_line() rejects negative override_quantity
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.extensions import db as _db
from app.models.article import Article
from app.models.category import Category
from app.models.uom_catalog import UomCatalog
from app.services import approval_service
from app.services.article_service import (
    ArticleServiceError,
    _get_article,
    _get_article_including_inactive,
    deactivate_article,
)
from app.utils.validators import sanitize_cell

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_catalog(suffix: str = "w6") -> tuple[Category, UomCatalog]:
    category = Category.query.filter_by(key=f"wave6-{suffix}").first()
    if category is None:
        category = Category(
            key=f"wave6-{suffix}",
            label_hr="Wave 6",
            label_en="Wave 6",
            label_de="Wave 6",
            label_hu="Wave 6",
            is_personal_issue=False,
            is_active=True,
        )
        _db.session.add(category)

    uom = UomCatalog.query.filter_by(code=f"W6PCS{suffix[:2].upper()}").first()
    if uom is None:
        uom = UomCatalog(
            code=f"W6PCS{suffix[:2].upper()}",
            label_hr="Komad",
            label_en="Piece",
            decimal_display=False,
        )
        _db.session.add(uom)

    _db.session.commit()
    return category, uom


def _make_article(*, article_no: str, description: str = "Test article") -> Article:
    category, uom = _ensure_catalog()
    article = Article(
        article_no=article_no,
        description=description,
        category_id=category.id,
        base_uom=uom.id,
        has_batch=False,
        is_active=True,
    )
    _db.session.add(article)
    _db.session.commit()
    return article


# ---------------------------------------------------------------------------
# Fix K-1: JWT_ALGORITHM pinned to HS256
# ---------------------------------------------------------------------------

class TestJwtAlgorithmPinned:
    def test_development_config_has_hs256(self):
        from app.config import Development
        cfg = Development()
        assert cfg.JWT_ALGORITHM == "HS256"

    def test_production_config_has_hs256(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "a-very-strong-jwt-secret-key-for-prod-2026")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/wms_prod_test")
        from app.config import Production
        cfg = Production()
        assert cfg.JWT_ALGORITHM == "HS256"


# ---------------------------------------------------------------------------
# Fix K-4: HSTS and Permissions-Policy headers
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    def test_hsts_header_present(self, client):
        resp = client.get("/")
        assert "Strict-Transport-Security" in resp.headers
        assert "max-age=31536000" in resp.headers["Strict-Transport-Security"]
        assert "includeSubDomains" in resp.headers["Strict-Transport-Security"]

    def test_permissions_policy_header_present(self, client):
        resp = client.get("/")
        assert "Permissions-Policy" in resp.headers
        pp = resp.headers["Permissions-Policy"]
        assert "geolocation=()" in pp
        assert "camera=()" in pp
        assert "microphone=()" in pp

    def test_existing_headers_still_present(self, client):
        resp = client.get("/")
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert "Content-Security-Policy" in resp.headers


# ---------------------------------------------------------------------------
# Fix V-3: per_page capped at 200
# ---------------------------------------------------------------------------

class TestPerPageCap:
    def test_get_transaction_log_caps_per_page(self, app):
        from app.services.report_service import get_transaction_log
        with app.app_context():
            result = get_transaction_log(per_page=999999)
        assert result["per_page"] <= 200

    def test_list_article_transactions_caps_per_page(self, app):
        from app.services.article_service import list_article_transactions
        with app.app_context():
            article = _make_article(article_no="W6-TXCAP-001")
            result = list_article_transactions(article.id, page=1, per_page=999999)
        assert result["per_page"] <= 200

    def test_list_articles_caps_per_page(self, app):
        from app.services.article_service import list_articles
        with app.app_context():
            result = list_articles(page=1, per_page=999999)
        assert result["per_page"] <= 200

    def test_per_page_at_200_is_accepted(self, app):
        from app.services.report_service import get_transaction_log
        with app.app_context():
            result = get_transaction_log(per_page=200)
        assert result["per_page"] == 200

    def test_per_page_below_200_unchanged(self, app):
        from app.services.report_service import get_transaction_log
        with app.app_context():
            result = get_transaction_log(per_page=50)
        assert result["per_page"] == 50


# ---------------------------------------------------------------------------
# Fix V-5: sanitize_cell() completeness
# ---------------------------------------------------------------------------

class TestSanitizeCellCompleteness:
    """Ensure sanitize_cell strips formula injection prefixes."""

    @pytest.mark.parametrize("dangerous_value,prefix", [
        ("=SUM(A1:A10)", "="),
        ("+cmd|' /C calc'!A0", "+"),
        ("-2+3+cmd|' /C calc'!A0", "-"),
        ("@SUM(1+1)*cmd|' /C calc'!A0", "@"),
    ])
    def test_sanitize_cell_prefixes_formula(self, dangerous_value, prefix):
        result = sanitize_cell(dangerous_value)
        assert result.startswith("'")
        assert result[1:] == dangerous_value

    def test_sanitize_cell_safe_value_unchanged(self):
        assert sanitize_cell("ARTICLE-001") == "ARTICLE-001"
        assert sanitize_cell("Normal description") == "Normal description"
        assert sanitize_cell("") == ""

    def test_sanitize_cell_non_string_passthrough(self):
        # sanitize_cell should return numeric/None unchanged (no crash)
        assert sanitize_cell(123) == 123  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Fix V-7: Surplus CHECK constraint exists in migrations
# ---------------------------------------------------------------------------

class TestSurplusMigration:
    def test_alembic_has_single_head(self):
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
        script = ScriptDirectory.from_config(config)
        heads = script.get_heads()
        assert len(heads) == 1, f"Expected single head, got: {heads}"

    def test_surplus_migration_file_exists(self):
        migration_dir = BACKEND_DIR / "migrations" / "versions"
        migration_files = list(migration_dir.glob("*surplus_quantity*"))
        assert migration_files, "No migration file matching *surplus_quantity* found"

    def test_surplus_migration_has_correct_constraint_name(self):
        migration_dir = BACKEND_DIR / "migrations" / "versions"
        migration_files = list(migration_dir.glob("*surplus_quantity*"))
        assert migration_files
        content = migration_files[0].read_text()
        assert "ck_surplus_quantity_gte_zero" in content
        assert "quantity >= 0" in content


# ---------------------------------------------------------------------------
# Fix S-1: Automatic revoked token cleanup
# ---------------------------------------------------------------------------

class TestAutoRevokedTokenCleanup:
    def test_cleanup_state_variable_exists(self):
        import app as app_module
        assert hasattr(app_module, "_last_token_cleanup")

    def test_cleanup_runs_on_first_request(self, app, client):
        import app as app_module
        # Reset state to force a run
        app_module._last_token_cleanup = None
        resp = client.get("/")
        # After a request, _last_token_cleanup should be set
        assert app_module._last_token_cleanup is not None

    def test_cleanup_skips_when_run_recently(self, app, client):
        import app as app_module
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        app_module._last_token_cleanup = recent_time
        client.get("/")
        # Should NOT have updated since last run was < 1 hour ago
        assert app_module._last_token_cleanup == recent_time

    def test_cleanup_runs_when_stale(self, app, client):
        import app as app_module
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        app_module._last_token_cleanup = old_time
        client.get("/")
        # Should have updated since last run was > 1 hour ago
        assert app_module._last_token_cleanup != old_time
        assert app_module._last_token_cleanup > old_time


# ---------------------------------------------------------------------------
# Fix S-2: _get_article filters is_active=True
# ---------------------------------------------------------------------------

class TestGetArticleIsActiveFilter:
    def test_get_article_raises_for_inactive(self, app):
        with app.app_context():
            article = _make_article(article_no="W6-INACTIVE-001")
            article.is_active = False
            _db.session.commit()

            with pytest.raises(ArticleServiceError) as exc_info:
                _get_article(article.id)
            assert exc_info.value.status_code == 404

    def test_get_article_returns_active(self, app):
        with app.app_context():
            article = _make_article(article_no="W6-ACTIVE-001")
            fetched = _get_article(article.id)
            assert fetched.id == article.id

    def test_get_article_including_inactive_returns_inactive(self, app):
        with app.app_context():
            article = _make_article(article_no="W6-INACTIVE-002")
            article.is_active = False
            _db.session.commit()

            fetched = _get_article_including_inactive(article.id)
            assert fetched.id == article.id
            assert fetched.is_active is False

    def test_deactivate_article_returns_deactivated_article(self, app):
        with app.app_context():
            article = _make_article(article_no="W6-DEACT-001")
            result = deactivate_article(article.id)
            assert result["is_active"] is False
            assert result["id"] == article.id


# ---------------------------------------------------------------------------
# Fix S-3: edit_aggregated_line rejects negative quantity
# ---------------------------------------------------------------------------

class TestNegativeOverrideQuantityRejected:
    def test_negative_quantity_raises_value_error(self, app):
        with app.app_context():
            # Validation fires before the DB lookup; no group/draft 9999 needed
            with pytest.raises(ValueError, match="negative"):
                approval_service.edit_aggregated_line(
                    group_id=9999,
                    line_id=9999,
                    new_quantity=Decimal("-1"),
                )

    def test_zero_quantity_is_accepted(self, app):
        with app.app_context():
            # Zero should pass the negative check (returns None since draft 9999 doesn't exist)
            result = approval_service.edit_aggregated_line(
                group_id=9999,
                line_id=9999,
                new_quantity=Decimal("0"),
            )
            # Returns None because draft doesn't exist, but no ValueError raised
            assert result is None

    def test_positive_quantity_is_accepted(self, app):
        with app.app_context():
            result = approval_service.edit_aggregated_line(
                group_id=9999,
                line_id=9999,
                new_quantity=Decimal("10.5"),
            )
            assert result is None  # draft doesn't exist but no ValueError


# ---------------------------------------------------------------------------
# Fix K-3: _approve_pending_bucket uses with_for_update
# ---------------------------------------------------------------------------

class TestApprovalWithForUpdate:
    """Verify the source code contains the with_for_update() locking call."""

    def test_approve_pending_bucket_source_has_with_for_update(self):
        import inspect
        from app.services import approval_service as svc
        source = inspect.getsource(svc._approve_pending_bucket)
        assert "with_for_update()" in source, (
            "_approve_pending_bucket must use with_for_update() on the draft query"
        )
