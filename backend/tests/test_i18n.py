"""Regression tests for locale-aware API error message resolution (DEC-I18N-001).

Verifies that:
  - A 404 error path returns Croatian when Accept-Language: hr
  - The same 404 path returns English when Accept-Language: en
  - A 409 error path follows the selected language
  - Missing / unsupported Accept-Language falls back deterministically to ``hr``
    (no SystemConfig default_language is seeded in the test DB, so the final
     fallback ``hr`` is exercised)
"""

from __future__ import annotations

import pytest
from werkzeug.security import generate_password_hash

from app.utils.errors import api_error
from app.extensions import db as _db
from app.models.article import Article
from app.models.category import Category
from app.models.enums import UserRole
from app.models.location import Location
from app.models.uom_catalog import UomCatalog
from app.models.user import User
from app.utils.validators import (
    QueryValidationError,
    parse_bool_query,
    parse_positive_int,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def i18n_data(app):
    """Minimal seed data for i18n localization tests."""
    with app.app_context():
        location = _db.session.get(Location, 1)
        if location is None:
            location = Location(id=1, name="I18N Test Site", timezone="UTC", is_active=True)
            _db.session.add(location)
            _db.session.flush()

        uom = UomCatalog.query.filter_by(code="i18n_kom").first()
        if uom is None:
            uom = UomCatalog(
                code="i18n_kom",
                label_hr="komad",
                label_en="piece",
                decimal_display=False,
            )
            _db.session.add(uom)

        cat = Category.query.filter_by(key="i18n_test_cat").first()
        if cat is None:
            cat = Category(
                key="i18n_test_cat",
                label_hr="Testna kategorija",
                label_en="Test Category",
                is_personal_issue=False,
                is_active=True,
            )
            _db.session.add(cat)
            _db.session.flush()

        article = Article.query.filter_by(article_no="I18N-ART-001").first()
        if article is None:
            article = Article(
                article_no="I18N-ART-001",
                description="I18N test article",
                category_id=cat.id,
                base_uom="i18n_kom",
                has_batch=False,
                is_active=True,
            )
            _db.session.add(article)

        admin = User.query.filter_by(username="i18n_admin").first()
        if admin is None:
            admin = User(
                username="i18n_admin",
                password_hash=generate_password_hash("adminpass", method="pbkdf2:sha256"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            _db.session.add(admin)

        viewer = User.query.filter_by(username="i18n_viewer").first()
        if viewer is None:
            viewer = User(
                username="i18n_viewer",
                password_hash=generate_password_hash("viewerpass", method="pbkdf2:sha256"),
                role=UserRole.VIEWER,
                is_active=True,
            )
            _db.session.add(viewer)

        _db.session.commit()
        yield {
            "article_id": article.id,
            "admin_username": "i18n_admin",
            "viewer_username": "i18n_viewer",
        }


def _login(client, username: str, password: str, remote_addr: str = "127.0.30.1") -> dict:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        environ_base={"REMOTE_ADDR": remote_addr},
    )
    assert resp.status_code == 200
    return resp.get_json()


def _auth(token: str, language: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if language:
        headers["Accept-Language"] = language
    return headers


# ---------------------------------------------------------------------------
# 404 localization
# ---------------------------------------------------------------------------


class TestLocalized404:
    """GET /api/v1/articles/<non_existent_id> returns ARTICLE_NOT_FOUND 404."""

    def test_404_returns_croatian_when_accept_language_hr(self, client, i18n_data):
        token = _login(client, i18n_data["admin_username"], "adminpass", "127.0.30.1")["access_token"]
        resp = client.get(
            "/api/v1/articles/99999",
            headers=_auth(token, "hr"),
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "ARTICLE_NOT_FOUND"
        assert data["message"] == "Artikl nije pronađen."

    def test_404_returns_english_when_accept_language_en(self, client, i18n_data):
        token = _login(client, i18n_data["admin_username"], "adminpass", "127.0.30.2")["access_token"]
        resp = client.get(
            "/api/v1/articles/99999",
            headers=_auth(token, "en"),
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "ARTICLE_NOT_FOUND"
        assert data["message"] == "Article not found."

    def test_404_returns_german_when_accept_language_de(self, client, i18n_data):
        token = _login(client, i18n_data["admin_username"], "adminpass", "127.0.30.3")["access_token"]
        resp = client.get(
            "/api/v1/articles/99999",
            headers=_auth(token, "de"),
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "ARTICLE_NOT_FOUND"
        assert data["message"] == "Artikel nicht gefunden."

    def test_404_returns_hungarian_when_accept_language_hu(self, client, i18n_data):
        token = _login(client, i18n_data["admin_username"], "adminpass", "127.0.30.4")["access_token"]
        resp = client.get(
            "/api/v1/articles/99999",
            headers=_auth(token, "hu"),
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "ARTICLE_NOT_FOUND"
        assert data["message"] == "A cikk nem található."


# ---------------------------------------------------------------------------
# 409 localization
# ---------------------------------------------------------------------------


class TestLocalized409:
    """POST /api/v1/articles/<id>/aliases twice → ALIAS_ALREADY_EXISTS 409."""

    def _add_alias(self, client, article_id: int, token: str, alias: str, language: str | None = None):
        return client.post(
            f"/api/v1/articles/{article_id}/aliases",
            json={"alias": alias},
            headers=_auth(token, language),
        )

    def test_409_returns_croatian_when_accept_language_hr(self, client, i18n_data):
        token = _login(client, i18n_data["admin_username"], "adminpass", "127.0.30.5")["access_token"]
        article_id = i18n_data["article_id"]
        alias = "i18n-duplicate-hr"
        # First add succeeds
        r1 = self._add_alias(client, article_id, token, alias)
        assert r1.status_code == 201
        # Second add returns 409
        r2 = self._add_alias(client, article_id, token, alias, "hr")
        assert r2.status_code == 409
        data = r2.get_json()
        assert data["error"] == "ALIAS_ALREADY_EXISTS"
        assert data["message"] == "Alias već postoji."

    def test_409_returns_english_when_accept_language_en(self, client, i18n_data):
        token = _login(client, i18n_data["admin_username"], "adminpass", "127.0.30.6")["access_token"]
        article_id = i18n_data["article_id"]
        alias = "i18n-duplicate-en"
        r1 = self._add_alias(client, article_id, token, alias)
        assert r1.status_code == 201
        r2 = self._add_alias(client, article_id, token, alias, "en")
        assert r2.status_code == 409
        data = r2.get_json()
        assert data["error"] == "ALIAS_ALREADY_EXISTS"
        assert data["message"] == "Alias already exists."

    def test_409_returns_german_when_accept_language_de(self, client, i18n_data):
        token = _login(client, i18n_data["admin_username"], "adminpass", "127.0.30.7")["access_token"]
        article_id = i18n_data["article_id"]
        alias = "i18n-duplicate-de"
        r1 = self._add_alias(client, article_id, token, alias)
        assert r1.status_code == 201
        r2 = self._add_alias(client, article_id, token, alias, "de")
        assert r2.status_code == 409
        data = r2.get_json()
        assert data["error"] == "ALIAS_ALREADY_EXISTS"
        assert data["message"] == "Alias existiert bereits."


# ---------------------------------------------------------------------------
# Fallback behaviour
# ---------------------------------------------------------------------------


class TestLocaleFallback:
    """Verify locale fallback: no header or unsupported language → hr."""

    def test_no_accept_language_falls_back_to_hr(self, client, i18n_data):
        """No Accept-Language header → fallback to hr (no SystemConfig in test DB)."""
        token = _login(client, i18n_data["admin_username"], "adminpass", "127.0.30.8")["access_token"]
        resp = client.get(
            "/api/v1/articles/99999",
            headers=_auth(token),  # no language
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "ARTICLE_NOT_FOUND"
        assert data["message"] == "Artikl nije pronađen."

    def test_unsupported_language_falls_back_to_hr(self, client, i18n_data):
        """Unsupported language (e.g. fr) → fallback to hr (no SystemConfig in test DB)."""
        token = _login(client, i18n_data["admin_username"], "adminpass", "127.0.30.9")["access_token"]
        resp = client.get(
            "/api/v1/articles/99999",
            headers=_auth(token, "fr"),
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "ARTICLE_NOT_FOUND"
        assert data["message"] == "Artikl nije pronađen."

    def test_complex_accept_language_header_extracts_primary_tag(self, client, i18n_data):
        """Accept-Language: de-AT,de;q=0.9,en;q=0.8 → de (primary supported tag)."""
        token = _login(client, i18n_data["admin_username"], "adminpass", "127.0.30.10")["access_token"]
        resp = client.get(
            "/api/v1/articles/99999",
            headers={**_auth(token), "Accept-Language": "de-AT,de;q=0.9,en;q=0.8"},
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "ARTICLE_NOT_FOUND"
        assert data["message"] == "Artikel nicht gefunden."

    def test_409_fallback_to_hr_when_no_header(self, client, i18n_data):
        """409 without Accept-Language falls back to hr."""
        token = _login(client, i18n_data["admin_username"], "adminpass", "127.0.30.11")["access_token"]
        article_id = i18n_data["article_id"]
        alias = "i18n-fallback-hr"
        r1 = client.post(
            f"/api/v1/articles/{article_id}/aliases",
            json={"alias": alias},
            headers=_auth(token),
        )
        assert r1.status_code == 201
        r2 = client.post(
            f"/api/v1/articles/{article_id}/aliases",
            json={"alias": alias},
            headers=_auth(token),  # no Accept-Language
        )
        assert r2.status_code == 409
        data = r2.get_json()
        assert data["error"] == "ALIAS_ALREADY_EXISTS"
        assert data["message"] == "Alias već postoji."


class TestLocalizedAuthAndValidation:
    def test_forbidden_error_returns_croatian_when_accept_language_hr(self, client, i18n_data):
        tokens = _login(client, i18n_data["viewer_username"], "viewerpass", "127.0.30.12")
        resp = client.get(
            "/api/v1/orders",
            headers=_auth(tokens["access_token"], "hr"),
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["error"] == "FORBIDDEN"
        assert data["message"] == "Nema ovlasti za pristup ovom resursu."

    def test_unauthorized_error_helper_returns_croatian_when_accept_language_hr(self, app):
        with app.test_request_context(headers={"Accept-Language": "hr"}):
            response, status = api_error(
                "UNAUTHORIZED",
                "User not found or account is inactive.",
                401,
            )
        assert status == 401
        data = response.get_json()
        assert data["error"] == "UNAUTHORIZED"
        assert data["message"] == "Korisnik nije pronađen ili je račun neaktivan."

    def test_validation_error_keeps_specific_english_message(self, client, i18n_data):
        tokens = _login(client, i18n_data["admin_username"], "adminpass", "127.0.30.13")
        resp = client.get(
            "/api/v1/orders?page=abc",
            headers=_auth(tokens["access_token"], "en"),
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "VALIDATION_ERROR"
        assert data["message"] == "page must be a valid integer."

    def test_validation_error_keeps_specific_croatian_message(self, client, i18n_data):
        tokens = _login(client, i18n_data["admin_username"], "adminpass", "127.0.30.14")
        resp = client.get(
            "/api/v1/orders?page=abc",
            headers=_auth(tokens["access_token"], "hr"),
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "VALIDATION_ERROR"
        assert data["message"] == "page mora biti cijeli broj."

    def test_employees_invalid_bool_query_is_localized(self, client, i18n_data):
        tokens = _login(client, i18n_data["admin_username"], "adminpass", "127.0.30.15")
        resp = client.get(
            "/api/v1/employees?include_inactive=maybe",
            headers=_auth(tokens["access_token"], "hr"),
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "VALIDATION_ERROR"
        assert data["message"] == "include_inactive mora biti 'true' ili 'false'."


class TestSharedQueryValidators:
    def test_parse_positive_int_uses_default_and_canonical_errors(self):
        assert parse_positive_int(None, field_name="page", default=7) == 7
        assert parse_positive_int("9", field_name="page", default=1) == 9

        with pytest.raises(QueryValidationError) as excinfo:
            parse_positive_int("abc", field_name="page", default=1)
        assert excinfo.value.error == "VALIDATION_ERROR"
        assert excinfo.value.message == "page must be a valid integer."

        with pytest.raises(QueryValidationError) as excinfo:
            parse_positive_int("0", field_name="page", default=1)
        assert excinfo.value.message == "page must be greater than zero."

    def test_parse_bool_query_uses_default_and_canonical_errors(self):
        assert parse_bool_query(None, field_name="include_inactive", default=False) is False
        assert parse_bool_query("true", field_name="include_inactive", default=False) is True
        assert parse_bool_query("0", field_name="include_inactive", default=True) is False

        with pytest.raises(QueryValidationError) as excinfo:
            parse_bool_query("maybe", field_name="include_inactive", default=False)
        assert excinfo.value.error == "VALIDATION_ERROR"
        assert excinfo.value.message == "include_inactive must be 'true' or 'false'."


class TestLocalizedOrderLineErrors:
    @pytest.mark.parametrize(
        ("error_code", "language", "fallback_message", "expected_message"),
        [
            ("ORDER_LINE_REMOVED", "hr", "Order line has been removed.", "Stavka narudžbe je uklonjena."),
            ("ORDER_LINE_REMOVED", "en", "Order line has been removed.", "Order line has been removed."),
            ("ORDER_LINE_REMOVED", "de", "Order line has been removed.", "Bestellposition wurde entfernt."),
            ("ORDER_LINE_REMOVED", "hu", "Order line has been removed.", "A rendelési sor el lett távolítva."),
            ("ORDER_LINE_CLOSED", "hr", "Order line is already closed.", "Stavka narudžbe je već zatvorena."),
            ("ORDER_LINE_CLOSED", "en", "Order line is already closed.", "Order line is already closed."),
            ("ORDER_LINE_CLOSED", "de", "Order line is already closed.", "Bestellposition ist bereits geschlossen."),
            ("ORDER_LINE_CLOSED", "hu", "Order line is already closed.", "A rendelési sor már le van zárva."),
        ],
    )
    def test_order_line_errors_are_localized_in_supported_locales(
        self,
        app,
        error_code: str,
        language: str,
        fallback_message: str,
        expected_message: str,
    ):
        with app.test_request_context(headers={"Accept-Language": language}):
            response, status = api_error(error_code, fallback_message, 409)
        assert status == 409
        data = response.get_json()
        assert data["error"] == error_code
        assert data["message"] == expected_message


class TestLocalizedPrinterErrors:
    @pytest.mark.parametrize(
        ("error_code", "details", "language", "expected_message"),
        [
            ("PRINTER_NOT_CONFIGURED", {}, "hr", "Pisač nije konfiguriran. Postavite IP adresu pisača u postavkama."),
            ("PRINTER_NOT_CONFIGURED", {}, "en", "Printer is not configured. Set the printer IP address in settings."),
            ("PRINTER_UNREACHABLE", {"printer_ip": "10.0.0.1"}, "hr", "Pisač nije dostupan na adresi 10.0.0.1."),
            ("PRINTER_UNREACHABLE", {"printer_ip": "10.0.0.1"}, "en", "Printer is not reachable at 10.0.0.1."),
            ("PRINTER_MODEL_UNKNOWN", {"model": "hp"}, "hr", "Nepoznat model pisača: hp."),
            ("PRINTER_MODEL_UNKNOWN", {"model": "hp"}, "en", "Unknown printer model: hp."),
        ],
    )
    def test_printer_errors_are_localized(
        self,
        app,
        error_code: str,
        details: dict,
        language: str,
        expected_message: str,
    ):
        with app.test_request_context(headers={"Accept-Language": language}):
            response, status = api_error(error_code, "fallback", 400, details)
        assert status == 400
        data = response.get_json()
        assert data["error"] == error_code
        assert data["message"] == expected_message
