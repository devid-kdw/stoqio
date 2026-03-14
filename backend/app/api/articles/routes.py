"""Articles API routes for Phase 9 Warehouse + Draft compatibility."""

from __future__ import annotations

from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from app.extensions import db
from app.services import article_service
from app.services.article_service import ArticleServiceError
from app.services.barcode_service import BarcodeServiceError
from app.services import barcode_service
from app.utils.auth import get_current_user, require_role

articles_bp = Blueprint("articles", __name__)

_WAREHOUSE_LIST_PARAMS = {"page", "per_page", "category", "include_inactive"}


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


def _forbidden(role: str):
    return _error(
        "FORBIDDEN",
        f"Role '{role}' is not permitted for this endpoint.",
        403,
    )


def _parse_positive_int(value, *, field_name: str, default: int) -> int:
    raw_value = default if value is None else value
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be a valid integer.",
            400,
        ) from None
    if parsed <= 0:
        raise ArticleServiceError(
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
    raise ArticleServiceError(
        "VALIDATION_ERROR",
        f"{field_name} must be 'true' or 'false'.",
        400,
    )


def _is_warehouse_list_request() -> bool:
    return any(param in request.args for param in _WAREHOUSE_LIST_PARAMS)


def _current_role() -> str:
    user = get_current_user()
    return user.role.value if hasattr(user.role, "value") else str(user.role)


@articles_bp.route("/articles/lookups/categories", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def get_category_lookups():
    return jsonify(article_service.lookup_categories()), 200


@articles_bp.route("/articles/lookups/uoms", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def get_uom_lookups():
    return jsonify(article_service.lookup_uoms()), 200


@articles_bp.route("/identifier", methods=["GET"])
@require_role("ADMIN", "MANAGER", "WAREHOUSE_STAFF", "VIEWER")
def search_identifier():
    try:
        result = article_service.search_identifier_articles(
            request.args.get("q"),
            role=_current_role(),
        )
        return jsonify(result), 200
    except ArticleServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@articles_bp.route("/identifier/reports", methods=["POST"])
@require_role("ADMIN", "MANAGER", "WAREHOUSE_STAFF", "VIEWER")
def submit_missing_article_report():
    try:
        current_user = get_current_user()
        result, created = article_service.submit_missing_article_report(
            request.get_json(silent=True) or {},
            reported_by_id=current_user.id,
        )
        return jsonify(result), 201 if created else 200
    except ArticleServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@articles_bp.route("/identifier/reports", methods=["GET"])
@require_role("ADMIN")
def get_missing_article_reports():
    try:
        return jsonify(
            article_service.list_missing_article_reports(request.args.get("status"))
        ), 200
    except ArticleServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@articles_bp.route("/identifier/reports/<int:report_id>/resolve", methods=["POST"])
@require_role("ADMIN")
def resolve_missing_article_report(report_id: int):
    try:
        result = article_service.resolve_missing_article_report(
            report_id,
            request.get_json(silent=True) or {},
        )
        return jsonify(result), 200
    except ArticleServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@articles_bp.route("/articles", methods=["GET"])
@require_role("ADMIN", "MANAGER", "OPERATOR")
def get_articles():
    role = _current_role()
    try:
        if _is_warehouse_list_request():
            if role not in {"ADMIN", "MANAGER"}:
                return _forbidden(role)

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
            result = article_service.list_articles(
                page,
                per_page,
                q=request.args.get("q"),
                category_key=request.args.get("category"),
                include_inactive=include_inactive,
            )
            return jsonify(result), 200

        if role not in {"ADMIN", "OPERATOR"}:
            return _forbidden(role)

        result = article_service.find_article_for_lookup(request.args.get("q"))
        return jsonify(result), 200
    except ArticleServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@articles_bp.route("/articles", methods=["POST"])
@require_role("ADMIN")
def create_article():
    try:
        result = article_service.create_article(request.get_json(silent=True) or {})
        return jsonify(result), 201
    except ArticleServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@articles_bp.route("/articles/<int:article_id>", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def get_article_detail(article_id: int):
    try:
        return jsonify(article_service.get_article_detail(article_id)), 200
    except ArticleServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@articles_bp.route("/articles/<int:article_id>", methods=["PUT"])
@require_role("ADMIN")
def update_article(article_id: int):
    try:
        result = article_service.update_article(
            article_id,
            request.get_json(silent=True) or {},
        )
        return jsonify(result), 200
    except ArticleServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@articles_bp.route("/articles/<int:article_id>/deactivate", methods=["PATCH"])
@require_role("ADMIN")
def deactivate_article(article_id: int):
    try:
        return jsonify(article_service.deactivate_article(article_id)), 200
    except ArticleServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@articles_bp.route("/articles/<int:article_id>/transactions", methods=["GET"])
@require_role("ADMIN", "MANAGER")
def get_article_transactions(article_id: int):
    try:
        page = _parse_positive_int(request.args.get("page"), field_name="page", default=1)
        per_page = _parse_positive_int(
            request.args.get("per_page"),
            field_name="per_page",
            default=50,
        )
        result = article_service.list_article_transactions(article_id, page, per_page)
        return jsonify(result), 200
    except ArticleServiceError as exc:
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@articles_bp.route("/articles/<int:article_id>/barcode", methods=["GET"])
@require_role("ADMIN")
def get_article_barcode(article_id: int):
    try:
        content, filename, mimetype = barcode_service.generate_article_barcode_pdf(
            article_id
        )
        return send_file(
            BytesIO(content),
            mimetype=mimetype,
            download_name=filename,
            as_attachment=True,
        )
    except BarcodeServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)


@articles_bp.route("/batches/<int:batch_id>/barcode", methods=["GET"])
@require_role("ADMIN")
def get_batch_barcode(batch_id: int):
    try:
        content, filename, mimetype = barcode_service.generate_batch_barcode_pdf(
            batch_id
        )
        return send_file(
            BytesIO(content),
            mimetype=mimetype,
            download_name=filename,
            as_attachment=True,
        )
    except BarcodeServiceError as exc:
        db.session.rollback()
        return _error(exc.error, exc.message, exc.status_code, exc.details)
