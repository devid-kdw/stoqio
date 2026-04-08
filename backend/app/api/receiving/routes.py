"""Receiving API routes for Phase 7."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.services import receiving_service
from app.services.receiving_service import ReceivingServiceError
from app.utils.auth import get_current_user, require_role
from app.utils.errors import api_error as _error
from app.utils.validators import QueryValidationError, parse_positive_int

receiving_bp = Blueprint("receiving", __name__)


@receiving_bp.route("/receiving", methods=["POST"])
@require_role("ADMIN")
def create_receipt():
    user = get_current_user()
    body = request.get_json(silent=True) or {}

    try:
        result = receiving_service.submit_receipt(user.id, body)
        return jsonify(result), 201
    except ReceivingServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)
    except IntegrityError:
        db.session.rollback()
        return _error(
            "CONFLICT",
            "Receiving update conflicted with another request. Please retry.",
            409,
        )


@receiving_bp.route("/receiving", methods=["GET"])
@require_role("ADMIN")
def get_receiving_history():
    try:
        page = parse_positive_int(request.args.get("page"), field_name="page", default=1)
        per_page = parse_positive_int(
            request.args.get("per_page"),
            field_name="per_page",
            default=50,
        )
        result = receiving_service.list_receiving_history(page, per_page)
        return jsonify(result), 200
    except (ReceivingServiceError, QueryValidationError) as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)
