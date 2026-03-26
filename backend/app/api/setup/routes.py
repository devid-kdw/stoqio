"""First-run setup routes."""

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.location import Location
from app.utils.auth import require_role
from app.utils.errors import api_error as _error_response

setup_bp = Blueprint("setup", __name__)

_INITIAL_LOCATION_ID = 1
_DEFAULT_TIMEZONE = "Europe/Berlin"
_MAX_LOCATION_NAME_LENGTH = 100


def _serialize_location(location: Location) -> dict:
    """Serialize a Location row for API responses."""
    return {
        "id": location.id,
        "name": location.name,
        "timezone": location.timezone,
        "is_active": location.is_active,
    }


def _setup_required() -> bool:
    """Return True until the first Location exists."""
    return Location.query.first() is None


@setup_bp.route("/setup/status", methods=["GET"])
def setup_status():
    """Report whether first-run setup still needs to run."""
    return jsonify({"setup_required": _setup_required()}), 200


@setup_bp.route("/setup", methods=["POST"])
@require_role("ADMIN")
def create_setup_location():
    """Create the installation's initial location."""
    if not _setup_required():
        return _error_response(
            "SETUP_ALREADY_COMPLETED",
            "Initial setup has already been completed.",
            409,
        )

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = {}

    name = (payload.get("name") or "").strip()
    timezone = (payload.get("timezone") or _DEFAULT_TIMEZONE).strip()
    if not timezone:
        timezone = _DEFAULT_TIMEZONE

    if not name:
        return _error_response(
            "VALIDATION_ERROR",
            "Location name is required.",
            400,
            {"field": "name", "_msg_key": "SETUP_LOCATION_NAME_REQUIRED"},
        )

    if len(name) > _MAX_LOCATION_NAME_LENGTH:
        return _error_response(
            "VALIDATION_ERROR",
            "Location name must be 100 characters or fewer.",
            400,
            {
                "field": "name",
                "max_length": _MAX_LOCATION_NAME_LENGTH,
                "_msg_key": "SETUP_LOCATION_NAME_TOO_LONG",
            },
        )

    # Reserve the first and only supported location row for v1 so concurrent
    # setup requests collide on the primary key instead of creating duplicates.
    location = Location(
        id=_INITIAL_LOCATION_ID,
        name=name,
        timezone=timezone,
        is_active=True,
    )
    db.session.add(location)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _error_response(
            "SETUP_ALREADY_COMPLETED",
            "Initial setup has already been completed.",
            409,
        )

    return jsonify(_serialize_location(location)), 201
