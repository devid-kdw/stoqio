"""Integration tests for the Phase 11 Employees module."""

from __future__ import annotations

from datetime import datetime, timezone
from datetime import date as dt_date
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db as _db
from app.models.annual_quota import AnnualQuota
from app.models.article import Article
from app.models.batch import Batch
from app.models.category import Category
from app.models.employee import Employee
from app.models.enums import QuotaEnforcement, TxType, UserRole
from app.models.location import Location
from app.models.personal_issuance import PersonalIssuance
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.models.uom_catalog import UomCatalog
from app.models.user import User


# ---------------------------------------------------------------------------
# Module-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def emp_data(app):
    """Seed employees module fixtures once per module."""
    with app.app_context():
        # Location
        loc = _db.session.get(Location, 1)
        if loc is None:
            loc = Location(id=1, name="Main", timezone="UTC", is_active=True)
            _db.session.add(loc)
            _db.session.flush()

        # UOM
        kom = UomCatalog.query.filter_by(code="emp_kom").first()
        if kom is None:
            kom = UomCatalog(code="emp_kom", label_hr="komad", decimal_display=False)
            _db.session.add(kom)
            _db.session.flush()

        # Category (personal issue)
        cat = Category.query.filter_by(key="emp_ppe").first()
        if cat is None:
            cat = Category(
                key="emp_ppe",
                label_hr="Zaštitna oprema",
                is_personal_issue=True,
                is_active=True,
            )
            _db.session.add(cat)
            _db.session.flush()

        # Category (non-personal issue)
        cat_npi = Category.query.filter_by(key="emp_mat").first()
        if cat_npi is None:
            cat_npi = Category(
                key="emp_mat",
                label_hr="Materijal",
                is_personal_issue=False,
                is_active=True,
            )
            _db.session.add(cat_npi)
            _db.session.flush()

        # Article — no batch
        art = Article.query.filter_by(article_no="EMP-ART-001").first()
        if art is None:
            art = Article(
                article_no="EMP-ART-001",
                description="Zaštitne rukavice",
                category_id=cat.id,
                base_uom=kom.id,
                has_batch=False,
                is_active=True,
            )
            _db.session.add(art)
            _db.session.flush()

        # Article — has_batch
        art_batch = Article.query.filter_by(article_no="EMP-ART-002").first()
        if art_batch is None:
            art_batch = Article(
                article_no="EMP-ART-002",
                description="Zaštitna maska",
                category_id=cat.id,
                base_uom=kom.id,
                has_batch=True,
                is_active=True,
            )
            _db.session.add(art_batch)
            _db.session.flush()

        # Article — non-personal-issue category
        art_npi = Article.query.filter_by(article_no="EMP-ART-NPI").first()
        if art_npi is None:
            art_npi = Article(
                article_no="EMP-ART-NPI",
                description="Non-personal article",
                category_id=cat_npi.id,
                base_uom=kom.id,
                has_batch=False,
                is_active=True,
            )
            _db.session.add(art_npi)
            _db.session.flush()

        # Batch for art_batch
        batch = Batch.query.filter_by(batch_code="EMP-B001").first()
        if batch is None:
            from datetime import date
            batch = Batch(
                article_id=art_batch.id,
                batch_code="EMP-B001",
                expiry_date=date(2027, 12, 31),
            )
            _db.session.add(batch)
            _db.session.flush()

        # Stock for art (no batch)
        stock_nb = Stock.query.filter_by(article_id=art.id, batch_id=None).first()
        if stock_nb is None:
            stock_nb = Stock(
                location_id=loc.id,
                article_id=art.id,
                batch_id=None,
                quantity=Decimal("100"),
                uom="emp_kom",
                average_price=Decimal("5.00"),
            )
            _db.session.add(stock_nb)
            _db.session.flush()

        # Stock for art_batch
        stock_b = Stock.query.filter_by(article_id=art_batch.id, batch_id=batch.id).first()
        if stock_b is None:
            stock_b = Stock(
                location_id=loc.id,
                article_id=art_batch.id,
                batch_id=batch.id,
                quantity=Decimal("50"),
                uom="emp_kom",
                average_price=Decimal("10.00"),
            )
            _db.session.add(stock_b)
            _db.session.flush()

        # Users
        admin = User.query.filter_by(username="emp_admin").first()
        if admin is None:
            admin = User(
                username="emp_admin",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            _db.session.add(admin)

        wstaff = User.query.filter_by(username="emp_wstaff").first()
        if wstaff is None:
            wstaff = User(
                username="emp_wstaff",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.WAREHOUSE_STAFF,
                is_active=True,
            )
            _db.session.add(wstaff)

        manager = User.query.filter_by(username="emp_manager").first()
        if manager is None:
            manager = User(
                username="emp_manager",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.MANAGER,
                is_active=True,
            )
            _db.session.add(manager)

        _db.session.commit()

        yield {
            "loc": loc,
            "kom": kom,
            "cat": cat,
            "cat_npi": cat_npi,
            "art": art,
            "art_batch": art_batch,
            "art_npi": art_npi,
            "batch": batch,
            "admin": admin,
            "wstaff": wstaff,
            "manager": manager,
            "stock_nb": stock_nb,
            "stock_b": stock_b,
        }


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

_token_cache: dict[str, str] = {}


def _login(client, username: str, password: str = "pass") -> str:
    if username in _token_cache:
        return _token_cache[username]
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        environ_base={"REMOTE_ADDR": "127.0.11.1"},
    )
    assert resp.status_code == 200, resp.get_json()
    token = resp.get_json()["access_token"]
    _token_cache[username] = token
    return token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_personal_issue_article_with_stock(
    app,
    emp_data,
    *,
    article_no: str,
    description: str,
    quantity: Decimal,
    has_batch: bool = False,
):
    with app.app_context():
        article = Article.query.filter_by(article_no=article_no).first()
        if article is None:
            article = Article(
                article_no=article_no,
                description=description,
                category_id=emp_data["cat"].id,
                base_uom=emp_data["kom"].id,
                has_batch=has_batch,
                is_active=True,
            )
            _db.session.add(article)
            _db.session.flush()

        batch = None
        if has_batch:
            batch = Batch.query.filter_by(batch_code=f"{article_no}-B01").first()
            if batch is None:
                batch = Batch(
                    article_id=article.id,
                    batch_code=f"{article_no}-B01",
                    expiry_date=dt_date(2028, 1, 1),
                )
                _db.session.add(batch)
                _db.session.flush()

        stock = Stock.query.filter_by(
            location_id=emp_data["loc"].id,
            article_id=article.id,
            batch_id=batch.id if batch else None,
        ).first()
        if stock is None:
            stock = Stock(
                location_id=emp_data["loc"].id,
                article_id=article.id,
                batch_id=batch.id if batch else None,
                quantity=quantity,
                uom="emp_kom",
                average_price=Decimal("1.00"),
            )
            _db.session.add(stock)
        else:
            stock.quantity = quantity
            stock.uom = "emp_kom"
        _db.session.commit()

        return {
            "article_id": article.id,
            "batch_id": batch.id if batch else None,
        }


