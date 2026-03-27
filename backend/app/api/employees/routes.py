"""Employees API routes (Phase 11).

RBAC:
  ADMIN        — full access (all verbs)
  WAREHOUSE_STAFF — GET-only (list, detail, quotas, issuances)
  Issuance lookup + check + create — ADMIN only
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.services.employee_service import EmployeeServiceError
from app.services import employee_service
from app.utils.auth import get_current_user, require_role
from app.utils.errors import api_error as _error
from app.utils.validators import (
    QueryValidationError,
    parse_bool_query,
    parse_positive_int,
)

employees_bp = Blueprint("employees", __name__)


# ---------------------------------------------------------------------------
# Lookups (must be defined BEFORE /<id> routes to avoid route ambiguity)
# ---------------------------------------------------------------------------

@employees_bp.route("/employees/lookups/articles", methods=["GET"])
@require_role("ADMIN")
def lookup_articles():
    """GET /api/v1/employees/lookups/articles?q=query"""
    try:
        result = employee_service.lookup_issuance_articles(request.args.get("q"))
        return jsonify(result), 200
    except EmployeeServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


# ---------------------------------------------------------------------------
# Employee list + create
# ---------------------------------------------------------------------------

@employees_bp.route("/employees", methods=["GET"])
@require_role("ADMIN", "WAREHOUSE_STAFF")
def list_employees():
    try:
        page = parse_positive_int(request.args.get("page"), field_name="page", default=1)
        per_page = parse_positive_int(
            request.args.get("per_page"), field_name="per_page", default=50
        )
        include_inactive = parse_bool_query(
            request.args.get("include_inactive"),
            field_name="include_inactive",
            default=False,
        )
        result = employee_service.list_employees(
            page=page,
            per_page=per_page,
            q=request.args.get("q"),
            include_inactive=include_inactive,
        )
        return jsonify(result), 200
    except (EmployeeServiceError, QueryValidationError) as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@employees_bp.route("/employees", methods=["POST"])
@require_role("ADMIN")
def create_employee():
    try:
        result = employee_service.create_employee(request.get_json(silent=True) or {})
        return jsonify(result), 201
    except EmployeeServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


# ---------------------------------------------------------------------------
# Employee detail, edit, deactivate
# ---------------------------------------------------------------------------

@employees_bp.route("/employees/<int:employee_id>", methods=["GET"])
@require_role("ADMIN", "WAREHOUSE_STAFF")
def get_employee(employee_id: int):
    try:
        return jsonify(employee_service.get_employee(employee_id)), 200
    except EmployeeServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@employees_bp.route("/employees/<int:employee_id>", methods=["PUT"])
@require_role("ADMIN")
def update_employee(employee_id: int):
    try:
        result = employee_service.update_employee(
            employee_id, request.get_json(silent=True) or {}
        )
        return jsonify(result), 200
    except EmployeeServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@employees_bp.route("/employees/<int:employee_id>/deactivate", methods=["PATCH"])
@require_role("ADMIN")
def deactivate_employee(employee_id: int):
    try:
        return jsonify(employee_service.deactivate_employee(employee_id)), 200
    except EmployeeServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


# ---------------------------------------------------------------------------
# Quota overview
# ---------------------------------------------------------------------------

@employees_bp.route("/employees/<int:employee_id>/quotas", methods=["GET"])
@require_role("ADMIN", "WAREHOUSE_STAFF")
def get_quotas(employee_id: int):
    try:
        return jsonify(employee_service.get_quota_overview(employee_id)), 200
    except EmployeeServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


# ---------------------------------------------------------------------------
# Issuance history, check, create
# ---------------------------------------------------------------------------

@employees_bp.route("/employees/<int:employee_id>/issuances", methods=["GET"])
@require_role("ADMIN", "WAREHOUSE_STAFF")
def list_issuances(employee_id: int):
    try:
        page = parse_positive_int(request.args.get("page"), field_name="page", default=1)
        per_page = parse_positive_int(
            request.args.get("per_page"), field_name="per_page", default=50
        )
        result = employee_service.list_issuances(employee_id, page, per_page)
        return jsonify(result), 200
    except (EmployeeServiceError, QueryValidationError) as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@employees_bp.route("/employees/<int:employee_id>/issuances/check", methods=["POST"])
@require_role("ADMIN")
def check_issuance(employee_id: int):
    try:
        result = employee_service.check_issuance(
            employee_id, request.get_json(silent=True) or {}
        )
        return jsonify(result), 200
    except EmployeeServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@employees_bp.route("/employees/<int:employee_id>/issuances", methods=["POST"])
@require_role("ADMIN")
def create_issuance(employee_id: int):
    try:
        current_user = get_current_user()
        result, warning = employee_service.create_issuance(
            employee_id,
            request.get_json(silent=True) or {},
            issued_by_user=current_user,
        )
        response = result.copy()
        if warning:
            response["warning"] = warning
        return jsonify(response), 201
    except EmployeeServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)
