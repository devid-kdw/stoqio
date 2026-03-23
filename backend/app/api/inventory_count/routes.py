"""Inventory Count API routes (Phase 12).

All endpoints are ADMIN-only per RBAC spec.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models.enums import InventoryCountType
from app.services import inventory_service
from app.services.inventory_service import InventoryServiceError
from app.utils.auth import get_current_user, require_role

inventory_bp = Blueprint("inventory", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error(error: str, message: str, status_code: int, details=None):
    return (
        jsonify({"error": error, "message": message, "details": details or {}}),
        status_code,
    )


def _parse_positive_int(value, *, field_name: str, default: int) -> int:
    raw = default if value is None else value
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        raise InventoryServiceError(
            "VALIDATION_ERROR", f"'{field_name}' must be a valid integer.", 400
        )
    if parsed <= 0:
        raise InventoryServiceError(
            "VALIDATION_ERROR", f"'{field_name}' must be greater than zero.", 400
        )
    return parsed


# ---------------------------------------------------------------------------
# Active count — must be declared before /<int:count_id> routes
# ---------------------------------------------------------------------------

@inventory_bp.route("/inventory/active", methods=["GET"])
@require_role("ADMIN")
def get_active_count():
    """GET /api/v1/inventory/active — return active count or {active: null}."""
    try:
        result = inventory_service.get_active_count()
        if result is None:
            return jsonify({"active": None}), 200
        return jsonify(result), 200
    except InventoryServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


# ---------------------------------------------------------------------------
# History + Start
# ---------------------------------------------------------------------------

@inventory_bp.route("/inventory", methods=["GET"])
@require_role("ADMIN")
def list_counts():
    """GET /api/v1/inventory?page=1&per_page=50 — paginated completed counts."""
    try:
        page = _parse_positive_int(
            request.args.get("page"), field_name="page", default=1
        )
        per_page = _parse_positive_int(
            request.args.get("per_page"), field_name="per_page", default=50
        )
        result = inventory_service.list_counts(page=page, per_page=per_page)
        return jsonify(result), 200
    except InventoryServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@inventory_bp.route("/inventory", methods=["POST"])
@require_role("ADMIN")
def start_count():
    """POST /api/v1/inventory — start a new inventory count."""
    try:
        current_user = get_current_user()
        body = request.get_json(silent=True) or {}
        raw_type = body.get("type", "REGULAR")
        try:
            count_type = InventoryCountType(raw_type)
        except ValueError:
            return _error(
                "VALIDATION_ERROR",
                f"'type' must be one of: {[t.value for t in InventoryCountType]}.",
                400,
            )
        result = inventory_service.start_count(current_user, count_type=count_type)
        return jsonify(result), 201
    except InventoryServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


# ---------------------------------------------------------------------------
# Count detail
# ---------------------------------------------------------------------------

@inventory_bp.route("/inventory/<int:count_id>", methods=["GET"])
@require_role("ADMIN")
def get_count_detail(count_id: int):
    """GET /api/v1/inventory/{id} — read-only detail for any count."""
    try:
        result = inventory_service.get_count_detail(count_id)
        return jsonify(result), 200
    except InventoryServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


# ---------------------------------------------------------------------------
# Update counted quantity
# ---------------------------------------------------------------------------

@inventory_bp.route("/inventory/<int:count_id>/lines/<int:line_id>", methods=["PATCH"])
@require_role("ADMIN")
def update_line(count_id: int, line_id: int):
    """PATCH /api/v1/inventory/{id}/lines/{line_id} — save counted quantity."""
    try:
        result = inventory_service.update_line(
            count_id, line_id, request.get_json(silent=True) or {}
        )
        return jsonify(result), 200
    except InventoryServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


# ---------------------------------------------------------------------------
# Complete count
# ---------------------------------------------------------------------------

@inventory_bp.route("/inventory/<int:count_id>/complete", methods=["POST"])
@require_role("ADMIN")
def complete_count(count_id: int):
    """POST /api/v1/inventory/{id}/complete — process discrepancies and close."""
    try:
        current_user = get_current_user()
        result = inventory_service.complete_count(count_id, current_user)
        return jsonify(result), 200
    except InventoryServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)
