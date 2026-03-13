"""Minimal order lookup/detail routes required by Phase 7 Receiving."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services import receiving_service
from app.services.receiving_service import ReceivingServiceError
from app.utils.auth import require_role

orders_bp = Blueprint("orders", __name__)


def _error(error: str, message: str, status_code: int, details=None):
    return (
        jsonify(
            {
                "error": error,
                "message": message,
                "details": details or {},
            }
        ),
        status_code,
    )


@orders_bp.route("/orders", methods=["GET"])
@require_role("ADMIN")
def find_order():
    try:
        result = receiving_service.find_order_by_number(request.args.get("q"))
        return jsonify(result), 200
    except ReceivingServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@orders_bp.route("/orders/<int:order_id>", methods=["GET"])
@require_role("ADMIN")
def get_order_detail(order_id: int):
    try:
        result = receiving_service.get_order_detail(order_id)
        return jsonify(result), 200
    except ReceivingServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)
