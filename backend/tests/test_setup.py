"""Phase 4 first-run setup tests."""

import pytest


def _login(client, username, password, remote_addr):
    return client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        environ_base={"REMOTE_ADDR": remote_addr},
    )


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _assert_error_shape(payload):
    assert "error" in payload
    assert "message" in payload
    assert "details" in payload


@pytest.fixture(autouse=True)
def clean_locations(app):
    from app.extensions import db as _db
    from app.models.location import Location

    with app.app_context():
        Location.query.delete()
        _db.session.commit()

    yield

    with app.app_context():
        Location.query.delete()
        _db.session.commit()


def test_setup_status_returns_true_when_no_location_exists(client):
    response = client.get("/api/v1/setup/status")

    assert response.status_code == 200
    assert response.get_json() == {"setup_required": True}


def test_setup_status_returns_false_when_location_exists(app, client):
    from app.extensions import db as _db
    from app.models.location import Location

    with app.app_context():
        _db.session.add(
            Location(name="Warehouse Alpha", timezone="Europe/Berlin", is_active=True)
        )
        _db.session.commit()

    response = client.get("/api/v1/setup/status")

    assert response.status_code == 200
    assert response.get_json() == {"setup_required": False}


def test_setup_creation_with_valid_admin_token_creates_location_with_default_timezone(
    client, auth_users
):
    login_response = _login(client, "auth_admin", "adminpass", "127.0.10.1")
    assert login_response.status_code == 200
    token = login_response.get_json()["access_token"]

    response = client.post(
        "/api/v1/setup",
        json={"name": "Factory Warehouse LLC"},
        headers=_auth_header(token),
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["id"] == 1
    assert payload["name"] == "Factory Warehouse LLC"
    assert payload["timezone"] == "Europe/Berlin"
    assert payload["is_active"] is True


def test_setup_creation_without_token_returns_401(client):
    response = client.post("/api/v1/setup", json={"name": "Warehouse Alpha"})

    assert response.status_code == 401
    _assert_error_shape(response.get_json())
    assert response.get_json()["error"] == "TOKEN_MISSING"


def test_setup_creation_with_non_admin_role_returns_403(client, auth_users):
    login_response = _login(client, "auth_manager", "managerpass", "127.0.10.2")
    assert login_response.status_code == 200
    token = login_response.get_json()["access_token"]

    response = client.post(
        "/api/v1/setup",
        json={"name": "Warehouse Alpha"},
        headers=_auth_header(token),
    )

    assert response.status_code == 403
    _assert_error_shape(response.get_json())
    assert response.get_json()["error"] == "FORBIDDEN"


def test_setup_creation_returns_409_when_location_already_exists(
    app, client, auth_users
):
    from app.extensions import db as _db
    from app.models.location import Location

    with app.app_context():
        _db.session.add(
            Location(name="Existing Warehouse", timezone="Europe/Berlin")
        )
        _db.session.commit()

    login_response = _login(client, "auth_admin", "adminpass", "127.0.10.3")
    assert login_response.status_code == 200
    token = login_response.get_json()["access_token"]

    response = client.post(
        "/api/v1/setup",
        json={"name": "Warehouse Beta"},
        headers=_auth_header(token),
    )

    assert response.status_code == 409
    _assert_error_shape(response.get_json())
    assert response.get_json()["error"] == "SETUP_ALREADY_COMPLETED"


@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        ({}, "Location name is required."),
        ({"name": ""}, "Location name is required."),
        ({"name": "   "}, "Location name is required."),
        (
            {"name": "A" * 101},
            "Location name must be 100 characters or fewer.",
        ),
    ],
)
def test_setup_creation_with_invalid_name_returns_400(
    client, auth_users, payload, expected_message
):
    login_response = _login(client, "auth_admin", "adminpass", "127.0.10.4")
    assert login_response.status_code == 200
    token = login_response.get_json()["access_token"]

    response = client.post(
        "/api/v1/setup",
        json=payload,
        headers={**_auth_header(token), "Accept-Language": "en"},
    )

    assert response.status_code == 400
    _assert_error_shape(response.get_json())
    assert response.get_json()["error"] == "VALIDATION_ERROR"
    assert response.get_json()["message"] == expected_message


@pytest.mark.parametrize(
    ("timezone", "expected_timezone"),
    [
        (None, "Europe/Berlin"),
        ("", "Europe/Berlin"),
        ("   ", "Europe/Berlin"),
        ("Europe/Zagreb", "Europe/Zagreb"),
    ],
)
def test_setup_creation_applies_timezone_fallback_rules(
    client, auth_users, timezone, expected_timezone
):
    login_response = _login(client, "auth_admin", "adminpass", "127.0.10.5")
    assert login_response.status_code == 200
    token = login_response.get_json()["access_token"]

    payload = {"name": "Warehouse Alpha"}
    if timezone is not None:
        payload["timezone"] = timezone

    response = client.post(
        "/api/v1/setup",
        json=payload,
        headers=_auth_header(token),
    )

    assert response.status_code == 201
    assert response.get_json()["timezone"] == expected_timezone


def test_setup_creation_returns_409_when_db_conflict_occurs(
    app, client, auth_users, monkeypatch
):
    from app.api.setup import routes as setup_routes
    from app.extensions import db as _db
    from app.models.location import Location

    with app.app_context():
        _db.session.add(
            Location(id=1, name="Existing Warehouse", timezone="Europe/Berlin")
        )
        _db.session.commit()

    monkeypatch.setattr(setup_routes, "_setup_required", lambda: True)

    login_response = _login(client, "auth_admin", "adminpass", "127.0.10.6")
    assert login_response.status_code == 200
    token = login_response.get_json()["access_token"]

    response = client.post(
        "/api/v1/setup",
        json={"name": "Warehouse Beta"},
        headers=_auth_header(token),
    )

    assert response.status_code == 409
    _assert_error_shape(response.get_json())
    assert response.get_json()["error"] == "SETUP_ALREADY_COMPLETED"
