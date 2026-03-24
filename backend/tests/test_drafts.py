"""Integration tests for Draft Entry and Article lookup endpoints.

Uses the session-scoped in-memory SQLite setup from conftest.py.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db as _db
from app.models.article import Article
from app.models.batch import Batch
from app.models.category import Category
from app.models.draft import Draft
from app.models.draft_group import DraftGroup
from app.models.approval_action import ApprovalAction
from app.models.enums import (
    ApprovalActionType,
    DraftGroupStatus,
    DraftGroupType,
    DraftSource,
    DraftStatus,
    DraftType,
    UserRole,
)
from app.models.location import Location
from app.models.uom_catalog import UomCatalog
from app.models.user import User


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def draft_data(app):
    """Seed the minimum data required by draft / article tests.

    Runs once per module so that all tests share the same baseline.
    """
    with app.app_context():
        # --- location (required for operational-date logic) ----------------
        loc = _db.session.get(Location, 1)
        if loc is None:
            loc = Location(id=1, name="Test Warehouse", timezone="UTC", is_active=True)
            _db.session.add(loc)

        # --- UOM -----------------------------------------------------------
        uom = UomCatalog.query.filter_by(code="tkg").first()
        if uom is None:
            uom = UomCatalog(
                code="tkg",
                label_hr="test-kilogram",
                label_en="test-kilogram",
                decimal_display=True,
            )
            _db.session.add(uom)
            _db.session.flush()

        # --- category ------------------------------------------------------
        cat = Category.query.filter_by(key="draft_test_cat").first()
        if cat is None:
            cat = Category(key="draft_test_cat", label_hr="Test kategorija", label_en="Test Category", is_active=True)
            _db.session.add(cat)
            _db.session.flush()

        # --- articles ------------------------------------------------------
        art = Article.query.filter_by(article_no="TEST-001").first()
        if art is None:
            art = Article(
                article_no="TEST-001",
                description="Test Article No Batch",
                category_id=cat.id,
                base_uom=uom.id,
                has_batch=False,
                barcode="9999999999",
                is_active=True,
            )
            _db.session.add(art)

        art_batch = Article.query.filter_by(article_no="TEST-002").first()
        if art_batch is None:
            art_batch = Article(
                article_no="TEST-002",
                description="Test Article With Batch",
                category_id=cat.id,
                base_uom=uom.id,
                has_batch=True,
                is_active=True,
            )
            _db.session.add(art_batch)
            _db.session.flush()

            # two batches — expiry order matters for FEFO
            b1 = Batch(article_id=art_batch.id, batch_code="12345", expiry_date=date(2026, 6, 1))
            b2 = Batch(article_id=art_batch.id, batch_code="54321", expiry_date=date(2026, 3, 1))
            _db.session.add_all([b1, b2])

        # --- users ---------------------------------------------------------
        operator = User.query.filter_by(username="draft_operator").first()
        if operator is None:
            operator = User(
                username="draft_operator",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.OPERATOR,
                is_active=True,
            )
            _db.session.add(operator)

        admin = User.query.filter_by(username="draft_admin").first()
        if admin is None:
            admin = User(
                username="draft_admin",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            _db.session.add(admin)

        manager = User.query.filter_by(username="draft_manager").first()
        if manager is None:
            manager = User(
                username="draft_manager",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.MANAGER,
                is_active=True,
            )
            _db.session.add(manager)

        _db.session.commit()

        yield {
            "operator": operator,
            "admin": admin,
            "manager": manager,
            "article": art,
            "article_batch": art_batch,
            "uom": uom,
        }


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


# ==========================================================================
# Article lookup tests
# ==========================================================================


class TestArticleLookup:
    """GET /api/v1/articles?q=..."""

    def test_lookup_by_article_no(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.get(
            "/api/v1/articles?q=test-001",
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["article_no"] == "TEST-001"
        assert data["has_batch"] is False
        assert "batches" not in data

    def test_lookup_by_barcode(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.get(
            "/api/v1/articles?q=9999999999",
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["article_no"] == "TEST-001"

    def test_lookup_not_found(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.get(
            "/api/v1/articles?q=NONEXIST",
            headers=_auth_header(token),
        )
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "ARTICLE_NOT_FOUND"

    def test_lookup_batch_article_fefo(self, client, draft_data):
        """Batch-tracked article returns batches ordered by expiry ASC."""
        token = _login(client, "draft_operator")
        resp = client.get(
            "/api/v1/articles?q=TEST-002",
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["has_batch"] is True
        batches = data["batches"]
        assert len(batches) == 2
        # FEFO: earliest expiry first
        assert batches[0]["expiry_date"] < batches[1]["expiry_date"]

    def test_lookup_missing_query(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.get("/api/v1/articles", headers=_auth_header(token))
        assert resp.status_code == 400

    def test_lookup_rbac_manager_forbidden(self, client, draft_data):
        token = _login(client, "draft_manager")
        resp = client.get(
            "/api/v1/articles?q=TEST-001",
            headers=_auth_header(token),
        )
        assert resp.status_code == 403


# ==========================================================================
# Drafts GET tests
# ==========================================================================


class TestGetDrafts:
    """GET /api/v1/drafts?date=today"""

    def test_empty_day(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.get("/api/v1/drafts?date=today", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data["items"], list)

    def test_get_todays_drafts(self, client, draft_data):
        token = _login(client, "draft_operator")
        eid = str(uuid.uuid4())
        create_resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 2.5,
                "uom": draft_data["uom"].code,
                "draft_note": "Dnevna napomena",
                "source": "manual",
                "client_event_id": eid,
            },
            headers=_auth_header(token),
        )
        created_id = create_resp.get_json()["id"]

        resp = client.get("/api/v1/drafts?date=today", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["items"]) >= 1
        assert any(item["id"] == created_id for item in data["items"])
        assert data["draft_group"]["draft_note"] == "Dnevna napomena"

    def test_rbac_unauthenticated(self, client, draft_data):
        resp = client.get("/api/v1/drafts?date=today")
        assert resp.status_code == 401


# ==========================================================================
# Drafts POST tests
# ==========================================================================


class TestCreateDraft:
    """POST /api/v1/drafts"""

    def test_create_line_no_batch(self, client, draft_data):
        token = _login(client, "draft_operator")
        eid = str(uuid.uuid4())
        resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 5.5,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": eid,
            },
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["article_no"] == "TEST-001"
        assert body["status"] == "DRAFT"
        assert float(body["quantity"]) == 5.5
        assert body["created_by"] == "draft_operator"
        assert "note" not in body

    def test_idempotency(self, client, draft_data):
        """Same client_event_id returns existing record with 200."""
        token = _login(client, "draft_operator")
        eid = str(uuid.uuid4())
        payload = {
            "article_id": draft_data["article"].id,
            "quantity": 1.0,
            "uom": draft_data["uom"].code,
            "source": "manual",
            "client_event_id": eid,
        }
        resp1 = client.post("/api/v1/drafts", json=payload, headers=_auth_header(token))
        assert resp1.status_code == 201

        resp2 = client.post("/api/v1/drafts", json=payload, headers=_auth_header(token))
        assert resp2.status_code == 200
        assert resp2.get_json()["id"] == resp1.get_json()["id"]

    def test_zero_quantity_rejected(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 0,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": str(uuid.uuid4()),
            },
            headers=_auth_header(token),
        )
        assert resp.status_code == 400

    def test_negative_quantity_rejected(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": -3,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": str(uuid.uuid4()),
            },
            headers=_auth_header(token),
        )
        assert resp.status_code == 400

    def test_missing_article(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": 99999,
                "quantity": 1,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": str(uuid.uuid4()),
            },
            headers=_auth_header(token),
        )
        assert resp.status_code == 404

    def test_mismatched_uom_rejected(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 1,
                "uom": "kom",
                "source": "manual",
                "client_event_id": str(uuid.uuid4()),
            },
            headers=_auth_header(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["details"]["expected_uom"] == draft_data["uom"].code

    def test_create_line_persists_shared_draft_note(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 1.25,
                "uom": draft_data["uom"].code,
                "draft_note": "Napomena za cijeli draft",
                "source": "manual",
                "client_event_id": str(uuid.uuid4()),
            },
            headers=_auth_header(token),
        )
        assert resp.status_code == 201

        drafts_resp = client.get("/api/v1/drafts?date=today", headers=_auth_header(token))
        assert drafts_resp.status_code == 200
        assert drafts_resp.get_json()["draft_group"]["draft_note"] == "Napomena za cijeli draft"

    def test_batch_required_for_batch_article(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article_batch"].id,
                "quantity": 2,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": str(uuid.uuid4()),
            },
            headers=_auth_header(token),
        )
        assert resp.status_code == 400
        assert "batch_id" in resp.get_json()["message"].lower()

    def test_create_with_batch(self, client, draft_data, app):
        token = _login(client, "draft_operator")
        with app.app_context():
            batch = Batch.query.filter_by(article_id=draft_data["article_batch"].id).first()
        resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article_batch"].id,
                "batch_id": batch.id,
                "quantity": 3.0,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": str(uuid.uuid4()),
            },
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        assert resp.get_json()["batch_code"] is not None

    def test_rbac_manager_forbidden(self, client, draft_data):
        token = _login(client, "draft_manager")
        resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 1,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": str(uuid.uuid4()),
            },
            headers=_auth_header(token),
        )
        assert resp.status_code == 403

    def test_retries_after_transient_draft_group_integrity_error(
        self,
        client,
        draft_data,
        app,
        monkeypatch,
    ):
        from app.api.drafts import routes as draft_routes

        with app.app_context():
            Draft.query.delete()
            DraftGroup.query.delete()
            _db.session.commit()

        token = _login(client, "draft_operator")
        original_flush = draft_routes.db.session.flush
        state = {"calls": 0}

        def flaky_flush(*args, **kwargs):
            state["calls"] += 1
            if state["calls"] == 1:
                raise IntegrityError("INSERT", {}, Exception("transient group conflict"))
            return original_flush(*args, **kwargs)

        monkeypatch.setattr(draft_routes.db.session, "flush", flaky_flush)

        resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 4,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": str(uuid.uuid4()),
            },
            headers=_auth_header(token),
        )

        assert resp.status_code == 201
        assert state["calls"] >= 2

    def test_group_number_uses_max_existing_suffix_not_id(self, client, draft_data, app):
        with app.app_context():
            Draft.query.delete()
            DraftGroup.query.delete()
            _db.session.commit()

            legacy_group = DraftGroup(
                id=47,
                group_number="IZL-0001",
                status=DraftGroupStatus.PENDING,
                operational_date=date(2026, 1, 1),
                created_by=draft_data["operator"].id,
            )
            _db.session.add(legacy_group)
            _db.session.commit()

        token = _login(client, "draft_operator")
        resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 1,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": str(uuid.uuid4()),
            },
            headers=_auth_header(token),
        )

        assert resp.status_code == 201

        with app.app_context():
            today_group = (
                DraftGroup.query
                .filter(DraftGroup.operational_date != date(2026, 1, 1))
                .order_by(DraftGroup.id.desc())
                .first()
            )
            assert today_group is not None
            assert today_group.group_number == "IZL-0002"

    def test_closed_same_day_group_is_not_reused_for_new_daily_outbound(
        self,
        client,
        draft_data,
        app,
    ):
        with app.app_context():
            Draft.query.delete()
            DraftGroup.query.delete()
            _db.session.commit()

            closed_group = DraftGroup(
                group_number="IZL-0900",
                status=DraftGroupStatus.APPROVED,
                group_type=DraftGroupType.DAILY_OUTBOUND,
                operational_date=date.today(),
                created_by=draft_data["operator"].id,
                description="Već zatvoreno",
            )
            _db.session.add(closed_group)
            _db.session.commit()
            closed_group_id = closed_group.id

        token = _login(client, "draft_operator")
        resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 2,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": str(uuid.uuid4()),
            },
            headers=_auth_header(token),
        )

        assert resp.status_code == 201

        with app.app_context():
            created = _db.session.get(Draft, resp.get_json()["id"])
            new_group = _db.session.get(DraftGroup, created.draft_group_id)
            assert new_group is not None
            assert new_group.id != closed_group_id
            assert new_group.status == DraftGroupStatus.PENDING
            assert new_group.group_type == DraftGroupType.DAILY_OUTBOUND

    def test_only_one_pending_daily_outbound_group_per_operational_date(
        self,
        draft_data,
        app,
    ):
        with app.app_context():
            Draft.query.delete()
            DraftGroup.query.delete()
            _db.session.commit()

            first_group = DraftGroup(
                group_number="IZL-1000",
                status=DraftGroupStatus.PENDING,
                group_type=DraftGroupType.DAILY_OUTBOUND,
                operational_date=date.today(),
                created_by=draft_data["operator"].id,
            )
            second_group = DraftGroup(
                group_number="IZL-1001",
                status=DraftGroupStatus.PENDING,
                group_type=DraftGroupType.DAILY_OUTBOUND,
                operational_date=date.today(),
                created_by=draft_data["operator"].id,
            )
            _db.session.add(first_group)
            _db.session.commit()

            _db.session.add(second_group)
            with pytest.raises(IntegrityError):
                _db.session.commit()
            _db.session.rollback()

    def test_pending_inventory_shortage_group_can_coexist_same_day(
        self,
        draft_data,
        app,
    ):
        with app.app_context():
            Draft.query.delete()
            DraftGroup.query.delete()
            _db.session.commit()

            outbound_group = DraftGroup(
                group_number="IZL-1100",
                status=DraftGroupStatus.PENDING,
                group_type=DraftGroupType.DAILY_OUTBOUND,
                operational_date=date.today(),
                created_by=draft_data["operator"].id,
            )
            shortage_group = DraftGroup(
                group_number="IZL-1101",
                status=DraftGroupStatus.PENDING,
                group_type=DraftGroupType.INVENTORY_SHORTAGE,
                operational_date=date.today(),
                created_by=draft_data["operator"].id,
            )
            _db.session.add_all([outbound_group, shortage_group])
            _db.session.commit()

            same_day_groups = (
                DraftGroup.query
                .filter_by(operational_date=date.today(), status=DraftGroupStatus.PENDING)
                .order_by(DraftGroup.id.asc())
                .all()
            )
            assert len(same_day_groups) == 2
            assert {group.group_type for group in same_day_groups} == {
                DraftGroupType.DAILY_OUTBOUND,
                DraftGroupType.INVENTORY_SHORTAGE,
            }


# ==========================================================================
# DraftGroup note tests
# ==========================================================================


class TestDraftGroupNote:
    """PATCH /api/v1/drafts/group"""

    def test_update_today_draft_note(self, client, draft_data):
        token = _login(client, "draft_operator")
        create_resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 2,
                "uom": draft_data["uom"].code,
                "draft_note": "Početna napomena",
                "source": "manual",
                "client_event_id": str(uuid.uuid4()),
            },
            headers=_auth_header(token),
        )
        assert create_resp.status_code == 201

        update_resp = client.patch(
            "/api/v1/drafts/group",
            json={"draft_note": "Ažurirana napomena"},
            headers=_auth_header(token),
        )
        assert update_resp.status_code == 200
        assert update_resp.get_json()["draft_note"] == "Ažurirana napomena"

    def test_update_today_draft_note_requires_field(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.patch(
            "/api/v1/drafts/group",
            json={},
            headers=_auth_header(token),
        )
        assert resp.status_code == 400

    def test_manager_cannot_update_today_draft_note(self, client, draft_data):
        token = _login(client, "draft_manager")
        resp = client.patch(
            "/api/v1/drafts/group",
            json={"draft_note": "Ne smije"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 403


# ==========================================================================
# Drafts PATCH tests
# ==========================================================================


class TestUpdateDraft:
    """PATCH /api/v1/drafts/{id}"""

    def test_update_quantity(self, client, draft_data):
        token = _login(client, "draft_operator")
        # create a line first
        eid = str(uuid.uuid4())
        create = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 1.0,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": eid,
            },
            headers=_auth_header(token),
        )
        draft_id = create.get_json()["id"]

        resp = client.patch(
            f"/api/v1/drafts/{draft_id}",
            json={"quantity": 7.75},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        assert float(resp.get_json()["quantity"]) == 7.75

    def test_update_approved_line_fails(self, client, draft_data, app):
        """Cannot edit a line whose status is not DRAFT."""
        token = _login(client, "draft_operator")
        eid = str(uuid.uuid4())
        create = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 1,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": eid,
            },
            headers=_auth_header(token),
        )
        draft_id = create.get_json()["id"]

        # Manually set status to APPROVED
        with app.app_context():
            d = _db.session.get(Draft, draft_id)
            d.status = DraftStatus.APPROVED
            _db.session.commit()

        resp = client.patch(
            f"/api/v1/drafts/{draft_id}",
            json={"quantity": 10},
            headers=_auth_header(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "INVALID_STATUS"

    def test_update_not_found(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.patch(
            "/api/v1/drafts/99999",
            json={"quantity": 1},
            headers=_auth_header(token),
        )
        assert resp.status_code == 404


# ==========================================================================
# Drafts DELETE tests
# ==========================================================================


class TestDeleteDraft:
    """DELETE /api/v1/drafts/{id}"""

    def test_delete_draft_line(self, client, draft_data):
        token = _login(client, "draft_operator")
        eid = str(uuid.uuid4())
        create = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 1,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": eid,
            },
            headers=_auth_header(token),
        )
        draft_id = create.get_json()["id"]

        resp = client.delete(
            f"/api/v1/drafts/{draft_id}",
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        assert "deleted" in resp.get_json()["message"].lower()

    def test_delete_approved_fails(self, client, draft_data, app):
        token = _login(client, "draft_operator")
        eid = str(uuid.uuid4())
        create = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 1,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": eid,
            },
            headers=_auth_header(token),
        )
        draft_id = create.get_json()["id"]

        with app.app_context():
            d = _db.session.get(Draft, draft_id)
            d.status = DraftStatus.APPROVED
            _db.session.commit()

        resp = client.delete(
            f"/api/v1/drafts/{draft_id}",
            headers=_auth_header(token),
        )
        assert resp.status_code == 400

    def test_delete_not_found(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.delete(
            "/api/v1/drafts/99999",
            headers=_auth_header(token),
        )
        assert resp.status_code == 404


# ==========================================================================
# Wave 1 Phase 5: same_day_lines + rejection_reason on draft lines
# ==========================================================================


class TestSameDayLinesAndRejectionReason:
    """
    GET /api/v1/drafts?date=today must include:
    - same_day_lines: all DAILY_OUTBOUND draft lines for the operational day
      (pending + resolved), newest first, INVENTORY_SHORTAGE excluded.
    - rejection_reason on each serialised line (null unless the line is REJECTED
      and has a note).
    """

    def test_get_drafts_response_includes_same_day_lines_key(self, client, draft_data):
        token = _login(client, "draft_operator")
        resp = client.get("/api/v1/drafts?date=today", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert "same_day_lines" in data
        assert isinstance(data["same_day_lines"], list)

    def test_draft_line_serialization_includes_rejection_reason_null(self, client, draft_data):
        """A freshly created DRAFT line has rejection_reason: null."""
        token = _login(client, "draft_operator")
        eid = str(uuid.uuid4())
        create_resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 1.0,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": eid,
            },
            headers=_auth_header(token),
        )
        assert create_resp.status_code == 201
        body = create_resp.get_json()
        assert "rejection_reason" in body
        assert body["rejection_reason"] is None

    def test_same_day_lines_includes_resolved_group_lines(self, client, draft_data, app):
        """Lines from a same-day APPROVED DAILY_OUTBOUND group appear in same_day_lines."""
        token = _login(client, "draft_operator")

        with app.app_context():
            Draft.query.delete()
            DraftGroup.query.delete()
            _db.session.commit()

            closed_group = DraftGroup(
                group_number="IZL-SDL-001",
                status=DraftGroupStatus.APPROVED,
                group_type=DraftGroupType.DAILY_OUTBOUND,
                operational_date=date.today(),
                created_by=draft_data["operator"].id,
            )
            _db.session.add(closed_group)
            _db.session.flush()

            resolved_draft = Draft(
                draft_group_id=closed_group.id,
                location_id=1,
                article_id=draft_data["article"].id,
                batch_id=None,
                quantity=5.0,
                uom=draft_data["uom"].code,
                status=DraftStatus.APPROVED,
                draft_type=DraftType.OUTBOUND,
                source=DraftSource.manual,
                client_event_id=str(uuid.uuid4()),
                created_by=draft_data["operator"].id,
            )
            _db.session.add(resolved_draft)
            _db.session.commit()
            resolved_draft_id = resolved_draft.id

        resp = client.get("/api/v1/drafts?date=today", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()

        # items should be empty (no pending group)
        assert data["draft_group"] is None
        # same_day_lines should contain the resolved draft
        same_day_ids = [line["id"] for line in data["same_day_lines"]]
        assert resolved_draft_id in same_day_ids

    def test_same_day_lines_excludes_inventory_shortage_groups(self, client, draft_data, app):
        """Lines from INVENTORY_SHORTAGE groups are NOT in same_day_lines."""
        token = _login(client, "draft_operator")

        with app.app_context():
            Draft.query.delete()
            DraftGroup.query.delete()
            _db.session.commit()

            shortage_group = DraftGroup(
                group_number="IZL-SRTG-001",
                status=DraftGroupStatus.PENDING,
                group_type=DraftGroupType.INVENTORY_SHORTAGE,
                operational_date=date.today(),
                created_by=draft_data["operator"].id,
            )
            _db.session.add(shortage_group)
            _db.session.flush()

            shortage_draft = Draft(
                draft_group_id=shortage_group.id,
                location_id=1,
                article_id=draft_data["article"].id,
                batch_id=None,
                quantity=3.0,
                uom=draft_data["uom"].code,
                status=DraftStatus.DRAFT,
                draft_type=DraftType.OUTBOUND,
                source=DraftSource.manual,
                client_event_id=str(uuid.uuid4()),
                created_by=draft_data["operator"].id,
            )
            _db.session.add(shortage_draft)
            _db.session.commit()
            shortage_draft_id = shortage_draft.id

        resp = client.get("/api/v1/drafts?date=today", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()

        same_day_ids = [line["id"] for line in data["same_day_lines"]]
        assert shortage_draft_id not in same_day_ids

    def test_same_day_lines_includes_both_pending_and_resolved_groups(self, client, draft_data, app):
        """same_day_lines spans multiple same-day groups (closed + pending)."""
        token = _login(client, "draft_operator")

        with app.app_context():
            Draft.query.delete()
            DraftGroup.query.delete()
            _db.session.commit()

            closed_group = DraftGroup(
                group_number="IZL-MULTI-001",
                status=DraftGroupStatus.REJECTED,
                group_type=DraftGroupType.DAILY_OUTBOUND,
                operational_date=date.today(),
                created_by=draft_data["operator"].id,
            )
            _db.session.add(closed_group)
            _db.session.flush()

            closed_draft = Draft(
                draft_group_id=closed_group.id,
                location_id=1,
                article_id=draft_data["article"].id,
                batch_id=None,
                quantity=2.0,
                uom=draft_data["uom"].code,
                status=DraftStatus.REJECTED,
                draft_type=DraftType.OUTBOUND,
                source=DraftSource.manual,
                client_event_id=str(uuid.uuid4()),
                created_by=draft_data["operator"].id,
            )
            _db.session.add(closed_draft)
            _db.session.commit()
            closed_draft_id = closed_draft.id

        # Create new line via the API (creates new pending group)
        new_eid = str(uuid.uuid4())
        new_resp = client.post(
            "/api/v1/drafts",
            json={
                "article_id": draft_data["article"].id,
                "quantity": 1.0,
                "uom": draft_data["uom"].code,
                "source": "manual",
                "client_event_id": new_eid,
            },
            headers=_auth_header(token),
        )
        assert new_resp.status_code == 201
        new_draft_id = new_resp.get_json()["id"]

        resp = client.get("/api/v1/drafts?date=today", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()

        same_day_ids = [line["id"] for line in data["same_day_lines"]]
        assert closed_draft_id in same_day_ids
        assert new_draft_id in same_day_ids
        # items should only contain the pending group line
        item_ids = [item["id"] for item in data["items"]]
        assert new_draft_id in item_ids
        assert closed_draft_id not in item_ids

    def test_rejected_line_serialization_includes_rejection_reason_string(self, client, draft_data, app):
        """A REJECTED line returns its rejection reason exactly as saved."""
        token = _login(client, "draft_operator")

        with app.app_context():
            Draft.query.delete()
            DraftGroup.query.delete()
            ApprovalAction.query.delete()
            _db.session.commit()

            group = DraftGroup(
                group_number="IZL-REJ-001",
                status=DraftGroupStatus.PENDING,
                group_type=DraftGroupType.DAILY_OUTBOUND,
                operational_date=date.today(),
                created_by=draft_data["operator"].id,
            )
            _db.session.add(group)
            _db.session.flush()

            draft = Draft(
                draft_group_id=group.id,
                location_id=1,
                article_id=draft_data["article"].id,
                batch_id=None,
                quantity=1.0,
                uom=draft_data["uom"].code,
                status=DraftStatus.REJECTED,
                draft_type=DraftType.OUTBOUND,
                source=DraftSource.manual,
                client_event_id=str(uuid.uuid4()),
                created_by=draft_data["operator"].id,
            )
            _db.session.add(draft)
            _db.session.flush()

            action = ApprovalAction(
                draft_id=draft.id,
                actor_id=draft_data["admin"].id,
                action=ApprovalActionType.REJECTED,
                note="Kriva količina, molim provjerite ponovo."
            )
            _db.session.add(action)
            _db.session.commit()

        resp = client.get("/api/v1/drafts?date=today", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()

        same_day_lines = data["same_day_lines"]
        assert len(same_day_lines) == 1
        line = same_day_lines[0]
        assert line["status"] == "REJECTED"
        assert line["rejection_reason"] == "Kriva količina, molim provjerite ponovo."
