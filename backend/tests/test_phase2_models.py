"""Phase 2 model and migration regression tests."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from app.models.article import Article
from app.models.category import Category
from app.models.uom_catalog import UomCatalog

BACKEND_DIR = Path(__file__).resolve().parents[1]

EXPECTED_TABLES = {
    "alembic_version",
    "annual_quota",
    "approval_action",
    "approval_override",
    "article",
    "article_alias",
    "article_supplier",
    "batch",
    "category",
    "draft",
    "draft_group",
    "employee",
    "inventory_count",
    "inventory_count_line",
    "location",
    "missing_article_report",
    "order",
    "order_line",
    "personal_issuance",
    "receiving",
    "revoked_token",
    "role_display_name",
    "stock",
    "supplier",
    "surplus",
    "system_config",
    "transaction",
    "uom_catalog",
    "user",
}


def _make_alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_article_number_is_normalized_to_uppercase_and_collides_on_case_only_duplicate(
    db_session,
):
    category = Category(key="raw_material", label_hr="Sirovine")
    uom = UomCatalog(code="kg", label_hr="kilogram", decimal_display=True)
    db_session.add_all([category, uom])
    db_session.commit()

    article = Article(
        article_no="abc-123",
        description="Test article",
        category_id=category.id,
        base_uom=uom.id,
    )
    db_session.add(article)
    db_session.commit()

    assert article.article_no == "ABC-123"

    duplicate = Article(
        article_no="AbC-123",
        description="Duplicate article",
        category_id=category.id,
        base_uom=uom.id,
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_initial_migration_creates_expected_tables_and_stock_check_constraint(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "phase2_migration.db"
    database_url = f"sqlite:///{db_path}"

    monkeypatch.chdir(BACKEND_DIR)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-suite-2026-0001")

    config = _make_alembic_config(database_url)
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    assert table_names == EXPECTED_TABLES

    draft_columns = {column["name"] for column in inspector.get_columns("draft")}
    assert "note" not in draft_columns

    draft_group_columns = {
        column["name"] for column in inspector.get_columns("draft_group")
    }
    assert "group_type" in draft_group_columns

    revoked_token_columns = {
        column["name"] for column in inspector.get_columns("revoked_token")
    }
    assert {"jti", "token_type", "user_id", "revoked_at", "expires_at"} <= revoked_token_columns

    check_constraints = inspector.get_check_constraints("stock")
    assert any(
        constraint.get("name") == "ck_stock_quantity_gte_zero"
        or "quantity >= 0" in (constraint.get("sqltext") or "")
        for constraint in check_constraints
    )
