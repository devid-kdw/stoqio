"""Integration tests for the Phase 14 Settings backend."""

from __future__ import annotations

from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db as _db
from app.models.annual_quota import AnnualQuota
from app.models.article import Article
from app.models.category import Category
from app.models.employee import Employee
from app.models.enums import QuotaEnforcement, UserRole
from app.models.location import Location
from app.models.role_display_name import RoleDisplayName
from app.models.supplier import Supplier
from app.models.system_config import SystemConfig
from app.models.uom_catalog import UomCatalog
from app.models.user import User

_DEFAULT_CONFIG = {
    "default_language": "hr",
    "barcode_format": "Code128",
    "barcode_printer": "",
    "export_format": "generic",
}
_DEFAULT_ROLE_LABELS = {
    UserRole.ADMIN: "Admin",
    UserRole.MANAGER: "Menadžment",
    UserRole.WAREHOUSE_STAFF: "Administracija",
    UserRole.VIEWER: "Kontrola",
    UserRole.OPERATOR: "Operater",
}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _assert_error_shape(payload: dict):
    assert "error" in payload
    assert "message" in payload
    assert "details" in payload


_token_cache: dict[str, str] = {}


def _login(client, username: str, password: str = "pass") -> str:
    cache_key = f"{username}:{password}"
    if cache_key in _token_cache:
        return _token_cache[cache_key]

    octet = (sum(ord(ch) for ch in cache_key) % 200) + 20
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        environ_base={"REMOTE_ADDR": f"127.0.14.{octet}"},
    )
    assert response.status_code == 200, response.get_json()
    token = response.get_json()["access_token"]
    _token_cache[cache_key] = token
    return token


def _raw_login(client, username: str, password: str):
    octet = (sum(ord(ch) for ch in f"{username}:{password}:raw") % 200) + 20
    return client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        environ_base={"REMOTE_ADDR": f"127.0.15.{octet}"},
    )


