"""Business logic for the Phase 13 Reports module."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from typing import Any, Iterable
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import case, func
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.utils.validators import sanitize_cell
from app.models.article import Article
from app.models.article_supplier import ArticleSupplier
from app.models.category import Category
from app.models.employee import Employee
from app.models.enums import TxType
from app.models.personal_issuance import PersonalIssuance
from app.models.receiving import Receiving
from app.models.supplier import Supplier
from app.models.surplus import Surplus
from app.models.transaction import Transaction
from app.services import article_service, employee_service
from app.utils.validators import (
    QueryValidationError,
    parse_bool_query,
    parse_positive_int,
)

_QTY_QUANT = Decimal("0.001")
_MONTHS_QUANT = Decimal("0.01")
_AVG_QUANT = Decimal("0.01")
_COVERAGE_QUANT = Decimal("0.1")
_VALUE_QUANT = Decimal("0.01")
_PAGE_DEFAULT = 1
_PER_PAGE_DEFAULT = 50
_EXPORT_XLSX_MIMETYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
_EXPORT_PDF_MIMETYPE = "application/pdf"
_OUTBOUND_TX_TYPES = (
    TxType.OUTBOUND,
    TxType.STOCK_CONSUMED,
    TxType.SURPLUS_CONSUMED,
    TxType.PERSONAL_ISSUE,
)
_INBOUND_TX_TYPES = (TxType.STOCK_RECEIPT,)
_MOVEMENT_NOTE = (
    "Quantities are summed across all units of measure. "
    "This chart shows trends, not precise totals."
)


class ReportServiceError(Exception):
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


def _decimal_from_model(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


def _quantize(value: Decimal, quant: Decimal) -> Decimal:
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def _as_float(value: Decimal | None, quant: Decimal | None = None) -> float | None:
    if value is None:
        return None
    normalized = _quantize(value, quant) if quant is not None else value
    return float(normalized)


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_iso_date(
    value: Any,
    *,
    field_name: str,
    required: bool = False,
) -> date | None:
    if value in (None, ""):
        if required:
            raise ReportServiceError(
                "VALIDATION_ERROR",
                f"{field_name} is required.",
                400,
                {"field": field_name},
            )
        return None

    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ReportServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be a valid ISO date.",
            400,
            {"field": field_name, "value": value},
        ) from None


def _parse_positive_int(
    value: Any,
    *,
    field_name: str,
    default: int,
) -> int:
    """Service-layer adapter: normalise '' → None, delegate to shared validator.

    Preserves blank-string/default behavior and converts QueryValidationError
    to ReportServiceError so the route layer remains unaffected.
    """
    normalized = None if value == "" else value
    try:
        return parse_positive_int(normalized, field_name=field_name, default=default)
    except QueryValidationError as exc:
        raise ReportServiceError(
            "VALIDATION_ERROR",
            exc.message,
            400,
            {"field": field_name, "value": value},
        ) from exc


def _parse_bool(value: Any, *, field_name: str, default: bool = False) -> bool:
    """Service-layer adapter: normalise '' → None, delegate to shared validator.

    Preserves blank-string/default behavior and converts QueryValidationError
    to ReportServiceError so the route layer remains unaffected.
    """
    normalized = None if value == "" else value
    try:
        return parse_bool_query(normalized, field_name=field_name, default=default)
    except QueryValidationError as exc:
        raise ReportServiceError(
            "VALIDATION_ERROR",
            exc.message,
            400,
            {"field": field_name, "value": value},
        ) from exc


def _parse_export_format(value: Any) -> str:
    normalized = (_normalize_optional_text(value) or "").lower()
    if normalized not in {"xlsx", "pdf"}:
        raise ReportServiceError(
            "VALIDATION_ERROR",
            "format must be 'xlsx' or 'pdf'.",
            400,
            {"field": "format", "value": value},
        )
    return normalized


def _parse_tx_types(values: Iterable[Any] | None) -> tuple[TxType, ...] | None:
    if not values:
        return None

    parsed: list[TxType] = []
    invalid: list[str] = []
    for raw_value in values:
        normalized = (_normalize_optional_text(raw_value) or "").upper()
        if not normalized:
            continue
        try:
            parsed.append(TxType(normalized))
        except ValueError:
            invalid.append(normalized)

    if invalid:
        raise ReportServiceError(
            "VALIDATION_ERROR",
            f"Unsupported tx_type values: {', '.join(sorted(set(invalid)))}.",
            400,
            {"tx_type": sorted(set(invalid))},
        )

    return tuple(dict.fromkeys(parsed)) or None


def _range_start(value: date) -> datetime:
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)


def _range_end_exclusive(value: date) -> datetime:
    next_day = value + timedelta(days=1)
    return _range_start(next_day)


def _require_date_range(date_from: Any, date_to: Any) -> tuple[date, date, Decimal]:
    parsed_from = _parse_iso_date(date_from, field_name="date_from", required=True)
    parsed_to = _parse_iso_date(date_to, field_name="date_to", required=True)
    if parsed_from >= parsed_to:
        raise ReportServiceError(
            "VALIDATION_ERROR",
            "date_from must be before date_to.",
            400,
            {
                "date_from": parsed_from.isoformat(),
                "date_to": parsed_to.isoformat(),
            },
        )

    days = Decimal((parsed_to - parsed_from).days)
    months = _quantize(days / Decimal("30.44"), _MONTHS_QUANT)
    return parsed_from, parsed_to, months


def _serialize_reference(transaction: Transaction) -> str | None:
    if transaction.order_number:
        return transaction.order_number
    if transaction.delivery_note_number:
        return transaction.delivery_note_number
    if transaction.reference_type and transaction.reference_id is not None:
        return f"{transaction.reference_type}:{transaction.reference_id}"
    return None


def _supplier_name_map(article_ids: list[int]) -> dict[int, str | None]:
    if not article_ids:
        return {}

    rows = (
        db.session.query(ArticleSupplier.article_id, Supplier.name)
        .join(Supplier, Supplier.id == ArticleSupplier.supplier_id)
        .filter(ArticleSupplier.article_id.in_(article_ids))
        .order_by(
            ArticleSupplier.article_id.asc(),
            ArticleSupplier.is_preferred.desc(),
            ArticleSupplier.id.asc(),
        )
        .all()
    )

    supplier_map: dict[int, str | None] = {}
    for article_id, supplier_name in rows:
        supplier_map.setdefault(article_id, supplier_name)
    return supplier_map


def _stock_overview_movement_map(
    article_ids: list[int],
    *,
    started_at: datetime,
    ended_at: datetime,
) -> dict[int, tuple[Decimal, Decimal]]:
    if not article_ids:
        return {}

    rows = (
        db.session.query(
            Transaction.article_id,
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.tx_type.in_(_INBOUND_TX_TYPES), func.abs(Transaction.quantity)),
                        else_=0,
                    )
                ),
                0,
            ).label("inbound_total"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.tx_type.in_(_OUTBOUND_TX_TYPES), func.abs(Transaction.quantity)),
                        else_=0,
                    )
                ),
                0,
            ).label("outbound_total"),
        )
        .filter(
            Transaction.article_id.in_(article_ids),
            Transaction.occurred_at >= started_at,
            Transaction.occurred_at < ended_at,
        )
        .group_by(Transaction.article_id)
        .all()
    )

    result = {
        article_id: (Decimal("0"), Decimal("0"))
        for article_id in article_ids
    }
    for article_id, inbound_total, outbound_total in rows:
        result[article_id] = (
            _decimal_from_model(inbound_total),
            _decimal_from_model(outbound_total),
        )
    return result


def _resolve_unit_value_map(article_ids: list[int]) -> dict[int, Decimal | None]:
    """Resolve unit_value per article using locked priority:
    1. Most recent Receiving row with non-null unit_price (received_at DESC, id DESC).
    2. Preferred supplier's ArticleSupplier.last_price.
    3. None.
    """
    if not article_ids:
        return {}

    result: dict[int, Decimal | None] = {aid: None for aid in article_ids}

    rows = (
        db.session.query(Receiving.article_id, Receiving.unit_price)
        .filter(
            Receiving.article_id.in_(article_ids),
            Receiving.unit_price.isnot(None),
        )
        .order_by(
            Receiving.article_id.asc(),
            Receiving.received_at.desc(),
            Receiving.id.desc(),
        )
        .all()
    )
    receiving_map: dict[int, Decimal] = {}
    for article_id, unit_price in rows:
        receiving_map.setdefault(article_id, _decimal_from_model(unit_price))
    for article_id, price in receiving_map.items():
        result[article_id] = price

    no_price_ids = [aid for aid in article_ids if result[aid] is None]
    if no_price_ids:
        supplier_rows = (
            db.session.query(ArticleSupplier.article_id, ArticleSupplier.last_price)
            .filter(
                ArticleSupplier.article_id.in_(no_price_ids),
                ArticleSupplier.is_preferred.is_(True),
                ArticleSupplier.last_price.isnot(None),
            )
            .all()
        )
        for article_id, last_price in supplier_rows:
            result[article_id] = _decimal_from_model(last_price)

    return result


def _serialize_stock_overview_item(
    article: Article,
    *,
    stock_total: Decimal,
    surplus_total: Decimal,
    supplier_name: str | None,
    inbound_total: Decimal,
    outbound_total: Decimal,
    months_in_period: Decimal,
    unit_value: Decimal | None,
) -> dict[str, Any]:
    total_available = stock_total + surplus_total
    avg_monthly = Decimal("0")
    coverage: Decimal | None = None
    if outbound_total > 0 and months_in_period > 0:
        avg_monthly = outbound_total / months_in_period
        coverage = total_available / avg_monthly if avg_monthly > 0 else None

    total_value: Decimal | None = (
        stock_total * unit_value if unit_value is not None else None
    )
    uom = article.base_uom_ref.code if article.base_uom_ref else None
    return {
        "article_id": article.id,
        "article_no": article.article_no,
        "description": article.description,
        "supplier_name": supplier_name,
        "stock": _as_float(stock_total, _QTY_QUANT),
        "surplus": _as_float(surplus_total, _QTY_QUANT),
        "total_available": _as_float(total_available, _QTY_QUANT),
        "uom": uom,
        "inbound": _as_float(inbound_total, _QTY_QUANT),
        "outbound": _as_float(outbound_total, _QTY_QUANT),
        "avg_monthly_consumption": _as_float(avg_monthly, _AVG_QUANT),
        "coverage_months": _as_float(coverage, _COVERAGE_QUANT),
        "reorder_threshold": (
            _as_float(_decimal_from_model(article.reorder_threshold), _QTY_QUANT)
            if article.reorder_threshold is not None
            else None
        ),
        "reorder_status": article_service._get_reorder_status(
            stock_total,
            surplus_total,
            article.reorder_threshold,
        ),
        "unit_value": _as_float(unit_value, _VALUE_QUANT),
        "total_value": _as_float(total_value, _VALUE_QUANT),
    }


def get_stock_overview(
    *,
    date_from: Any,
    date_to: Any,
    category: Any = None,
    reorder_only: Any = None,
    page: int = 1,
    per_page: int = 100,
) -> dict[str, Any]:
    parsed_from, parsed_to, months_in_period = _require_date_range(date_from, date_to)
    reorder_only_enabled = _parse_bool(
        reorder_only,
        field_name="reorder_only",
        default=False,
    )
    normalized_category = _normalize_optional_text(category)
    # V-3 / Wave 6 Phase 1: cap per_page to prevent DoS via large result sets
    per_page = min(per_page, 200)

    query = (
        Article.query
        .options(
            joinedload(Article.base_uom_ref),
            joinedload(Article.category),
        )
        .join(Category, Category.id == Article.category_id)
        .filter(Article.is_active.is_(True))
    )
    if normalized_category is not None:
        query = query.filter(Category.key == normalized_category)

    # Fetch all matching articles to support reorder_only filtering before pagination
    all_articles = query.order_by(Article.article_no.asc(), Article.id.asc()).all()
    all_article_ids = [article.id for article in all_articles]
    totals_map = article_service._build_article_totals_map(all_article_ids)
    supplier_map = _supplier_name_map(all_article_ids)
    movement_map = _stock_overview_movement_map(
        all_article_ids,
        started_at=_range_start(parsed_from),
        ended_at=_range_end_exclusive(parsed_to),
    )
    unit_value_map = _resolve_unit_value_map(all_article_ids)

    all_items: list[dict[str, Any]] = []
    warehouse_total_value = Decimal("0")
    for article in all_articles:
        stock_total, surplus_total = totals_map.get(article.id, (Decimal("0"), Decimal("0")))
        inbound_total, outbound_total = movement_map.get(article.id, (Decimal("0"), Decimal("0")))
        unit_value = unit_value_map.get(article.id)
        item = _serialize_stock_overview_item(
            article,
            stock_total=stock_total,
            surplus_total=surplus_total,
            supplier_name=supplier_map.get(article.id),
            inbound_total=inbound_total,
            outbound_total=outbound_total,
            months_in_period=months_in_period,
            unit_value=unit_value,
        )
        if reorder_only_enabled and item["reorder_status"] == "NORMAL":
            continue
        all_items.append(item)
        if unit_value is not None:
            warehouse_total_value += stock_total * unit_value

    total = len(all_items)
    offset = (page - 1) * per_page
    items = all_items[offset: offset + per_page]

    return {
        "period": {
            "date_from": parsed_from.isoformat(),
            "date_to": parsed_to.isoformat(),
            "months": _as_float(months_in_period, _MONTHS_QUANT),
        },
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "summary": {
            "warehouse_total_value": _as_float(warehouse_total_value, _VALUE_QUANT),
        },
    }


def get_surplus_report(
    page: int = 1,
    per_page: int = 100,
) -> dict[str, Any]:
    # V-3 / Wave 6 Phase 1: cap per_page to prevent DoS via large result sets
    per_page = min(per_page, 200)

    base_query = (
        Surplus.query
        .options(
            joinedload(Surplus.article),
            joinedload(Surplus.batch),
        )
        .join(Article, Article.id == Surplus.article_id)
        .filter(Surplus.quantity > 0)
        .order_by(Article.article_no.asc(), Surplus.created_at.desc(), Surplus.id.asc())
    )

    total = base_query.count()
    rows = base_query.offset((page - 1) * per_page).limit(per_page).all()

    items = [
        {
            "id": row.id,
            "article_id": row.article_id,
            "article_no": row.article.article_no if row.article else None,
            "description": row.article.description if row.article else None,
            "batch_id": row.batch_id,
            "batch_code": row.batch.batch_code if row.batch else None,
            "expiry_date": row.batch.expiry_date.isoformat() if row.batch and row.batch.expiry_date else None,
            "surplus_qty": _as_float(_decimal_from_model(row.quantity), _QTY_QUANT),
            "uom": row.uom,
            "discovered": row.created_at.date().isoformat() if row.created_at else None,
        }
        for row in rows
    ]
    return {"items": items, "total": total, "page": page, "per_page": per_page}


def _transaction_base_query(
    *,
    article_id: Any = None,
    date_from: Any = None,
    date_to: Any = None,
    tx_types: Iterable[Any] | None = None,
):
    parsed_article_id = None
    if article_id not in (None, ""):
        parsed_article_id = _parse_positive_int(
            article_id,
            field_name="article_id",
            default=0,
        )
        if db.session.get(Article, parsed_article_id) is None:
            raise ReportServiceError(
                "ARTICLE_NOT_FOUND",
                "Article not found.",
                400,
                {"article_id": parsed_article_id},
            )

    parsed_from = _parse_iso_date(date_from, field_name="date_from")
    parsed_to = _parse_iso_date(date_to, field_name="date_to")
    if parsed_from and parsed_to and parsed_from > parsed_to:
        raise ReportServiceError(
            "VALIDATION_ERROR",
            "date_from must be before or equal to date_to.",
            400,
            {
                "date_from": parsed_from.isoformat(),
                "date_to": parsed_to.isoformat(),
            },
        )

    parsed_tx_types = _parse_tx_types(tx_types)

    query = (
        Transaction.query
        .options(
            joinedload(Transaction.article).joinedload(Article.base_uom_ref),
            joinedload(Transaction.batch),
            joinedload(Transaction.user),
        )
    )
    if parsed_article_id is not None:
        query = query.filter(Transaction.article_id == parsed_article_id)
    if parsed_from is not None:
        query = query.filter(Transaction.occurred_at >= _range_start(parsed_from))
    if parsed_to is not None:
        query = query.filter(Transaction.occurred_at < _range_end_exclusive(parsed_to))
    if parsed_tx_types:
        query = query.filter(Transaction.tx_type.in_(parsed_tx_types))

    return query.order_by(Transaction.occurred_at.desc(), Transaction.id.desc())


def _serialize_transaction(row: Transaction) -> dict[str, Any]:
    return {
        "id": row.id,
        "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
        "article_id": row.article_id,
        "article_no": row.article.article_no if row.article else None,
        "description": row.article.description if row.article else None,
        "type": row.tx_type.value if hasattr(row.tx_type, "value") else row.tx_type,
        "quantity": _as_float(_decimal_from_model(row.quantity), _QTY_QUANT),
        "uom": row.uom,
        "batch_code": row.batch.batch_code if row.batch else None,
        "reference": _serialize_reference(row),
        "user": row.user.username if row.user else None,
    }


def get_transaction_log(
    *,
    article_id: Any = None,
    date_from: Any = None,
    date_to: Any = None,
    tx_types: Iterable[Any] | None = None,
    page: Any = None,
    per_page: Any = None,
) -> dict[str, Any]:
    parsed_page = _parse_positive_int(page, field_name="page", default=_PAGE_DEFAULT)
    parsed_per_page = _parse_positive_int(
        per_page,
        field_name="per_page",
        default=_PER_PAGE_DEFAULT,
    )
    # V-3 / Wave 6 Phase 1: cap per_page to prevent DoS via large result sets
    parsed_per_page = min(parsed_per_page, 200)

    query = _transaction_base_query(
        article_id=article_id,
        date_from=date_from,
        date_to=date_to,
        tx_types=tx_types,
    )
    total = query.count()
    rows = query.offset((parsed_page - 1) * parsed_per_page).limit(parsed_per_page).all()
    return {
        "items": [_serialize_transaction(row) for row in rows],
        "total": total,
        "page": parsed_page,
        "per_page": parsed_per_page,
    }


def _top_consumption_bounds(period: str) -> tuple[date, date]:
    current_date = datetime.now(timezone.utc).date()
    if period == "week":
        start = current_date - timedelta(days=current_date.weekday())
    elif period == "month":
        start = current_date.replace(day=1)
    elif period == "year":
        start = current_date.replace(month=1, day=1)
    else:
        raise ReportServiceError(
            "VALIDATION_ERROR",
            "period must be one of: week, month, year.",
            400,
            {"field": "period", "value": period},
        )
    return start, current_date


def get_top_consumption_statistics(period: Any) -> dict[str, Any]:
    normalized_period = (_normalize_optional_text(period) or "month").lower()
    start_date, end_date = _top_consumption_bounds(normalized_period)
    rows = (
        db.session.query(
            Transaction.article_id,
            Article.article_no,
            Article.description,
            func.coalesce(func.sum(func.abs(Transaction.quantity)), 0).label("outbound_total"),
        )
        .join(Article, Article.id == Transaction.article_id)
        .filter(
            Transaction.tx_type.in_(_OUTBOUND_TX_TYPES),
            Transaction.occurred_at >= _range_start(start_date),
            Transaction.occurred_at < _range_end_exclusive(end_date),
        )
        .group_by(Transaction.article_id, Article.article_no, Article.description)
        .order_by(
            func.coalesce(func.sum(func.abs(Transaction.quantity)), 0).desc(),
            Article.article_no.asc(),
        )
        .limit(10)
        .all()
    )

    article_ids = [row.article_id for row in rows]
    articles = {
        article.id: article
        for article in (
            Article.query
            .options(joinedload(Article.base_uom_ref))
            .filter(Article.id.in_(article_ids))
            .all()
            if article_ids
            else []
        )
    }
    items = [
        {
            "article_id": row.article_id,
            "article_no": row.article_no,
            "description": row.description,
            "outbound": _as_float(_decimal_from_model(row.outbound_total), _QTY_QUANT),
            "uom": (
                articles[row.article_id].base_uom_ref.code
                if row.article_id in articles and articles[row.article_id].base_uom_ref
                else None
            ),
        }
        for row in rows
    ]
    return {
        "period": normalized_period,
        "date_from": start_date.isoformat(),
        "date_to": end_date.isoformat(),
        "items": items,
    }


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _add_months(value: date, months: int) -> date:
    total_months = (value.year * 12) + (value.month - 1) + months
    year = total_months // 12
    month = (total_months % 12) + 1
    return date(year, month, 1)


def get_movement_statistics(range_key: Any) -> dict[str, Any]:
    normalized_range = (_normalize_optional_text(range_key) or "6m").lower()
    today = datetime.now(timezone.utc).date()

    if normalized_range == "3m":
        granularity = "week"
        current_week_start = today - timedelta(days=today.weekday())
        bucket_starts = [
            current_week_start - timedelta(weeks=12 - index)
            for index in range(13)
        ]
        end_exclusive = _range_start(bucket_starts[-1] + timedelta(days=7))
    elif normalized_range in {"6m", "12m"}:
        granularity = "month"
        month_count = int(normalized_range[:-1])
        current_month_start = _month_start(today)
        bucket_starts = [
            _add_months(current_month_start, -(month_count - 1) + index)
            for index in range(month_count)
        ]
        end_exclusive = _range_start(_add_months(bucket_starts[-1], 1))
    else:
        raise ReportServiceError(
            "VALIDATION_ERROR",
            "range must be one of: 3m, 6m, 12m.",
            400,
            {"field": "range", "value": range_key},
        )

    items: list[dict[str, Any]] = []
    bucket_index: dict[date, dict[str, Any]] = {}
    for bucket_start in bucket_starts:
        if granularity == "week":
            iso_year, iso_week, _ = bucket_start.isocalendar()
            bucket_key = f"{iso_year}-W{iso_week:02d}"
            bucket_end = bucket_start + timedelta(days=6)
        else:
            bucket_key = bucket_start.strftime("%Y-%m")
            last_day = monthrange(bucket_start.year, bucket_start.month)[1]
            bucket_end = date(bucket_start.year, bucket_start.month, last_day)

        item = {
            "bucket": bucket_key,
            "label": bucket_key,
            "period_start": bucket_start.isoformat(),
            "period_end": bucket_end.isoformat(),
            "inbound": 0.0,
            "outbound": 0.0,
        }
        items.append(item)
        bucket_index[bucket_start] = item

    rows = (
        db.session.query(Transaction.occurred_at, Transaction.tx_type, Transaction.quantity)
        .filter(
            Transaction.occurred_at >= _range_start(bucket_starts[0]),
            Transaction.occurred_at < end_exclusive,
            Transaction.tx_type.in_(_INBOUND_TX_TYPES + _OUTBOUND_TX_TYPES),
        )
        .order_by(Transaction.occurred_at.asc(), Transaction.id.asc())
        .all()
    )

    for occurred_at, tx_type, quantity in rows:
        tx_date = occurred_at.date()
        if granularity == "week":
            bucket_start = tx_date - timedelta(days=tx_date.weekday())
        else:
            bucket_start = tx_date.replace(day=1)

        bucket = bucket_index.get(bucket_start)
        if bucket is None:
            continue

        amount = _decimal_from_model(quantity).copy_abs()
        if tx_type in _INBOUND_TX_TYPES:
            bucket["inbound"] = _as_float(
                _decimal_from_model(bucket["inbound"]) + amount,
                _QTY_QUANT,
            ) or 0.0
        elif tx_type in _OUTBOUND_TX_TYPES:
            bucket["outbound"] = _as_float(
                _decimal_from_model(bucket["outbound"]) + amount,
                _QTY_QUANT,
            ) or 0.0

    return {
        "range": normalized_range,
        "granularity": granularity,
        "items": items,
        "note": _MOVEMENT_NOTE,
    }


def get_reorder_summary_statistics() -> dict[str, Any]:
    articles = Article.query.filter(Article.is_active.is_(True)).order_by(Article.id.asc()).all()
    article_ids = [article.id for article in articles]
    totals_map = article_service._build_article_totals_map(article_ids)
    counts = {"RED": 0, "YELLOW": 0, "NORMAL": 0}
    for article in articles:
        stock_total, surplus_total = totals_map.get(article.id, (Decimal("0"), Decimal("0")))
        status = article_service._get_reorder_status(
            stock_total,
            surplus_total,
            article.reorder_threshold,
        )
        counts[status] += 1

    items = [
        {"reorder_status": "RED", "count": counts["RED"]},
        {"reorder_status": "YELLOW", "count": counts["YELLOW"]},
        {"reorder_status": "NORMAL", "count": counts["NORMAL"]},
    ]
    return {"items": items, "total": len(article_ids)}

def get_personal_issuances_statistics() -> dict[str, Any]:
    current_year = datetime.now(timezone.utc).date().year
    started_at = datetime(current_year, 1, 1, tzinfo=timezone.utc)
    ended_at = datetime(current_year + 1, 1, 1, tzinfo=timezone.utc)

    rows = (
        db.session.query(
            PersonalIssuance.employee_id,
            PersonalIssuance.article_id,
            func.coalesce(func.sum(PersonalIssuance.quantity), 0).label("issued_total"),
        )
        .filter(
            PersonalIssuance.issued_at >= started_at,
            PersonalIssuance.issued_at < ended_at,
        )
        .group_by(PersonalIssuance.employee_id, PersonalIssuance.article_id)
        .all()
    )

    employee_ids = [row.employee_id for row in rows]
    article_ids = [row.article_id for row in rows]
    employees = {
        employee.id: employee
        for employee in (
            Employee.query.filter(Employee.id.in_(employee_ids)).all()
            if employee_ids
            else []
        )
    }
    articles = {
        article.id: article
        for article in (
            Article.query
            .options(
                joinedload(Article.category),
                joinedload(Article.base_uom_ref),
            )
            .filter(Article.id.in_(article_ids))
            .all()
            if article_ids
            else []
        )
    }

    def _sort_key(row) -> tuple[str, str, str]:
        employee = employees.get(row.employee_id)
        article = articles.get(row.article_id)
        return (
            (employee.last_name if employee else ""),
            (employee.first_name if employee else ""),
            (article.description if article else ""),
        )

    items: list[dict[str, Any]] = []
    for row in sorted(rows, key=_sort_key):
        employee = employees.get(row.employee_id)
        article = articles.get(row.article_id)
        if employee is None or article is None:
            continue

        issued_total = _decimal_from_model(row.issued_total)
        quota_row = employee_service._find_applicable_quota(employee, article)
        quota_qty = _decimal_from_model(quota_row.quantity) if quota_row is not None else None
        remaining = quota_qty - issued_total if quota_qty is not None else None
        employee_name = " ".join(
            part for part in [employee.first_name, employee.last_name] if part
        ).strip()

        items.append(
            {
                "employee_id": employee.id,
                "employee_name": employee_name or None,
                "job_title": employee.job_title,
                "article_id": article.id,
                "article_no": article.article_no,
                "article": article.description,
                "quantity_issued": _as_float(issued_total, _QTY_QUANT),
                "quota": _as_float(quota_qty, _QTY_QUANT),
                "remaining": _as_float(remaining, _QTY_QUANT),
                "uom": article.base_uom_ref.code if article.base_uom_ref else None,
                "quota_uom": quota_row.uom if quota_row is not None else None,
            }
        )

    return {"year": current_year, "items": items, "total": len(items)}


def _build_export_filename(report_type: str, export_format: str) -> str:
    export_date = datetime.now(timezone.utc).date().isoformat()
    return f"wms_{report_type}_{export_date}.{export_format}"


def _exported_at_line() -> str:
    return f"Exported at: {datetime.now(timezone.utc).isoformat()}"


def _format_export_quantity(value: Any, uom: str | None) -> str:
    numeric_value = _as_float(_decimal_from_model(value), _QTY_QUANT)
    if uom:
        return f"{numeric_value} {uom}"
    return str(numeric_value)


def _format_coverage_for_export(item: dict[str, Any]) -> Any:
    if item["coverage_months"] is None and (item["outbound"] in (None, 0, 0.0)):
        return "∞"
    return item["coverage_months"]


def _autofit_columns(worksheet) -> None:
    for column_cells in worksheet.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter
        for cell in column_cells:
            value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, len(value))
        worksheet.column_dimensions[column_letter].width = min(max_length + 2, 60)


def _build_xlsx(sheet_title: str, headers: list[str], rows: list[list[Any]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_title[:31]
    worksheet.append(headers)
    for cell in worksheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        worksheet.append(row)
    _autofit_columns(worksheet)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _pdf_cell(value: Any, style) -> Paragraph:
    if value is None or value == "":
        text = "-"
    else:
        text = escape(str(value))
    return Paragraph(text.replace("\n", "<br/>"), style)


def _build_pdf(
    *,
    title: str,
    headers: list[str],
    rows: list[list[Any]],
    subtitle_lines: list[str],
    landscape_mode: bool,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4) if landscape_mode else A4,
        topMargin=16 * mm,
        bottomMargin=14 * mm,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"])]
    for line in subtitle_lines:
        story.append(Paragraph(escape(line), styles["BodyText"]))
    story.append(Spacer(1, 4 * mm))

    cell_style = styles["BodyText"]
    table_rows = [
        [_pdf_cell(header, cell_style) for header in headers],
        *[[_pdf_cell(value, cell_style) for value in row] for row in rows],
    ]

    col_width = doc.width / max(len(headers), 1)
    table = Table(
        table_rows,
        colWidths=[col_width] * len(headers),
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e3f0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEADING", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return buffer.getvalue()


def export_stock_overview(
    *,
    export_format: Any,
    date_from: Any,
    date_to: Any,
    category: Any = None,
    reorder_only: Any = None,
) -> tuple[bytes, str, str]:
    parsed_format = _parse_export_format(export_format)
    report = get_stock_overview(
        date_from=date_from,
        date_to=date_to,
        category=category,
        reorder_only=reorder_only,
    )
    headers = [
        "Article No.",
        "Description",
        "Supplier",
        "Stock",
        "Surplus",
        "Total available",
        "Inbound",
        "Outbound",
        "Avg monthly consumption",
        "Coverage (months)",
        "Reorder threshold",
        "Status",
    ]
    rows = [
        [
            sanitize_cell(item["article_no"]),
            sanitize_cell(item["description"]),
            sanitize_cell(item["supplier_name"]) if item["supplier_name"] else "-",
            _format_export_quantity(item["stock"], item["uom"]),
            _format_export_quantity(item["surplus"], item["uom"]),
            _format_export_quantity(item["total_available"], item["uom"]),
            _format_export_quantity(item["inbound"], item["uom"]),
            _format_export_quantity(item["outbound"], item["uom"]),
            _format_export_quantity(item["avg_monthly_consumption"], item["uom"]),
            _format_coverage_for_export(item),
            (
                _format_export_quantity(item["reorder_threshold"], item["uom"])
                if item["reorder_threshold"] is not None
                else "-"
            ),
            item["reorder_status"],
        ]
        for item in report["items"]
    ]
    if parsed_format == "xlsx":
        return (
            _build_xlsx("Stock Overview", headers, rows),
            _build_export_filename("stock_overview", "xlsx"),
            _EXPORT_XLSX_MIMETYPE,
        )

    subtitle_lines = [
        f"Date range: {report['period']['date_from']} to {report['period']['date_to']}",
        _exported_at_line(),
    ]
    return (
        _build_pdf(
            title="Stock Overview",
            headers=headers,
            rows=rows,
            subtitle_lines=subtitle_lines,
            landscape_mode=True,
        ),
        _build_export_filename("stock_overview", "pdf"),
        _EXPORT_PDF_MIMETYPE,
    )


def export_surplus_report(*, export_format: Any) -> tuple[bytes, str, str]:
    parsed_format = _parse_export_format(export_format)
    report = get_surplus_report()
    headers = [
        "Article No.",
        "Description",
        "Batch",
        "Expiry date",
        "Surplus qty",
        "Discovered",
    ]
    rows = [
        [
            sanitize_cell(item["article_no"]),
            sanitize_cell(item["description"]),
            sanitize_cell(item["batch_code"]) if item["batch_code"] else "-",
            item["expiry_date"] or "-",
            _format_export_quantity(item["surplus_qty"], item["uom"]),
            item["discovered"],
        ]
        for item in report["items"]
    ]
    if parsed_format == "xlsx":
        return (
            _build_xlsx("Surplus", headers, rows),
            _build_export_filename("surplus", "xlsx"),
            _EXPORT_XLSX_MIMETYPE,
        )

    subtitle_lines = [_exported_at_line()]
    return (
        _build_pdf(
            title="Surplus List",
            headers=headers,
            rows=rows,
            subtitle_lines=subtitle_lines,
            landscape_mode=False,
        ),
        _build_export_filename("surplus", "pdf"),
        _EXPORT_PDF_MIMETYPE,
    )


def export_transaction_log(
    *,
    export_format: Any,
    article_id: Any = None,
    date_from: Any = None,
    date_to: Any = None,
    tx_types: Iterable[Any] | None = None,
) -> tuple[bytes, str, str]:
    parsed_format = _parse_export_format(export_format)
    rows = _transaction_base_query(
        article_id=article_id,
        date_from=date_from,
        date_to=date_to,
        tx_types=tx_types,
    ).all()
    items = [_serialize_transaction(row) for row in rows]
    headers = [
        "Occurred at",
        "Article No.",
        "Description",
        "Type",
        "Quantity",
        "Batch",
        "Reference",
        "User",
    ]
    export_rows = [
        [
            item["occurred_at"],
            sanitize_cell(item["article_no"]),
            sanitize_cell(item["description"]),
            item["type"],
            _format_export_quantity(item["quantity"], item["uom"]),
            sanitize_cell(item["batch_code"]) if item["batch_code"] else "-",
            sanitize_cell(item["reference"]) if item["reference"] else "-",
            sanitize_cell(item["user"]) if item["user"] else "-",
        ]
        for item in items
    ]
    if parsed_format == "xlsx":
        return (
            _build_xlsx("Transactions", headers, export_rows),
            _build_export_filename("transactions", "xlsx"),
            _EXPORT_XLSX_MIMETYPE,
        )

    subtitle_lines = [_exported_at_line()]
    if date_from not in (None, "") or date_to not in (None, ""):
        subtitle_lines.insert(
            0,
            f"Date range: {date_from or '-'} to {date_to or '-'}",
        )
    return (
        _build_pdf(
            title="Transaction Log",
            headers=headers,
            rows=export_rows,
            subtitle_lines=subtitle_lines,
            landscape_mode=True,
        ),
        _build_export_filename("transactions", "pdf"),
        _EXPORT_PDF_MIMETYPE,
    )
