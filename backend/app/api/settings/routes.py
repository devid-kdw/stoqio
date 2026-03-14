"""Settings API routes for Phase 14."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.services import settings_service
from app.services.settings_service import SettingsServiceError
from app.utils.auth import get_current_user, require_role

settings_bp = Blueprint("settings", __name__)


def _error(error: str, message: str, status_code: int, details=None):
    return (
        jsonify({"error": error, "message": message, "details": details or {}}),
        status_code,
    )


def _parse_positive_int(value, *, field_name: str, default: int) -> int:
    raw_value = default if value is None else value
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be a valid integer.",
            400,
        ) from None
    if parsed <= 0:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be greater than zero.",
            400,
        )
    return parsed


def _parse_bool_query(value, *, field_name: str, default: bool) -> bool:
    if value is None:
        return default

    normalized = str(value).strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise SettingsServiceError(
        "VALIDATION_ERROR",
        f"{field_name} must be 'true' or 'false'.",
        400,
    )


@settings_bp.route("/settings/general", methods=["GET"])
@require_role("ADMIN")
def get_general_settings():
    try:
        return jsonify(settings_service.get_general_settings()), 200
    except SettingsServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/general", methods=["PUT"])
@require_role("ADMIN")
def update_general_settings():
    try:
        result = settings_service.update_general_settings(request.get_json(silent=True) or {})
        return jsonify(result), 200
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/roles", methods=["GET"])
@require_role("ADMIN")
def get_role_display_names():
    try:
        return jsonify(settings_service.list_role_display_names()), 200
    except SettingsServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/roles", methods=["PUT"])
@require_role("ADMIN")
def update_role_display_names():
    try:
        result = settings_service.update_role_display_names(request.get_json(silent=True) or {})
        return jsonify(result), 200
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/uom", methods=["GET"])
@require_role("ADMIN")
def get_uom_catalog():
    try:
        return jsonify(settings_service.list_uom_catalog()), 200
    except SettingsServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/uom", methods=["POST"])
@require_role("ADMIN")
def create_uom():
    try:
        result = settings_service.create_uom(request.get_json(silent=True) or {})
        return jsonify(result), 201
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/categories", methods=["GET"])
@require_role("ADMIN")
def get_categories():
    try:
        return jsonify(settings_service.list_categories()), 200
    except SettingsServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/categories/<int:category_id>", methods=["PUT"])
@require_role("ADMIN")
def update_category(category_id: int):
    try:
        result = settings_service.update_category(
            category_id,
            request.get_json(silent=True) or {},
        )
        return jsonify(result), 200
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/quotas", methods=["GET"])
@require_role("ADMIN")
def get_quotas():
    try:
        return jsonify(settings_service.list_settings_quotas()), 200
    except SettingsServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/quotas", methods=["POST"])
@require_role("ADMIN")
def create_quota():
    try:
        result = settings_service.create_quota(request.get_json(silent=True) or {})
        return jsonify(result), 201
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/quotas/<int:quota_id>", methods=["PUT"])
@require_role("ADMIN")
def update_quota(quota_id: int):
    try:
        result = settings_service.update_quota(quota_id, request.get_json(silent=True) or {})
        return jsonify(result), 200
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/quotas/<int:quota_id>", methods=["DELETE"])
@require_role("ADMIN")
def delete_quota(quota_id: int):
    try:
        result = settings_service.delete_quota(quota_id)
        return jsonify(result), 200
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/barcode", methods=["GET"])
@require_role("ADMIN")
def get_barcode_settings():
    try:
        return jsonify(settings_service.get_barcode_settings()), 200
    except SettingsServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/barcode", methods=["PUT"])
@require_role("ADMIN")
def update_barcode_settings():
    try:
        result = settings_service.update_barcode_settings(request.get_json(silent=True) or {})
        return jsonify(result), 200
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/export", methods=["GET"])
@require_role("ADMIN")
def get_export_settings():
    try:
        return jsonify(settings_service.get_export_settings()), 200
    except SettingsServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/export", methods=["PUT"])
@require_role("ADMIN")
def update_export_settings():
    try:
        result = settings_service.update_export_settings(request.get_json(silent=True) or {})
        return jsonify(result), 200
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/suppliers", methods=["GET"])
@require_role("ADMIN")
def get_suppliers():
    try:
        page = _parse_positive_int(request.args.get("page"), field_name="page", default=1)
        per_page = _parse_positive_int(
            request.args.get("per_page"),
            field_name="per_page",
            default=50,
        )
        include_inactive = _parse_bool_query(
            request.args.get("include_inactive"),
            field_name="include_inactive",
            default=False,
        )
        result = settings_service.list_suppliers(
            page=page,
            per_page=per_page,
            q=request.args.get("q"),
            include_inactive=include_inactive,
        )
        return jsonify(result), 200
    except SettingsServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/suppliers", methods=["POST"])
@require_role("ADMIN")
def create_supplier():
    try:
        result = settings_service.create_supplier(request.get_json(silent=True) or {})
        return jsonify(result), 201
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/suppliers/<int:supplier_id>", methods=["PUT"])
@require_role("ADMIN")
def update_supplier(supplier_id: int):
    try:
        result = settings_service.update_supplier(
            supplier_id,
            request.get_json(silent=True) or {},
        )
        return jsonify(result), 200
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/suppliers/<int:supplier_id>/deactivate", methods=["PATCH"])
@require_role("ADMIN")
def deactivate_supplier(supplier_id: int):
    try:
        result = settings_service.deactivate_supplier(supplier_id)
        return jsonify(result), 200
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/users", methods=["GET"])
@require_role("ADMIN")
def get_users():
    try:
        return jsonify(settings_service.list_users()), 200
    except SettingsServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/users", methods=["POST"])
@require_role("ADMIN")
def create_user():
    try:
        result = settings_service.create_user(request.get_json(silent=True) or {})
        return jsonify(result), 201
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/users/<int:user_id>", methods=["PUT"])
@require_role("ADMIN")
def update_user(user_id: int):
    try:
        current_user = get_current_user()
        result = settings_service.update_user(
            user_id,
            request.get_json(silent=True) or {},
            acting_user_id=current_user.id,
        )
        return jsonify(result), 200
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@settings_bp.route("/settings/users/<int:user_id>/deactivate", methods=["PATCH"])
@require_role("ADMIN")
def deactivate_user(user_id: int):
    try:
        current_user = get_current_user()
        result = settings_service.deactivate_user(
            user_id,
            acting_user_id=current_user.id,
        )
        return jsonify(result), 200
    except SettingsServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)
