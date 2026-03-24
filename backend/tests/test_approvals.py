"""Integration tests for Approvals module.

These tests prove correct logic for surplus-first consumption, stock validation,
transaction signs, and other non-negotiable correctness rules.
"""

from datetime import date
from decimal import Decimal
import uuid

import pytest

from app.extensions import db as _db
from app.models.approval_action import ApprovalAction
from app.models.approval_override import ApprovalOverride
from app.models.article import Article
from app.models.batch import Batch
from app.models.category import Category
from app.models.draft import Draft
from app.models.draft_group import DraftGroup
from app.models.enums import (
    ApprovalActionType,
    DraftGroupStatus,
    DraftSource,
    DraftStatus,
    DraftType,
    TxType,
    UserRole,
)
from app.models.location import Location
from app.models.stock import Stock
from app.models.surplus import Surplus
from app.models.transaction import Transaction
from app.models.uom_catalog import UomCatalog
from app.models.user import User
from app.services import approval_service
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="module")
def app_data(app):
    """Seed the DB with everything needed to thoroughly test approval logic."""
    with app.app_context():
        # Location
        loc = _db.session.get(Location, 1)
        if loc is None:
            loc = Location(id=1, name="Approval Warehouse", timezone="UTC", is_active=True)
            _db.session.add(loc)

        # UOM
        uom = UomCatalog.query.filter_by(code="akg").first()
        if uom is None:
            uom = UomCatalog(
                code="akg",
                label_hr="kilogram",
                label_en="kilogram",
                decimal_display=True,
            )
            _db.session.add(uom)

        # Category
        cat = Category.query.filter_by(key="test_cat").first()
        if cat is None:
            cat = Category(key="test_cat", label_hr="Test Cat", is_active=True)
            _db.session.add(cat)

        _db.session.flush()

        # Users
        users = []
        for uname, role in [("appr_admin", UserRole.ADMIN), ("appr_manager", UserRole.MANAGER), ("appr_op", UserRole.OPERATOR)]:
            u = User.query.filter_by(username=uname).first()
            if not u:
                u = User(
                    username=uname,
                    password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                    role=role,
                    is_active=True,
                )
                _db.session.add(u)
            users.append(u)
        admin, manager, operator = users
        _db.session.flush()

        # Articles
        art_no_batch = Article.query.filter_by(article_no="APP-001").first()
        if not art_no_batch:
            art_no_batch = Article(
                article_no="APP-001",
                description="Article without batch",
                category_id=cat.id,
                base_uom=uom.id,
                has_batch=False,
                is_active=True,
            )
            _db.session.add(art_no_batch)

        art_with_batch = Article.query.filter_by(article_no="APP-002").first()
        if not art_with_batch:
            art_with_batch = Article(
                article_no="APP-002",
                description="Article with batch",
                category_id=cat.id,
                base_uom=uom.id,
                has_batch=True,
                is_active=True,
            )
            _db.session.add(art_with_batch)
        _db.session.flush()

        # Batches
        b1 = Batch.query.filter_by(batch_code="B-100").first()
        if not b1:
            b1 = Batch(article_id=art_with_batch.id, batch_code="B-100", expiry_date=date(2027, 1, 1))
            _db.session.add(b1)
        
        b2 = Batch.query.filter_by(batch_code="B-200").first()
        if not b2:
            b2 = Batch(article_id=art_with_batch.id, batch_code="B-200", expiry_date=date(2027, 2, 1))
            _db.session.add(b2)
        _db.session.flush()

        _db.session.commit()

        yield {
            "loc": loc,
            "uom": uom,
            "admin": admin,
            "manager": manager,
            "operator": operator,
            "art_no_batch": art_no_batch,
            "art_with_batch": art_with_batch,
            "b1": b1,
            "b2": b2,
        }

@pytest.fixture(autouse=True)
def clean_tx_and_stock(app):
    """Clean dynamic data before every test to ensure strict assertions."""
    with app.app_context():
        _db.session.query(ApprovalOverride).delete()
        _db.session.query(Transaction).delete()
        _db.session.query(ApprovalAction).delete()
        _db.session.query(Draft).delete()
        _db.session.query(DraftGroup).delete()
        _db.session.query(Stock).delete()
        _db.session.query(Surplus).delete()
        _db.session.commit()
        yield

