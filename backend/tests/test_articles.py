"""Integration tests for the Phase 9 Warehouse articles module."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import re

import pytest
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.extensions import db as _db
from app.models.article import Article
from app.models.article_alias import ArticleAlias
from app.models.article_supplier import ArticleSupplier
from app.models.batch import Batch
from app.models.category import Category
from app.models.draft import Draft
from app.models.draft_group import DraftGroup
from app.models.enums import (
    DraftGroupStatus,
    DraftSource,
    DraftStatus,
    DraftType,
    MissingArticleReportStatus,
    TxType,
    UserRole,
)
from app.models.location import Location
from app.models.missing_article_report import MissingArticleReport
from app.models.receiving import Receiving
from app.models.stock import Stock
from app.models.supplier import Supplier
from app.models.surplus import Surplus
from app.models.system_config import SystemConfig
from app.models.transaction import Transaction
from app.models.uom_catalog import UomCatalog
from app.models.user import User


@pytest.fixture(scope="module")
def warehouse_data(app):
    """Seed Warehouse-specific fixtures once for the module."""
    with app.app_context():
        location = _db.session.get(Location, 1)
        if location is None:
            location = Location(id=1, name="Warehouse", timezone="UTC", is_active=True)
            _db.session.add(location)
            _db.session.flush()

        kg = UomCatalog.query.filter_by(code="whkg").first()
        if kg is None:
            kg = UomCatalog(code="whkg", label_hr="Warehouse kilogram", label_en="Warehouse kilogram", decimal_display=True)
            _db.session.add(kg)
            _db.session.flush()

        kom = UomCatalog.query.filter_by(code="whkom").first()
        if kom is None:
            kom = UomCatalog(code="whkom", label_hr="Warehouse piece", label_en="Warehouse piece", decimal_display=False)
            _db.session.add(kom)
            _db.session.flush()

        active_category = Category.query.filter_by(key="warehouse_active_cat").first()
        if active_category is None:
            active_category = Category(
                key="warehouse_active_cat",
                label_hr="Warehouse Active",
                label_en="Warehouse Active",
                is_active=True,
            )
            _db.session.add(active_category)
            _db.session.flush()

        batch_category = Category.query.filter_by(key="warehouse_batch_cat").first()
        if batch_category is None:
            batch_category = Category(
                key="warehouse_batch_cat",
                label_hr="Warehouse Batch",
                label_en="Warehouse Batch",
                is_active=True,
            )
            _db.session.add(batch_category)
            _db.session.flush()

        inactive_category = Category.query.filter_by(key="warehouse_inactive_cat").first()
        if inactive_category is None:
            inactive_category = Category(
                key="warehouse_inactive_cat",
                label_hr="Warehouse Inactive",
                label_en="Warehouse Inactive",
                is_active=False,
            )
            _db.session.add(inactive_category)
            _db.session.flush()

        admin = User.query.filter_by(username="warehouse_admin").first()
        if admin is None:
            admin = User(
                username="warehouse_admin",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            _db.session.add(admin)

        manager = User.query.filter_by(username="warehouse_manager").first()
        if manager is None:
            manager = User(
                username="warehouse_manager",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.MANAGER,
                is_active=True,
            )
            _db.session.add(manager)

        staff = User.query.filter_by(username="warehouse_staff").first()
        if staff is None:
            staff = User(
                username="warehouse_staff",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.WAREHOUSE_STAFF,
                is_active=True,
            )
            _db.session.add(staff)

        viewer = User.query.filter_by(username="warehouse_viewer").first()
        if viewer is None:
            viewer = User(
                username="warehouse_viewer",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.VIEWER,
                is_active=True,
            )
            _db.session.add(viewer)

        operator = User.query.filter_by(username="warehouse_operator").first()
        if operator is None:
            operator = User(
                username="warehouse_operator",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.OPERATOR,
                is_active=True,
            )
            _db.session.add(operator)

        for key, value in (
            ("default_language", "hr"),
            ("barcode_format", "Code128"),
            ("barcode_printer", ""),
            ("export_format", "generic"),
        ):
            config_row = SystemConfig.query.filter_by(key=key).first()
            if config_row is None:
                _db.session.add(SystemConfig(key=key, value=value))
            else:
                config_row.value = value

        supplier_primary = Supplier.query.filter_by(internal_code="WH-SUP-001").first()
        if supplier_primary is None:
            supplier_primary = Supplier(
                internal_code="WH-SUP-001",
                name="Warehouse Supplier 1",
                is_active=True,
            )
            _db.session.add(supplier_primary)
            _db.session.flush()

        supplier_secondary = Supplier.query.filter_by(internal_code="WH-SUP-002").first()
        if supplier_secondary is None:
            supplier_secondary = Supplier(
                internal_code="WH-SUP-002",
                name="Warehouse Supplier 2",
                is_active=True,
            )
            _db.session.add(supplier_secondary)
            _db.session.flush()

        supplier_tertiary = Supplier.query.filter_by(internal_code="WH-SUP-003").first()
        if supplier_tertiary is None:
            supplier_tertiary = Supplier(
                internal_code="WH-SUP-003",
                name="Warehouse Supplier 3",
                is_active=True,
            )
            _db.session.add(supplier_tertiary)
            _db.session.flush()

        supplier_inactive = Supplier.query.filter_by(internal_code="WH-SUP-004").first()
        if supplier_inactive is None:
            supplier_inactive = Supplier(
                internal_code="WH-SUP-004",
                name="Warehouse Supplier Inactive",
                is_active=False,
            )
            _db.session.add(supplier_inactive)
            _db.session.flush()

        active_article = Article.query.filter_by(article_no="WH-ACT-001").first()
        if active_article is None:
            active_article = Article(
                article_no="WH-ACT-001",
                description="Warehouse red status article",
                category_id=active_category.id,
                base_uom=kg.id,
                has_batch=False,
                reorder_threshold=Decimal("10.000"),
                density=Decimal("1.000"),
                barcode="WHBAR001",
                is_active=True,
            )
            _db.session.add(active_article)
            _db.session.flush()

        batch_article = Article.query.filter_by(article_no="WH-BATCH-002").first()
        if batch_article is None:
            batch_article = Article(
                article_no="WH-BATCH-002",
                description="Warehouse batch tracked article",
                category_id=batch_category.id,
                base_uom=kg.id,
                pack_size=Decimal("25.000"),
                pack_uom=kom.id,
                has_batch=True,
                reorder_threshold=Decimal("100.000"),
                reorder_coverage_days=14,
                density=Decimal("1.100"),
                manufacturer="PaintCo",
                manufacturer_art_number="P-9000",
                is_active=True,
            )
            _db.session.add(batch_article)
            _db.session.flush()

        inactive_article = Article.query.filter_by(article_no="WH-INACTIVE-003").first()
        if inactive_article is None:
            inactive_article = Article(
                article_no="WH-INACTIVE-003",
                description="Warehouse inactive article",
                category_id=active_category.id,
                base_uom=kg.id,
                has_batch=False,
                density=Decimal("1.000"),
                is_active=False,
            )
            _db.session.add(inactive_article)
            _db.session.flush()

        deactivation_article = Article.query.filter_by(article_no="WH-DEACT-004").first()
        if deactivation_article is None:
            deactivation_article = Article(
                article_no="WH-DEACT-004",
                description="Warehouse article to deactivate",
                category_id=active_category.id,
                base_uom=kg.id,
                has_batch=False,
                density=Decimal("1.000"),
                is_active=True,
            )
            _db.session.add(deactivation_article)
            _db.session.flush()

        normal_article = Article.query.filter_by(article_no="WH-NORMAL-005").first()
        if normal_article is None:
            normal_article = Article(
                article_no="WH-NORMAL-005",
                description="Warehouse normal status article",
                category_id=active_category.id,
                base_uom=kg.id,
                has_batch=False,
                reorder_threshold=Decimal("10.000"),
                density=Decimal("1.000"),
                is_active=True,
            )
            _db.session.add(normal_article)
            _db.session.flush()

        batch_early = (
            Batch.query
            .filter_by(article_id=batch_article.id, batch_code="24001")
            .first()
        )
        if batch_early is None:
            batch_early = Batch(
                article_id=batch_article.id,
                batch_code="24001",
                expiry_date=date(2026, 4, 1),
            )
            _db.session.add(batch_early)
            _db.session.flush()

        batch_late = (
            Batch.query
            .filter_by(article_id=batch_article.id, batch_code="24099")
            .first()
        )
        if batch_late is None:
            batch_late = Batch(
                article_id=batch_article.id,
                batch_code="24099",
                expiry_date=date(2026, 5, 1),
            )
            _db.session.add(batch_late)
            _db.session.flush()

        if not Stock.query.filter_by(location_id=location.id, article_id=active_article.id, batch_id=None).first():
            _db.session.add(
                Stock(
                    location_id=location.id,
                    article_id=active_article.id,
                    batch_id=None,
                    quantity=Decimal("9.000"),
                    uom="whkg",
                    average_price=Decimal("1.2500"),
                )
            )

        if not Surplus.query.filter_by(location_id=location.id, article_id=active_article.id, batch_id=None).first():
            _db.session.add(
                Surplus(
                    location_id=location.id,
                    article_id=active_article.id,
                    batch_id=None,
                    quantity=Decimal("0.500"),
                    uom="whkg",
                )
            )

        if not Stock.query.filter_by(location_id=location.id, article_id=normal_article.id, batch_id=None).first():
            _db.session.add(
                Stock(
                    location_id=location.id,
                    article_id=normal_article.id,
                    batch_id=None,
                    quantity=Decimal("15.000"),
                    uom="whkg",
                    average_price=Decimal("1.2500"),
                )
            )

        if not Stock.query.filter_by(location_id=location.id, article_id=batch_article.id, batch_id=batch_early.id).first():
            _db.session.add(
                Stock(
                    location_id=location.id,
                    article_id=batch_article.id,
                    batch_id=batch_early.id,
                    quantity=Decimal("100.000"),
                    uom="whkg",
                    average_price=Decimal("2.5000"),
                )
            )

        if not Stock.query.filter_by(location_id=location.id, article_id=batch_article.id, batch_id=batch_late.id).first():
            _db.session.add(
                Stock(
                    location_id=location.id,
                    article_id=batch_article.id,
                    batch_id=batch_late.id,
                    quantity=Decimal("3.000"),
                    uom="whkg",
                    average_price=Decimal("2.6000"),
                )
            )

        if not Surplus.query.filter_by(location_id=location.id, article_id=batch_article.id, batch_id=batch_early.id).first():
            _db.session.add(
                Surplus(
                    location_id=location.id,
                    article_id=batch_article.id,
                    batch_id=batch_early.id,
                    quantity=Decimal("4.000"),
                    uom="whkg",
                )
            )

        if not Surplus.query.filter_by(location_id=location.id, article_id=batch_article.id, batch_id=batch_late.id).first():
            _db.session.add(
                Surplus(
                    location_id=location.id,
                    article_id=batch_article.id,
                    batch_id=batch_late.id,
                    quantity=Decimal("1.000"),
                    uom="whkg",
                )
            )

        if not ArticleAlias.query.filter_by(article_id=batch_article.id, alias="Batch Paint").first():
            _db.session.add(
                ArticleAlias(
                    article_id=batch_article.id,
                    alias="Batch Paint",
                    normalized="BATCH PAINT",
                )
            )
        if not ArticleAlias.query.filter_by(article_id=batch_article.id, alias="P-9000").first():
            _db.session.add(
                ArticleAlias(
                    article_id=batch_article.id,
                    alias="P-9000",
                    normalized="P-9000",
                )
            )

        if not ArticleSupplier.query.filter_by(article_id=batch_article.id, supplier_id=supplier_primary.id).first():
            _db.session.add(
                ArticleSupplier(
                    article_id=batch_article.id,
                    supplier_id=supplier_primary.id,
                    supplier_article_code="SUP-BATCH-1",
                    last_price=Decimal("4.2500"),
                    last_ordered_at=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
                    is_preferred=True,
                )
            )
        if not ArticleSupplier.query.filter_by(article_id=batch_article.id, supplier_id=supplier_secondary.id).first():
            _db.session.add(
                ArticleSupplier(
                    article_id=batch_article.id,
                    supplier_id=supplier_secondary.id,
                    supplier_article_code="SUP-BATCH-2",
                    last_price=Decimal("4.1000"),
                    last_ordered_at=datetime(2026, 2, 5, 8, 0, tzinfo=timezone.utc),
                    is_preferred=False,
                )
            )

        if not Transaction.query.filter_by(article_id=batch_article.id, reference_id=11, reference_type="receiving").first():
            _db.session.add(
                Transaction(
                    tx_type=TxType.STOCK_RECEIPT,
                    occurred_at=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
                    location_id=location.id,
                    article_id=batch_article.id,
                    batch_id=batch_early.id,
                    quantity=Decimal("25.000"),
                    uom="whkg",
                    user_id=admin.id,
                    reference_type="receiving",
                    reference_id=11,
                    delivery_note_number="DN-001",
                )
            )
        if not Transaction.query.filter_by(article_id=batch_article.id, reference_id=33, reference_type="draft").first():
            _db.session.add(
                Transaction(
                    tx_type=TxType.OUTBOUND,
                    occurred_at=datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc),
                    location_id=location.id,
                    article_id=batch_article.id,
                    batch_id=batch_early.id,
                    quantity=Decimal("-5.000"),
                    uom="whkg",
                    user_id=admin.id,
                    reference_type="draft",
                    reference_id=33,
                )
            )
        if not Transaction.query.filter_by(article_id=batch_article.id, order_number="ORD-9001").first():
            _db.session.add(
                Transaction(
                    tx_type=TxType.SURPLUS_CONSUMED,
                    occurred_at=datetime(2026, 3, 12, 10, 0, tzinfo=timezone.utc),
                    location_id=location.id,
                    article_id=batch_article.id,
                    batch_id=batch_late.id,
                    quantity=Decimal("-2.000"),
                    uom="whkg",
                    user_id=admin.id,
                    reference_type="draft",
                    reference_id=44,
                    order_number="ORD-9001",
                )
            )

        if not Receiving.query.filter_by(delivery_note_number="WH-REC-001", batch_id=batch_early.id).first():
            _db.session.add(
                Receiving(
                    order_line_id=None,
                    article_id=batch_article.id,
                    batch_id=batch_early.id,
                    location_id=location.id,
                    quantity=Decimal("25.000"),
                    uom="whkg",
                    unit_price=Decimal("4.2000"),
                    delivery_note_number="WH-REC-001",
                    note="Warehouse barcode seed 1",
                    barcodes_printed=4,
                    received_by=admin.id,
                    received_at=datetime(2026, 3, 10, 8, 15, tzinfo=timezone.utc),
                )
            )

        if not Receiving.query.filter_by(delivery_note_number="WH-REC-002", batch_id=batch_early.id).first():
            _db.session.add(
                Receiving(
                    order_line_id=None,
                    article_id=batch_article.id,
                    batch_id=batch_early.id,
                    location_id=location.id,
                    quantity=Decimal("15.000"),
                    uom="whkg",
                    unit_price=Decimal("4.3000"),
                    delivery_note_number="WH-REC-002",
                    note="Warehouse barcode seed 2",
                    barcodes_printed=2,
                    received_by=admin.id,
                    received_at=datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc),
                )
            )

        draft_group = DraftGroup.query.filter_by(group_number="WH-DR-0001").first()
        if draft_group is None:
            draft_group = DraftGroup(
                group_number="WH-DR-0001",
                description="Warehouse pending draft",
                status=DraftGroupStatus.PENDING,
                operational_date=date(2026, 3, 13),
                created_by=admin.id,
            )
            _db.session.add(draft_group)
            _db.session.flush()

        if not Draft.query.filter_by(client_event_id="warehouse-pending-draft-001").first():
            _db.session.add(
                Draft(
                    draft_group_id=draft_group.id,
                    location_id=location.id,
                    article_id=deactivation_article.id,
                    batch_id=None,
                    quantity=Decimal("2.000"),
                    uom="whkg",
                    status=DraftStatus.DRAFT,
                    draft_type=DraftType.OUTBOUND,
                    source=DraftSource.manual,
                    client_event_id="warehouse-pending-draft-001",
                    created_by=admin.id,
                )
            )

        _db.session.commit()

        yield {
            "location": location,
            "kg": kg,
            "kom": kom,
            "active_category": active_category,
            "batch_category": batch_category,
            "inactive_category": inactive_category,
            "admin": admin,
            "manager": manager,
            "staff": staff,
            "viewer": viewer,
            "operator": operator,
            "supplier_primary": supplier_primary,
            "supplier_secondary": supplier_secondary,
            "supplier_tertiary": supplier_tertiary,
            "supplier_inactive": supplier_inactive,
            "active_article": active_article,
            "batch_article": batch_article,
            "inactive_article": inactive_article,
            "deactivation_article": deactivation_article,
            "normal_article": normal_article,
            "batch_early": batch_early,
            "batch_late": batch_late,
        }


_token_cache: dict[str, str] = {}


def _login(client, username: str) -> str:
    if username in _token_cache:
        return _token_cache[username]
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "pass"},
        environ_base={"REMOTE_ADDR": "127.0.9.1"},
    )
    token = response.get_json()["access_token"]
    _token_cache[username] = token
    return token


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _set_system_config(key: str, value: str) -> None:
    row = SystemConfig.query.filter_by(key=key).first()
    if row is None:
        _db.session.add(SystemConfig(key=key, value=value))
    else:
        row.value = value
    _db.session.commit()


def _count_pdf_pages(content: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page\b", content))


def _create_missing_article_report(
    *,
    reported_by: int,
    search_term: str,
    normalized_term: str,
    report_count: int = 1,
    status: MissingArticleReportStatus = MissingArticleReportStatus.OPEN,
    created_at: datetime | None = None,
    resolved_at: datetime | None = None,
    resolution_note: str | None = None,
) -> MissingArticleReport:
    report = MissingArticleReport(
        reported_by=reported_by,
        search_term=search_term,
        normalized_term=normalized_term,
        report_count=report_count,
        status=status,
        created_at=created_at or datetime.now(timezone.utc),
        resolved_at=resolved_at,
        resolution_note=resolution_note,
    )
    _db.session.add(report)
    _db.session.flush()
    return report


class TestWarehouseArticles:
    def test_create_article_returns_201_and_stores_uppercase(self, client, app, warehouse_data):
        token = _login(client, "warehouse_admin")
        response = client.post(
            "/api/v1/articles",
            json={
                "article_no": "wh-new-005",
                "description": "New warehouse article",
                "category_id": warehouse_data["active_category"].id,
                "base_uom": "whkg",
                "pack_size": 5,
                "pack_uom": "whkom",
                "has_batch": False,
                "reorder_threshold": 7.5,
                "reorder_coverage_days": 10,
                "density": 1.2,
                "is_active": True,
            },
            headers=_auth_header(token),
        )
        assert response.status_code == 201
        payload = response.get_json()
        assert payload["article_no"] == "WH-NEW-005"
        assert payload["base_uom"] == "whkg"
        assert payload["pack_uom"] == "whkom"
        assert payload["stock_total"] == 0.0
        assert payload["surplus_total"] == 0.0
        assert payload["reorder_status"] == "RED"
        assert payload["pending_draft_count"] == 0
        assert payload["has_pending_drafts"] is False
        assert payload["suppliers"] == []
        assert payload["aliases"] == []

        with app.app_context():
            stored = Article.query.filter_by(article_no="WH-NEW-005").first()
            assert stored is not None
            assert stored.description == "New warehouse article"

    def test_duplicate_article_no_returns_409(self, client, warehouse_data):
        token = _login(client, "warehouse_admin")
        response = client.post(
            "/api/v1/articles",
            json={
                "article_no": "wh-act-001",
                "description": "Duplicate",
                "category_id": warehouse_data["active_category"].id,
                "base_uom": "whkg",
                "has_batch": False,
            },
            headers=_auth_header(token),
        )
        assert response.status_code == 409
        assert response.get_json()["error"] == "ARTICLE_ALREADY_EXISTS"

    def test_create_article_with_suppliers_creates_article_supplier_rows(
        self, client, app, warehouse_data
    ):
        token = _login(client, "warehouse_admin")
        response = client.post(
            "/api/v1/articles",
            json={
                "article_no": "WH-SUP-LINK-006",
                "description": "Warehouse article with supplier links",
                "category_id": warehouse_data["active_category"].id,
                "base_uom": "whkg",
                "has_batch": False,
                "suppliers": [
                    {
                        "supplier_id": warehouse_data["supplier_secondary"].id,
                        "supplier_article_code": "SUP-LINK-2",
                        "is_preferred": False,
                    },
                    {
                        "supplier_id": warehouse_data["supplier_primary"].id,
                        "supplier_article_code": "SUP-LINK-1",
                        "is_preferred": True,
                    },
                ],
            },
            headers=_auth_header(token),
        )
        assert response.status_code == 201
        payload = response.get_json()
        assert [row["supplier_id"] for row in payload["suppliers"]] == [
            warehouse_data["supplier_primary"].id,
            warehouse_data["supplier_secondary"].id,
        ]
        assert payload["suppliers"][0]["supplier_name"] == "Warehouse Supplier 1"
        assert payload["suppliers"][0]["supplier_article_code"] == "SUP-LINK-1"
        assert payload["suppliers"][0]["is_preferred"] is True

        with app.app_context():
            article = Article.query.filter_by(article_no="WH-SUP-LINK-006").first()
            assert article is not None
            links = (
                ArticleSupplier.query
                .filter_by(article_id=article.id)
                .order_by(ArticleSupplier.supplier_id.asc())
                .all()
            )
            assert [(link.supplier_id, link.supplier_article_code, link.is_preferred) for link in links] == [
                (
                    warehouse_data["supplier_primary"].id,
                    "SUP-LINK-1",
                    True,
                ),
                (
                    warehouse_data["supplier_secondary"].id,
                    "SUP-LINK-2",
                    False,
                ),
            ]

    def test_create_article_rejects_duplicate_supplier_ids(self, client, warehouse_data):
        token = _login(client, "warehouse_admin")
        response = client.post(
            "/api/v1/articles",
            json={
                "article_no": "WH-SUP-DUP-007",
                "description": "Warehouse duplicate supplier ids",
                "category_id": warehouse_data["active_category"].id,
                "base_uom": "whkg",
                "has_batch": False,
                "suppliers": [
                    {
                        "supplier_id": warehouse_data["supplier_primary"].id,
                        "supplier_article_code": "SUP-DUP-1",
                        "is_preferred": True,
                    },
                    {
                        "supplier_id": warehouse_data["supplier_primary"].id,
                        "supplier_article_code": "SUP-DUP-2",
                        "is_preferred": False,
                    },
                ],
            },
            headers={**_auth_header(token), "Accept-Language": "en"},
        )
        assert response.status_code == 400
        payload = response.get_json()
        assert payload["error"] == "VALIDATION_ERROR"
        assert "duplicate supplier_id" in payload["message"]

    def test_create_article_rejects_inactive_supplier_ids(self, client, warehouse_data):
        token = _login(client, "warehouse_admin")
        response = client.post(
            "/api/v1/articles",
            json={
                "article_no": "WH-SUP-INACTIVE-008",
                "description": "Warehouse inactive supplier id",
                "category_id": warehouse_data["active_category"].id,
                "base_uom": "whkg",
                "has_batch": False,
                "suppliers": [
                    {
                        "supplier_id": warehouse_data["supplier_inactive"].id,
                        "supplier_article_code": "SUP-INACTIVE-1",
                        "is_preferred": False,
                    }
                ],
            },
            headers={**_auth_header(token), "Accept-Language": "en"},
        )
        assert response.status_code == 400
        payload = response.get_json()
        assert payload["error"] == "VALIDATION_ERROR"
        assert "active suppliers only" in payload["message"]

    def test_invalid_article_no_chars_return_400(self, client, warehouse_data):
        token = _login(client, "warehouse_admin")
        response = client.post(
            "/api/v1/articles",
            json={
                "article_no": "BAD 001!",
                "description": "Invalid",
                "category_id": warehouse_data["active_category"].id,
                "base_uom": "whkg",
                "has_batch": False,
            },
            headers=_auth_header(token),
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "VALIDATION_ERROR"

    def test_list_mode_excludes_inactive_and_filters_by_category(self, client, warehouse_data):
        token = _login(client, "warehouse_manager")
        response = client.get(
            "/api/v1/articles?page=1&per_page=50&category=warehouse_batch_cat&q=batch",
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["page"] == 1
        assert payload["per_page"] == 50
        assert payload["total"] >= 1

        items = payload["items"]
        assert len(items) == 1
        item = items[0]
        assert item["article_no"] == "WH-BATCH-002"
        assert item["category_key"] == "warehouse_batch_cat"
        assert item["reorder_status"] == "YELLOW"

        default_list = client.get(
            "/api/v1/articles?page=1&per_page=50",
            headers=_auth_header(token),
        )
        article_nos = {row["article_no"] for row in default_list.get_json()["items"]}
        assert "WH-INACTIVE-003" not in article_nos

    def test_include_inactive_true_includes_inactive_articles(self, client, warehouse_data):
        token = _login(client, "warehouse_manager")
        response = client.get(
            "/api/v1/articles?page=1&per_page=50&include_inactive=true&q=inactive",
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["items"][0]["article_no"] == "WH-INACTIVE-003"
        assert payload["items"][0]["is_active"] is False

    def test_detail_includes_batches_suppliers_aliases_and_totals(self, client, warehouse_data):
        token = _login(client, "warehouse_manager")
        response = client.get(
            f"/api/v1/articles/{warehouse_data['batch_article'].id}",
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["article_no"] == "WH-BATCH-002"
        assert payload["stock_total"] == 103.0
        assert payload["surplus_total"] == 5.0
        assert payload["reorder_status"] == "YELLOW"
        assert payload["pending_draft_count"] == 0
        assert payload["has_pending_drafts"] is False
        assert payload["category_key"] == "warehouse_batch_cat"
        assert payload["base_uom"] == "whkg"
        assert payload["pack_uom"] == "whkom"
        assert [batch["batch_code"] for batch in payload["batches"]] == ["24001", "24099"]
        assert payload["batches"][0]["stock_total"] == 100.0
        assert payload["batches"][0]["surplus_total"] == 4.0
        assert len(payload["suppliers"]) == 2
        assert payload["suppliers"][0]["is_preferred"] is True
        assert {alias["alias"] for alias in payload["aliases"]} == {"Batch Paint", "P-9000"}

    def test_manager_get_access_and_operator_warehouse_forbidden(self, client, warehouse_data):
        manager_token = _login(client, "warehouse_manager")
        operator_token = _login(client, "warehouse_operator")

        list_response = client.get(
            "/api/v1/articles?page=1&per_page=50",
            headers=_auth_header(manager_token),
        )
        assert list_response.status_code == 200

        transactions_response = client.get(
            f"/api/v1/articles/{warehouse_data['batch_article'].id}/transactions?page=1&per_page=50",
            headers=_auth_header(manager_token),
        )
        assert transactions_response.status_code == 200

        categories_response = client.get(
            "/api/v1/articles/lookups/categories",
            headers=_auth_header(manager_token),
        )
        assert categories_response.status_code == 200

        uoms_response = client.get(
            "/api/v1/articles/lookups/uoms",
            headers=_auth_header(manager_token),
        )
        assert uoms_response.status_code == 200

        operator_list = client.get(
            "/api/v1/articles?page=1&per_page=50",
            headers=_auth_header(operator_token),
        )
        assert operator_list.status_code == 403

        operator_lookup = client.get(
            "/api/v1/articles?q=WH-ACT-001",
            headers=_auth_header(operator_token),
        )
        assert operator_lookup.status_code == 200
        assert operator_lookup.get_json()["article_no"] == "WH-ACT-001"

    def test_manager_post_returns_403(self, client, warehouse_data):
        token = _login(client, "warehouse_manager")
        response = client.post(
            "/api/v1/articles",
            json={
                "article_no": "WH-MGR-TEST",
                "description": "Manager test",
                "category_id": warehouse_data["active_category"].id,
                "base_uom": "whkg",
                "has_batch": False,
            },
            headers=_auth_header(token),
        )
        assert response.status_code == 403

    def test_reorder_status_normal(self, client, warehouse_data):
        token = _login(client, "warehouse_admin")
        response = client.get(
            f"/api/v1/articles/{warehouse_data['normal_article'].id}",
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        assert response.get_json()["reorder_status"] == "NORMAL"

    def test_update_article_returns_detail_payload(self, client, app, warehouse_data):
        token = _login(client, "warehouse_admin")
        response = client.put(
            f"/api/v1/articles/{warehouse_data['active_article'].id}",
            json={
                "article_no": "wh-act-001-upd",
                "description": "Warehouse red status article updated",
                "category_id": warehouse_data["active_category"].id,
                "base_uom": "whkg",
                "pack_size": None,
                "pack_uom": None,
                "barcode": "WHBAR001",
                "manufacturer": "UpdatedCo",
                "manufacturer_art_number": "UPD-001",
                "has_batch": False,
                "reorder_threshold": 10,
                "reorder_coverage_days": 12,
                "density": 1.5,
                "is_active": True,
            },
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["article_no"] == "WH-ACT-001-UPD"
        assert payload["manufacturer"] == "UpdatedCo"
        assert payload["manufacturer_art_number"] == "UPD-001"
        assert payload["density"] == 1.5

        with app.app_context():
            stored = _db.session.get(Article, warehouse_data["active_article"].id)
            assert stored.article_no == "WH-ACT-001-UPD"

    def test_update_article_without_suppliers_preserves_existing_links(
        self, client, app, warehouse_data
    ):
        token = _login(client, "warehouse_admin")
        with app.app_context():
            before_links = (
                ArticleSupplier.query
                .filter_by(article_id=warehouse_data["batch_article"].id)
                .order_by(ArticleSupplier.supplier_id.asc())
                .all()
            )
            before_snapshot = [
                (link.supplier_id, link.supplier_article_code, link.is_preferred)
                for link in before_links
            ]

        response = client.put(
            f"/api/v1/articles/{warehouse_data['batch_article'].id}",
            json={},
            headers=_auth_header(token),
        )
        assert response.status_code == 200

        with app.app_context():
            after_links = (
                ArticleSupplier.query
                .filter_by(article_id=warehouse_data["batch_article"].id)
                .order_by(ArticleSupplier.supplier_id.asc())
                .all()
            )
            after_snapshot = [
                (link.supplier_id, link.supplier_article_code, link.is_preferred)
                for link in after_links
            ]
            assert after_snapshot == before_snapshot

    def test_update_article_suppliers_syncs_by_supplier_id(
        self, client, app, warehouse_data
    ):
        token = _login(client, "warehouse_admin")
        response = client.put(
            f"/api/v1/articles/{warehouse_data['batch_article'].id}",
            json={
                "suppliers": [
                    {
                        "supplier_id": warehouse_data["supplier_secondary"].id,
                        "supplier_article_code": "SUP-BATCH-2-UPD",
                        "is_preferred": False,
                    },
                    {
                        "supplier_id": warehouse_data["supplier_tertiary"].id,
                        "supplier_article_code": "SUP-BATCH-3",
                        "is_preferred": True,
                    },
                ]
            },
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert [row["supplier_id"] for row in payload["suppliers"]] == [
            warehouse_data["supplier_tertiary"].id,
            warehouse_data["supplier_secondary"].id,
        ]
        assert payload["suppliers"][0]["supplier_name"] == "Warehouse Supplier 3"
        assert payload["suppliers"][0]["supplier_article_code"] == "SUP-BATCH-3"
        assert payload["suppliers"][0]["is_preferred"] is True

        with app.app_context():
            links = (
                ArticleSupplier.query
                .filter_by(article_id=warehouse_data["batch_article"].id)
                .order_by(ArticleSupplier.supplier_id.asc())
                .all()
            )
            assert [(link.supplier_id, link.supplier_article_code, link.is_preferred) for link in links] == [
                (
                    warehouse_data["supplier_secondary"].id,
                    "SUP-BATCH-2-UPD",
                    False,
                ),
                (
                    warehouse_data["supplier_tertiary"].id,
                    "SUP-BATCH-3",
                    True,
                ),
            ]

    def test_deactivate_sets_is_active_false(self, client, app, warehouse_data):
        token = _login(client, "warehouse_admin")
        response = client.patch(
            f"/api/v1/articles/{warehouse_data['deactivation_article'].id}/deactivate",
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["is_active"] is False
        assert payload["pending_draft_count"] == 1
        assert payload["has_pending_drafts"] is True

        with app.app_context():
            stored = _db.session.get(Article, warehouse_data["deactivation_article"].id)
            assert stored.is_active is False

    def test_transactions_endpoint_is_paginated_and_newest_first(self, client, warehouse_data):
        token = _login(client, "warehouse_manager")
        response = client.get(
            f"/api/v1/articles/{warehouse_data['batch_article'].id}/transactions?page=1&per_page=2",
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["total"] == 3
        assert payload["page"] == 1
        assert payload["per_page"] == 2
        assert payload["items"][0]["type"] == "SURPLUS_CONSUMED"
        assert payload["items"][0]["reference"] == "ORD-9001"
        assert payload["items"][0]["batch_code"] == "24099"
        assert payload["items"][0]["user"] == "warehouse_admin"
        assert payload["items"][1]["type"] == "OUTBOUND"
        assert payload["items"][1]["reference"] == "draft:33"

    def test_lookup_endpoints_return_expected_rows(self, client, warehouse_data):
        token = _login(client, "warehouse_manager")

        categories_response = client.get(
            "/api/v1/articles/lookups/categories",
            headers=_auth_header(token),
        )
        assert categories_response.status_code == 200
        category_keys = {row["key"] for row in categories_response.get_json()}
        assert "warehouse_active_cat" in category_keys
        assert "warehouse_batch_cat" in category_keys
        assert "warehouse_inactive_cat" not in category_keys

        uoms_response = client.get(
            "/api/v1/articles/lookups/uoms",
            headers=_auth_header(token),
        )
        assert uoms_response.status_code == 200
        uom_codes = {row["code"] for row in uoms_response.get_json()}
        assert {"whkg", "whkom"}.issubset(uom_codes)

    def test_supplier_lookup_returns_active_suppliers_only(self, client, warehouse_data):
        token = _login(client, "warehouse_manager")
        response = client.get(
            "/api/v1/suppliers",
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        payload = response.get_json()
        # Bare mode must remain a flat array for backward compatibility
        assert isinstance(payload, list)
        internal_codes = {row["internal_code"] for row in payload}
        assert {"WH-SUP-001", "WH-SUP-002", "WH-SUP-003"}.issubset(internal_codes)
        assert "WH-SUP-004" not in internal_codes

    def test_supplier_paginated_preload_returns_paginated_shape(self, client, warehouse_data):
        token = _login(client, "warehouse_manager")
        response = client.get(
            "/api/v1/suppliers?per_page=200",
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert "items" in payload
        assert "total" in payload
        assert payload["page"] == 1
        assert payload["per_page"] == 200
        internal_codes = {row["internal_code"] for row in payload["items"]}
        assert {"WH-SUP-001", "WH-SUP-002", "WH-SUP-003"}.issubset(internal_codes)
        assert "WH-SUP-004" not in internal_codes

    def test_supplier_paginated_explicit_page_and_per_page(self, client, warehouse_data):
        token = _login(client, "warehouse_manager")
        response = client.get(
            "/api/v1/suppliers?page=1&per_page=2",
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["page"] == 1
        assert payload["per_page"] == 2
        assert len(payload["items"]) <= 2
        assert payload["total"] >= 3  # at least three active suppliers in seed data

    def test_supplier_paginated_invalid_page_returns_400(self, client, warehouse_data):
        token = _login(client, "warehouse_manager")
        response = client.get(
            "/api/v1/suppliers?page=abc&per_page=10",
            headers=_auth_header(token),
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "VALIDATION_ERROR"

    def test_barcode_routes_are_admin_only(self, client, app, warehouse_data):
        manager_token = _login(client, "warehouse_manager")
        with app.app_context():
            _set_system_config("barcode_format", "Code128")

        article_response = client.get(
            f"/api/v1/articles/{warehouse_data['active_article'].id}/barcode",
            headers=_auth_header(manager_token),
        )
        assert article_response.status_code == 403

        batch_response = client.get(
            f"/api/v1/batches/{warehouse_data['batch_early'].id}/barcode",
            headers=_auth_header(manager_token),
        )
        assert batch_response.status_code == 403

    def test_article_barcode_download_returns_pdf_for_admin(self, client, app, warehouse_data):
        token = _login(client, "warehouse_admin")
        with app.app_context():
            _set_system_config("barcode_format", "Code128")
            active_article = _db.session.get(Article, warehouse_data["active_article"].id)
            article_no = active_article.article_no

        response = client.get(
            f"/api/v1/articles/{warehouse_data['active_article'].id}/barcode",
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        assert response.mimetype == "application/pdf"
        assert f"wms_article_{article_no}_barcode.pdf" in response.headers["Content-Disposition"]
        assert _count_pdf_pages(response.data) == 1
        assert b"Article Barcode" in response.data
        assert article_no.encode() in response.data
        assert b"WHBAR001" in response.data

    def test_article_barcode_generation_persists_missing_value_idempotently(
        self, client, app, warehouse_data
    ):
        token = _login(client, "warehouse_admin")
        with app.app_context():
            batch_article = _db.session.get(Article, warehouse_data["batch_article"].id)
            batch_article.barcode = None
            _db.session.commit()
            _set_system_config("barcode_format", "EAN-13")

        first_response = client.get(
            f"/api/v1/articles/{warehouse_data['batch_article'].id}/barcode",
            headers=_auth_header(token),
        )
        assert first_response.status_code == 200
        assert first_response.mimetype == "application/pdf"
        assert _count_pdf_pages(first_response.data) == 1

        with app.app_context():
            stored = _db.session.get(Article, warehouse_data["batch_article"].id)
            generated_barcode = stored.barcode
            assert generated_barcode is not None
            assert re.fullmatch(r"\d{13}", generated_barcode)

        second_response = client.get(
            f"/api/v1/articles/{warehouse_data['batch_article'].id}/barcode",
            headers=_auth_header(token),
        )
        assert second_response.status_code == 200

        with app.app_context():
            stored = _db.session.get(Article, warehouse_data["batch_article"].id)
            assert stored.barcode == generated_barcode

    def test_batch_barcode_download_returns_one_label_per_batch(self, client, app, warehouse_data):
        token = _login(client, "warehouse_admin")
        with app.app_context():
            batch = _db.session.get(Batch, warehouse_data["batch_early"].id)
            batch.barcode = None
            _db.session.commit()
            _set_system_config("barcode_format", "Code128")

        response = client.get(
            f"/api/v1/batches/{warehouse_data['batch_early'].id}/barcode",
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        assert response.mimetype == "application/pdf"
        assert "wms_batch_WH-BATCH-002_24001_barcode.pdf" in response.headers["Content-Disposition"]
        assert _count_pdf_pages(response.data) == 1
        assert b"Batch Barcode" in response.data
        assert b"WH-BATCH-002" in response.data
        assert b"24001" in response.data

        with app.app_context():
            stored_batch = _db.session.get(Batch, warehouse_data["batch_early"].id)
            assert stored_batch.barcode is not None
            assert re.fullmatch(r"\d{13}", stored_batch.barcode)

    def test_barcode_route_rejects_ean13_for_incompatible_existing_value(
        self, client, app, warehouse_data
    ):
        token = _login(client, "warehouse_admin")
        with app.app_context():
            active_article = _db.session.get(Article, warehouse_data["active_article"].id)
            active_article.barcode = "WHBAR001"
            _db.session.commit()
            _set_system_config("barcode_format", "EAN-13")

        response = client.get(
            f"/api/v1/articles/{warehouse_data['active_article'].id}/barcode",
            headers=_auth_header(token),
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "INVALID_BARCODE_VALUE"

        with app.app_context():
            _set_system_config("barcode_format", "Code128")


class TestIdentifier:
    def test_identifier_search_by_article_no(self, client, warehouse_data):
        token = _login(client, "warehouse_staff")
        response = client.get(
            "/api/v1/identifier?q=wh-batch-002",
            headers=_auth_header(token),
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["total"] == 1

        item = payload["items"][0]
        assert item["article_no"] == "WH-BATCH-002"
        assert item["matched_via"] == "article_no"

    def test_identifier_search_short_query_returns_empty(self, client, warehouse_data):
        token = _login(client, "warehouse_staff")
        response = client.get(
            "/api/v1/identifier?q=a",
            headers=_auth_header(token),
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["total"] == 0
        assert payload["items"] == []

    def test_identifier_search_returns_alias_match_with_exact_quantities(
        self, client, warehouse_data
    ):
        token = _login(client, "warehouse_staff")
        response = client.get(
            "/api/v1/identifier?q=p-9000",
            headers=_auth_header(token),
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["total"] == 1

        item = payload["items"][0]
        assert item["article_no"] == "WH-BATCH-002"
        assert item["description"] == "Warehouse batch tracked article"
        assert item["category_label_hr"] == "Warehouse Batch"
        assert item["base_uom"] == "whkg"
        assert item["decimal_display"] is True
        assert item["matched_via"] == "alias"
        assert item["matched_alias"] == "P-9000"
        assert item["stock"] == 103.0
        assert item["surplus"] == 5.0

    def test_identifier_search_viewer_receives_in_stock_only(
        self, client, warehouse_data
    ):
        token = _login(client, "warehouse_viewer")
        response = client.get(
            "/api/v1/identifier?q=whbar001",
            headers=_auth_header(token),
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["total"] == 1

        item = payload["items"][0]
        assert item["id"] == warehouse_data["active_article"].id
        assert item["matched_via"] == "barcode"
        assert item["in_stock"] is True
        assert "stock" not in item
        assert "surplus" not in item

    def test_missing_report_submit_merges_duplicates_by_normalized_term(
        self, client, app, warehouse_data
    ):
        viewer_token = _login(client, "warehouse_viewer")
        manager_token = _login(client, "warehouse_manager")
        first_response = client.post(
            "/api/v1/identifier/reports",
            json={"search_term": "  Identifier Merge Term 001  "},
            headers=_auth_header(viewer_token),
        )

        assert first_response.status_code == 201
        first_payload = first_response.get_json()
        assert first_payload["search_term"] == "Identifier Merge Term 001"
        assert first_payload["report_count"] == 1
        assert first_payload["status"] == "OPEN"

        second_response = client.post(
            "/api/v1/identifier/reports",
            json={"search_term": "identifier merge term 001"},
            headers=_auth_header(manager_token),
        )

        assert second_response.status_code == 200
        second_payload = second_response.get_json()
        assert second_payload["id"] == first_payload["id"]
        assert second_payload["search_term"] == "Identifier Merge Term 001"
        assert second_payload["report_count"] == 2
        assert second_payload["resolved_at"] is None

        with app.app_context():
            stored = _db.session.get(MissingArticleReport, first_payload["id"])
            assert stored is not None
            assert stored.normalized_term == "identifier merge term 001"
            assert stored.report_count == 2

    def test_missing_article_report_open_rows_are_unique_by_normalized_term(
        self, app, warehouse_data
    ):
        with app.app_context():
            _create_missing_article_report(
                reported_by=warehouse_data["viewer"].id,
                search_term="Identifier Unique Open",
                normalized_term="identifier unique open",
                report_count=1,
            )
            _db.session.commit()

            duplicate_open = MissingArticleReport(
                reported_by=warehouse_data["staff"].id,
                search_term="Identifier Unique Open Duplicate",
                normalized_term="identifier unique open",
                report_count=1,
                status=MissingArticleReportStatus.OPEN,
            )
            _db.session.add(duplicate_open)
            with pytest.raises(IntegrityError):
                _db.session.commit()
            _db.session.rollback()

            resolved_duplicate = MissingArticleReport(
                reported_by=warehouse_data["admin"].id,
                search_term="Identifier Unique Open Resolved",
                normalized_term="identifier unique open",
                report_count=1,
                status=MissingArticleReportStatus.RESOLVED,
            )
            _db.session.add(resolved_duplicate)
            _db.session.commit()
            assert resolved_duplicate.id is not None

    def test_admin_report_queue_defaults_to_open_and_orders_newest_first(
        self, client, app, warehouse_data
    ):
        admin_token = _login(client, "warehouse_admin")
        with app.app_context():
            old_report = _create_missing_article_report(
                reported_by=warehouse_data["viewer"].id,
                search_term="Identifier Queue Old",
                normalized_term="identifier queue old",
                report_count=2,
                created_at=datetime(2026, 12, 31, 22, 58, tzinfo=timezone.utc),
            )
            new_report = _create_missing_article_report(
                reported_by=warehouse_data["staff"].id,
                search_term="Identifier Queue New",
                normalized_term="identifier queue new",
                report_count=4,
                created_at=datetime(2026, 12, 31, 22, 59, tzinfo=timezone.utc),
            )
            _create_missing_article_report(
                reported_by=warehouse_data["admin"].id,
                search_term="Identifier Queue Resolved",
                normalized_term="identifier queue resolved",
                report_count=3,
                status=MissingArticleReportStatus.RESOLVED,
                created_at=datetime(2026, 12, 31, 22, 57, tzinfo=timezone.utc),
                resolved_at=datetime(2026, 12, 31, 23, 0, tzinfo=timezone.utc),
                resolution_note="Handled already",
            )
            _db.session.commit()
            old_report_id = old_report.id
            new_report_id = new_report.id

        response = client.get(
            "/api/v1/identifier/reports",
            headers=_auth_header(admin_token),
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["total"] >= 2
        assert payload["items"][0]["id"] == new_report_id
        assert payload["items"][0]["search_term"] == "Identifier Queue New"
        assert payload["items"][0]["report_count"] == 4
        assert payload["items"][1]["id"] == old_report_id
        assert payload["items"][1]["search_term"] == "Identifier Queue Old"
        assert all(item["status"] == "OPEN" for item in payload["items"])

        resolved_response = client.get(
            "/api/v1/identifier/reports?status=resolved",
            headers=_auth_header(admin_token),
        )
        assert resolved_response.status_code == 200
        resolved_terms = {
            item["search_term"] for item in resolved_response.get_json()["items"]
        }
        assert "Identifier Queue Resolved" in resolved_terms

    def test_identifier_report_queue_and_resolve_are_admin_only(
        self, client, app, warehouse_data
    ):
        manager_token = _login(client, "warehouse_manager")
        admin_token = _login(client, "warehouse_admin")

        with app.app_context():
            report = _create_missing_article_report(
                reported_by=warehouse_data["viewer"].id,
                search_term="Identifier Resolve Term",
                normalized_term="identifier resolve term",
                report_count=1,
                created_at=datetime(2026, 12, 31, 22, 55, tzinfo=timezone.utc),
            )
            _db.session.commit()
            report_id = report.id

        queue_response = client.get(
            "/api/v1/identifier/reports",
            headers=_auth_header(manager_token),
        )
        assert queue_response.status_code == 403

        manager_resolve = client.post(
            f"/api/v1/identifier/reports/{report_id}/resolve",
            json={"resolution_note": "Manager should not resolve"},
            headers=_auth_header(manager_token),
        )
        assert manager_resolve.status_code == 403

        admin_resolve = client.post(
            f"/api/v1/identifier/reports/{report_id}/resolve",
            json={"resolution_note": "Article added as WH-RESOLVE-001."},
            headers=_auth_header(admin_token),
        )
        assert admin_resolve.status_code == 200
        resolve_payload = admin_resolve.get_json()
        assert resolve_payload["id"] == report_id
        assert resolve_payload["status"] == "RESOLVED"
        assert resolve_payload["resolution_note"] == "Article added as WH-RESOLVE-001."
        assert resolve_payload["resolved_at"] is not None

        with app.app_context():
            stored = _db.session.get(MissingArticleReport, report_id)
            assert stored is not None
            assert stored.status == MissingArticleReportStatus.RESOLVED
            assert stored.resolution_note == "Article added as WH-RESOLVE-001."
            assert stored.resolved_at is not None
