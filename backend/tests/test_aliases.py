"""Integration tests for Wave 1 Phase 3 Article Aliases."""

from __future__ import annotations

import pytest

from app.extensions import db
from app.models.article_alias import ArticleAlias
from tests.test_articles import _auth_header, _login, warehouse_data


@pytest.fixture(autouse=True)
def _restore_aliases(app, warehouse_data):
    """Keep alias tests isolated from the shared Warehouse module fixture."""
    with app.app_context():
        baseline_ids = {row[0] for row in db.session.query(ArticleAlias.id).all()}

    yield

    with app.app_context():
        current_ids = {row[0] for row in db.session.query(ArticleAlias.id).all()}
        extra_ids = current_ids - baseline_ids
        if extra_ids:
            (
                db.session.query(ArticleAlias)
                .filter(ArticleAlias.id.in_(extra_ids))
                .delete(synchronize_session=False)
            )
            db.session.commit()
        else:
            db.session.rollback()


class TestArticleAliases:
    def test_add_alias_returns_201_and_saves_normalized(self, client, app, warehouse_data):
        article_id = warehouse_data["active_article"].id
        token = _login(client, "warehouse_admin")

        response = client.post(
            f"/api/v1/articles/{article_id}/aliases",
            json={"alias": "  Test Alias  "},
            headers=_auth_header(token),
        )
        assert response.status_code == 201
        payload = response.get_json()
        assert payload["alias"] == "Test Alias"
        assert payload["normalized"] == "test alias"
        assert "id" in payload

        with app.app_context():
            alias = db.session.get(ArticleAlias, payload["id"])
            assert alias is not None
            assert alias.article_id == article_id
            assert alias.alias == "Test Alias"
            assert alias.normalized == "test alias"

    def test_add_duplicate_alias_returns_409(self, client, warehouse_data):
        article_id = warehouse_data["batch_article"].id
        token = _login(client, "warehouse_admin")

        # Add an alias to duplicate
        resp1 = client.post(
            f"/api/v1/articles/{article_id}/aliases",
            json={"alias": "Duplicate Test"},
            headers=_auth_header(token),
        )
        assert resp1.status_code == 201

        resp2 = client.post(
            f"/api/v1/articles/{article_id}/aliases",
            json={"alias": "Duplicate Test"},
            headers=_auth_header(token),
        )
        assert resp2.status_code == 409
        payload = resp2.get_json()
        assert payload["error"] == "ALIAS_ALREADY_EXISTS"
        assert payload["message"] == "Alias already exists."

    def test_add_alias_different_casing_returns_409(self, client, warehouse_data):
        article_id = warehouse_data["batch_article"].id
        token = _login(client, "warehouse_admin")

        setup_resp = client.post(
            f"/api/v1/articles/{article_id}/aliases",
            json={"alias": "Duplicate Test"},
            headers=_auth_header(token),
        )
        assert setup_resp.status_code == 201

        resp = client.post(
            f"/api/v1/articles/{article_id}/aliases",
            json={"alias": " dUplicAte TEst "},
            headers=_auth_header(token),
        )
        assert resp.status_code == 409
        assert resp.get_json()["error"] == "ALIAS_ALREADY_EXISTS"
        assert resp.get_json()["message"] == "Alias already exists."

    def test_delete_alias_returns_204(self, client, app, warehouse_data):
        article_id = warehouse_data["active_article"].id
        token = _login(client, "warehouse_admin")

        add_resp = client.post(
            f"/api/v1/articles/{article_id}/aliases",
            json={"alias": "To Delete"},
            headers=_auth_header(token),
        )
        assert add_resp.status_code == 201
        alias_id = add_resp.get_json()["id"]

        del_resp = client.delete(
            f"/api/v1/articles/{article_id}/aliases/{alias_id}",
            headers=_auth_header(token),
        )
        assert del_resp.status_code == 204

        with app.app_context():
            assert db.session.get(ArticleAlias, alias_id) is None

    def test_delete_non_existent_alias_returns_404(self, client, warehouse_data):
        article_id = warehouse_data["active_article"].id
        token = _login(client, "warehouse_admin")

        del_resp = client.delete(
            f"/api/v1/articles/{article_id}/aliases/999999",
            headers=_auth_header(token),
        )
        assert del_resp.status_code == 404
        assert del_resp.get_json()["error"] == "ALIAS_NOT_FOUND"

    def test_get_article_includes_aliases_list(self, client, warehouse_data):
        article_id = warehouse_data["active_article"].id
        token = _login(client, "warehouse_manager")

        # Admin adds an alias to be sure
        admin_token = _login(client, "warehouse_admin")
        client.post(
            f"/api/v1/articles/{article_id}/aliases",
            json={"alias": "Included Alias"},
            headers=_auth_header(admin_token),
        )

        resp = client.get(
            f"/api/v1/articles/{article_id}",
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        payload = resp.get_json()
        assert "aliases" in payload
        assert isinstance(payload["aliases"], list)
        
        aliases = [a["alias"] for a in payload["aliases"]]
        assert "Included Alias" in aliases
        # Check that normalized form is exposed
        alias_items = {a["alias"]: a for a in payload["aliases"]}
        assert alias_items["Included Alias"]["normalized"] == "included alias"

    def test_non_admin_cannot_post_or_delete(self, client, warehouse_data):
        article_id = warehouse_data["active_article"].id
        token = _login(client, "warehouse_manager")

        post_resp = client.post(
            f"/api/v1/articles/{article_id}/aliases",
            json={"alias": "Manager Alias"},
            headers=_auth_header(token),
        )
        assert post_resp.status_code == 403

        del_resp = client.delete(
            f"/api/v1/articles/{article_id}/aliases/1",
            headers=_auth_header(token),
        )
        assert del_resp.status_code == 403

    def test_identifier_search_finds_article_by_alias(self, client, warehouse_data):
        article_id = warehouse_data["normal_article"].id
        admin_token = _login(client, "warehouse_admin")

        client.post(
            f"/api/v1/articles/{article_id}/aliases",
            json={"alias": "Searchable Alias"},
            headers=_auth_header(admin_token),
        )

        token = _login(client, "warehouse_staff")
        resp = client.get(
            "/api/v1/identifier?q=searchable alias",
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        payload = resp.get_json()
        
        found = next((p for p in payload["items"] if p["id"] == article_id), None)
        assert found is not None
        assert found["matched_via"] == "alias"
        assert found["matched_alias"] == "Searchable Alias"