_token_cache: dict[str, str] = {}

def _login(client, username):
    """Log in and return an access token (cached to avoid rate limiting)."""
    if username in _token_cache:
        return _token_cache[username]
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "pass"},
    )
    token = resp.get_json()["access_token"]
    _token_cache[username] = token
    return token

def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _get_detail(client, token, group_id):
    response = client.get(
        f"/api/v1/approvals/{group_id}",
        headers=_auth_header(token),
    )
    assert response.status_code == 200
    return response.get_json()


def _get_line_id(client, token, group_id, article_id, batch_id=None):
    detail = _get_detail(client, token, group_id)
    for row in detail["rows"]:
        if row["article_id"] != article_id:
            continue
        if row["batch_id"] != batch_id:
            continue
        return row["line_id"]
    raise AssertionError(
        f"Could not find aggregated row for article_id={article_id}, batch_id={batch_id}"
    )

def _insert_balances(app, loc_id, items):
    """Helper to insert starting stock and surplus."""
    with app.app_context():
        for item in items:
            s = Stock(
                location_id=loc_id,
                article_id=item["article_id"],
                batch_id=item.get("batch_id"),
                quantity=Decimal(str(item.get("stock", 0))),
                uom=item["uom"],
                average_price=Decimal("10.0")
            )
            _db.session.add(s)
            surplus_qty = item.get("surplus", 0)
            if surplus_qty > 0:
                sur = Surplus(
                    location_id=loc_id,
                    article_id=item["article_id"],
                    batch_id=item.get("batch_id"),
                    quantity=Decimal(str(surplus_qty)),
                    uom=item["uom"]
                )
                _db.session.add(sur)
        _db.session.commit()

def _create_drafts(app, loc_id, op_id, lines):
    with app.app_context():
        g = DraftGroup(
            group_number=f"IZL-{uuid.uuid4().hex[:4].upper()}",
            status=DraftGroupStatus.PENDING,
            operational_date=date.today(),
            description="Test draft",
            created_by=op_id
        )
        _db.session.add(g)
        _db.session.flush()

        # we enforce that draft_group_id is captured, returning exactly what was built
        inserted_drafts = []
        for line in lines:
            d = Draft(
                draft_group_id=g.id,
                location_id=loc_id,
                article_id=line["article_id"],
                batch_id=line.get("batch_id"),
                quantity=Decimal(str(line["quantity"])),
                uom=line["uom"],
                status=line.get("status", DraftStatus.DRAFT),
                draft_type=DraftType.OUTBOUND,
                source=DraftSource.manual,
                client_event_id=str(uuid.uuid4()),
                created_by=op_id
            )
            _db.session.add(d)
            inserted_drafts.append(d)
        _db.session.commit()
        return g.id, [d.id for d in inserted_drafts]


class TestApprovalsRead:

    def test_get_pending_approvals_aggregation(self, client, app, app_data):
        """1. GET pending aggregates same article + batch, keeps separate batches."""
        _insert_balances(app, app_data["loc"].id, [])
        # We need two lines of art_no_batch, and two lines for art_batch with different batches
        group_id, _ = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 3, "uom": "akg"},
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 4, "uom": "akg"},
            {"article_id": app_data["art_with_batch"].id, "batch_id": app_data["b1"].id, "quantity": 2, "uom": "akg"},
            {"article_id": app_data["art_with_batch"].id, "batch_id": app_data["b2"].id, "quantity": 1, "uom": "akg"}
        ])

        token = _login(client, "appr_admin")
        resp = client.get("/api/v1/approvals?status=pending", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json().get("items", [])
        
        assert len(data) == 1
        draft = data[0]
        assert draft["draft_group_id"] == group_id
        
        # the rows should be aggregated in the list response
        rows = draft["rows"]
        assert len(rows) == 3
        # art_no_batch should be 7
        no_batch_line = next(
            row for row in rows if row["article_id"] == app_data["art_no_batch"].id
        )
        assert no_batch_line["total_quantity"] == 7.0
        assert no_batch_line["uom"] == "akg"
        
        # art_with_batch should be split into 2 and 1
        with_batch_lines = [
            row for row in rows if row["article_id"] == app_data["art_with_batch"].id
        ]
        assert len(with_batch_lines) == 2
        assert any(
            row["batch_id"] == app_data["b1"].id and row["total_quantity"] == 2.0
            for row in with_batch_lines
        )
        assert any(
            row["batch_id"] == app_data["b2"].id and row["total_quantity"] == 1.0
            for row in with_batch_lines
        )

    def test_get_approval_details(self, client, app, app_data):
        """2. GET detail returns expandable individual entries for an aggregated row."""
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 3, "uom": "akg"},
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 4, "uom": "akg"}
        ])

        token = _login(client, "appr_admin")
        data = _get_detail(client, token, group_id)
        assert "rows" in data, "Detailed response missing 'rows'"
        assert len(data["rows"]) == 1
        aggr_line = data["rows"][0]
        assert aggr_line["total_quantity"] == 7.0
        assert aggr_line["uom"] == "akg"
        assert len(aggr_line["entries"]) == 2
        assert set(e["id"] for e in aggr_line["entries"]) == set(draft_ids)


