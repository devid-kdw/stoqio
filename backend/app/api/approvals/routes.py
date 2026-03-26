"""API routes for Approvals (Phase 6)."""

from decimal import Decimal
from flask import Blueprint, jsonify, request

from app.services import approval_service
from app.utils.auth import get_current_user, require_role
from app.utils.errors import api_error as _error

approvals_bp = Blueprint("approvals", __name__)


@approvals_bp.route("/approvals", methods=["GET"])
@require_role("ADMIN")
def get_approvals():
    status_filter = request.args.get("status", "pending")
    
    if status_filter == "history":
        groups = approval_service.get_history_draft_groups()
    else:
        # pending is default
        groups = approval_service.get_pending_draft_groups()
    
    return jsonify({
        "items": groups,
        "total": len(groups),
        "page": 1,
        "per_page": max(len(groups), 50)
    }), 200


@approvals_bp.route("/approvals/<int:group_id>", methods=["GET"])
@require_role("ADMIN")
def get_approval_group_detail(group_id: int):
    detail = approval_service.get_draft_group_detail(group_id)
    if not detail:
        return _error("NOT_FOUND", "Draft group not found.", 404)
    return jsonify(detail), 200


@approvals_bp.route("/approvals/<int:group_id>/lines/<int:line_id>", methods=["PATCH"])
@require_role("ADMIN")
def edit_aggregated_line(group_id: int, line_id: int):
    body = request.get_json(silent=True) or {}
    raw_quantity = body.get("quantity")

    if raw_quantity is None:
        return _error("VALIDATION_ERROR", "quantity is required.", 400)
    try:
        quantity = Decimal(str(raw_quantity))
        if quantity <= 0:
            return _error("VALIDATION_ERROR", "quantity must be greater than zero.", 400)
    except (ValueError, TypeError):
        return _error("VALIDATION_ERROR", "quantity must be a number.", 400)

    updated_detail = approval_service.edit_aggregated_line(group_id, line_id, quantity)
    if not updated_detail:
        return _error("NOT_FOUND", "Line or group not found.", 404)

    return jsonify(updated_detail), 200


@approvals_bp.route("/approvals/<int:group_id>/lines/<int:line_id>/approve", methods=["POST"])
@require_role("ADMIN")
def approve_single_line(group_id: int, line_id: int):
    user = get_current_user()
    try:
        result = approval_service.approve_line(user.id, group_id, line_id)
        return jsonify(result), 200
    except ValueError as e:
        msg = str(e)
        if "already been approved" in msg or "processed" in msg:
            return _error("CONFLICT", msg, 409)
        elif "Insufficient stock" in msg:
            return _error("INSUFFICIENT_STOCK", msg, 409)
        return _error("BAD_REQUEST", msg, 400)


@approvals_bp.route("/approvals/<int:group_id>/approve", methods=["POST"])
@require_role("ADMIN")
def approve_all(group_id: int):
    user = get_current_user()
    result = approval_service.approve_all(user.id, group_id)
    return jsonify(result), 200


@approvals_bp.route("/approvals/<int:group_id>/lines/<int:line_id>/reject", methods=["POST"])
@require_role("ADMIN")
def reject_single_line(group_id: int, line_id: int):
    user = get_current_user()
    body = request.get_json(silent=True) or {}
    raw_reason = body.get("reason", "")
    reason = raw_reason.strip() if isinstance(raw_reason, str) else ""
    reason = reason or None  # normalize blank to None

    if reason is not None and len(reason) > 500:
        return _error("VALIDATION_ERROR", "Reason must be max 500 characters.", 400)

    try:
        result = approval_service.reject_line(user.id, group_id, line_id, reason)
        return jsonify(result), 200
    except ValueError as e:
        msg = str(e)
        if "processed" in msg:
            return _error("CONFLICT", msg, 409)
        return _error("BAD_REQUEST", msg, 400)


@approvals_bp.route("/approvals/<int:group_id>/reject", methods=["POST"])
@require_role("ADMIN")
def reject_group(group_id: int):
    user = get_current_user()
    body = request.get_json(silent=True) or {}
    raw_reason = body.get("reason", "")
    reason = raw_reason.strip() if isinstance(raw_reason, str) else ""
    reason = reason or None  # normalize blank to None

    if reason is not None and len(reason) > 500:
        return _error("VALIDATION_ERROR", "Reason must be max 500 characters.", 400)

    try:
        result = approval_service.reject_group(user.id, group_id, reason)
        return jsonify(result), 200
    except ValueError as e:
        return _error("BAD_REQUEST", str(e), 400)
