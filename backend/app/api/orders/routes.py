"""Orders API routes for the Phase 8 Orders module."""

from __future__ import annotations

from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from app.extensions import db
from app.services import order_service
from app.services.order_service import OrderServiceError
from app.utils.auth import get_current_user, require_role
from app.utils.errors import api_error as _error
from app.utils.validators import QueryValidationError, parse_positive_int

orders_bp = Blueprint("orders", __name__)


@orders_bp.route("/orders/lookups/suppliers", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def lookup_suppliers():
    try:
        result = order_service.lookup_suppliers(request.args.get("q"))
        return jsonify(result), 200
    except OrderServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@orders_bp.route("/orders/lookups/articles", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def lookup_articles():
    supplier_id = request.args.get("supplier_id")
    try:
        parsed_supplier_id = None
        if supplier_id not in (None, ""):
            parsed_supplier_id = parse_positive_int(
                supplier_id,
                field_name="supplier_id",
                default=0,
            )
        result = order_service.lookup_articles(
            request.args.get("q"),
            supplier_id=parsed_supplier_id,
        )
        return jsonify(result), 200
    except (OrderServiceError, QueryValidationError) as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


_VALID_ORDER_STATUSES = {"OPEN", "CLOSED"}


@orders_bp.route("/orders", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def get_orders():
    try:
        if "q" in request.args:
            result = order_service.find_order_by_number(request.args.get("q"))
        else:
            page = parse_positive_int(request.args.get("page"), field_name="page", default=1)
            per_page = parse_positive_int(
                request.args.get("per_page"),
                field_name="per_page",
                default=50,
            )
            status_raw = request.args.get("status")
            if status_raw is not None:
                status_upper = status_raw.strip().upper()
                if status_upper not in _VALID_ORDER_STATUSES:
                    return _error(
                        "VALIDATION_ERROR",
                        f"status must be one of: {', '.join(sorted(_VALID_ORDER_STATUSES))}.",
                        400,
                    )
            else:
                status_upper = None
            result = order_service.list_orders(page, per_page, status=status_upper)
        return jsonify(result), 200
    except (OrderServiceError, QueryValidationError) as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@orders_bp.route("/orders", methods=["POST"])
@require_role("ADMIN")
def create_order():
    user = get_current_user()
    try:
        result = order_service.create_order(user.id, request.get_json(silent=True) or {})
        return jsonify(result), 201
    except OrderServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@orders_bp.route("/orders/<int:order_id>", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def get_order_detail(order_id: int):
    try:
        result = order_service.get_order_detail(order_id, view=request.args.get("view"))
        return jsonify(result), 200
    except OrderServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@orders_bp.route("/orders/<int:order_id>", methods=["PATCH"])
@require_role("ADMIN")
def update_order_header(order_id: int):
    try:
        result = order_service.update_order_header(
            order_id,
            request.get_json(silent=True) or {},
        )
        return jsonify(result), 200
    except OrderServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@orders_bp.route("/orders/<int:order_id>/lines", methods=["POST"])
@require_role("ADMIN")
def add_order_line(order_id: int):
    try:
        result = order_service.add_order_line(
            order_id,
            request.get_json(silent=True) or {},
        )
        return jsonify(result), 200
    except OrderServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@orders_bp.route("/orders/<int:order_id>/lines/<int:line_id>", methods=["PATCH"])
@require_role("ADMIN")
def update_order_line(order_id: int, line_id: int):
    try:
        result = order_service.update_order_line(
            order_id,
            line_id,
            request.get_json(silent=True) or {},
        )
        return jsonify(result), 200
    except OrderServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@orders_bp.route("/orders/<int:order_id>/lines/<int:line_id>", methods=["DELETE"])
@require_role("ADMIN")
def remove_order_line(order_id: int, line_id: int):
    try:
        result = order_service.remove_order_line(order_id, line_id)
        return jsonify(result), 200
    except OrderServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@orders_bp.route("/orders/<int:order_id>/pdf", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def generate_order_pdf(order_id: int):
    try:
        pdf_bytes, order_number = order_service.generate_order_pdf(order_id)
        return send_file(
            BytesIO(pdf_bytes),
            mimetype="application/pdf",
            download_name=f"{order_number}.pdf",
            as_attachment=False,
        )
    except OrderServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)