class TestApprovalsAction:

    def test_approve_single_row_stock_only(self, client, app, app_data):
        """3. Approve single row with enough stock only."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 10.0, "surplus": 0.0, "uom": "akg"}
        ])
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 4.0, "uom": "akg"}
        ])

        token = _login(client, "appr_admin")
        line_id = _get_line_id(
            client, token, group_id, app_data["art_no_batch"].id, None
        )
        resp = client.post(
            f"/api/v1/approvals/{group_id}/lines/{line_id}/approve",
            headers=_auth_header(token)
        )
        assert resp.status_code == 200

        with app.app_context():
            st = Stock.query.filter_by(article_id=app_data["art_no_batch"].id).first()
            assert st.quantity == Decimal("6.0")
            
            # Check transaction was created with negative quantity
            tx = Transaction.query.filter_by(article_id=app_data["art_no_batch"].id).all()
            assert len(tx) == 1
            assert tx[0].quantity == Decimal("-4.0")
            assert tx[0].tx_type == TxType.OUTBOUND or tx[0].tx_type == TxType.STOCK_CONSUMED
            
            # Check draft was approved
            d = _db.session.get(Draft, draft_ids[0])
            assert d.status == DraftStatus.APPROVED
            group = _db.session.get(DraftGroup, group_id)
            assert group.status == DraftGroupStatus.APPROVED

    def test_approve_single_row_surplus_and_stock(self, client, app, app_data):
        """4. Approve single row with surplus + stock explicitly showing surplus-first logic."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 10.0, "surplus": 5.0, "uom": "akg"}
        ])
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 8.0, "uom": "akg"}
        ])

        token = _login(client, "appr_admin")
        line_id = _get_line_id(
            client, token, group_id, app_data["art_no_batch"].id, None
        )
        resp = client.post(
            f"/api/v1/approvals/{group_id}/lines/{line_id}/approve",
            headers=_auth_header(token)
        )
        assert resp.status_code == 200

        with app.app_context():
            # Surplus must be 0
            sur = Surplus.query.filter_by(article_id=app_data["art_no_batch"].id).first()
            assert not sur or sur.quantity == Decimal("0")
            
            # Stock should be 10 - (8 - 5) = 7.0
            st = Stock.query.filter_by(article_id=app_data["art_no_batch"].id).first()
            assert st.quantity == Decimal("7.0")
            
            txs = Transaction.query.filter_by(article_id=app_data["art_no_batch"].id).all()
            assert len(txs) == 2
            quantities = set(tx.quantity for tx in txs)
            assert Decimal("-5.0") in quantities  # surplus consumed
            assert Decimal("-3.0") in quantities  # stock consumed

    def test_approve_single_row_insufficient_stock(self, client, app, app_data):
        """5. Approve single row with insufficient stock."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 2.0, "surplus": 1.0, "uom": "akg"}
        ])
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 4.0, "uom": "akg"}
        ])

        token = _login(client, "appr_admin")
        line_id = _get_line_id(
            client, token, group_id, app_data["art_no_batch"].id, None
        )
        resp = client.post(
            f"/api/v1/approvals/{group_id}/lines/{line_id}/approve",
            headers=_auth_header(token)
        )
        assert resp.status_code == 409

        with app.app_context():
            # No mutations
            st = Stock.query.filter_by(article_id=app_data["art_no_batch"].id).first()
            assert st.quantity == Decimal("2.0")
            sur = Surplus.query.filter_by(article_id=app_data["art_no_batch"].id).first()
            assert sur.quantity == Decimal("1.0")
            txs = Transaction.query.filter_by(article_id=app_data["art_no_batch"].id).all()
            assert len(txs) == 0
            
            # Row remains unresolved
            d = _db.session.get(Draft, draft_ids[0])
            assert d.status == DraftStatus.DRAFT

    def test_approve_all_mixed_outcomes(self, client, app, app_data):
        """6. Approve all with mixed outcomes (some approved, some skipped)."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 10.0, "surplus": 0.0, "uom": "akg"},
            {"article_id": app_data["art_with_batch"].id, "batch_id": app_data["b1"].id, "stock": 2.0, "surplus": 0.0, "uom": "akg"},
        ])
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 4.0, "uom": "akg"},
            {"article_id": app_data["art_with_batch"].id, "batch_id": app_data["b1"].id, "quantity": 5.0, "uom": "akg"}
        ])

        token = _login(client, "appr_admin")
        resp = client.post(
            f"/api/v1/approvals/{group_id}/approve",
            headers=_auth_header(token)
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        
        # Verify response separation
        assert len(resp_data.get("approved", [])) == 1
        assert len(resp_data.get("skipped", [])) == 1

        with app.app_context():
            st1 = Stock.query.filter_by(article_id=app_data["art_no_batch"].id).first()
            assert st1.quantity == Decimal("6.0")
            st2 = Stock.query.filter_by(article_id=app_data["art_with_batch"].id).first()
            assert st2.quantity == Decimal("2.0")  # unchanged

            # draft 1 approved, draft 2 pending
            d1 = _db.session.get(Draft, draft_ids[0])
            d2 = _db.session.get(Draft, draft_ids[1])
            assert d1.status == DraftStatus.APPROVED
            assert d2.status == DraftStatus.DRAFT

    def test_edit_aggregated_quantity_before_approval(self, client, app, app_data):
        """7. Edit aggregated quantity before approval."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 10.0, "surplus": 0.0, "uom": "akg"}
        ])
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 2.0, "uom": "akg"},
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 3.0, "uom": "akg"}
        ])

        token = _login(client, "appr_admin")
        line_id = _get_line_id(
            client, token, group_id, app_data["art_no_batch"].id, None
        )
        resp = client.patch(
            f"/api/v1/approvals/{group_id}/lines/{line_id}",
            json={"quantity": 8.0},
            headers=_auth_header(token)
        )
        assert resp.status_code == 200

        with app.app_context():
            # Check DB has NO Transaction created, NO stock changes
            st = Stock.query.filter_by(article_id=app_data["art_no_batch"].id).first()
            assert st.quantity == Decimal("10.0")
            assert len(Transaction.query.all()) == 0
            override = ApprovalOverride.query.filter_by(
                draft_group_id=group_id,
                article_id=app_data["art_no_batch"].id,
                batch_key="__NO_BATCH__",
            ).first()
            assert override is not None
            assert override.override_quantity == Decimal("8.0")
            
        data = _get_detail(client, token, group_id)
        assert "rows" in data, "Detailed response missing 'rows'"
        line = data["rows"][0]
        assert line["total_quantity"] == 8.0
        assert line["uom"] == "akg"
        assert [entry["quantity"] for entry in line["entries"]] == [2.0, 3.0]

    def test_approve_all_unexpected_failure_rolls_back_all_changes(self, client, app, app_data, monkeypatch):
        """Bulk approval should not leave partial commits on unexpected failures."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 10.0, "surplus": 0.0, "uom": "akg"},
            {"article_id": app_data["art_with_batch"].id, "batch_id": app_data["b1"].id, "stock": 10.0, "surplus": 0.0, "uom": "akg"},
        ])
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 4.0, "uom": "akg"},
            {"article_id": app_data["art_with_batch"].id, "batch_id": app_data["b1"].id, "quantity": 3.0, "uom": "akg"},
        ])

        original_approve_pending_bucket = approval_service._approve_pending_bucket
        call_count = {"value": 0}

        def _crash_on_second_bucket(user_id, group_id_arg, line_id):
            call_count["value"] += 1
            if call_count["value"] == 2:
                raise RuntimeError("simulated bulk approval failure")
            return original_approve_pending_bucket(user_id, group_id_arg, line_id)

        monkeypatch.setattr(approval_service, "_approve_pending_bucket", _crash_on_second_bucket)

        token = _login(client, "appr_admin")
        with pytest.raises(RuntimeError, match="simulated bulk approval failure"):
            client.post(
                f"/api/v1/approvals/{group_id}/approve",
                headers=_auth_header(token),
            )

        with app.app_context():
            d1 = _db.session.get(Draft, draft_ids[0])
            d2 = _db.session.get(Draft, draft_ids[1])
            assert d1.status == DraftStatus.DRAFT
            assert d2.status == DraftStatus.DRAFT

            stock_no_batch = Stock.query.filter_by(article_id=app_data["art_no_batch"].id).first()
            stock_batch = Stock.query.filter_by(article_id=app_data["art_with_batch"].id).first()
            assert stock_no_batch.quantity == Decimal("10.0")
            assert stock_batch.quantity == Decimal("10.0")
            assert Transaction.query.count() == 0

    def test_reject_single_row_with_reason(self, client, app, app_data):
        """8. Reject single row with reason."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 10.0, "surplus": 0.0, "uom": "akg"}
        ])
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 4.0, "uom": "akg"}
        ])

        token = _login(client, "appr_admin")
        line_id = _get_line_id(
            client, token, group_id, app_data["art_no_batch"].id, None
        )
        resp = client.post(
            f"/api/v1/approvals/{group_id}/lines/{line_id}/reject",
            json={"reason": "Incorrect quantity"},
            headers=_auth_header(token)
        )
        assert resp.status_code == 200

        with app.app_context():
            st = Stock.query.filter_by(article_id=app_data["art_no_batch"].id).first()
            assert st.quantity == Decimal("10.0")  # unchanged
            assert len(Transaction.query.all()) == 0
            d = _db.session.get(Draft, draft_ids[0])
            assert d.status == DraftStatus.REJECTED
            acts = ApprovalAction.query.filter_by(draft_id=d.id, action=ApprovalActionType.REJECTED).all()
            assert len(acts) == 1
            assert acts[0].note == "Incorrect quantity"
            group = _db.session.get(DraftGroup, group_id)
            assert group.status == DraftGroupStatus.REJECTED

    def test_reject_without_reason(self, client, app, app_data):
        """9. Reject without reason now returns 200 (reason is optional)."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 10.0, "surplus": 0.0, "uom": "akg"}
        ])
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 4.0, "uom": "akg"}
        ])

        token = _login(client, "appr_admin")
        line_id = _get_line_id(
            client, token, group_id, app_data["art_no_batch"].id, None
        )
        resp = client.post(
            f"/api/v1/approvals/{group_id}/lines/{line_id}/reject",
            json={},
            headers=_auth_header(token)
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "REJECTED"
        assert resp.get_json()["reason"] is None

        with app.app_context():
            d = _db.session.get(Draft, draft_ids[0])
            assert d.status == DraftStatus.REJECTED
            action = ApprovalAction.query.filter_by(draft_id=draft_ids[0]).first()
            assert action is not None
            assert action.note is None

    def test_reject_entire_draft(self, client, app, app_data):
        """10. Reject entire draft."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 10.0, "surplus": 0.0, "uom": "akg"}
        ])
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 4.0, "uom": "akg"},
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 2.0, "uom": "akg"}
        ])

        token = _login(client, "appr_admin")
        resp = client.post(
            f"/api/v1/approvals/{group_id}/reject",
            json={"reason": "Duplicated entire draft by mistake"},
            headers=_auth_header(token)
        )
        assert resp.status_code == 200

        with app.app_context():
            d1 = _db.session.get(Draft, draft_ids[0])
            d2 = _db.session.get(Draft, draft_ids[1])
            assert d1.status == DraftStatus.REJECTED
            assert d2.status == DraftStatus.REJECTED
            st = Stock.query.filter_by(article_id=app_data["art_no_batch"].id).first()
            assert st.quantity == Decimal("10.0")

    def test_approve_already_approved_row(self, client, app, app_data):
        """11. Approve already-approved row returns 409."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 10.0, "surplus": 0.0, "uom": "akg"}
        ])
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 4.0, "uom": "akg", "status": DraftStatus.APPROVED}
        ])
        
        token = _login(client, "appr_admin")
        line_id = draft_ids[0]
        resp = client.post(
            f"/api/v1/approvals/{group_id}/lines/{line_id}/approve",
            headers=_auth_header(token)
        )
        assert resp.status_code == 409

    def test_manager_access_forbidden(self, client, app, app_data):
        """12. Manager access returns 403 on approval endpoints."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 10.0, "surplus": 0.0, "uom": "akg"}
        ])
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 4.0, "uom": "akg"}
        ])

        admin_token = _login(client, "appr_admin")
        line_id = _get_line_id(
            client, admin_token, group_id, app_data["art_no_batch"].id, None
        )
        token = _login(client, "appr_manager")
        resp = client.post(
            f"/api/v1/approvals/{group_id}/lines/{line_id}/approve",
            headers=_auth_header(token)
        )
        assert resp.status_code == 403

    def test_transaction_sign_correctness(self, client, app, app_data):
        """13. Transaction sign correctness: outbound consumption rows must be negative."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 10.0, "surplus": 0.0, "uom": "akg"}
        ])
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 3.0, "uom": "akg"}
        ])

        token = _login(client, "appr_admin")
        line_id = _get_line_id(
            client, token, group_id, app_data["art_no_batch"].id, None
        )
        resp = client.post(
            f"/api/v1/approvals/{group_id}/lines/{line_id}/approve",
            headers=_auth_header(token),
        )
        assert resp.status_code == 200

        with app.app_context():
            txs = Transaction.query.filter_by(article_id=app_data["art_no_batch"].id).all()
            assert len(txs) > 0
            for tx in txs:
                assert tx.quantity < 0

    def test_no_duplicate_accounting(self, client, app, app_data):
        """14. No duplicate accounting: approval must not create extra summary transaction."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 10.0, "surplus": 0.0, "uom": "akg"}
        ])
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 2.5, "uom": "akg"},
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 1.5, "uom": "akg"}
        ])

        token = _login(client, "appr_admin")
        line_id = _get_line_id(
            client, token, group_id, app_data["art_no_batch"].id, None
        )
        resp = client.post(
            f"/api/v1/approvals/{group_id}/lines/{line_id}/approve",
            headers=_auth_header(token),
        )
        assert resp.status_code == 200

        with app.app_context():
            # Should only be the exact consumption transaction(s), e.g. one for each draft component, or 1 aggregated if the backend sums before inserting.
            # EITHER way, the total transaction delta must equal -4.0.
            txs = Transaction.query.all()
            total_delta = sum(tx.quantity for tx in txs)
            assert total_delta == Decimal("-4.0")

    def test_computed_group_status(self, client, app, app_data):
        """15. Computed group status: mixed approved/rejected surfaces as PARTIAL."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 10.0, "surplus": 0.0, "uom": "akg"},
            {"article_id": app_data["art_with_batch"].id, "batch_id": app_data["b1"].id, "stock": 10.0, "surplus": 0.0, "uom": "akg"}
        ])
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 2.0, "uom": "akg"},
            {"article_id": app_data["art_with_batch"].id, "batch_id": app_data["b1"].id, "quantity": 2.0, "uom": "akg"}
        ])

        token = _login(client, "appr_admin")
        
        # Approve one
        no_batch_line_id = _get_line_id(
            client, token, group_id, app_data["art_no_batch"].id, None
        )
        appr_resp = client.post(
            f"/api/v1/approvals/{group_id}/lines/{no_batch_line_id}/approve",
            headers=_auth_header(token),
        )
        assert appr_resp.status_code == 200

        batch_line_id = _get_line_id(
            client, token, group_id, app_data["art_with_batch"].id, app_data["b1"].id
        )
        reject_resp = client.post(
            f"/api/v1/approvals/{group_id}/lines/{batch_line_id}/reject",
            json={"reason": "no"},
            headers=_auth_header(token),
        )
        assert reject_resp.status_code == 200
        
        history_resp = client.get("/api/v1/approvals?status=history", headers=_auth_header(token))
        assert history_resp.status_code == 200
        items = history_resp.get_json().get("items", [])
        
        me = [item for item in items if item.get("draft_group_id") == group_id]
        assert me
        assert me[0]["status"] == "PARTIAL"


