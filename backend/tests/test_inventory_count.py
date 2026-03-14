"""Integration tests for Phase 12 — Inventory Count module."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db as _db
from app.models.article import Article
from app.models.batch import Batch
from app.models.category import Category
from app.models.draft import Draft
from app.models.draft_group import DraftGroup
from app.models.enums import (
    DraftType,
    InventoryCountLineResolution,
    InventoryCountStatus,
    TxType,
    UserRole,
)
from app.models.inventory_count import InventoryCount, InventoryCountLine
from app.models.location import Location
from app.models.stock import Stock
from app.models.surplus import Surplus
from app.models.transaction import Transaction
from app.models.uom_catalog import UomCatalog
from app.models.user import User
from app.services import inventory_service


# ---------------------------------------------------------------------------
# Module-scoped fixture: shared seed data
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def inv_data(app):
    """Seed inventory count module fixtures once per module."""
    with app.app_context():
        # Location id=1
        loc = _db.session.get(Location, 1)
        if loc is None:
            loc = Location(id=1, name="Main", timezone="UTC", is_active=True)
            _db.session.add(loc)
            _db.session.flush()

        # UOMs
        kom = UomCatalog.query.filter_by(code="inv_kom").first()
        if kom is None:
            kom = UomCatalog(code="inv_kom", label_hr="komad", decimal_display=False)
            _db.session.add(kom)
            _db.session.flush()

        kg = UomCatalog.query.filter_by(code="inv_kg").first()
        if kg is None:
            kg = UomCatalog(code="inv_kg", label_hr="kilogram", decimal_display=True)
            _db.session.add(kg)
            _db.session.flush()

        # Category
        cat = Category.query.filter_by(key="inv_cat").first()
        if cat is None:
            cat = Category(
                key="inv_cat",
                label_hr="Inventura kategorija",
                is_personal_issue=False,
                is_active=True,
            )
            _db.session.add(cat)
            _db.session.flush()

        # Articles
        art_no_batch = Article.query.filter_by(article_no="INV-ART-001").first()
        if art_no_batch is None:
            art_no_batch = Article(
                article_no="INV-ART-001",
                description="Non-batch article",
                category_id=cat.id,
                base_uom=kom.id,
                has_batch=False,
                is_active=True,
                density=Decimal("1.0"),
            )
            _db.session.add(art_no_batch)
            _db.session.flush()

        art_batch = Article.query.filter_by(article_no="INV-ART-002").first()
        if art_batch is None:
            art_batch = Article(
                article_no="INV-ART-002",
                description="Batch article",
                category_id=cat.id,
                base_uom=kg.id,
                has_batch=True,
                is_active=True,
                density=Decimal("1.0"),
            )
            _db.session.add(art_batch)
            _db.session.flush()

        art_no_stock = Article.query.filter_by(article_no="INV-ART-003").first()
        if art_no_stock is None:
            art_no_stock = Article(
                article_no="INV-ART-003",
                description="Article with no stock",
                category_id=cat.id,
                base_uom=kom.id,
                has_batch=False,
                is_active=True,
                density=Decimal("1.0"),
            )
            _db.session.add(art_no_stock)
            _db.session.flush()

        art_with_surplus = Article.query.filter_by(article_no="INV-ART-004").first()
        if art_with_surplus is None:
            art_with_surplus = Article(
                article_no="INV-ART-004",
                description="Article with stock and surplus",
                category_id=cat.id,
                base_uom=kom.id,
                has_batch=False,
                is_active=True,
                density=Decimal("1.0"),
            )
            _db.session.add(art_with_surplus)
            _db.session.flush()

        art_batch_surplus_only = Article.query.filter_by(article_no="INV-ART-005").first()
        if art_batch_surplus_only is None:
            art_batch_surplus_only = Article(
                article_no="INV-ART-005",
                description="Batch article with surplus only",
                category_id=cat.id,
                base_uom=kg.id,
                has_batch=True,
                is_active=True,
                density=Decimal("1.0"),
            )
            _db.session.add(art_batch_surplus_only)
            _db.session.flush()

        art_inactive = Article.query.filter_by(article_no="INV-ART-999").first()
        if art_inactive is None:
            art_inactive = Article(
                article_no="INV-ART-999",
                description="Inactive article",
                category_id=cat.id,
                base_uom=kom.id,
                has_batch=False,
                is_active=False,
                density=Decimal("1.0"),
            )
            _db.session.add(art_inactive)
            _db.session.flush()

        # Batch for batch article
        batch1 = Batch.query.filter_by(batch_code="20241001", article_id=art_batch.id).first()
        if batch1 is None:
            batch1 = Batch(
                article_id=art_batch.id,
                batch_code="20241001",
                expiry_date=date(2025, 10, 1),
            )
            _db.session.add(batch1)
            _db.session.flush()

        batch2 = Batch.query.filter_by(batch_code="20241002", article_id=art_batch_surplus_only.id).first()
        if batch2 is None:
            batch2 = Batch(
                article_id=art_batch_surplus_only.id,
                batch_code="20241002",
                expiry_date=date(2025, 10, 2),
            )
            _db.session.add(batch2)
            _db.session.flush()

        # Stock rows
        stock_nb = Stock.query.filter_by(
            location_id=loc.id, article_id=art_no_batch.id
        ).first()
        if stock_nb is None:
            stock_nb = Stock(
                location_id=loc.id,
                article_id=art_no_batch.id,
                batch_id=None,
                quantity=Decimal("100"),
                uom=kom.code,
                average_price=Decimal("5.0"),
            )
            _db.session.add(stock_nb)
            _db.session.flush()

        stock_b = Stock.query.filter_by(
            location_id=loc.id, article_id=art_batch.id, batch_id=batch1.id
        ).first()
        if stock_b is None:
            stock_b = Stock(
                location_id=loc.id,
                article_id=art_batch.id,
                batch_id=batch1.id,
                quantity=Decimal("50"),
                uom=kg.code,
                average_price=Decimal("10.0"),
            )
            _db.session.add(stock_b)
            _db.session.flush()

        stock_surplus = Stock.query.filter_by(
            location_id=loc.id, article_id=art_with_surplus.id, batch_id=None
        ).first()
        if stock_surplus is None:
            stock_surplus = Stock(
                location_id=loc.id,
                article_id=art_with_surplus.id,
                batch_id=None,
                quantity=Decimal("5"),
                uom=kom.code,
                average_price=Decimal("3.0"),
            )
            _db.session.add(stock_surplus)
            _db.session.flush()

        surplus_nb = Surplus.query.filter_by(
            location_id=loc.id, article_id=art_with_surplus.id, batch_id=None
        ).first()
        if surplus_nb is None:
            surplus_nb = Surplus(
                location_id=loc.id,
                article_id=art_with_surplus.id,
                batch_id=None,
                quantity=Decimal("7"),
                uom=kom.code,
            )
            _db.session.add(surplus_nb)
            _db.session.flush()

        surplus_batch = Surplus.query.filter_by(
            location_id=loc.id, article_id=art_batch_surplus_only.id, batch_id=batch2.id
        ).first()
        if surplus_batch is None:
            surplus_batch = Surplus(
                location_id=loc.id,
                article_id=art_batch_surplus_only.id,
                batch_id=batch2.id,
                quantity=Decimal("4"),
                uom=kg.code,
            )
            _db.session.add(surplus_batch)
            _db.session.flush()

        # Admin user (unique IP for rate-limit isolation)
        admin = User.query.filter_by(username="inv_admin").first()
        if admin is None:
            admin = User(
                username="inv_admin",
                password_hash=generate_password_hash("adminpass", method="pbkdf2:sha256"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            _db.session.add(admin)
            _db.session.flush()

        # Non-admin user for RBAC tests
        non_admin = User.query.filter_by(username="inv_manager").first()
        if non_admin is None:
            non_admin = User(
                username="inv_manager",
                password_hash=generate_password_hash(
                    "managerpass", method="pbkdf2:sha256"
                ),
                role=UserRole.MANAGER,
                is_active=True,
            )
            _db.session.add(non_admin)
            _db.session.flush()

        _db.session.commit()

        yield {
            "loc": loc,
            "kom": kom,
            "kg": kg,
            "cat": cat,
            "art_no_batch": art_no_batch,
            "art_batch": art_batch,
            "art_no_stock": art_no_stock,
            "art_with_surplus": art_with_surplus,
            "art_batch_surplus_only": art_batch_surplus_only,
            "art_inactive": art_inactive,
            "batch1": batch1,
            "batch2": batch2,
            "stock_nb": stock_nb,
            "stock_b": stock_b,
            "stock_surplus": stock_surplus,
            "surplus_nb": surplus_nb,
            "surplus_batch": surplus_batch,
            "admin": admin,
            "non_admin": non_admin,
        }


# ---------------------------------------------------------------------------
# Token helper
# ---------------------------------------------------------------------------

_token_cache: dict[str, str] = {}


def _get_token(client, username: str, password: str, ip: str) -> str:
    cache_key = f"{username}:{ip}"
    if cache_key not in _token_cache:
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
            environ_base={"REMOTE_ADDR": ip},
        )
        assert resp.status_code == 200, resp.get_json()
        _token_cache[cache_key] = resp.get_json()["access_token"]
    return _token_cache[cache_key]


def _admin_headers(client):
    token = _get_token(client, "inv_admin", "adminpass", "127.0.20.1")
    return {"Authorization": f"Bearer {token}"}


def _manager_headers(client):
    token = _get_token(client, "inv_manager", "managerpass", "127.0.20.2")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Test: RBAC — non-admin is rejected
# ---------------------------------------------------------------------------

def test_rbac_non_admin_rejected(client, inv_data):
    headers = _manager_headers(client)
    resp = client.post("/api/v1/inventory", headers=headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test: history is empty before any count
# ---------------------------------------------------------------------------

def test_history_empty(client, inv_data):
    headers = _admin_headers(client)
    resp = client.get("/api/v1/inventory?page=1&per_page=50", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 0
    assert data["items"] == []


# ---------------------------------------------------------------------------
# Test: active count returns null when none exists
# ---------------------------------------------------------------------------

def test_active_none(client, inv_data):
    headers = _admin_headers(client)
    resp = client.get("/api/v1/inventory/active", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["active"] is None


# ---------------------------------------------------------------------------
# Test: start count
# ---------------------------------------------------------------------------

def test_start_count(client, inv_data, app):
    headers = _admin_headers(client)
    resp = client.post("/api/v1/inventory", headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "IN_PROGRESS"
    assert data["started_by"] == "inv_admin"
    # At least our 3 test articles are included (DB may contain articles from other modules)
    assert data["total_lines"] >= 3

    with app.app_context():
        count = _db.session.get(InventoryCount, data["id"])
        assert count is not None
        assert count.status == InventoryCountStatus.IN_PROGRESS
        assert count.lines.count() >= 3


# ---------------------------------------------------------------------------
# Test: second start is blocked
# ---------------------------------------------------------------------------

def test_start_count_blocked_when_in_progress(client, inv_data):
    headers = _admin_headers(client)
    resp = client.post("/api/v1/inventory", headers=headers)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "COUNT_IN_PROGRESS"


# ---------------------------------------------------------------------------
# Test: active count returns the in-progress count with lines
# ---------------------------------------------------------------------------

def test_active_count_returned(client, inv_data, app):
    headers = _admin_headers(client)
    resp = client.get("/api/v1/inventory/active", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "IN_PROGRESS"
    # At least our 3 test articles present
    assert len(data["lines"]) >= 3
    # Progress: nothing counted yet (our articles)
    assert data["counted_lines"] == 0
    assert data["total_lines"] >= 3

    # Non-batch article line has system_quantity=100
    nb_line = next(
        l for l in data["lines"] if l["article_no"] == "INV-ART-001"
    )
    assert nb_line["system_quantity"] == 100.0
    assert nb_line["batch_id"] is None

    # Batch article line has system_quantity=50
    b_line = next(
        l for l in data["lines"] if l["article_no"] == "INV-ART-002"
    )
    assert b_line["system_quantity"] == 50.0
    assert b_line["batch_code"] == "20241001"

    # No-stock article has system_quantity=0
    ns_line = next(
        l for l in data["lines"] if l["article_no"] == "INV-ART-003"
    )
    assert ns_line["system_quantity"] == 0.0


def test_snapshot_includes_surplus_and_excludes_inactive(client, inv_data):
    headers = _admin_headers(client)
    active = client.get("/api/v1/inventory/active", headers=headers).get_json()

    with_surplus = next(
        l for l in active["lines"] if l["article_no"] == "INV-ART-004"
    )
    assert with_surplus["system_quantity"] == 12.0

    surplus_only_batch = next(
        l for l in active["lines"] if l["article_no"] == "INV-ART-005"
    )
    assert surplus_only_batch["system_quantity"] == 4.0
    assert surplus_only_batch["batch_code"] == "20241002"

    assert not any(l["article_no"] == "INV-ART-999" for l in active["lines"])


def test_snapshot_is_frozen_when_balances_change(client, inv_data, app):
    headers = _admin_headers(client)

    with app.app_context():
        stock_row = (
            _db.session.query(Stock)
            .filter_by(location_id=inv_data["loc"].id, article_id=inv_data["art_with_surplus"].id)
            .first()
        )
        surplus_row = (
            _db.session.query(Surplus)
            .filter_by(location_id=inv_data["loc"].id, article_id=inv_data["art_with_surplus"].id)
            .first()
        )
        original_stock = Decimal(str(stock_row.quantity))
        original_surplus = Decimal(str(surplus_row.quantity))

        stock_row.quantity = Decimal("999")
        surplus_row.quantity = Decimal("888")
        _db.session.commit()

    try:
        active = client.get("/api/v1/inventory/active", headers=headers).get_json()
        frozen_line = next(
            l for l in active["lines"] if l["article_no"] == "INV-ART-004"
        )
        assert frozen_line["system_quantity"] == 12.0
    finally:
        with app.app_context():
            stock_row = (
                _db.session.query(Stock)
                .filter_by(
                    location_id=inv_data["loc"].id,
                    article_id=inv_data["art_with_surplus"].id,
                )
                .first()
            )
            surplus_row = (
                _db.session.query(Surplus)
                .filter_by(
                    location_id=inv_data["loc"].id,
                    article_id=inv_data["art_with_surplus"].id,
                )
                .first()
            )
            stock_row.quantity = original_stock
            surplus_row.quantity = original_surplus
            _db.session.commit()


# ---------------------------------------------------------------------------
# Test: update counted quantity — validation
# ---------------------------------------------------------------------------

def test_update_line_negative_rejected(client, inv_data, app):
    headers = _admin_headers(client)
    # Get the active count
    active = client.get("/api/v1/inventory/active", headers=headers).get_json()
    count_id = active["id"]
    line_id = active["lines"][0]["line_id"]

    resp = client.patch(
        f"/api/v1/inventory/{count_id}/lines/{line_id}",
        json={"counted_quantity": -1},
        headers=headers,
    )
    assert resp.status_code == 400


def test_update_line_non_integer_uom(client, inv_data, app):
    """kom UOM requires whole numbers."""
    headers = _admin_headers(client)
    active = client.get("/api/v1/inventory/active", headers=headers).get_json()
    count_id = active["id"]
    # Find the non-batch article line (inv_kom = integer UOM)
    nb_line = next(l for l in active["lines"] if l["article_no"] == "INV-ART-001")

    resp = client.patch(
        f"/api/v1/inventory/{count_id}/lines/{nb_line['line_id']}",
        json={"counted_quantity": 5.5},
        headers=headers,
    )
    assert resp.status_code == 400


def test_update_line_decimal_uom_ok(client, inv_data, app):
    """inv_kg UOM (decimal_display=True) accepts decimals."""
    headers = _admin_headers(client)
    active = client.get("/api/v1/inventory/active", headers=headers).get_json()
    count_id = active["id"]
    b_line = next(l for l in active["lines"] if l["article_no"] == "INV-ART-002")

    resp = client.patch(
        f"/api/v1/inventory/{count_id}/lines/{b_line['line_id']}",
        json={"counted_quantity": 47.5},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["counted_quantity"] == 47.5
    assert data["difference"] == pytest.approx(-2.5)


# ---------------------------------------------------------------------------
# Test: update all lines (prepare for completion tests)
# ---------------------------------------------------------------------------

def test_update_all_lines(client, inv_data, app):
    """Fill in counted quantities for all remaining lines."""
    headers = _admin_headers(client)
    active = client.get("/api/v1/inventory/active", headers=headers).get_json()
    count_id = active["id"]

    for line in active["lines"]:
        if line["counted_quantity"] is not None:
            continue  # already set (batch article from previous test)
        article_no = line["article_no"]
        if article_no == "INV-ART-001":
            # system=100, counted=110 → surplus of 10
            qty = 110
        elif article_no == "INV-ART-003":
            # system=0, counted=0 → no change
            qty = 0
        else:
            # For all other articles from other test modules: match system qty → no change
            # Use integer for integer UOMs, same value otherwise
            sys_qty = line["system_quantity"]
            qty = int(sys_qty) if sys_qty == int(sys_qty) else sys_qty

        resp = client.patch(
            f"/api/v1/inventory/{count_id}/lines/{line['line_id']}",
            json={"counted_quantity": qty},
            headers=headers,
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test: complete count — blocked when uncounted lines present
# ---------------------------------------------------------------------------

# We skip this because all lines are counted now; test it on a fresh scenario below.

# ---------------------------------------------------------------------------
# Test: complete count — success
# ---------------------------------------------------------------------------

def test_complete_count(client, inv_data, app):
    headers = _admin_headers(client)
    active = client.get("/api/v1/inventory/active", headers=headers).get_json()
    count_id = active["id"]

    resp = client.post(f"/api/v1/inventory/{count_id}/complete", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "COMPLETED"
    # DB may have articles from other modules; at least our 3 lines are present
    assert data["summary"]["total_lines"] >= 3

    # INV-ART-001 → surplus, INV-ART-002 → shortage, others matched → no_change
    assert data["summary"]["surplus_added"] >= 1
    assert data["summary"]["shortage_drafts_created"] >= 1
    assert data["summary"]["no_change"] >= 1

    with app.app_context():
        count = _db.session.get(InventoryCount, count_id)
        assert count.status == InventoryCountStatus.COMPLETED
        assert count.completed_at is not None

        # Surplus row created for INV-ART-001
        surplus = (
            _db.session.query(Surplus)
            .filter_by(article_id=inv_data["art_no_batch"].id, batch_id=None)
            .first()
        )
        assert surplus is not None
        assert float(surplus.quantity) == pytest.approx(10.0)

        # INVENTORY_ADJUSTMENT Transaction created for surplus
        tx = (
            _db.session.query(Transaction)
            .filter_by(
                article_id=inv_data["art_no_batch"].id,
                tx_type=TxType.INVENTORY_ADJUSTMENT,
            )
            .first()
        )
        assert tx is not None
        assert float(tx.quantity) == pytest.approx(10.0)

        # Shortage Draft + DraftGroup created for INV-ART-002
        draft = (
            _db.session.query(Draft)
            .filter_by(
                article_id=inv_data["art_batch"].id,
                draft_type=DraftType.INVENTORY_SHORTAGE,
            )
            .first()
        )
        assert draft is not None
        assert float(draft.quantity) == pytest.approx(2.5)

        group = _db.session.get(DraftGroup, draft.draft_group_id)
        assert group is not None
        assert group.group_number.startswith("IZL-")

        # Resolutions on lines
        lines = count.lines.all()
        resolutions = {l.article_id: l.resolution for l in lines}
        assert resolutions[inv_data["art_no_batch"].id] == InventoryCountLineResolution.SURPLUS_ADDED
        assert resolutions[inv_data["art_batch"].id] == InventoryCountLineResolution.SHORTAGE_DRAFT_CREATED
        assert resolutions[inv_data["art_no_stock"].id] == InventoryCountLineResolution.NO_CHANGE


# ---------------------------------------------------------------------------
# Test: completed count appears in history
# ---------------------------------------------------------------------------

def test_history_shows_completed(client, inv_data):
    headers = _admin_headers(client)
    resp = client.get("/api/v1/inventory?page=1&per_page=50", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] >= 1
    completed = data["items"][0]
    assert completed["status"] == "COMPLETED"
    assert completed["started_by"] == "inv_admin"
    assert completed["total_lines"] >= 3
    # INV-ART-001 surplus and INV-ART-002 shortage are discrepancies
    assert completed["discrepancies"] >= 2


# ---------------------------------------------------------------------------
# Test: active count is now null after completion
# ---------------------------------------------------------------------------

def test_active_null_after_complete(client, inv_data):
    headers = _admin_headers(client)
    resp = client.get("/api/v1/inventory/active", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["active"] is None


# ---------------------------------------------------------------------------
# Test: count detail endpoint
# ---------------------------------------------------------------------------

def test_count_detail(client, inv_data, app):
    headers = _admin_headers(client)
    # Get the completed count id from history
    history = client.get(
        "/api/v1/inventory?page=1&per_page=50", headers=headers
    ).get_json()
    count_id = history["items"][0]["id"]

    resp = client.get(f"/api/v1/inventory/{count_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "COMPLETED"
    assert data["summary"]["total_lines"] >= 3
    assert data["summary"]["surplus_added"] >= 1
    assert data["summary"]["shortage_drafts_created"] >= 1
    assert data["summary"]["no_change"] >= 1
    assert len(data["lines"]) >= 3

    # Every line has a resolution
    for line in data["lines"]:
        assert line["resolution"] is not None


# ---------------------------------------------------------------------------
# Test: cannot update line after count is completed
# ---------------------------------------------------------------------------

def test_update_line_completed_count_rejected(client, inv_data, app):
    headers = _admin_headers(client)
    history = client.get(
        "/api/v1/inventory?page=1&per_page=50", headers=headers
    ).get_json()
    count_id = history["items"][0]["id"]

    with app.app_context():
        count = _db.session.get(InventoryCount, count_id)
        line_id = count.lines.first().id

    resp = client.patch(
        f"/api/v1/inventory/{count_id}/lines/{line_id}",
        json={"counted_quantity": 5},
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "COUNT_NOT_IN_PROGRESS"


# ---------------------------------------------------------------------------
# Test: complete count with uncounted lines is rejected
# ---------------------------------------------------------------------------

def test_complete_count_with_uncounted_lines(client, inv_data, app):
    """Start a second count, try to complete without counting all lines."""
    headers = _admin_headers(client)

    # Start a new count
    resp = client.post("/api/v1/inventory", headers=headers)
    assert resp.status_code == 201
    count_id = resp.get_json()["id"]

    # Do NOT fill in any counted quantities — try to complete immediately
    resp = client.post(f"/api/v1/inventory/{count_id}/complete", headers=headers)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "UNCOUNTED_LINES"

    # Cleanup: fill in all lines and complete so next test starts clean
    active = client.get("/api/v1/inventory/active", headers=headers).get_json()
    for line in active["lines"]:
        client.patch(
            f"/api/v1/inventory/{count_id}/lines/{line['line_id']}",
            json={"counted_quantity": int(line["system_quantity"])},
            headers=headers,
        )
    client.post(f"/api/v1/inventory/{count_id}/complete", headers=headers)


def test_shortage_draft_group_uses_operational_timezone(
    client, inv_data, app, monkeypatch
):
    headers = _admin_headers(client)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            fixed = cls(2026, 3, 14, 23, 30, tzinfo=timezone.utc)
            if tz is None:
                return fixed.replace(tzinfo=None)
            return fixed.astimezone(tz)

    with app.app_context():
        location = _db.session.get(Location, inv_data["loc"].id)
        original_timezone = location.timezone
        location.timezone = "Europe/Berlin"
        _db.session.commit()

    monkeypatch.setattr(inventory_service, "datetime", _FixedDateTime)

    try:
        start_resp = client.post("/api/v1/inventory", headers=headers)
        assert start_resp.status_code == 201
        count_id = start_resp.get_json()["id"]

        active = client.get("/api/v1/inventory/active", headers=headers).get_json()
        for line in active["lines"]:
            qty = line["system_quantity"]
            if line["article_no"] == "INV-ART-002":
                qty = line["system_quantity"] - 1
            payload_qty = int(qty) if qty == int(qty) else qty
            patch_resp = client.patch(
                f"/api/v1/inventory/{count_id}/lines/{line['line_id']}",
                json={"counted_quantity": payload_qty},
                headers=headers,
            )
            assert patch_resp.status_code == 200

        complete_resp = client.post(f"/api/v1/inventory/{count_id}/complete", headers=headers)
        assert complete_resp.status_code == 200

        with app.app_context():
            group = (
                _db.session.query(DraftGroup)
                .filter_by(description=f"Inventory count #{count_id} shortages")
                .first()
            )
            assert group is not None
            assert group.operational_date.isoformat() == "2026-03-15"
    finally:
        with app.app_context():
            location = _db.session.get(Location, inv_data["loc"].id)
            location.timezone = original_timezone
            _db.session.commit()


# ---------------------------------------------------------------------------
# Test: 404 for non-existent count
# ---------------------------------------------------------------------------

def test_count_detail_not_found(client, inv_data):
    headers = _admin_headers(client)
    resp = client.get("/api/v1/inventory/99999", headers=headers)
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "COUNT_NOT_FOUND"
