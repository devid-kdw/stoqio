"""Reports API routes for the Phase 13 Reports module."""

from __future__ import annotations

from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from app.extensions import db
from app.services import report_service
from app.services.report_service import ReportServiceError
from app.utils.auth import check_rate_limit, require_role
from app.utils.errors import api_error as _error

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/reports/stock-overview", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def get_stock_overview():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 100))
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 1
        result = report_service.get_stock_overview(
            date_from=request.args.get("date_from"),
            date_to=request.args.get("date_to"),
            category=request.args.get("category"),
            reorder_only=request.args.get("reorder_only"),
            page=page,
            per_page=per_page,
        )
        return jsonify(result), 200
    except ReportServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@reports_bp.route("/reports/stock-overview/export", methods=["GET"])
@require_role("ADMIN")
def export_stock_overview():
    ip = request.remote_addr or "unknown"
    allowed = check_rate_limit(f"export:{ip}", max_requests=30, window_seconds=60)
    if not allowed:
        return _error("TOO_MANY_REQUESTS", "Too many requests. Please wait.", 429)
    try:
        content, filename, mimetype = report_service.export_stock_overview(
            export_format=request.args.get("format"),
            date_from=request.args.get("date_from"),
            date_to=request.args.get("date_to"),
            category=request.args.get("category"),
            reorder_only=request.args.get("reorder_only"),
        )
        return send_file(
            BytesIO(content),
            mimetype=mimetype,
            download_name=filename,
            as_attachment=True,
        )
    except ReportServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@reports_bp.route("/reports/surplus", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def get_surplus_report():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 100))
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 1
        return jsonify(report_service.get_surplus_report(page=page, per_page=per_page)), 200
    except ReportServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@reports_bp.route("/reports/surplus/export", methods=["GET"])
@require_role("ADMIN")
def export_surplus_report():
    ip = request.remote_addr or "unknown"
    allowed = check_rate_limit(f"export:{ip}", max_requests=30, window_seconds=60)
    if not allowed:
        return _error("TOO_MANY_REQUESTS", "Too many requests. Please wait.", 429)
    try:
        content, filename, mimetype = report_service.export_surplus_report(
            export_format=request.args.get("format"),
        )
        return send_file(
            BytesIO(content),
            mimetype=mimetype,
            download_name=filename,
            as_attachment=True,
        )
    except ReportServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@reports_bp.route("/reports/transactions", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def get_transaction_log():
    try:
        result = report_service.get_transaction_log(
            article_id=request.args.get("article_id"),
            date_from=request.args.get("date_from"),
            date_to=request.args.get("date_to"),
            tx_types=request.args.getlist("tx_type"),
            page=request.args.get("page"),
            per_page=request.args.get("per_page"),
        )
        return jsonify(result), 200
    except ReportServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@reports_bp.route("/reports/transactions/export", methods=["GET"])
@require_role("ADMIN")
def export_transaction_log():
    ip = request.remote_addr or "unknown"
    allowed = check_rate_limit(f"export:{ip}", max_requests=30, window_seconds=60)
    if not allowed:
        return _error("TOO_MANY_REQUESTS", "Too many requests. Please wait.", 429)
    try:
        content, filename, mimetype = report_service.export_transaction_log(
            export_format=request.args.get("format"),
            article_id=request.args.get("article_id"),
            date_from=request.args.get("date_from"),
            date_to=request.args.get("date_to"),
            tx_types=request.args.getlist("tx_type"),
        )
        return send_file(
            BytesIO(content),
            mimetype=mimetype,
            download_name=filename,
            as_attachment=True,
        )
    except ReportServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@reports_bp.route("/reports/statistics/top-consumption", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def get_top_consumption_statistics():
    try:
        return jsonify(
            report_service.get_top_consumption_statistics(
                request.args.get("period")
            )
        ), 200
    except ReportServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@reports_bp.route("/reports/statistics/movement", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def get_movement_statistics():
    try:
        return jsonify(
            report_service.get_movement_statistics(request.args.get("range"))
        ), 200
    except ReportServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@reports_bp.route("/reports/statistics/reorder-summary", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def get_reorder_summary_statistics():
    try:
        return jsonify(report_service.get_reorder_summary_statistics()), 200
    except ReportServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@reports_bp.route("/reports/statistics/personal-issuances", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def get_personal_issuances_statistics():
    try:
        return jsonify(report_service.get_personal_issuances_statistics()), 200
    except ReportServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)