# ---------------------------------------------------------------------------
# Employee CRUD tests
# ---------------------------------------------------------------------------

class TestEmployeeCRUD:
    def test_create_employee_admin(self, client, emp_data):
        token = _login(client, "emp_admin")
        resp = client.post(
            "/api/v1/employees",
            json={
                "employee_id": "EMP-T001",
                "first_name": "Ana",
                "last_name": "Kovač",
                "department": "Lakirnica",
                "job_title": "Operater lakiranja",
                "is_active": True,
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["employee_id"] == "EMP-T001"
        assert data["first_name"] == "Ana"
        assert "id" in data

    def test_create_employee_duplicate_id(self, client, emp_data):
        token = _login(client, "emp_admin")
        payload = {
            "employee_id": "EMP-DUP",
            "first_name": "Ivan",
            "last_name": "Horvat",
        }
        r1 = client.post("/api/v1/employees", json=payload, headers=_auth(token))
        assert r1.status_code == 201
        r2 = client.post("/api/v1/employees", json=payload, headers=_auth(token))
        assert r2.status_code == 409
        assert r2.get_json()["error"] == "EMPLOYEE_ID_EXISTS"

    def test_create_employee_missing_required(self, client, emp_data):
        token = _login(client, "emp_admin")
        resp = client.post(
            "/api/v1/employees",
            json={"first_name": "Ivan"},
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "VALIDATION_ERROR"

    def test_create_employee_forbidden_for_wstaff(self, client, emp_data):
        token = _login(client, "emp_wstaff")
        resp = client.post(
            "/api/v1/employees",
            json={"employee_id": "EMP-X", "first_name": "X", "last_name": "Y"},
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_list_employees_admin(self, client, emp_data):
        token = _login(client, "emp_admin")
        resp = client.get("/api/v1/employees?page=1&per_page=50", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

    def test_list_employees_wstaff(self, client, emp_data):
        token = _login(client, "emp_wstaff")
        resp = client.get("/api/v1/employees?page=1&per_page=50", headers=_auth(token))
        assert resp.status_code == 200

    def test_list_employees_manager_forbidden(self, client, emp_data):
        token = _login(client, "emp_manager")
        resp = client.get("/api/v1/employees?page=1&per_page=50", headers=_auth(token))
        assert resp.status_code == 403

    def test_list_employees_search(self, client, emp_data):
        token = _login(client, "emp_admin")
        # Create a unique employee to search for
        client.post(
            "/api/v1/employees",
            json={"employee_id": "EMP-SRCH", "first_name": "Zeljko", "last_name": "Srchtest"},
            headers=_auth(token),
        )
        resp = client.get("/api/v1/employees?q=Srchtest", headers=_auth(token))
        assert resp.status_code == 200
        items = resp.get_json()["items"]
        assert any(e["last_name"] == "Srchtest" for e in items)

    def test_list_employees_include_inactive(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        # Create and deactivate an employee
        r = client.post(
            "/api/v1/employees",
            json={"employee_id": "EMP-INACT", "first_name": "Neaktivan", "last_name": "Korisnik"},
            headers=_auth(token),
        )
        emp_id = r.get_json()["id"]
        client.patch(f"/api/v1/employees/{emp_id}/deactivate", headers=_auth(token))

        # Default: inactive not shown
        resp_active = client.get("/api/v1/employees?q=Neaktivan", headers=_auth(token))
        active_items = resp_active.get_json()["items"]
        assert not any(e["id"] == emp_id for e in active_items)

        # include_inactive=true
        resp_all = client.get(
            "/api/v1/employees?q=Neaktivan&include_inactive=true", headers=_auth(token)
        )
        all_items = resp_all.get_json()["items"]
        assert any(e["id"] == emp_id for e in all_items)

    def test_get_employee_detail(self, client, emp_data):
        token = _login(client, "emp_admin")
        r = client.post(
            "/api/v1/employees",
            json={"employee_id": "EMP-DET", "first_name": "Detail", "last_name": "Test"},
            headers=_auth(token),
        )
        emp_id = r.get_json()["id"]
        resp = client.get(f"/api/v1/employees/{emp_id}", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.get_json()["id"] == emp_id

    def test_get_employee_not_found(self, client, emp_data):
        token = _login(client, "emp_admin")
        resp = client.get("/api/v1/employees/999999", headers=_auth(token))
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "EMPLOYEE_NOT_FOUND"

    def test_update_employee(self, client, emp_data):
        token = _login(client, "emp_admin")
        r = client.post(
            "/api/v1/employees",
            json={"employee_id": "EMP-UPD", "first_name": "Staro", "last_name": "Ime"},
            headers=_auth(token),
        )
        emp_id = r.get_json()["id"]
        resp = client.put(
            f"/api/v1/employees/{emp_id}",
            json={"first_name": "Novo", "department": "Skladište"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["first_name"] == "Novo"
        assert resp.get_json()["department"] == "Skladište"

    def test_deactivate_employee(self, client, emp_data):
        token = _login(client, "emp_admin")
        r = client.post(
            "/api/v1/employees",
            json={"employee_id": "EMP-DEACT", "first_name": "Deact", "last_name": "User"},
            headers=_auth(token),
        )
        emp_id = r.get_json()["id"]
        resp = client.patch(
            f"/api/v1/employees/{emp_id}/deactivate", headers=_auth(token)
        )
        assert resp.status_code == 200
        assert resp.get_json()["is_active"] is False


# ---------------------------------------------------------------------------
# Quota overview tests
# ---------------------------------------------------------------------------

class TestQuotaOverview:
    def _make_employee_with_job_title(self, client, token, emp_id_str, job_title):
        r = client.post(
            "/api/v1/employees",
            json={
                "employee_id": emp_id_str,
                "first_name": "Quota",
                "last_name": "Test",
                "job_title": job_title,
            },
            headers=_auth(token),
        )
        assert r.status_code == 201
        return r.get_json()["id"]

    def test_quota_overview_empty(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._make_employee_with_job_title(client, token, "EMP-QE1", "NoneTitle")
        resp = client.get(f"/api/v1/employees/{emp_id}/quotas", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["quotas"] == []
        assert "year" in data

    def test_quota_overview_category_level(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        job_title = "Lakar"
        emp_id = self._make_employee_with_job_title(client, token, "EMP-QC1", job_title)

        with app.app_context():
            aq = AnnualQuota(
                job_title=job_title,
                category_id=emp_data["cat"].id,
                article_id=None,
                employee_id=None,
                quantity=Decimal("10"),
                uom="emp_kom",
                reset_month=1,
                enforcement=QuotaEnforcement.WARN,
            )
            _db.session.add(aq)
            _db.session.commit()

        resp = client.get(f"/api/v1/employees/{emp_id}/quotas", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["quotas"]) == 1
        row = data["quotas"][0]
        assert row["category_id"] == emp_data["cat"].id
        assert row["quota"] == 10.0
        assert row["received"] == 0.0
        assert row["remaining"] == 10.0
        assert row["status"] == "OK"
        assert row["enforcement"] == "WARN"

    def test_quota_overview_article_level(self, client, emp_data, app):
        """Use employee-specific article quota so it does not leak to other tests."""
        token = _login(client, "emp_admin")
        emp_id = self._make_employee_with_job_title(client, token, "EMP-QA1", "SpecTitle")

        with app.app_context():
            emp = _db.session.query(Employee).filter_by(id=emp_id).first()
            # Employee-specific article override (does not pollute global article quotas)
            aq = AnnualQuota(
                job_title=None,
                category_id=None,
                article_id=emp_data["art"].id,
                employee_id=emp.id,
                quantity=Decimal("5"),
                uom="emp_kom",
                reset_month=1,
                enforcement=QuotaEnforcement.BLOCK,
            )
            _db.session.add(aq)
            _db.session.commit()

        resp = client.get(f"/api/v1/employees/{emp_id}/quotas", headers=_auth(token))
        assert resp.status_code == 200
        quotas = resp.get_json()["quotas"]
        art_rows = [q for q in quotas if q.get("article_id") == emp_data["art"].id]
        assert len(art_rows) == 1
        assert art_rows[0]["quota"] == 5.0

    def test_quota_overview_wstaff_can_read(self, client, emp_data, app):
        token_admin = _login(client, "emp_admin")
        emp_id = self._make_employee_with_job_title(client, token_admin, "EMP-QW1", "WStaffTitle")
        token_ws = _login(client, "emp_wstaff")
        resp = client.get(f"/api/v1/employees/{emp_id}/quotas", headers=_auth(token_ws))
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Issuance history tests
# ---------------------------------------------------------------------------

class TestIssuanceHistory:
    def test_issuance_history_empty(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        r = client.post(
            "/api/v1/employees",
            json={"employee_id": "EMP-IH1", "first_name": "History", "last_name": "Empty"},
            headers=_auth(token),
        )
        emp_id = r.get_json()["id"]
        resp = client.get(f"/api/v1/employees/{emp_id}/issuances", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_issuance_history_has_required_fields(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        r = client.post(
            "/api/v1/employees",
            json={"employee_id": "EMP-IH2", "first_name": "History", "last_name": "Fields"},
            headers=_auth(token),
        )
        emp_id = r.get_json()["id"]

        # Issue something
        client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={"article_id": emp_data["art"].id, "quantity": 1, "uom": "emp_kom"},
            headers=_auth(token),
        )

        resp = client.get(f"/api/v1/employees/{emp_id}/issuances", headers=_auth(token))
        assert resp.status_code == 200
        items = resp.get_json()["items"]
        assert len(items) == 1
        row = items[0]
        assert "id" in row
        assert "issued_at" in row
        assert "article_id" in row
        assert "article_no" in row
        assert "description" in row
        assert "batch_id" in row
        assert "batch_code" in row
        assert "quantity" in row
        assert "uom" in row
        assert "issued_by" in row
        assert "note" in row
        # issued_by must be username string, not int
        assert isinstance(row["issued_by"], str)

    def test_issuance_history_wstaff_can_read(self, client, emp_data, app):
        token_admin = _login(client, "emp_admin")
        r = client.post(
            "/api/v1/employees",
            json={"employee_id": "EMP-IHW", "first_name": "History", "last_name": "WStaff"},
            headers=_auth(token_admin),
        )
        emp_id = r.get_json()["id"]
        token_ws = _login(client, "emp_wstaff")
        resp = client.get(f"/api/v1/employees/{emp_id}/issuances", headers=_auth(token_ws))
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Article lookup tests
# ---------------------------------------------------------------------------

class TestArticleLookup:
    def test_lookup_returns_personal_issue_articles(self, client, emp_data):
        token = _login(client, "emp_admin")
        resp = client.get("/api/v1/employees/lookups/articles?q=rukavice", headers=_auth(token))
        assert resp.status_code == 200
        items = resp.get_json()
        assert isinstance(items, list)
        # Personal-issue article should appear
        assert any(a["article_no"] == "EMP-ART-001" for a in items)

    def test_lookup_excludes_non_personal_issue(self, client, emp_data):
        token = _login(client, "emp_admin")
        resp = client.get("/api/v1/employees/lookups/articles?q=Non-personal", headers=_auth(token))
        assert resp.status_code == 200
        items = resp.get_json()
        # Non-personal article should NOT appear
        assert not any(a["article_no"] == "EMP-ART-NPI" for a in items)

    def test_lookup_includes_batches_for_batch_article(self, client, emp_data):
        token = _login(client, "emp_admin")
        resp = client.get("/api/v1/employees/lookups/articles?q=maska", headers=_auth(token))
        assert resp.status_code == 200
        items = resp.get_json()
        batch_art = next((a for a in items if a["article_no"] == "EMP-ART-002"), None)
        assert batch_art is not None
        assert batch_art["has_batch"] is True
        assert "batches" in batch_art
        assert len(batch_art["batches"]) > 0
        assert "batch_code" in batch_art["batches"][0]
        assert "available" in batch_art["batches"][0]

    def test_lookup_wstaff_forbidden(self, client, emp_data):
        token = _login(client, "emp_wstaff")
        resp = client.get("/api/v1/employees/lookups/articles?q=x", headers=_auth(token))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Issuance check tests
# ---------------------------------------------------------------------------

class TestIssuanceCheck:
    def _create_emp(self, client, token, emp_id_str, job_title=None):
        payload = {"employee_id": emp_id_str, "first_name": "Check", "last_name": "Test"}
        if job_title:
            payload["job_title"] = job_title
        r = client.post("/api/v1/employees", json=payload, headers=_auth(token))
        return r.get_json()["id"]

    def test_check_no_quota_returns_no_quota(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-CHK1")
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances/check",
            json={"article_id": emp_data["art"].id, "quantity": 1},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "NO_QUOTA"

    def test_check_ok_status(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        job_title = "CheckerOK"
        emp_id = self._create_emp(client, token, "EMP-CHK2", job_title)
        with app.app_context():
            aq = AnnualQuota(
                job_title=job_title,
                category_id=emp_data["cat"].id,
                article_id=None,
                employee_id=None,
                quantity=Decimal("10"),
                uom="emp_kom",
                reset_month=1,
                enforcement=QuotaEnforcement.WARN,
            )
            _db.session.add(aq)
            _db.session.commit()

        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances/check",
            json={"article_id": emp_data["art"].id, "quantity": 1},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "OK"

    def test_check_blocked_returns_400(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        job_title = "CheckerBLOCK"
        emp_id = self._create_emp(client, token, "EMP-CHK3", job_title)
        with app.app_context():
            emp = _db.session.query(Employee).filter_by(id=emp_id).first()
            # Employee-specific quota so it does not pollute global state
            aq = AnnualQuota(
                job_title=None,
                category_id=None,
                article_id=emp_data["art"].id,
                employee_id=emp.id,
                quantity=Decimal("2"),
                uom="emp_kom",
                reset_month=1,
                enforcement=QuotaEnforcement.BLOCK,
            )
            _db.session.add(aq)
            _db.session.commit()

        # First issue 2 (exactly fills quota) — BLOCK enforcement: projected==quota → BLOCKED
        # So we must check first before issuing to see the BLOCKED state
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances/check",
            json={"article_id": emp_data["art"].id, "quantity": 2},
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "QUOTA_EXCEEDED"

    def test_check_non_personal_issue_article_rejected(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-CHK4")
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances/check",
            json={"article_id": emp_data["art_npi"].id, "quantity": 1},
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "NOT_PERSONAL_ISSUE"

    def test_check_requires_batch_when_has_batch(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-CHK5")
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances/check",
            json={"article_id": emp_data["art_batch"].id, "quantity": 1},
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "BATCH_REQUIRED"

    def test_check_rejects_insufficient_stock_for_non_batch(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-CHK6")
        low_stock = _seed_personal_issue_article_with_stock(
            app,
            emp_data,
            article_no="EMP-ART-LOW-CHECK",
            description="Low stock check article",
            quantity=Decimal("1"),
        )
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances/check",
            json={"article_id": low_stock["article_id"], "quantity": 2},
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "INSUFFICIENT_STOCK"

    def test_check_rejects_insufficient_stock_for_batch(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-CHK7")
        low_stock = _seed_personal_issue_article_with_stock(
            app,
            emp_data,
            article_no="EMP-ART-BLOW-CHECK",
            description="Low stock batch check article",
            quantity=Decimal("1"),
            has_batch=True,
        )
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances/check",
            json={
                "article_id": low_stock["article_id"],
                "batch_id": low_stock["batch_id"],
                "quantity": 2,
            },
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "INSUFFICIENT_STOCK"

    def test_check_wstaff_forbidden(self, client, emp_data, app):
        token_admin = _login(client, "emp_admin")
        r = client.post(
            "/api/v1/employees",
            json={"employee_id": "EMP-CHKWS", "first_name": "W", "last_name": "S"},
            headers=_auth(token_admin),
        )
        emp_id = r.get_json()["id"]
        token_ws = _login(client, "emp_wstaff")
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances/check",
            json={"article_id": emp_data["art"].id, "quantity": 1},
            headers=_auth(token_ws),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Issuance create tests
# ---------------------------------------------------------------------------

class TestIssuanceCreate:
    def _create_emp(self, client, token, emp_id_str, job_title=None):
        payload = {"employee_id": emp_id_str, "first_name": "Issue", "last_name": "Test"}
        if job_title:
            payload["job_title"] = job_title
        r = client.post("/api/v1/employees", json=payload, headers=_auth(token))
        assert r.status_code == 201
        return r.get_json()["id"]

    def test_create_issuance_basic(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-IS1")
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={"article_id": emp_data["art"].id, "quantity": 2, "uom": "emp_kom"},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["article_id"] == emp_data["art"].id
        assert data["quantity"] == 2.0
        # issued_by must be username string
        assert data["issued_by"] == "emp_admin"

    def test_create_issuance_decrements_stock(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-IS2")

        with app.app_context():
            before = _db.session.query(Stock).filter_by(
                article_id=emp_data["art"].id, batch_id=None
            ).first()
            qty_before = float(before.quantity) if before else 0

        client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={"article_id": emp_data["art"].id, "quantity": 3, "uom": "emp_kom"},
            headers=_auth(token),
        )

        with app.app_context():
            after = _db.session.query(Stock).filter_by(
                article_id=emp_data["art"].id, batch_id=None
            ).first()
            qty_after = float(after.quantity) if after else 0

        assert qty_after == qty_before - 3

    def test_create_issuance_creates_transaction(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-IS3")

        with app.app_context():
            tx_count_before = _db.session.query(Transaction).filter_by(
                tx_type=TxType.PERSONAL_ISSUE, article_id=emp_data["art"].id
            ).count()

        client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={"article_id": emp_data["art"].id, "quantity": 1, "uom": "emp_kom"},
            headers=_auth(token),
        )

        with app.app_context():
            tx_count_after = _db.session.query(Transaction).filter_by(
                tx_type=TxType.PERSONAL_ISSUE, article_id=emp_data["art"].id
            ).count()

        assert tx_count_after == tx_count_before + 1

    def test_create_issuance_with_batch(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-IS4")
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={
                "article_id": emp_data["art_batch"].id,
                "batch_id": emp_data["batch"].id,
                "quantity": 1,
                "uom": "emp_kom",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["batch_id"] == emp_data["batch"].id
        assert data["batch_code"] == "EMP-B001"

    def test_create_issuance_batch_required_error(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-IS5")
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={"article_id": emp_data["art_batch"].id, "quantity": 1},
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "BATCH_REQUIRED"

    def test_create_issuance_non_personal_issue_rejected(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-IS6")
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={"article_id": emp_data["art_npi"].id, "quantity": 1},
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "NOT_PERSONAL_ISSUE"

    def test_create_issuance_zero_quantity_rejected(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-IS7")
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={"article_id": emp_data["art"].id, "quantity": 0},
            headers=_auth(token),
        )
        assert resp.status_code == 400

    def test_create_issuance_rejects_insufficient_stock_and_does_not_persist(
        self, client, emp_data, app
    ):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-IS7B")
        low_stock = _seed_personal_issue_article_with_stock(
            app,
            emp_data,
            article_no="EMP-ART-LOW-CREATE",
            description="Low stock create article",
            quantity=Decimal("1"),
        )

        with app.app_context():
            issuance_before = _db.session.query(PersonalIssuance).count()
            tx_before = _db.session.query(Transaction).filter_by(
                tx_type=TxType.PERSONAL_ISSUE
            ).count()

        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={"article_id": low_stock["article_id"], "quantity": 2, "uom": "emp_kom"},
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "INSUFFICIENT_STOCK"

        with app.app_context():
            issuance_after = _db.session.query(PersonalIssuance).count()
            tx_after = _db.session.query(Transaction).filter_by(
                tx_type=TxType.PERSONAL_ISSUE
            ).count()

        assert issuance_after == issuance_before
        assert tx_after == tx_before

    def test_create_issuance_rejects_insufficient_stock_for_batch(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-IS7C")
        low_stock = _seed_personal_issue_article_with_stock(
            app,
            emp_data,
            article_no="EMP-ART-BLOW-CREATE",
            description="Low stock batch create article",
            quantity=Decimal("1"),
            has_batch=True,
        )

        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={
                "article_id": low_stock["article_id"],
                "batch_id": low_stock["batch_id"],
                "quantity": 2,
                "uom": "emp_kom",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "INSUFFICIENT_STOCK"

    def test_create_issuance_warn_quota_allowed(self, client, emp_data, app):
        """Quota WARN: issuance that exceeds quota is allowed, response includes warning."""
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-IS8")

        with app.app_context():
            emp = _db.session.query(Employee).filter_by(id=emp_id).first()
            # Employee+article quota (highest priority, isolated to this employee)
            aq = AnnualQuota(
                job_title=None,
                category_id=None,
                article_id=emp_data["art"].id,
                employee_id=emp.id,
                quantity=Decimal("1"),
                uom="emp_kom",
                reset_month=1,
                enforcement=QuotaEnforcement.WARN,
            )
            _db.session.add(aq)
            _db.session.commit()

        # Issue exceeding quota with WARN → should succeed with warning
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={"article_id": emp_data["art"].id, "quantity": 2, "uom": "emp_kom"},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert "warning" in data

    def test_create_issuance_block_quota_rejected(self, client, emp_data, app):
        """Quota BLOCK: issuance that hits/exceeds quota is rejected."""
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-IS9")

        with app.app_context():
            emp = _db.session.query(Employee).filter_by(id=emp_id).first()
            # Employee+article quota (highest priority, isolated to this employee)
            aq = AnnualQuota(
                job_title=None,
                category_id=None,
                article_id=emp_data["art"].id,
                employee_id=emp.id,
                quantity=Decimal("1"),
                uom="emp_kom",
                reset_month=1,
                enforcement=QuotaEnforcement.BLOCK,
            )
            _db.session.add(aq)
            _db.session.commit()

        # Issue 2 units with quota=1 BLOCK → projected(2) >= quota(1) → rejected
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={"article_id": emp_data["art"].id, "quantity": 2, "uom": "emp_kom"},
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "QUOTA_EXCEEDED"

    def test_create_issuance_wstaff_forbidden(self, client, emp_data, app):
        token_admin = _login(client, "emp_admin")
        r = client.post(
            "/api/v1/employees",
            json={"employee_id": "EMP-ISWS", "first_name": "W", "last_name": "S"},
            headers=_auth(token_admin),
        )
        emp_id = r.get_json()["id"]
        token_ws = _login(client, "emp_wstaff")
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={"article_id": emp_data["art"].id, "quantity": 1},
            headers=_auth(token_ws),
        )
        assert resp.status_code == 403

    def test_quota_priority_emp_article_beats_global(self, client, emp_data, app):
        """Employee+article override (quota=5) beats global article override (quota=1)."""
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-PRI1")

        with app.app_context():
            emp = _db.session.query(Employee).filter_by(id=emp_id).first()
            # Global override: quota = 1
            aq_global = AnnualQuota(
                job_title=None,
                category_id=None,
                article_id=emp_data["art"].id,
                employee_id=None,
                quantity=Decimal("1"),
                uom="emp_kom",
                reset_month=1,
                enforcement=QuotaEnforcement.BLOCK,
            )
            # Employee override: quota = 5
            aq_emp = AnnualQuota(
                job_title=None,
                category_id=None,
                article_id=emp_data["art"].id,
                employee_id=emp.id,
                quantity=Decimal("5"),
                uom="emp_kom",
                reset_month=1,
                enforcement=QuotaEnforcement.WARN,
            )
            _db.session.add_all([aq_global, aq_emp])
            _db.session.commit()

        # Issue 3 — should be OK (employee quota=5, not blocked by global quota=1)
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={"article_id": emp_data["art"].id, "quantity": 3, "uom": "emp_kom"},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        # No blocked error means the employee override was applied correctly

    def test_issuance_history_shows_batch_code(self, client, emp_data, app):
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "EMP-BCH1")

        # Issue batch-tracked article
        client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={
                "article_id": emp_data["art_batch"].id,
                "batch_id": emp_data["batch"].id,
                "quantity": 1,
                "uom": "emp_kom",
            },
            headers=_auth(token),
        )

        resp = client.get(f"/api/v1/employees/{emp_id}/issuances", headers=_auth(token))
        items = resp.get_json()["items"]
        assert len(items) == 1
        assert items[0]["batch_code"] == "EMP-B001"
        assert items[0]["batch_id"] == emp_data["batch"].id


# ---------------------------------------------------------------------------
# Wave 7 Phase 1 — M-3 UOM validation + H-4 stock locking
# ---------------------------------------------------------------------------

class TestIssuanceUOMValidation:
    """M-3: check_issuance and create_issuance must reject mismatched UOM."""

    def _create_emp(self, client, token, employee_id: str) -> int:
        resp = client.post(
            "/api/v1/employees",
            json={"employee_id": employee_id, "first_name": "UOM", "last_name": "Test"},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        return resp.get_json()["id"]

    def test_create_issuance_wrong_uom_returns_400(self, client, emp_data, app):
        """M-3: create_issuance with a UOM that doesn't match article base UOM -> 400 UOM_MISMATCH."""
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "M3-CREATE-001")

        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={
                "article_id": emp_data["art"].id,
                "quantity": 1,
                "uom": "wrong_uom",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"] == "UOM_MISMATCH"
        assert "emp_kom" in body["message"]

    def test_check_issuance_wrong_uom_returns_400(self, client, emp_data, app):
        """M-3: check_issuance with a UOM that doesn't match article base UOM -> 400 UOM_MISMATCH."""
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "M3-CHECK-001")

        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances/check",
            json={
                "article_id": emp_data["art"].id,
                "quantity": 1,
                "uom": "wrong_uom",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"] == "UOM_MISMATCH"

    def test_create_issuance_correct_uom_succeeds(self, client, emp_data, app):
        """M-3: create_issuance with the correct base UOM succeeds."""
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "M3-CREATE-OK-001")
        # Use a dedicated article to avoid shared-stock depletion from earlier tests.
        fresh = _seed_personal_issue_article_with_stock(
            app, emp_data, article_no="M3-ART-OK", description="M3 UOM test article", quantity=Decimal("10")
        )
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={
                "article_id": fresh["article_id"],
                "quantity": 1,
                "uom": "emp_kom",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201

    def test_create_issuance_no_uom_falls_back_to_base(self, client, emp_data, app):
        """M-3: create_issuance with no uom field falls back to article base UOM."""
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "M3-CREATE-NOOM-001")
        # Use a dedicated article to avoid shared-stock depletion from earlier tests.
        fresh = _seed_personal_issue_article_with_stock(
            app, emp_data, article_no="M3-ART-NOOM", description="M3 no-UOM test article", quantity=Decimal("10")
        )
        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances",
            json={
                "article_id": fresh["article_id"],
                "quantity": 1,
            },
            headers=_auth(token),
        )
        assert resp.status_code == 201
        assert resp.get_json()["uom"] == "emp_kom"

    def test_check_issuance_no_uom_falls_back_to_base(self, client, emp_data, app):
        """M-3: check_issuance with no uom does not raise UOM_MISMATCH."""
        token = _login(client, "emp_admin")
        emp_id = self._create_emp(client, token, "M3-CHECK-NOOM-001")

        resp = client.post(
            f"/api/v1/employees/{emp_id}/issuances/check",
            json={
                "article_id": emp_data["art"].id,
                "quantity": 1,
            },
            headers=_auth(token),
        )
        # Should not be a UOM_MISMATCH (could be NO_QUOTA or OK)
        if resp.status_code == 400:
            assert resp.get_json().get("error") != "UOM_MISMATCH"
