"""Business logic for the Phase 9 Warehouse articles module."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.article import Article
from app.models.article_alias import ArticleAlias
from app.models.article_supplier import ArticleSupplier
from app.models.batch import Batch
from app.models.category import Category
from app.models.draft import Draft
from app.models.enums import DraftStatus, MissingArticleReportStatus
from app.models.missing_article_report import MissingArticleReport
from app.models.stock import Stock
from app.models.supplier import Supplier
from app.models.surplus import Surplus
from app.models.transaction import Transaction
from app.models.uom_catalog import UomCatalog

_QTY_QUANT = Decimal("0.001")
_ARTICLE_NO_RE = re.compile(r"^[A-Z0-9-]+$")
_SUPPLIERS_MISSING = object()


class ArticleServiceError(Exception):
    """Structured service error that maps directly to API responses."""

    def __init__(
        self,
        error: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error = error
        self.message = message
        self.status_code = status_code
        self.details = details or {}


@dataclass(slots=True)
class PreparedArticlePayload:
    """Validated article payload prepared for persistence."""

    article_no: str
    description: str
    category: Category
    base_uom: UomCatalog
    pack_size: Decimal | None
    pack_uom: UomCatalog | None
    barcode: str | None
    manufacturer: str | None
    manufacturer_art_number: str | None
    has_batch: bool
    reorder_threshold: Decimal | None
    reorder_coverage_days: int | None
    density: Decimal
    is_active: bool


@dataclass(slots=True)
class PreparedArticleSupplierPayload:
    """Validated supplier-link payload prepared for persistence."""

    supplier: Supplier
    supplier_article_code: str | None
    is_preferred: bool


@dataclass(slots=True)
class IdentifierMatch:
    """Resolved Identifier search match metadata for one article."""

    matched_via: str
    matched_alias: str | None
    sort_rank: int


def _quantize_quantity(value: Decimal) -> Decimal:
    return value.quantize(_QTY_QUANT, rounding=ROUND_HALF_UP)


def _decimal_from_model(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    trimmed = value.strip()
    return trimmed or None


def _normalize_identifier_term(value: Any) -> str | None:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    return normalized.lower()


def _validate_allowed_fields(
    payload: dict[str, Any],
    *,
    allowed_fields: set[str],
) -> None:
    extra_fields = sorted(set(payload.keys()) - allowed_fields)
    if extra_fields:
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            f"Unsupported fields: {', '.join(extra_fields)}.",
            400,
            {"fields": extra_fields},
        )


def _require_text(
    value: Any,
    *,
    field_name: str,
    max_length: int,
    details: dict[str, Any] | None = None,
) -> str:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            f"{field_name} is required.",
            400,
            details,
        )
    if len(normalized) > max_length:
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be {max_length} characters or fewer.",
            400,
            details,
        )
    return normalized


def _parse_int(
    value: Any,
    *,
    field_name: str,
    details: dict[str, Any] | None = None,
) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be a valid integer.",
            400,
            details,
        ) from None
    if parsed <= 0:
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be greater than zero.",
            400,
            details,
        )
    return parsed


def _parse_optional_positive_int(
    value: Any,
    *,
    field_name: str,
    details: dict[str, Any] | None = None,
) -> int | None:
    if value in (None, ""):
        return None
    return _parse_int(value, field_name=field_name, details=details)


def _parse_optional_decimal(
    value: Any,
    *,
    field_name: str,
    allow_zero: bool = False,
    details: dict[str, Any] | None = None,
) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be a valid number.",
            400,
            details,
        ) from None

    if allow_zero:
        valid = parsed >= 0
        comparator = "greater than or equal to zero"
    else:
        valid = parsed > 0
        comparator = "greater than zero"

    if not valid:
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be {comparator}.",
            400,
            details,
        )
    return _quantize_quantity(parsed)


def _parse_bool(
    value: Any,
    *,
    field_name: str,
    default: bool | None = None,
    details: dict[str, Any] | None = None,
) -> bool:
    if value is None:
        if default is not None:
            return default
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be a boolean.",
            400,
            details,
        )

    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1"}:
            return True
        if normalized in {"false", "0"}:
            return False

    raise ArticleServiceError(
        "VALIDATION_ERROR",
        f"{field_name} must be a boolean.",
        400,
        details,
    )


def _normalize_article_no(value: Any) -> str:
    article_no = _require_text(value, field_name="article_no", max_length=50)
    normalized = article_no.upper()
    if not _ARTICLE_NO_RE.fullmatch(normalized):
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            "article_no may contain only letters, digits, and hyphens.",
            400,
        )
    return normalized


def _uom_is_active(uom: UomCatalog | None) -> bool:
    if uom is None:
        return False
    return bool(getattr(uom, "is_active", True))


def _get_category(category_id: int, *, require_active: bool) -> Category:
    category = db.session.get(Category, category_id)
    if category is None:
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            "category_id must reference an existing category.",
            400,
            {"category_id": category_id},
        )
    if require_active and not category.is_active:
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            "category_id must reference an active category.",
            400,
            {"category_id": category_id},
        )
    return category


def _get_uom_by_code(
    code: str | None,
    *,
    field_name: str,
    require_active: bool,
) -> UomCatalog | None:
    normalized = _normalize_optional_text(code)
    if normalized is None:
        return None

    uom = UomCatalog.query.filter(func.lower(UomCatalog.code) == normalized.lower()).first()
    if uom is None:
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must reference an existing UOM code.",
            400,
            {field_name: normalized},
        )
    if require_active and not _uom_is_active(uom):
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must reference an active UOM code.",
            400,
            {field_name: normalized},
        )
    return uom


def _get_article(article_id: int) -> Article:
    article = (
        Article.query
        .options(
            joinedload(Article.category),
            joinedload(Article.base_uom_ref),
            joinedload(Article.pack_uom_ref),
        )
        .filter(Article.id == article_id)
        .first()
    )
    if article is None:
        raise ArticleServiceError(
            "ARTICLE_NOT_FOUND",
            "Article not found.",
            404,
            {"article_id": article_id},
        )
    return article


def _serialize_category(category: Category | None) -> dict[str, Any]:
    return {
        "category_id": category.id if category else None,
        "category_key": category.key if category else None,
        "category_label_hr": category.label_hr if category else None,
    }


def _serialize_uom_code(uom: UomCatalog | None, fallback: Any) -> str | None:
    if uom is not None:
        return uom.code
    if fallback is None:
        return None
    return str(fallback)


def _build_article_totals_map(article_ids: list[int]) -> dict[int, tuple[Decimal, Decimal]]:
    if not article_ids:
        return {}

    stock_rows = (
        db.session.query(
            Stock.article_id,
            func.coalesce(func.sum(Stock.quantity), 0),
        )
        .filter(Stock.article_id.in_(article_ids))
        .group_by(Stock.article_id)
        .all()
    )
    surplus_rows = (
        db.session.query(
            Surplus.article_id,
            func.coalesce(func.sum(Surplus.quantity), 0),
        )
        .filter(Surplus.article_id.in_(article_ids))
        .group_by(Surplus.article_id)
        .all()
    )

    totals = {
        article_id: (Decimal("0"), Decimal("0"))
        for article_id in article_ids
    }

    for article_id, quantity in stock_rows:
        _stock_total, surplus_total = totals.get(article_id, (Decimal("0"), Decimal("0")))
        totals[article_id] = (_decimal_from_model(quantity), surplus_total)

    for article_id, quantity in surplus_rows:
        stock_total, _surplus_total = totals.get(article_id, (Decimal("0"), Decimal("0")))
        totals[article_id] = (stock_total, _decimal_from_model(quantity))

    return totals


def _build_batch_totals(article_id: int) -> tuple[dict[int, Decimal], dict[int, Decimal]]:
    stock_rows = (
        db.session.query(
            Stock.batch_id,
            func.coalesce(func.sum(Stock.quantity), 0),
        )
        .filter(
            Stock.article_id == article_id,
            Stock.batch_id.isnot(None),
        )
        .group_by(Stock.batch_id)
        .all()
    )
    surplus_rows = (
        db.session.query(
            Surplus.batch_id,
            func.coalesce(func.sum(Surplus.quantity), 0),
        )
        .filter(
            Surplus.article_id == article_id,
            Surplus.batch_id.isnot(None),
        )
        .group_by(Surplus.batch_id)
        .all()
    )

    stock_totals = {
        batch_id: _decimal_from_model(quantity)
        for batch_id, quantity in stock_rows
        if batch_id is not None
    }
    surplus_totals = {
        batch_id: _decimal_from_model(quantity)
        for batch_id, quantity in surplus_rows
        if batch_id is not None
    }
    return stock_totals, surplus_totals


def _get_reorder_status(
    stock_total: Decimal,
    surplus_total: Decimal,
    threshold_value: Any,
) -> str:
    if threshold_value is None:
        return "NORMAL"

    threshold = _decimal_from_model(threshold_value)
    available_qty = stock_total + surplus_total
    if available_qty <= threshold:
        return "RED"
    if available_qty <= (threshold * Decimal("1.10")):
        return "YELLOW"
    return "NORMAL"


def _serialize_batch(
    batch: Batch,
    *,
    stock_total: Decimal,
    surplus_total: Decimal,
) -> dict[str, Any]:
    return {
        "id": batch.id,
        "batch_code": batch.batch_code,
        "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
        "stock_total": float(stock_total),
        "surplus_total": float(surplus_total),
    }


def _serialize_supplier(link: ArticleSupplier) -> dict[str, Any]:
    supplier = link.supplier
    return {
        "id": link.id,
        "supplier_id": link.supplier_id,
        "supplier_name": supplier.name if supplier else None,
        "supplier_internal_code": supplier.internal_code if supplier else None,
        "supplier_article_code": link.supplier_article_code,
        "last_price": (
            float(_decimal_from_model(link.last_price))
            if link.last_price is not None
            else None
        ),
        "last_ordered_at": (
            link.last_ordered_at.isoformat() if link.last_ordered_at else None
        ),
        "is_preferred": link.is_preferred,
        "is_active": supplier.is_active if supplier else None,
    }


def _serialize_alias(alias: ArticleAlias) -> dict[str, Any]:
    return {
        "id": alias.id,
        "alias": alias.alias,
        "normalized": alias.normalized,
    }


def _serialize_missing_article_report(report: MissingArticleReport) -> dict[str, Any]:
    return {
        "id": report.id,
        "search_term": report.search_term,
        "report_count": int(report.report_count or 0),
        "status": report.status.value if hasattr(report.status, "value") else report.status,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "resolution_note": report.resolution_note,
        "resolved_at": report.resolved_at.isoformat() if report.resolved_at else None,
    }


def _serialize_lookup_article(article: Article) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": article.id,
        "article_no": article.article_no,
        "description": article.description,
        "base_uom": _serialize_uom_code(article.base_uom_ref, article.base_uom),
        "has_batch": article.has_batch,
    }

    if article.has_batch:
        batches = (
            Batch.query
            .filter_by(article_id=article.id)
            .order_by(Batch.expiry_date.asc(), Batch.id.asc())
            .all()
        )
        data["batches"] = [
            {
                "id": batch.id,
                "batch_code": batch.batch_code,
                "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
            }
            for batch in batches
        ]

    return data


def _serialize_list_item(
    article: Article,
    *,
    stock_total: Decimal,
    surplus_total: Decimal,
) -> dict[str, Any]:
    category_data = _serialize_category(article.category)
    return {
        "id": article.id,
        "article_no": article.article_no,
        "description": article.description,
        **category_data,
        "base_uom": _serialize_uom_code(article.base_uom_ref, article.base_uom),
        "stock_total": float(stock_total),
        "surplus_total": float(surplus_total),
        "reorder_threshold": (
            float(_decimal_from_model(article.reorder_threshold))
            if article.reorder_threshold is not None
            else None
        ),
        "reorder_status": _get_reorder_status(
            stock_total,
            surplus_total,
            article.reorder_threshold,
        ),
        "is_active": article.is_active,
    }


def _resolve_identifier_match(
    article: Article,
    aliases: list[ArticleAlias],
    *,
    normalized_query: str,
) -> IdentifierMatch | None:
    article_no = (article.article_no or "").strip().lower()
    barcode = (article.barcode or "").strip().lower()
    description = (article.description or "").strip().lower()

    exact_alias = next(
        (
            alias
            for alias in aliases
            if normalized_query == _normalize_identifier_term(alias.normalized)
        ),
        None,
    )
    partial_alias = next(
        (
            alias
            for alias in aliases
            if normalized_query in (_normalize_identifier_term(alias.normalized) or "")
        ),
        None,
    )

    if article_no == normalized_query:
        return IdentifierMatch("article_no", None, 0)
    if barcode and barcode == normalized_query:
        return IdentifierMatch("barcode", None, 1)
    if exact_alias is not None:
        return IdentifierMatch("alias", exact_alias.alias, 2)
    if normalized_query in article_no:
        return IdentifierMatch("article_no", None, 3)
    if barcode and normalized_query in barcode:
        return IdentifierMatch("barcode", None, 4)
    if partial_alias is not None:
        return IdentifierMatch("alias", partial_alias.alias, 5)
    if normalized_query in description:
        return IdentifierMatch("description", None, 6)
    return None


def _serialize_identifier_item(
    article: Article,
    *,
    stock_total: Decimal,
    surplus_total: Decimal,
    match: IdentifierMatch,
    role: str,
) -> dict[str, Any]:
    item = {
        "id": article.id,
        "article_no": article.article_no,
        "description": article.description,
        "category_label_hr": article.category.label_hr if article.category else None,
        "base_uom": _serialize_uom_code(article.base_uom_ref, article.base_uom),
        "decimal_display": (
            bool(article.base_uom_ref.decimal_display)
            if article.base_uom_ref is not None
            else None
        ),
        "matched_via": match.matched_via,
        "matched_alias": match.matched_alias,
    }
    if role == "VIEWER":
        item["in_stock"] = (stock_total + surplus_total) > 0
    else:
        item["stock"] = float(stock_total)
        item["surplus"] = float(surplus_total)
    return item


def _serialize_detail(article: Article) -> dict[str, Any]:
    stock_total, surplus_total = _build_article_totals_map([article.id]).get(
        article.id,
        (Decimal("0"), Decimal("0")),
    )
    pending_draft_count = (
        db.session.query(func.count(Draft.id))
        .filter(
            Draft.article_id == article.id,
            Draft.status == DraftStatus.DRAFT,
        )
        .scalar()
    ) or 0
    category_data = _serialize_category(article.category)

    suppliers = (
        ArticleSupplier.query
        .options(joinedload(ArticleSupplier.supplier))
        .filter(ArticleSupplier.article_id == article.id)
        .order_by(ArticleSupplier.is_preferred.desc(), ArticleSupplier.id.asc())
        .all()
    )
    aliases = (
        ArticleAlias.query
        .filter(ArticleAlias.article_id == article.id)
        .order_by(ArticleAlias.id.asc())
        .all()
    )

    response = {
        "id": article.id,
        "article_no": article.article_no,
        "description": article.description,
        **category_data,
        "base_uom": _serialize_uom_code(article.base_uom_ref, article.base_uom),
        "pack_size": (
            float(_decimal_from_model(article.pack_size))
            if article.pack_size is not None
            else None
        ),
        "pack_uom": _serialize_uom_code(article.pack_uom_ref, article.pack_uom),
        "barcode": article.barcode,
        "manufacturer": article.manufacturer,
        "manufacturer_art_number": article.manufacturer_art_number,
        "has_batch": article.has_batch,
        "reorder_threshold": (
            float(_decimal_from_model(article.reorder_threshold))
            if article.reorder_threshold is not None
            else None
        ),
        "reorder_coverage_days": article.reorder_coverage_days,
        "density": float(_decimal_from_model(article.density, default="1.0")),
        "stock_total": float(stock_total),
        "surplus_total": float(surplus_total),
        "reorder_status": _get_reorder_status(
            stock_total,
            surplus_total,
            article.reorder_threshold,
        ),
        "pending_draft_count": int(pending_draft_count),
        "has_pending_drafts": pending_draft_count > 0,
        "is_active": article.is_active,
        "created_at": article.created_at.isoformat() if article.created_at else None,
        "updated_at": article.updated_at.isoformat() if article.updated_at else None,
        "suppliers": [_serialize_supplier(link) for link in suppliers],
        "aliases": [_serialize_alias(alias) for alias in aliases],
    }

    if article.has_batch:
        batch_stock_totals, batch_surplus_totals = _build_batch_totals(article.id)
        batches = (
            Batch.query
            .filter(Batch.article_id == article.id)
            .order_by(Batch.expiry_date.asc(), Batch.id.asc())
            .all()
        )
        response["batches"] = [
            _serialize_batch(
                batch,
                stock_total=batch_stock_totals.get(batch.id, Decimal("0")),
                surplus_total=batch_surplus_totals.get(batch.id, Decimal("0")),
            )
            for batch in batches
        ]

    return response


def _prepare_article_suppliers_payload(
    value: Any,
    *,
    treat_missing_as_empty: bool,
) -> list[PreparedArticleSupplierPayload] | None:
    if value is _SUPPLIERS_MISSING:
        return [] if treat_missing_as_empty else None
    if not isinstance(value, list):
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            "suppliers must be an array.",
            400,
        )
    if not value:
        return []

    normalized_rows: list[dict[str, Any]] = []
    supplier_ids: list[int] = []
    seen_supplier_ids: set[int] = set()
    duplicate_supplier_ids: set[int] = set()

    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise ArticleServiceError(
                "VALIDATION_ERROR",
                f"suppliers[{index}] must be an object.",
                400,
                {"index": index},
            )
        _validate_allowed_fields(
            entry,
            allowed_fields={"supplier_id", "supplier_article_code", "is_preferred"},
        )
        supplier_id = _parse_int(
            entry.get("supplier_id"),
            field_name=f"suppliers[{index}].supplier_id",
            details={"index": index},
        )
        if supplier_id in seen_supplier_ids:
            duplicate_supplier_ids.add(supplier_id)
        else:
            seen_supplier_ids.add(supplier_id)

        normalized_rows.append(
            {
                "supplier_id": supplier_id,
                "supplier_article_code": _normalize_optional_text(
                    entry.get("supplier_article_code")
                ),
                "is_preferred": _parse_bool(
                    entry.get("is_preferred"),
                    field_name=f"suppliers[{index}].is_preferred",
                    default=False,
                    details={"index": index},
                ),
            }
        )
        supplier_ids.append(supplier_id)

    if duplicate_supplier_ids:
        duplicate_ids = sorted(duplicate_supplier_ids)
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            "suppliers contains duplicate supplier_id values.",
            400,
            {"supplier_ids": duplicate_ids, "_msg_key": "ARTICLE_DUPLICATE_SUPPLIER_ID"},
        )

    active_suppliers = (
        Supplier.query
        .filter(
            Supplier.id.in_(supplier_ids),
            Supplier.is_active.is_(True),
        )
        .all()
    )
    suppliers_by_id = {supplier.id: supplier for supplier in active_suppliers}
    invalid_supplier_ids = [
        supplier_id for supplier_id in supplier_ids if supplier_id not in suppliers_by_id
    ]
    if invalid_supplier_ids:
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            "suppliers must reference active suppliers only.",
            400,
            {"supplier_ids": invalid_supplier_ids, "_msg_key": "ARTICLE_INACTIVE_SUPPLIER"},
        )

    return [
        PreparedArticleSupplierPayload(
            supplier=suppliers_by_id[row["supplier_id"]],
            supplier_article_code=row["supplier_article_code"],
            is_preferred=row["is_preferred"],
        )
        for row in normalized_rows
    ]


def _create_article_supplier_links(
    article_id: int,
    suppliers: list[PreparedArticleSupplierPayload],
) -> None:
    for prepared in suppliers:
        db.session.add(
            ArticleSupplier(
                article_id=article_id,
                supplier_id=prepared.supplier.id,
                supplier_article_code=prepared.supplier_article_code,
                is_preferred=prepared.is_preferred,
            )
        )


def _sync_article_supplier_links(
    article_id: int,
    suppliers: list[PreparedArticleSupplierPayload],
) -> None:
    existing_links = (
        ArticleSupplier.query
        .filter(ArticleSupplier.article_id == article_id)
        .order_by(ArticleSupplier.id.asc())
        .all()
    )

    existing_by_supplier_id: dict[int, ArticleSupplier] = {}
    duplicate_links: list[ArticleSupplier] = []
    for link in existing_links:
        if link.supplier_id in existing_by_supplier_id:
            duplicate_links.append(link)
            continue
        existing_by_supplier_id[link.supplier_id] = link

    submitted_supplier_ids: set[int] = set()
    for prepared in suppliers:
        submitted_supplier_ids.add(prepared.supplier.id)
        link = existing_by_supplier_id.get(prepared.supplier.id)
        if link is None:
            db.session.add(
                ArticleSupplier(
                    article_id=article_id,
                    supplier_id=prepared.supplier.id,
                    supplier_article_code=prepared.supplier_article_code,
                    is_preferred=prepared.is_preferred,
                )
            )
            continue

        link.supplier_article_code = prepared.supplier_article_code
        link.is_preferred = prepared.is_preferred

    for link in existing_links:
        if link in duplicate_links or link.supplier_id not in submitted_supplier_ids:
            db.session.delete(link)


def _prepare_article_payload(
    payload: dict[str, Any] | None,
    *,
    existing_article: Article | None = None,
) -> PreparedArticlePayload:
    body = payload or {}
    _validate_allowed_fields(
        body,
        allowed_fields={
            "article_no",
            "description",
            "category_id",
            "base_uom",
            "pack_size",
            "pack_uom",
            "barcode",
            "manufacturer",
            "manufacturer_art_number",
            "has_batch",
            "reorder_threshold",
            "reorder_coverage_days",
            "density",
            "is_active",
            "suppliers",
        },
    )

    details = (
        {"article_id": existing_article.id}
        if existing_article is not None
        else None
    )

    article_no = _normalize_article_no(
        body.get("article_no", existing_article.article_no if existing_article else None)
    )
    description = _require_text(
        body.get("description", existing_article.description if existing_article else None),
        field_name="description",
        max_length=500,
        details=details,
    )

    category_id = body.get(
        "category_id",
        existing_article.category_id if existing_article else None,
    )
    category = _get_category(
        _parse_int(category_id, field_name="category_id", details=details),
        require_active=True,
    )

    base_uom = _get_uom_by_code(
        body.get(
            "base_uom",
            _serialize_uom_code(
                existing_article.base_uom_ref if existing_article else None,
                existing_article.base_uom if existing_article else None,
            ),
        ),
        field_name="base_uom",
        require_active=True,
    )
    if base_uom is None:
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            "base_uom is required.",
            400,
            details,
        )

    pack_uom = _get_uom_by_code(
        body.get(
            "pack_uom",
            _serialize_uom_code(
                existing_article.pack_uom_ref if existing_article else None,
                existing_article.pack_uom if existing_article else None,
            ),
        ),
        field_name="pack_uom",
        require_active=True,
    )

    pack_size = _parse_optional_decimal(
        body.get(
            "pack_size",
            existing_article.pack_size if existing_article else None,
        ),
        field_name="pack_size",
        details=details,
    )
    reorder_threshold = _parse_optional_decimal(
        body.get(
            "reorder_threshold",
            existing_article.reorder_threshold if existing_article else None,
        ),
        field_name="reorder_threshold",
        details=details,
    )
    reorder_coverage_days = _parse_optional_positive_int(
        body.get(
            "reorder_coverage_days",
            existing_article.reorder_coverage_days if existing_article else None,
        ),
        field_name="reorder_coverage_days",
        details=details,
    )
    density = _parse_optional_decimal(
        body.get(
            "density",
            existing_article.density if existing_article else Decimal("1.0"),
        ),
        field_name="density",
        details=details,
    )
    if density is None:
        density = Decimal("1.0")

    has_batch = _parse_bool(
        body.get(
            "has_batch",
            existing_article.has_batch if existing_article else False,
        ),
        field_name="has_batch",
        details=details,
    )
    is_active = _parse_bool(
        body.get(
            "is_active",
            existing_article.is_active if existing_article else True,
        ),
        field_name="is_active",
        details=details,
    )

    barcode = _normalize_optional_text(
        body.get("barcode", existing_article.barcode if existing_article else None)
    )
    manufacturer = _normalize_optional_text(
        body.get(
            "manufacturer",
            existing_article.manufacturer if existing_article else None,
        )
    )
    manufacturer_art_number = _normalize_optional_text(
        body.get(
            "manufacturer_art_number",
            existing_article.manufacturer_art_number if existing_article else None,
        )
    )

    duplicate_query = Article.query.filter(func.upper(Article.article_no) == article_no)
    if existing_article is not None:
        duplicate_query = duplicate_query.filter(Article.id != existing_article.id)
    if duplicate_query.first() is not None:
        raise ArticleServiceError(
            "ARTICLE_ALREADY_EXISTS",
            "Article number already exists.",
            409,
            {"article_no": article_no},
        )

    return PreparedArticlePayload(
        article_no=article_no,
        description=description,
        category=category,
        base_uom=base_uom,
        pack_size=pack_size,
        pack_uom=pack_uom,
        barcode=barcode,
        manufacturer=manufacturer,
        manufacturer_art_number=manufacturer_art_number,
        has_batch=has_batch,
        reorder_threshold=reorder_threshold,
        reorder_coverage_days=reorder_coverage_days,
        density=density,
        is_active=is_active,
    )


def find_article_for_lookup(query: str | None) -> dict[str, Any]:
    """Return the Draft Entry / Receiving exact-match lookup response."""
    normalized = (query or "").strip()
    if not normalized:
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            "Query parameter 'q' is required.",
            400,
        )

    article = (
        Article.query
        .options(joinedload(Article.base_uom_ref))
        .filter(
            or_(
                func.upper(Article.article_no) == normalized.upper(),
                Article.barcode == normalized,
            ),
            Article.is_active.is_(True),
        )
        .first()
    )
    if article is None:
        raise ArticleServiceError(
            "ARTICLE_NOT_FOUND",
            "Article not found.",
            404,
            {"query": normalized},
        )

    return _serialize_lookup_article(article)


def lookup_suppliers() -> list[dict[str, Any]]:
    """Return the Warehouse supplier lookup response."""
    rows = (
        Supplier.query
        .filter(Supplier.is_active.is_(True))
        .order_by(Supplier.name.asc(), Supplier.id.asc())
        .all()
    )
    return [
        {
            "id": supplier.id,
            "name": supplier.name,
            "internal_code": supplier.internal_code,
        }
        for supplier in rows
    ]


def lookup_suppliers_paginated(page: int, per_page: int) -> dict[str, Any]:
    """Return the paginated Warehouse supplier preload response."""
    query = (
        Supplier.query
        .filter(Supplier.is_active.is_(True))
        .order_by(Supplier.name.asc(), Supplier.id.asc())
    )
    total = query.count()
    rows = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [
            {
                "id": supplier.id,
                "name": supplier.name,
                "internal_code": supplier.internal_code,
            }
            for supplier in rows
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def list_articles(
    page: int,
    per_page: int,
    *,
    q: str | None = None,
    category_key: str | None = None,
    include_inactive: bool = False,
) -> dict[str, Any]:
    """Return the canonical Warehouse paginated articles list."""
    query = (
        Article.query
        .options(
            joinedload(Article.category),
            joinedload(Article.base_uom_ref),
        )
        .join(Category, Category.id == Article.category_id)
    )

    if not include_inactive:
        query = query.filter(Article.is_active.is_(True))

    normalized_q = _normalize_optional_text(q)
    if normalized_q is not None:
        like_pattern = f"%{normalized_q}%"
        query = query.filter(
            or_(
                Article.article_no.ilike(like_pattern),
                Article.description.ilike(like_pattern),
            )
        )

    normalized_category_key = _normalize_optional_text(category_key)
    if normalized_category_key is not None:
        query = query.filter(Category.key == normalized_category_key)

    query = query.order_by(Article.is_active.desc(), Article.article_no.asc(), Article.id.asc())
    total = query.count()
    rows = query.offset((page - 1) * per_page).limit(per_page).all()

    totals = _build_article_totals_map([article.id for article in rows])
    items = [
        _serialize_list_item(
            article,
            stock_total=totals.get(article.id, (Decimal("0"), Decimal("0")))[0],
            surplus_total=totals.get(article.id, (Decimal("0"), Decimal("0")))[1],
        )
        for article in rows
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def search_identifier_articles(query: str | None, *, role: str) -> dict[str, Any]:
    """Search active articles across identifier fields for the Identifier module."""
    normalized_query = _normalize_identifier_term(query)
    if normalized_query is None or len(normalized_query) < 2:
        return {
            "items": [],
            "total": 0,
        }

    like_pattern = f"%{normalized_query}%"
    article_id_rows = (
        db.session.query(Article.id)
        .outerjoin(ArticleAlias, ArticleAlias.article_id == Article.id)
        .filter(Article.is_active.is_(True))
        .filter(
            or_(
                func.lower(Article.article_no).like(like_pattern),
                func.lower(Article.description).like(like_pattern),
                func.lower(func.coalesce(Article.barcode, "")).like(like_pattern),
                func.lower(ArticleAlias.normalized).like(like_pattern),
            )
        )
        .distinct()
        .all()
    )
    article_ids = [article_id for article_id, in article_id_rows]
    if not article_ids:
        return {
            "items": [],
            "total": 0,
        }

    articles = (
        Article.query
        .options(
            joinedload(Article.category),
            joinedload(Article.base_uom_ref),
        )
        .filter(Article.id.in_(article_ids))
        .all()
    )
    alias_rows = (
        ArticleAlias.query
        .filter(ArticleAlias.article_id.in_(article_ids))
        .order_by(ArticleAlias.article_id.asc(), ArticleAlias.id.asc())
        .all()
    )
    aliases_by_article: dict[int, list[ArticleAlias]] = {}
    for alias in alias_rows:
        aliases_by_article.setdefault(alias.article_id, []).append(alias)

    totals = _build_article_totals_map(article_ids)
    matched_rows: list[tuple[int, str, dict[str, Any]]] = []
    for article in articles:
        match = _resolve_identifier_match(
            article,
            aliases_by_article.get(article.id, []),
            normalized_query=normalized_query,
        )
        if match is None:
            continue
        stock_total, surplus_total = totals.get(article.id, (Decimal("0"), Decimal("0")))
        matched_rows.append(
            (
                match.sort_rank,
                article.article_no or "",
                _serialize_identifier_item(
                    article,
                    stock_total=stock_total,
                    surplus_total=surplus_total,
                    match=match,
                    role=role,
                ),
            )
        )

    matched_rows.sort(key=lambda row: (row[0], row[1].lower()))
    items = [item for _rank, _article_no, item in matched_rows]
    return {
        "items": items,
        "total": len(items),
    }


def get_article_detail(article_id: int) -> dict[str, Any]:
    """Return the canonical Warehouse detail payload."""
    return _serialize_detail(_get_article(article_id))


def create_article_alias(article_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Create an alias for an article. Returns the created alias object."""
    body = payload or {}
    raw_alias = body.get("alias")
    if not isinstance(raw_alias, str) or not raw_alias.strip():
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            "alias is required.",
            400,
        )
    display_alias = raw_alias.strip()
    normalized = display_alias.lower()

    article = _get_article(article_id)

    existing = (
        ArticleAlias.query
        .filter_by(article_id=article.id, normalized=normalized)
        .first()
    )
    if existing is not None:
        raise ArticleServiceError(
            "ALIAS_ALREADY_EXISTS",
            "Alias already exists.",
            409,
        )

    alias_row = ArticleAlias(
        article_id=article.id,
        alias=display_alias,
        normalized=normalized,
    )
    db.session.add(alias_row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ArticleServiceError(
            "ALIAS_ALREADY_EXISTS",
            "Alias already exists.",
            409,
        ) from None
    return _serialize_alias(alias_row)


def delete_article_alias(article_id: int, alias_id: int) -> None:
    """Delete an alias that belongs to the specified article."""
    _get_article(article_id)
    alias_row = ArticleAlias.query.filter_by(id=alias_id, article_id=article_id).first()
    if alias_row is None:
        raise ArticleServiceError(
            "ALIAS_NOT_FOUND",
            "Alias not found.",
            404,
        )
    db.session.delete(alias_row)
    db.session.commit()


def create_article(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Create a new article and return the canonical detail payload."""
    body = payload or {}
    prepared = _prepare_article_payload(body)
    prepared_suppliers = _prepare_article_suppliers_payload(
        body.get("suppliers", _SUPPLIERS_MISSING),
        treat_missing_as_empty=True,
    )
    article = Article(
        article_no=prepared.article_no,
        description=prepared.description,
        category_id=prepared.category.id,
        base_uom=prepared.base_uom.id,
        pack_size=prepared.pack_size,
        pack_uom=prepared.pack_uom.id if prepared.pack_uom else None,
        barcode=prepared.barcode,
        manufacturer=prepared.manufacturer,
        manufacturer_art_number=prepared.manufacturer_art_number,
        has_batch=prepared.has_batch,
        reorder_threshold=prepared.reorder_threshold,
        reorder_coverage_days=prepared.reorder_coverage_days,
        density=prepared.density,
        is_active=prepared.is_active,
    )
    db.session.add(article)
    try:
        db.session.flush()
        _create_article_supplier_links(article.id, prepared_suppliers or [])
        db.session.commit()
    except IntegrityError as exc:
        raise ArticleServiceError(
            "ARTICLE_ALREADY_EXISTS",
            "Article number already exists.",
            409,
            {"article_no": prepared.article_no},
        ) from exc
    return get_article_detail(article.id)


def update_article(article_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Update an existing article and return the canonical detail payload."""
    article = _get_article(article_id)
    body = payload or {}
    prepared = _prepare_article_payload(body, existing_article=article)
    prepared_suppliers = _prepare_article_suppliers_payload(
        body.get("suppliers", _SUPPLIERS_MISSING),
        treat_missing_as_empty=False,
    )

    article.article_no = prepared.article_no
    article.description = prepared.description
    article.category_id = prepared.category.id
    article.base_uom = prepared.base_uom.id
    article.pack_size = prepared.pack_size
    article.pack_uom = prepared.pack_uom.id if prepared.pack_uom else None
    article.barcode = prepared.barcode
    article.manufacturer = prepared.manufacturer
    article.manufacturer_art_number = prepared.manufacturer_art_number
    article.has_batch = prepared.has_batch
    article.reorder_threshold = prepared.reorder_threshold
    article.reorder_coverage_days = prepared.reorder_coverage_days
    article.density = prepared.density
    article.is_active = prepared.is_active
    article.updated_at = datetime.now(timezone.utc)
    if prepared_suppliers is not None:
        _sync_article_supplier_links(article.id, prepared_suppliers)

    try:
        db.session.commit()
    except IntegrityError as exc:
        raise ArticleServiceError(
            "ARTICLE_ALREADY_EXISTS",
            "Article number already exists.",
            409,
            {"article_no": prepared.article_no},
        ) from exc
    return get_article_detail(article.id)


def deactivate_article(article_id: int) -> dict[str, Any]:
    """Soft-deactivate an article and return the canonical detail payload."""
    article = _get_article(article_id)
    article.is_active = False
    article.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return get_article_detail(article.id)


def _serialize_reference(transaction: Transaction) -> str | None:
    if transaction.order_number:
        return transaction.order_number
    if transaction.delivery_note_number:
        return transaction.delivery_note_number
    if transaction.reference_type and transaction.reference_id is not None:
        return f"{transaction.reference_type}:{transaction.reference_id}"
    return None


def list_article_transactions(article_id: int, page: int, per_page: int) -> dict[str, Any]:
    """Return paginated article transaction history ordered newest first."""
    _get_article(article_id)
    query = (
        Transaction.query
        .options(
            joinedload(Transaction.batch),
            joinedload(Transaction.user),
        )
        .filter(Transaction.article_id == article_id)
        .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
    )
    total = query.count()
    rows = query.offset((page - 1) * per_page).limit(per_page).all()

    items = [
        {
            "id": row.id,
            "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
            "type": row.tx_type.value if hasattr(row.tx_type, "value") else row.tx_type,
            "quantity": float(_decimal_from_model(row.quantity)),
            "uom": row.uom,
            "batch_code": row.batch.batch_code if row.batch else None,
            "reference": _serialize_reference(row),
            "reference_type": row.reference_type,
            "reference_id": row.reference_id,
            "user": row.user.username if row.user else None,
        }
        for row in rows
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def _get_latest_open_missing_article_report(
    normalized_term: str,
) -> MissingArticleReport | None:
    return (
        MissingArticleReport.query
        .filter(
            MissingArticleReport.normalized_term == normalized_term,
            MissingArticleReport.status == MissingArticleReportStatus.OPEN,
        )
        .order_by(
            MissingArticleReport.created_at.desc(),
            MissingArticleReport.id.desc(),
        )
        .first()
    )


def _increment_missing_article_report_count(report_id: int) -> MissingArticleReport:
    db.session.execute(
        update(MissingArticleReport)
        .where(MissingArticleReport.id == report_id)
        .values(report_count=MissingArticleReport.report_count + 1)
    )
    db.session.commit()

    report = db.session.get(MissingArticleReport, report_id)
    if report is None:
        raise ArticleServiceError(
            "MISSING_ARTICLE_REPORT_NOT_FOUND",
            "Missing article report not found.",
            404,
            {"report_id": report_id},
        )
    return report


def submit_missing_article_report(
    payload: dict[str, Any] | None,
    *,
    reported_by_id: int,
) -> tuple[dict[str, Any], bool]:
    """Create or merge a missing-article report."""
    body = payload or {}
    _validate_allowed_fields(body, allowed_fields={"search_term"})

    search_term = _require_text(
        body.get("search_term"),
        field_name="search_term",
        max_length=255,
    )
    normalized_term = _normalize_identifier_term(search_term)
    assert normalized_term is not None

    existing = _get_latest_open_missing_article_report(normalized_term)
    if existing is not None:
        merged = _increment_missing_article_report_count(existing.id)
        return _serialize_missing_article_report(merged), False

    report = MissingArticleReport(
        reported_by=reported_by_id,
        search_term=search_term,
        normalized_term=normalized_term,
        report_count=1,
        status=MissingArticleReportStatus.OPEN,
    )
    db.session.add(report)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = _get_latest_open_missing_article_report(normalized_term)
        if existing is None:
            raise ArticleServiceError(
                "MISSING_ARTICLE_REPORT_CONFLICT",
                "Missing article report merge failed after a concurrent conflict.",
                409,
                {"normalized_term": normalized_term},
            ) from None

        merged = _increment_missing_article_report_count(existing.id)
        return _serialize_missing_article_report(merged), False
    return _serialize_missing_article_report(report), True


def _parse_missing_article_report_status(value: Any) -> MissingArticleReportStatus:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return MissingArticleReportStatus.OPEN
    try:
        return MissingArticleReportStatus(normalized.upper())
    except ValueError:
        raise ArticleServiceError(
            "VALIDATION_ERROR",
            "status must be 'OPEN' or 'RESOLVED'.",
            400,
            {"status": normalized},
        ) from None


def list_missing_article_reports(status: str | None = None) -> dict[str, Any]:
    """Return the Identifier missing-article report queue."""
    report_status = _parse_missing_article_report_status(status)
    reports = (
        MissingArticleReport.query
        .filter(MissingArticleReport.status == report_status)
        .order_by(
            MissingArticleReport.created_at.desc(),
            MissingArticleReport.id.desc(),
        )
        .all()
    )
    items = [_serialize_missing_article_report(report) for report in reports]
    return {
        "items": items,
        "total": len(items),
    }


def resolve_missing_article_report(
    report_id: int,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve an Identifier missing-article report."""
    body = payload or {}
    _validate_allowed_fields(body, allowed_fields={"resolution_note"})

    report = db.session.get(MissingArticleReport, report_id)
    if report is None:
        raise ArticleServiceError(
            "MISSING_ARTICLE_REPORT_NOT_FOUND",
            "Missing article report not found.",
            404,
            {"report_id": report_id},
        )

    if report.status != MissingArticleReportStatus.RESOLVED:
        report.status = MissingArticleReportStatus.RESOLVED
        report.resolution_note = _normalize_optional_text(body.get("resolution_note"))
        report.resolved_at = datetime.now(timezone.utc)
        db.session.commit()

    return _serialize_missing_article_report(report)


def lookup_categories() -> list[dict[str, Any]]:
    """Return active article categories for the Warehouse form/filter UI."""
    categories = (
        Category.query
        .filter(Category.is_active.is_(True))
        .order_by(Category.label_hr.asc(), Category.id.asc())
        .all()
    )
    return [
        {
            "id": category.id,
            "key": category.key,
            "label_hr": category.label_hr,
        }
        for category in categories
    ]


def lookup_uoms() -> list[dict[str, Any]]:
    """Return active UOM rows for the Warehouse form UI."""
    query = UomCatalog.query
    if hasattr(UomCatalog, "is_active"):
        query = query.filter(UomCatalog.is_active.is_(True))
    uoms = query.order_by(UomCatalog.code.asc(), UomCatalog.id.asc()).all()
    return [
        {
            "code": uom.code,
            "label_hr": uom.label_hr,
            "decimal_display": uom.decimal_display,
        }
        for uom in uoms
    ]