class TestRejectionReasonVisibility:
    """Wave 1 Phase 5: optional rejection reason + metadata exposure."""

    def test_reject_whole_draft_without_reason_returns_200(self, client, app, app_data):
        """Reject entire draft with no reason body -> 200, reason null."""
        group_id, _ = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 2.0, "uom": "akg"}
        ])
        token = _login(client, "appr_admin")
        resp = client.post(
            f"/api/v1/approvals/{group_id}/reject",
            json={},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "REJECTED"
        assert body["reason"] is None

    def test_reject_whole_draft_with_whitespace_reason_treated_as_none(self, client, app, app_data):
        """Whitespace-only reason normalizes to null, not a 400."""
        group_id, _ = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 1.0, "uom": "akg"}
        ])
        token = _login(client, "appr_admin")
        resp = client.post(
            f"/api/v1/approvals/{group_id}/reject",
            json={"reason": "   "},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["reason"] is None

    def test_reject_line_with_reason_persists_and_surfaces_in_detail(self, client, app, app_data):
        """Reject line with reason -> reason appears in GET detail rows and entries."""
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 3.0, "uom": "akg"}
        ])
        token = _login(client, "appr_admin")
        line_id = _get_line_id(client, token, group_id, app_data["art_no_batch"].id, None)
        reason_text = "Quantity appears incorrect — please re-enter."
        resp = client.post(
            f"/api/v1/approvals/{group_id}/lines/{line_id}/reject",
            json={"reason": reason_text},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200

        detail = _get_detail(client, token, group_id)
        row = next(r for r in detail["rows"] if r["article_id"] == app_data["art_no_batch"].id)
        assert row["rejection_reason"] == reason_text
        assert row["status"] == "REJECTED"
        entry = next(e for e in row["entries"] if e["id"] == draft_ids[0])
        assert entry["rejection_reason"] == reason_text

    def test_reject_line_without_reason_rejection_reason_is_null_in_detail(self, client, app, app_data):
        """Reject line without reason -> rejection_reason is null in detail, not omitted."""
        group_id, draft_ids = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 1.5, "uom": "akg"}
        ])
        token = _login(client, "appr_admin")
        line_id = _get_line_id(client, token, group_id, app_data["art_no_batch"].id, None)
        resp = client.post(
            f"/api/v1/approvals/{group_id}/lines/{line_id}/reject",
            json={},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200

        detail = _get_detail(client, token, group_id)
        row = next(r for r in detail["rows"] if r["article_id"] == app_data["art_no_batch"].id)
        assert "rejection_reason" in row
        assert row["rejection_reason"] is None
        entry = next(e for e in row["entries"] if e["id"] == draft_ids[0])
        assert "rejection_reason" in entry
        assert entry["rejection_reason"] is None

    def test_approved_row_has_null_rejection_reason(self, client, app, app_data):
        """Approved rows expose rejection_reason: null (field present, value null)."""
        _insert_balances(app, app_data["loc"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "stock": 10.0, "surplus": 0.0, "uom": "akg"}
        ])
        group_id, _ = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 2.0, "uom": "akg"}
        ])
        token = _login(client, "appr_admin")
        line_id = _get_line_id(client, token, group_id, app_data["art_no_batch"].id, None)
        client.post(
            f"/api/v1/approvals/{group_id}/lines/{line_id}/approve",
            headers=_auth_header(token),
        )
        detail = _get_detail(client, token, group_id)
        row = next(r for r in detail["rows"] if r["article_id"] == app_data["art_no_batch"].id)
        assert "rejection_reason" in row
        assert row["rejection_reason"] is None

    def test_reject_reason_max_length_validation_still_enforced(self, client, app, app_data):
        """Non-empty reasons exceeding 500 chars still return 400."""
        group_id, _ = _create_drafts(app, app_data["loc"].id, app_data["operator"].id, [
            {"article_id": app_data["art_no_batch"].id, "batch_id": None, "quantity": 1.0, "uom": "akg"}
        ])
        token = _login(client, "appr_admin")
        line_id = _get_line_id(client, token, group_id, app_data["art_no_batch"].id, None)
        resp = client.post(
            f"/api/v1/approvals/{group_id}/lines/{line_id}/reject",
            json={"reason": "x" * 501},
            headers=_auth_header(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "VALIDATION_ERROR"