@pytest.fixture(scope="module")
def settings_data(app):
    """Seed dedicated Settings module fixtures once per module."""
    with app.app_context():
        location = _db.session.get(Location, 1)
        if location is None:
            location = Location(
                id=1,
                name="Settings Main",
                timezone="Europe/Berlin",
                is_active=True,
            )
            _db.session.add(location)
            _db.session.flush()
        else:
            location.name = "Settings Main"
            location.timezone = "Europe/Berlin"
            location.is_active = True

        for key, value in _DEFAULT_CONFIG.items():
            row = SystemConfig.query.filter_by(key=key).first()
            if row is None:
                row = SystemConfig(key=key, value=value)
                _db.session.add(row)
            else:
                row.value = value

        for role, display_name in _DEFAULT_ROLE_LABELS.items():
            row = RoleDisplayName.query.filter_by(role=role).first()
            if row is None:
                row = RoleDisplayName(role=role, display_name=display_name)
                _db.session.add(row)
            else:
                row.display_name = display_name

        piece_uom = UomCatalog.query.filter_by(code="set_kom").first()
        if piece_uom is None:
            piece_uom = UomCatalog(
                code="set_kom",
                label_hr="settings piece",
                label_en="settings piece",
                decimal_display=False,
            )
            _db.session.add(piece_uom)

        weight_uom = UomCatalog.query.filter_by(code="set_kg").first()
        if weight_uom is None:
            weight_uom = UomCatalog(
                code="set_kg",
                label_hr="settings kilogram",
                label_en="settings kilogram",
                decimal_display=True,
            )
            _db.session.add(weight_uom)

        _db.session.flush()

        personal_category = Category.query.filter_by(key="settings_personal_issue").first()
        if personal_category is None:
            personal_category = Category(
                key="settings_personal_issue",
                label_hr="Settings PPE",
                label_en="Settings PPE",
                is_personal_issue=True,
                is_active=True,
            )
            _db.session.add(personal_category)

        general_category = Category.query.filter_by(key="settings_general").first()
        if general_category is None:
            general_category = Category(
                key="settings_general",
                label_hr="Settings General",
                label_en="Settings General",
                is_personal_issue=False,
                is_active=True,
            )
            _db.session.add(general_category)

        _db.session.flush()

        article_personal = Article.query.filter_by(article_no="SET-ART-001").first()
        if article_personal is None:
            article_personal = Article(
                article_no="SET-ART-001",
                description="Settings Gloves",
                category_id=personal_category.id,
                base_uom=piece_uom.id,
                has_batch=False,
                is_active=True,
            )
            _db.session.add(article_personal)

        article_general = Article.query.filter_by(article_no="SET-ART-002").first()
        if article_general is None:
            article_general = Article(
                article_no="SET-ART-002",
                description="Settings Detergent",
                category_id=general_category.id,
                base_uom=weight_uom.id,
                has_batch=False,
                is_active=True,
            )
            _db.session.add(article_general)

        employee = Employee.query.filter_by(employee_id="SET-EMP-001").first()
        if employee is None:
            employee = Employee(
                employee_id="SET-EMP-001",
                first_name="Settings",
                last_name="Employee",
                job_title="Settings Worker",
                is_active=True,
            )
            _db.session.add(employee)

        admin = User.query.filter_by(username="settings_admin").first()
        if admin is None:
            admin = User(
                username="settings_admin",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            _db.session.add(admin)

        manager = User.query.filter_by(username="settings_manager").first()
        if manager is None:
            manager = User(
                username="settings_manager",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.MANAGER,
                is_active=True,
            )
            _db.session.add(manager)

        target = User.query.filter_by(username="settings_target").first()
        if target is None:
            target = User(
                username="settings_target",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.VIEWER,
                is_active=True,
            )
            _db.session.add(target)

        staff = User.query.filter_by(username="settings_staff").first()
        if staff is None:
            staff = User(
                username="settings_staff",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.WAREHOUSE_STAFF,
                is_active=True,
            )
            _db.session.add(staff)

        operator = User.query.filter_by(username="settings_operator").first()
        if operator is None:
            operator = User(
                username="settings_operator",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.OPERATOR,
                is_active=True,
            )
            _db.session.add(operator)

        active_supplier = Supplier.query.filter_by(internal_code="SET-SUP-ACTIVE").first()
        if active_supplier is None:
            active_supplier = Supplier(
                internal_code="SET-SUP-ACTIVE",
                name="Settings Active Supplier",
                contact_person="Ana",
                phone="+385111111",
                note="baseline",
                is_active=True,
            )
            _db.session.add(active_supplier)

        inactive_supplier = Supplier.query.filter_by(internal_code="SET-SUP-INACTIVE").first()
        if inactive_supplier is None:
            inactive_supplier = Supplier(
                internal_code="SET-SUP-INACTIVE",
                name="Settings Inactive Supplier",
                is_active=False,
            )
            _db.session.add(inactive_supplier)

        _db.session.flush()

        article_quota = (
            AnnualQuota.query
            .filter_by(article_id=article_personal.id, employee_id=None, job_title=None)
            .first()
        )
        if article_quota is None:
            article_quota = AnnualQuota(
                article_id=article_personal.id,
                employee_id=None,
                job_title=None,
                category_id=None,
                quantity=Decimal("12.000"),
                uom=piece_uom.code,
                reset_month=2,
                enforcement=QuotaEnforcement.WARN,
            )
            _db.session.add(article_quota)

        category_quota = (
            AnnualQuota.query
            .filter_by(
                article_id=None,
                employee_id=None,
                job_title="Settings Painter",
                category_id=personal_category.id,
            )
            .first()
        )
        if category_quota is None:
            category_quota = AnnualQuota(
                article_id=None,
                employee_id=None,
                job_title="Settings Painter",
                category_id=personal_category.id,
                quantity=Decimal("20.000"),
                uom=piece_uom.code,
                reset_month=1,
                enforcement=QuotaEnforcement.BLOCK,
            )
            _db.session.add(category_quota)

        employee_quota = (
            AnnualQuota.query
            .filter_by(article_id=article_personal.id, employee_id=employee.id)
            .first()
        )
        if employee_quota is None:
            employee_quota = AnnualQuota(
                article_id=article_personal.id,
                employee_id=employee.id,
                job_title=None,
                category_id=None,
                quantity=Decimal("2.000"),
                uom=piece_uom.code,
                reset_month=1,
                enforcement=QuotaEnforcement.BLOCK,
            )
            _db.session.add(employee_quota)

        _db.session.commit()

        yield {
            "location_id": location.id,
            "admin_username": admin.username,
            "admin_id": admin.id,
            "manager_username": manager.username,
            "manager_id": manager.id,
            "target_username": target.username,
            "target_id": target.id,
            "staff_username": staff.username,
            "staff_id": staff.id,
            "operator_username": operator.username,
            "operator_id": operator.id,
            "piece_uom_code": piece_uom.code,
            "weight_uom_code": weight_uom.code,
            "personal_category_id": personal_category.id,
            "general_category_id": general_category.id,
            "article_personal_id": article_personal.id,
            "article_general_id": article_general.id,
            "employee_id": employee.id,
            "active_supplier_id": active_supplier.id,
            "inactive_supplier_id": inactive_supplier.id,
            "seed_article_quota_id": article_quota.id,
            "seed_category_quota_id": category_quota.id,
            "seed_employee_quota_id": employee_quota.id,
        }


@pytest.fixture(autouse=True)
def reset_settings_state(app, settings_data):
    """Reset shared Settings state before and after each test."""

    def _restore():
        with app.app_context():
            location = _db.session.get(Location, settings_data["location_id"])
            location.name = "Settings Main"
            location.timezone = "Europe/Berlin"

            for key, value in _DEFAULT_CONFIG.items():
                row = SystemConfig.query.filter_by(key=key).first()
                if row is None:
                    _db.session.add(SystemConfig(key=key, value=value))
                else:
                    row.value = value

            for role, display_name in _DEFAULT_ROLE_LABELS.items():
                row = RoleDisplayName.query.filter_by(role=role).first()
                if row is None:
                    _db.session.add(RoleDisplayName(role=role, display_name=display_name))
                else:
                    row.display_name = display_name

            seeded_users = {
                "settings_admin": UserRole.ADMIN,
                "settings_manager": UserRole.MANAGER,
                "settings_target": UserRole.VIEWER,
                "settings_staff": UserRole.WAREHOUSE_STAFF,
                "settings_operator": UserRole.OPERATOR,
            }
            for username, role in seeded_users.items():
                user = User.query.filter_by(username=username).first()
                user.role = role
                user.is_active = True
                user.password_hash = generate_password_hash(
                    "pass",
                    method="pbkdf2:sha256",
                )

            active_supplier = Supplier.query.filter_by(internal_code="SET-SUP-ACTIVE").first()
            active_supplier.name = "Settings Active Supplier"
            active_supplier.contact_person = "Ana"
            active_supplier.phone = "+385111111"
            active_supplier.note = "baseline"
            active_supplier.is_active = True

            inactive_supplier = Supplier.query.filter_by(internal_code="SET-SUP-INACTIVE").first()
            inactive_supplier.name = "Settings Inactive Supplier"
            inactive_supplier.is_active = False

            for user in User.query.filter(User.username.like("settings_new_%")).all():
                _db.session.delete(user)

            for supplier in Supplier.query.filter(Supplier.internal_code.like("SET-NEW-%")).all():
                _db.session.delete(supplier)

            for uom in UomCatalog.query.filter(UomCatalog.code.like("set_new_%")).all():
                _db.session.delete(uom)

            seeded_quota_ids = {
                settings_data["seed_article_quota_id"],
                settings_data["seed_category_quota_id"],
                settings_data["seed_employee_quota_id"],
            }
            for quota in AnnualQuota.query.all():
                if quota.id in seeded_quota_ids:
                    continue
                if (
                    quota.article_id in {
                        settings_data["article_personal_id"],
                        settings_data["article_general_id"],
                    }
                    or quota.category_id in {
                        settings_data["personal_category_id"],
                        settings_data["general_category_id"],
                    }
                    or (quota.job_title or "").startswith("Settings Test")
                ):
                    _db.session.delete(quota)

            article_quota = _db.session.get(AnnualQuota, settings_data["seed_article_quota_id"])
            article_quota.article_id = settings_data["article_personal_id"]
            article_quota.category_id = None
            article_quota.employee_id = None
            article_quota.job_title = None
            article_quota.quantity = Decimal("12.000")
            article_quota.uom = settings_data["piece_uom_code"]
            article_quota.reset_month = 2
            article_quota.enforcement = QuotaEnforcement.WARN

            category_quota = _db.session.get(AnnualQuota, settings_data["seed_category_quota_id"])
            category_quota.article_id = None
            category_quota.category_id = settings_data["personal_category_id"]
            category_quota.employee_id = None
            category_quota.job_title = "Settings Painter"
            category_quota.quantity = Decimal("20.000")
            category_quota.uom = settings_data["piece_uom_code"]
            category_quota.reset_month = 1
            category_quota.enforcement = QuotaEnforcement.BLOCK

            employee_quota = _db.session.get(AnnualQuota, settings_data["seed_employee_quota_id"])
            employee_quota.article_id = settings_data["article_personal_id"]
            employee_quota.category_id = None
            employee_quota.employee_id = settings_data["employee_id"]
            employee_quota.job_title = None
            employee_quota.quantity = Decimal("2.000")
            employee_quota.uom = settings_data["piece_uom_code"]
            employee_quota.reset_month = 1
            employee_quota.enforcement = QuotaEnforcement.BLOCK

            _db.session.commit()

    _restore()
    yield
    _restore()


_MUTABLE_ENDPOINTS = [
    ("GET", "/api/v1/settings/general"),
    ("PUT", "/api/v1/settings/general"),
    ("GET", "/api/v1/settings/roles"),
    ("PUT", "/api/v1/settings/roles"),
    ("GET", "/api/v1/settings/uom"),
    ("POST", "/api/v1/settings/uom"),
    ("GET", "/api/v1/settings/categories"),
    ("PUT", "/api/v1/settings/categories/1"),
    ("GET", "/api/v1/settings/quotas"),
    ("POST", "/api/v1/settings/quotas"),
    ("PUT", "/api/v1/settings/quotas/1"),
    ("DELETE", "/api/v1/settings/quotas/1"),
    ("GET", "/api/v1/settings/barcode"),
    ("PUT", "/api/v1/settings/barcode"),
    ("GET", "/api/v1/settings/export"),
    ("PUT", "/api/v1/settings/export"),
    ("GET", "/api/v1/settings/suppliers"),
    ("POST", "/api/v1/settings/suppliers"),
    ("PUT", "/api/v1/settings/suppliers/1"),
    ("PATCH", "/api/v1/settings/suppliers/1/deactivate"),
    ("GET", "/api/v1/settings/users"),
    ("POST", "/api/v1/settings/users"),
    ("PUT", "/api/v1/settings/users/1"),
    ("PATCH", "/api/v1/settings/users/1/deactivate"),
]


@pytest.mark.parametrize("method, url", _MUTABLE_ENDPOINTS)
def test_mutable_settings_endpoints_forbidden_for_non_admin(client, settings_data, method, url):
    token = _login(client, settings_data["manager_username"])
    response = client.open(url, method=method, headers=_auth(token))

    assert response.status_code == 403
    _assert_error_shape(response.get_json())

    token_viewer = _login(client, settings_data["target_username"])
    response_viewer = client.open(url, method=method, headers=_auth(token_viewer))

    assert response_viewer.status_code == 403
    _assert_error_shape(response_viewer.get_json())


def test_get_general_settings_returns_current_values(client, settings_data):
    token = _login(client, settings_data["admin_username"])
    response = client.get("/api/v1/settings/general", headers=_auth(token))

    assert response.status_code == 200
    assert response.get_json() == {
        "location_name": "Settings Main",
        "timezone": "Europe/Berlin",
        "default_language": "hr",
    }


def test_update_general_settings_persists_location_and_language(client, settings_data, app):
    token = _login(client, settings_data["admin_username"])
    response = client.put(
        "/api/v1/settings/general",
        json={
            "location_name": "Factory Settings Site",
            "timezone": "Europe/Zagreb",
            "default_language": "de",
        },
        headers=_auth(token),
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "location_name": "Factory Settings Site",
        "timezone": "Europe/Zagreb",
        "default_language": "de",
    }

    with app.app_context():
        location = _db.session.get(Location, settings_data["location_id"])
        language = SystemConfig.query.filter_by(key="default_language").first()
        assert location.name == "Factory Settings Site"
        assert location.timezone == "Europe/Zagreb"
        assert language.value == "de"


def test_default_language_canonical_round_trip(client, settings_data):
    """PUT /settings/general -> GET /settings/general -> GET /settings/shell must all agree."""
    token = _login(client, settings_data["admin_username"])

    put_response = client.put(
        "/api/v1/settings/general",
        json={
            "location_name": "Settings Main",
            "timezone": "Europe/Berlin",
            "default_language": "en",
        },
        headers=_auth(token),
    )
    assert put_response.status_code == 200
    assert put_response.get_json()["default_language"] == "en"

    general_response = client.get("/api/v1/settings/general", headers=_auth(token))
    assert general_response.status_code == 200
    assert general_response.get_json()["default_language"] == "en"

    shell_response = client.get("/api/v1/settings/shell", headers=_auth(token))
    assert shell_response.status_code == 200
    assert shell_response.get_json()["default_language"] == "en"


def test_update_general_settings_rejects_empty_location_name(client, settings_data):
    token = _login(client, settings_data["admin_username"])
    response = client.put(
        "/api/v1/settings/general",
        json={
            "location_name": "   ",
            "timezone": "Europe/Berlin",
            "default_language": "hr",
        },
        headers={**_auth(token), "Accept-Language": "en"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    _assert_error_shape(payload)
    assert payload["error"] == "VALIDATION_ERROR"
    assert payload["message"] == "location_name is required."


def test_roles_get_and_put_round_trip(client, settings_data, app):
    token = _login(client, settings_data["admin_username"])

    get_response = client.get("/api/v1/settings/roles", headers=_auth(token))
    assert get_response.status_code == 200
    assert [item["role"] for item in get_response.get_json()] == [
        "ADMIN",
        "MANAGER",
        "WAREHOUSE_STAFF",
        "VIEWER",
        "OPERATOR",
    ]

    put_response = client.put(
        "/api/v1/settings/roles",
        json=[
            {"role": "ADMIN", "display_name": "Administrator"},
            {"role": "MANAGER", "display_name": "Leadership"},
            {"role": "WAREHOUSE_STAFF", "display_name": "Office"},
            {"role": "VIEWER", "display_name": "Audit"},
            {"role": "OPERATOR", "display_name": "Line Operator"},
        ],
        headers=_auth(token),
    )

    assert put_response.status_code == 200
    assert put_response.get_json()[0] == {
        "role": "ADMIN",
        "display_name": "Administrator",
    }

    with app.app_context():
        viewer_label = RoleDisplayName.query.filter_by(role=UserRole.VIEWER).first()
        assert viewer_label.display_name == "Audit"


def test_uom_list_is_sorted_and_create_rejects_duplicate_code(client):
    token = _login(client, "settings_admin")
    list_response = client.get("/api/v1/settings/uom", headers=_auth(token))

    assert list_response.status_code == 200
    codes = [item["code"] for item in list_response.get_json()]
    assert codes == sorted(codes)

    create_response = client.post(
        "/api/v1/settings/uom",
        json={
            "code": "set_new_unit",
            "label_hr": "new hr",
            "label_en": "new en",
            "decimal_display": True,
        },
        headers=_auth(token),
    )
    assert create_response.status_code == 201
    assert create_response.get_json()["code"] == "set_new_unit"

    duplicate_response = client.post(
        "/api/v1/settings/uom",
        json={
            "code": "set_new_unit",
            "label_hr": "dup hr",
            "label_en": "dup en",
            "decimal_display": False,
        },
        headers=_auth(token),
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.get_json()["error"] == "UOM_CODE_EXISTS"


def test_categories_get_and_update_only_allowed_fields(client, settings_data, app):
    token = _login(client, settings_data["admin_username"])

    get_response = client.get("/api/v1/settings/categories", headers=_auth(token))
    assert get_response.status_code == 200
    keys = [item["key"] for item in get_response.get_json()]
    assert keys == sorted(keys)

    update_response = client.put(
        f"/api/v1/settings/categories/{settings_data['personal_category_id']}",
        json={
            "label_hr": "Nova PPE",
            "label_en": "New PPE",
            "is_personal_issue": False,
        },
        headers=_auth(token),
    )

    assert update_response.status_code == 200
    assert update_response.get_json()["is_personal_issue"] is False

    with app.app_context():
        category = _db.session.get(Category, settings_data["personal_category_id"])
        assert category.label_hr == "Nova PPE"
        assert category.label_en == "New PPE"
        assert category.is_personal_issue is False


def test_get_quotas_excludes_employee_specific_overrides(client, settings_data):
    token = _login(client, settings_data["admin_username"])
    response = client.get("/api/v1/settings/quotas", headers=_auth(token))

    assert response.status_code == 200
    payload = response.get_json()
    ids = {item["id"] for item in payload}
    assert settings_data["seed_article_quota_id"] in ids
    assert settings_data["seed_category_quota_id"] in ids
    assert settings_data["seed_employee_quota_id"] not in ids

    article_row = next(item for item in payload if item["id"] == settings_data["seed_article_quota_id"])
    assert article_row["scope"] == "GLOBAL_ARTICLE_OVERRIDE"
    assert article_row["article_id"] == settings_data["article_personal_id"]

    category_row = next(item for item in payload if item["id"] == settings_data["seed_category_quota_id"])
    assert category_row["scope"] == "JOB_TITLE_CATEGORY_DEFAULT"
    assert category_row["job_title"] == "Settings Painter"


def test_create_update_and_delete_quota_round_trip(client, settings_data, app):
    token = _login(client, settings_data["admin_username"])

    create_response = client.post(
        "/api/v1/settings/quotas",
        json={
            "scope": "GLOBAL_ARTICLE_OVERRIDE",
            "article_id": settings_data["article_general_id"],
            "quantity": "7.500",
            "uom": settings_data["weight_uom_code"],
            "enforcement": "BLOCK",
            "reset_month": 3,
        },
        headers=_auth(token),
    )
    assert create_response.status_code == 201
    created = create_response.get_json()
    quota_id = created["id"]
    assert created["scope"] == "GLOBAL_ARTICLE_OVERRIDE"
    assert created["article_id"] == settings_data["article_general_id"]

    update_response = client.put(
        f"/api/v1/settings/quotas/{quota_id}",
        json={
            "scope": "JOB_TITLE_CATEGORY_DEFAULT",
            "job_title": "Settings Test Foreman",
            "category_id": settings_data["general_category_id"],
            "quantity": "9",
            "uom": settings_data["weight_uom_code"],
            "enforcement": "WARN",
            "reset_month": 4,
        },
        headers=_auth(token),
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()
    assert updated["scope"] == "JOB_TITLE_CATEGORY_DEFAULT"
    assert updated["job_title"] == "Settings Test Foreman"
    assert updated["category_id"] == settings_data["general_category_id"]

    delete_response = client.delete(
        f"/api/v1/settings/quotas/{quota_id}",
        headers=_auth(token),
    )
    assert delete_response.status_code == 200
    assert delete_response.get_json() == {"id": quota_id, "deleted": True}

    with app.app_context():
        assert _db.session.get(AnnualQuota, quota_id) is None


def test_barcode_settings_get_put_and_validate_format(client, app):
    token = _login(client, "settings_admin")

    get_response = client.get("/api/v1/settings/barcode", headers=_auth(token))
    assert get_response.status_code == 200
    payload = get_response.get_json()
    assert payload["barcode_format"] == "Code128"
    assert payload["barcode_printer"] == ""
    # new Phase-8 fields are always present; values depend on module test order
    assert "label_printer_ip" in payload
    assert isinstance(payload["label_printer_port"], int)
    assert "label_printer_model" in payload

    put_response = client.put(
        "/api/v1/settings/barcode",
        json={"barcode_format": "EAN-13", "barcode_printer": "Zebra GX430"},
        headers=_auth(token),
    )
    assert put_response.status_code == 200
    assert put_response.get_json()["barcode_format"] == "EAN-13"

    invalid_response = client.put(
        "/api/v1/settings/barcode",
        json={"barcode_format": "QR", "barcode_printer": "Zebra GX430"},
        headers=_auth(token),
    )
    assert invalid_response.status_code == 400
    assert invalid_response.get_json()["error"] == "VALIDATION_ERROR"

    with app.app_context():
        fmt = SystemConfig.query.filter_by(key="barcode_format").first()
        printer = SystemConfig.query.filter_by(key="barcode_printer").first()
        assert fmt.value == "EAN-13"
        assert printer.value == "Zebra GX430"


def test_barcode_settings_label_printer_fields(client, app):
    token = _login(client, "settings_admin")

    put_response = client.put(
        "/api/v1/settings/barcode",
        json={
            "barcode_format": "Code128",
            "barcode_printer": "",
            "label_printer_ip": "192.168.1.50",
            "label_printer_port": 9100,
            "label_printer_model": "zebra_zpl",
        },
        headers=_auth(token),
    )
    assert put_response.status_code == 200
    result = put_response.get_json()
    assert result["label_printer_ip"] == "192.168.1.50"
    assert result["label_printer_port"] == 9100
    assert result["label_printer_model"] == "zebra_zpl"

    with app.app_context():
        ip_row = SystemConfig.query.filter_by(key="label_printer_ip").first()
        port_row = SystemConfig.query.filter_by(key="label_printer_port").first()
        model_row = SystemConfig.query.filter_by(key="label_printer_model").first()
        assert ip_row.value == "192.168.1.50"
        assert port_row.value == "9100"
        assert model_row.value == "zebra_zpl"


def test_barcode_settings_rejects_unknown_printer_model(client):
    token = _login(client, "settings_admin")

    response = client.put(
        "/api/v1/settings/barcode",
        json={
            "barcode_format": "Code128",
            "label_printer_model": "hp_pcl",
        },
        headers=_auth(token),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "VALIDATION_ERROR"


def test_barcode_settings_rejects_invalid_port(client):
    token = _login(client, "settings_admin")

    response = client.put(
        "/api/v1/settings/barcode",
        json={
            "barcode_format": "Code128",
            "label_printer_port": 0,
        },
        headers=_auth(token),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "VALIDATION_ERROR"


def test_export_settings_use_machine_values(client, app):
    token = _login(client, "settings_admin")

    get_response = client.get("/api/v1/settings/export", headers=_auth(token))
    assert get_response.status_code == 200
    assert get_response.get_json() == {"export_format": "generic"}

    put_response = client.put(
        "/api/v1/settings/export",
        json={"export_format": "sap"},
        headers=_auth(token),
    )
    assert put_response.status_code == 200
    assert put_response.get_json() == {"export_format": "sap"}

    invalid_response = client.put(
        "/api/v1/settings/export",
        json={"export_format": "xlsx"},
        headers=_auth(token),
    )
    assert invalid_response.status_code == 400
    assert invalid_response.get_json()["error"] == "VALIDATION_ERROR"

    with app.app_context():
        export_row = SystemConfig.query.filter_by(key="export_format").first()
        assert export_row.value == "sap"


def test_suppliers_list_search_create_update_and_deactivate(client, settings_data, app):
    token = _login(client, settings_data["admin_username"])

    default_list = client.get(
        "/api/v1/settings/suppliers?page=1&per_page=50&q=SET-SUP",
        headers=_auth(token),
    )
    assert default_list.status_code == 200
    default_codes = [item["internal_code"] for item in default_list.get_json()["items"]]
    assert "SET-SUP-ACTIVE" in default_codes
    assert "SET-SUP-INACTIVE" not in default_codes

    inactive_list = client.get(
        "/api/v1/settings/suppliers?page=1&per_page=50&q=inactive&include_inactive=true",
        headers=_auth(token),
    )
    assert inactive_list.status_code == 200
    inactive_codes = [item["internal_code"] for item in inactive_list.get_json()["items"]]
    assert "SET-SUP-INACTIVE" in inactive_codes

    create_response = client.post(
        "/api/v1/settings/suppliers",
        json={
            "internal_code": "SET-NEW-001",
            "name": "Settings Created Supplier",
            "contact_person": "Iva",
            "phone": "+385222222",
            "note": "created",
        },
        headers=_auth(token),
    )
    assert create_response.status_code == 201
    supplier_id = create_response.get_json()["id"]

    duplicate_response = client.post(
        "/api/v1/settings/suppliers",
        json={"internal_code": "SET-NEW-001", "name": "Duplicate"},
        headers=_auth(token),
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.get_json()["error"] == "SUPPLIER_CODE_EXISTS"

    update_response = client.put(
        f"/api/v1/settings/suppliers/{supplier_id}",
        json={"name": "Settings Updated Supplier", "note": "updated"},
        headers=_auth(token),
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["name"] == "Settings Updated Supplier"

    deactivate_response = client.patch(
        f"/api/v1/settings/suppliers/{supplier_id}/deactivate",
        headers=_auth(token),
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.get_json()["is_active"] is False

    with app.app_context():
        supplier = _db.session.get(Supplier, supplier_id)
        assert supplier.is_active is False
        assert supplier.internal_code == "SET-NEW-001"


def test_users_list_is_sorted_and_includes_role_display_name(client, settings_data):
    token = _login(client, settings_data["admin_username"])
    response = client.get("/api/v1/settings/users", headers=_auth(token))

    assert response.status_code == 200
    payload = response.get_json()
    usernames = [item["username"] for item in payload]
    assert usernames == sorted(usernames, key=str.lower)

    target_row = next(item for item in payload if item["username"] == settings_data["target_username"])
    assert target_row["role"] == "VIEWER"
    assert target_row["role_display_name"] == "Kontrola"


def test_create_user_duplicate_username_update_password_and_deactivate(client, settings_data):
    token = _login(client, settings_data["admin_username"])

    create_response = client.post(
        "/api/v1/settings/users",
        json={
            "username": "settings_new_user",
            "password": "pass1",
            "role": "OPERATOR",
            "is_active": True,
        },
        headers=_auth(token),
    )
    assert create_response.status_code == 201
    created_user = create_response.get_json()
    assert created_user["role_display_name"] == "Operater"

    duplicate_response = client.post(
        "/api/v1/settings/users",
        json={
            "username": "settings_new_user",
            "password": "pass1",
            "role": "OPERATOR",
            "is_active": True,
        },
        headers=_auth(token),
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.get_json()["error"] == "USERNAME_EXISTS"

    update_response = client.put(
        f"/api/v1/settings/users/{settings_data['target_id']}",
        json={
            "role": "MANAGER",
            "is_active": True,
            "password": "pass-reset",
        },
        headers=_auth(token),
    )
    assert update_response.status_code == 200
    updated_user = update_response.get_json()
    assert updated_user["role"] == "MANAGER"
    assert updated_user["role_display_name"] == "Menadžment"

    old_login = _raw_login(client, settings_data["target_username"], "pass")
    assert old_login.status_code == 401
    assert old_login.get_json()["error"] == "INVALID_CREDENTIALS"

    new_login = _raw_login(client, settings_data["target_username"], "pass-reset")
    assert new_login.status_code == 200

    deactivate_response = client.patch(
        f"/api/v1/settings/users/{created_user['id']}/deactivate",
        headers=_auth(token),
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.get_json()["is_active"] is False

    inactive_login = _raw_login(client, "settings_new_user", "pass1")
    assert inactive_login.status_code == 401
    assert inactive_login.get_json()["error"] == "ACCOUNT_INACTIVE"


# ---------------------------------------------------------------------------
# GET /api/v1/settings/shell — Wave 2 Phase 7
# ---------------------------------------------------------------------------

_SHELL_ROLES = ["settings_admin", "settings_manager", "settings_target"]


def test_shell_endpoint_accessible_to_admin(client, settings_data):
    token = _login(client, settings_data["admin_username"])
    response = client.get("/api/v1/settings/shell", headers=_auth(token))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["location_name"] == "Settings Main"
    assert payload["default_language"] == "hr"
    assert isinstance(payload["role_display_names"], list)
    roles_in_payload = [r["role"] for r in payload["role_display_names"]]
    assert set(roles_in_payload) == {"ADMIN", "MANAGER", "WAREHOUSE_STAFF", "VIEWER", "OPERATOR"}


def test_shell_endpoint_accessible_to_manager(client, settings_data):
    token = _login(client, settings_data["manager_username"])
    response = client.get("/api/v1/settings/shell", headers=_auth(token))

    assert response.status_code == 200
    payload = response.get_json()
    assert "location_name" in payload
    assert "default_language" in payload
    assert "role_display_names" in payload


def test_shell_endpoint_accessible_to_viewer(client, settings_data):
    token = _login(client, settings_data["target_username"])
    response = client.get("/api/v1/settings/shell", headers=_auth(token))

    assert response.status_code == 200
    payload = response.get_json()
    assert "location_name" in payload
    assert "default_language" in payload
    assert "role_display_names" in payload


def test_shell_endpoint_anonymous_rejected(client, settings_data):
    response = client.get("/api/v1/settings/shell")

    assert response.status_code == 401


def test_shell_endpoint_does_not_expose_admin_only_fields(client, settings_data):
    token = _login(client, settings_data["manager_username"])
    response = client.get("/api/v1/settings/shell", headers=_auth(token))

    assert response.status_code == 200
    payload = response.get_json()
    # Ensure admin-only settings are not leaked
    for forbidden_key in ("timezone", "barcode_format", "barcode_printer", "export_format"):
        assert forbidden_key not in payload


def test_shell_role_display_names_match_defaults(client, settings_data):
    token = _login(client, settings_data["admin_username"])
    response = client.get("/api/v1/settings/shell", headers=_auth(token))

    assert response.status_code == 200
    role_map = {r["role"]: r["display_name"] for r in response.get_json()["role_display_names"]}
    assert role_map["ADMIN"] == "Admin"
    assert role_map["MANAGER"] == "Menadžment"
    assert role_map["WAREHOUSE_STAFF"] == "Administracija"
    assert role_map["VIEWER"] == "Kontrola"
    assert role_map["OPERATOR"] == "Operater"


# ---------------------------------------------------------------------------
# GET /api/v1/settings/shell — W3-003 auth-consistency additions
# ---------------------------------------------------------------------------


def test_shell_endpoint_accessible_to_warehouse_staff(client, settings_data):
    token = _login(client, settings_data["staff_username"])
    response = client.get("/api/v1/settings/shell", headers=_auth(token))

    assert response.status_code == 200
    payload = response.get_json()
    assert "location_name" in payload
    assert "default_language" in payload
    assert "role_display_names" in payload


def test_shell_endpoint_accessible_to_operator(client, settings_data):
    token = _login(client, settings_data["operator_username"])
    response = client.get("/api/v1/settings/shell", headers=_auth(token))

    assert response.status_code == 200
    payload = response.get_json()
    assert "location_name" in payload
    assert "default_language" in payload
    assert "role_display_names" in payload


def test_shell_endpoint_inactive_user_rejected(client, settings_data):
    """A valid token for a user that has since been deactivated must be rejected."""
    # Get a valid token while the user is still active.
    token = _login(client, settings_data["staff_username"])

    # Deactivate the user directly in the shared session so the change is
    # committed and visible to subsequent request handlers.
    user = User.query.filter_by(username=settings_data["staff_username"]).first()
    user.is_active = False
    _db.session.commit()

    try:
        response = client.get("/api/v1/settings/shell", headers=_auth(token))
        assert response.status_code == 401
    finally:
        user = User.query.filter_by(username=settings_data["staff_username"]).first()
        user.is_active = True
        _db.session.commit()


def test_shell_endpoint_nonexistent_user_rejected(client, settings_data):
    """A token for a user row that no longer exists must be rejected."""
    # Create a temporary user and obtain a token.
    ghost = User.query.filter_by(username="settings_new_ghost").first()
    if ghost is None:
        ghost = User(
            username="settings_new_ghost",
            password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
            role=UserRole.VIEWER,
            is_active=True,
        )
        _db.session.add(ghost)
        _db.session.commit()

    login_resp = _raw_login(client, "settings_new_ghost", "pass")
    assert login_resp.status_code == 200, login_resp.get_json()
    access_token = login_resp.get_json()["access_token"]

    # Delete the user so the row no longer exists.
    ghost = User.query.filter_by(username="settings_new_ghost").first()
    if ghost:
        _db.session.delete(ghost)
        _db.session.commit()

    response = client.get("/api/v1/settings/shell", headers=_auth(access_token))
    assert response.status_code == 401


def test_admin_cannot_deactivate_self(client, settings_data):
    token = _login(client, settings_data["admin_username"])

    put_response = client.put(
        f"/api/v1/settings/users/{settings_data['admin_id']}",
        json={"is_active": False},
        headers={**_auth(token), "Accept-Language": "en"},
    )
    assert put_response.status_code == 400
    assert put_response.get_json()["error"] == "SELF_DEACTIVATION_FORBIDDEN"
    assert put_response.get_json()["message"] == "You cannot deactivate your own account."

    patch_response = client.patch(
        f"/api/v1/settings/users/{settings_data['admin_id']}/deactivate",
        headers=_auth(token),
    )
    assert patch_response.status_code == 400
    assert patch_response.get_json()["error"] == "SELF_DEACTIVATION_FORBIDDEN"
