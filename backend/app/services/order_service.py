"""Business logic for the Phase 8 Orders module."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import case, func

from app.extensions import db
from app.models.article import Article
from app.models.article_supplier import ArticleSupplier
from app.models.enums import OrderLineStatus, OrderStatus
from app.models.order import Order
from app.models.order_line import OrderLine
from app.models.supplier import Supplier
from app.models.uom_catalog import UomCatalog
from app.utils.validators import validate_note, validate_quantity

_QTY_QUANT = Decimal("0.001")
_PRICE_QUANT = Decimal("0.0001")
_ORDER_NUMBER_RE = re.compile(r"^ORD-(\d+)$", re.IGNORECASE)


class OrderServiceError(Exception):
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
class PreparedOrderLine:
    """Validated order-line payload prepared for persistence."""

    article: Article
    supplier_article_code: str | None
    ordered_qty: Decimal
    uom: str
    unit_price: Decimal
    delivery_date: date | None
    note: str | None


def _quantize_quantity(value: Decimal) -> Decimal:
    return value.quantize(_QTY_QUANT, rounding=ROUND_HALF_UP)


def _quantize_price(value: Decimal) -> Decimal:
    return value.quantize(_PRICE_QUANT, rounding=ROUND_HALF_UP)


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


def _validate_optional_text(
    value: Any,
    *,
    field_name: str,
    max_length: int,
) -> str | None:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    if len(normalized) > max_length:
        raise OrderServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be {max_length} characters or fewer.",
            400,
        )
    return normalized


def _require_text(
    value: Any,
    *,
    field_name: str,
    max_length: int,
    details: dict[str, Any] | None = None,
) -> str:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        raise OrderServiceError(
            "VALIDATION_ERROR",
            f"{field_name} is required.",
            400,
            details,
        )
    if len(normalized) > max_length:
        raise OrderServiceError(
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
        return int(value)
    except (TypeError, ValueError):
        raise OrderServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be a valid integer.",
            400,
            details,
        ) from None


def _parse_required_price(
    value: Any,
    *,
    field_name: str,
    details: dict[str, Any] | None = None,
) -> Decimal:
    if value in (None, ""):
        raise OrderServiceError(
            "VALIDATION_ERROR",
            f"{field_name} is required.",
            400,
            details,
        )
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise OrderServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be a valid number.",
            400,
            details,
        ) from None
    if parsed < 0:
        raise OrderServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be greater than or equal to zero.",
            400,
            details,
        )
    return _quantize_price(parsed)


def _parse_optional_date(
    value: Any,
    *,
    field_name: str,
    details: dict[str, Any] | None = None,
) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise OrderServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be a valid ISO date.",
            400,
            details,
        ) from None


def _validate_allowed_fields(
    payload: dict[str, Any],
    *,
    allowed_fields: set[str],
) -> None:
    extra_fields = sorted(set(payload.keys()) - allowed_fields)
    if extra_fields:
        raise OrderServiceError(
            "VALIDATION_ERROR",
            f"Unsupported fields: {', '.join(extra_fields)}.",
            400,
            {"fields": extra_fields},
        )


def _get_order_number_suffix(order_number: str) -> int | None:
    match = _ORDER_NUMBER_RE.match(order_number)
    if not match:
        return None
    return int(match.group(1))


def _generate_order_number() -> str:
    max_suffix = 0
    rows = db.session.query(Order.order_number).all()
    for (order_number,) in rows:
        if not order_number:
            continue
        suffix = _get_order_number_suffix(order_number)
        if suffix is not None:
            max_suffix = max(max_suffix, suffix)
    return f"ORD-{max_suffix + 1:04d}"


def _order_number_exists(order_number: str, *, exclude_order_id: int | None = None) -> bool:
    query = db.session.query(Order.id).filter(
        func.upper(Order.order_number) == order_number.upper()
    )
    if exclude_order_id is not None:
        query = query.filter(Order.id != exclude_order_id)
    return query.first() is not None


def _resolve_order_number(raw_value: Any) -> str:
    manual_value = _normalize_optional_text(raw_value)
    if manual_value is None:
        generated = _generate_order_number()
        while _order_number_exists(generated):
            generated = _generate_order_number()
        return generated

    if len(manual_value) > 100:
        raise OrderServiceError(
            "VALIDATION_ERROR",
            "order_number must be 100 characters or fewer.",
            400,
        )
    if _order_number_exists(manual_value):
        raise OrderServiceError(
            "ORDER_NUMBER_EXISTS",
            "Order number already exists.",
            409,
            {"order_number": manual_value},
        )
    return manual_value


def _get_supplier(
    supplier_id: int,
    *,
    require_active: bool = True,
) -> Supplier:
    supplier = db.session.get(Supplier, supplier_id)
    if supplier is None or (require_active and not supplier.is_active):
        raise OrderServiceError(
            "SUPPLIER_NOT_FOUND",
            "Supplier not found.",
            404,
            {"supplier_id": supplier_id},
        )
    return supplier


def _get_order(order_id: int, *, for_update: bool = False) -> Order:
    query = db.session.query(Order).filter_by(id=order_id)
    if for_update:
        query = query.with_for_update()
    order = query.first()
    if order is None:
        raise OrderServiceError(
            "ORDER_NOT_FOUND",
            "Order not found.",
            404,
            {"order_id": order_id},
        )
    return order


def _get_order_line(order_id: int, line_id: int, *, for_update: bool = False) -> OrderLine:
    query = db.session.query(OrderLine).filter_by(id=line_id, order_id=order_id)
    if for_update:
        query = query.with_for_update()
    line = query.first()
    if line is None:
        raise OrderServiceError(
            "ORDER_LINE_NOT_FOUND",
            "Order line not found.",
            404,
            {"order_id": order_id, "line_id": line_id},
        )
    return line


def _ensure_order_open(order: Order) -> None:
    if order.status != OrderStatus.OPEN:
        raise OrderServiceError(
            "ORDER_CLOSED",
            "This order is already closed.",
            400,
            {"order_id": order.id},
        )


def _ensure_line_open(line: OrderLine) -> None:
    if line.status == OrderLineStatus.REMOVED:
        raise OrderServiceError(
            "ORDER_LINE_REMOVED",
            "Order line has been removed.",
            409,
            {"order_line_id": line.id},
        )
    if line.status == OrderLineStatus.CLOSED:
        raise OrderServiceError(
            "ORDER_LINE_CLOSED",
            "Order line is already closed.",
            409,
            {"order_line_id": line.id},
        )


def _get_article(article_id: int, *, details: dict[str, Any] | None = None) -> Article:
    article = db.session.get(Article, article_id)
    if article is None or not article.is_active:
        raise OrderServiceError(
            "ARTICLE_NOT_FOUND",
            "Article not found.",
            404,
            details or {"article_id": article_id},
        )
    return article


def _get_article_base_uom(article: Article) -> str:
    uom = db.session.get(UomCatalog, article.base_uom)
    if uom is None:
        raise OrderServiceError(
            "INTERNAL_ERROR",
            f"Article {article.article_no} has no valid base UOM.",
            500,
            {"article_id": article.id},
        )
    return uom.code


def _get_article_supplier_link(article_id: int, supplier_id: int) -> ArticleSupplier | None:
    return (
        db.session.query(ArticleSupplier)
        .filter_by(article_id=article_id, supplier_id=supplier_id)
        .first()
    )


def _prepare_new_line(
    raw_line: Any,
    *,
    supplier_id: int,
    line_index: int,
) -> PreparedOrderLine:
    if not isinstance(raw_line, dict):
        raise OrderServiceError(
            "VALIDATION_ERROR",
            "Each order line must be an object.",
            400,
            {"line_index": line_index},
        )

    _validate_allowed_fields(
        raw_line,
        allowed_fields={
            "article_id",
            "supplier_article_code",
            "ordered_qty",
            "uom",
            "unit_price",
            "delivery_date",
            "note",
        },
    )

    details = {"line_index": line_index}
    article = _get_article(
        _parse_int(raw_line.get("article_id"), field_name="article_id", details=details),
        details=details,
    )

    qty_ok, ordered_qty, qty_error = validate_quantity(raw_line.get("ordered_qty"))
    if not qty_ok or ordered_qty is None:
        raise OrderServiceError(
            "VALIDATION_ERROR",
            qty_error or "ordered_qty is invalid.",
            400,
            details,
        )

    requested_uom = _require_text(
        raw_line.get("uom"),
        field_name="uom",
        max_length=50,
        details=details,
    )
    authoritative_uom = _get_article_base_uom(article)
    if requested_uom != authoritative_uom:
        raise OrderServiceError(
            "UOM_MISMATCH",
            f"uom must match article base UOM '{authoritative_uom}'.",
            400,
            {
                **details,
                "expected_uom": authoritative_uom,
                "received_uom": requested_uom,
            },
        )

    supplier_link = _get_article_supplier_link(article.id, supplier_id)
    supplier_article_code = _validate_optional_text(
        raw_line.get("supplier_article_code"),
        field_name="supplier_article_code",
        max_length=255,
    )
    if supplier_article_code is None and supplier_link is not None:
        supplier_article_code = supplier_link.supplier_article_code

    unit_price = _parse_required_price(
        raw_line.get("unit_price"),
        field_name="unit_price",
        details=details,
    )

    note = _normalize_optional_text(raw_line.get("note"))
    note_ok, note_error = validate_note(note)
    if not note_ok:
        raise OrderServiceError(
            "VALIDATION_ERROR",
            note_error or "Invalid note.",
            400,
            details,
        )

    return PreparedOrderLine(
        article=article,
        supplier_article_code=supplier_article_code,
        ordered_qty=_quantize_quantity(ordered_qty),
        uom=authoritative_uom,
        unit_price=unit_price,
        delivery_date=_parse_optional_date(
            raw_line.get("delivery_date"),
            field_name="delivery_date",
            details=details,
        ),
        note=note,
    )


def recalculate_order_status(order: Order, occurred_at: datetime | None = None) -> None:
    """Recalculate order status from its active lines."""
    active_statuses = [
        row[0]
        for row in db.session.query(OrderLine.status)
        .filter(
            OrderLine.order_id == order.id,
            OrderLine.status != OrderLineStatus.REMOVED,
        )
        .all()
    ]

    if not active_statuses or all(status == OrderLineStatus.CLOSED for status in active_statuses):
        order.status = OrderStatus.CLOSED
    else:
        order.status = OrderStatus.OPEN

    if occurred_at is not None:
        order.updated_at = occurred_at


def recalculate_order_line_status(line: OrderLine) -> None:
    """Recalculate a line status after a quantity mutation."""
    if line.status == OrderLineStatus.REMOVED:
        return

    ordered_qty = _decimal_from_model(line.ordered_qty)
    received_qty = _decimal_from_model(line.received_qty)
    if received_qty >= ordered_qty:
        line.status = OrderLineStatus.CLOSED
    else:
        line.status = OrderLineStatus.OPEN


def _compute_total_value(lines: list[OrderLine]) -> Decimal:
    total = Decimal("0")
    for line in lines:
        if line.status == OrderLineStatus.REMOVED:
            continue
        if line.unit_price is None:
            continue
        total += _decimal_from_model(line.ordered_qty) * _decimal_from_model(line.unit_price)
    return _quantize_price(total)


def _serialize_receiving_summary(order: Order) -> dict[str, Any]:
    open_line_count = (
        db.session.query(func.count(OrderLine.id))
        .filter(
            OrderLine.order_id == order.id,
            OrderLine.status == OrderLineStatus.OPEN,
        )
        .scalar()
        or 0
    )
    supplier = db.session.get(Supplier, order.supplier_id)
    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status.value if hasattr(order.status, "value") else order.status,
        "supplier_id": order.supplier_id,
        "supplier_name": supplier.name if supplier else None,
        "open_line_count": int(open_line_count),
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


def _serialize_order_list_item(order: Order) -> dict[str, Any]:
    supplier = db.session.get(Supplier, order.supplier_id)
    lines = (
        db.session.query(OrderLine)
        .filter(OrderLine.order_id == order.id)
        .order_by(OrderLine.id.asc())
        .all()
    )
    total_value = _compute_total_value(lines)
    return {
        "id": order.id,
        "order_number": order.order_number,
        "supplier_id": order.supplier_id,
        "supplier_name": supplier.name if supplier else None,
        "status": order.status.value if hasattr(order.status, "value") else order.status,
        "line_count": len(lines),
        "total_value": float(total_value),
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


def _serialize_detail_line(line: OrderLine, *, position: int) -> dict[str, Any]:
    article = db.session.get(Article, line.article_id)
    unit_price = (
        _decimal_from_model(line.unit_price) if line.unit_price is not None else None
    )
    total_price = (
        _quantize_price(_decimal_from_model(line.ordered_qty) * unit_price)
        if unit_price is not None
        else Decimal("0")
    )
    return {
        "id": line.id,
        "position": position,
        "article_id": line.article_id,
        "article_no": article.article_no if article else None,
        "description": article.description if article else None,
        "supplier_article_code": line.supplier_article_code,
        "ordered_qty": float(_decimal_from_model(line.ordered_qty)),
        "received_qty": float(_decimal_from_model(line.received_qty)),
        "uom": line.uom,
        "unit_price": float(unit_price) if unit_price is not None else None,
        "total_price": float(total_price),
        "delivery_date": line.delivery_date.isoformat() if line.delivery_date else None,
        "status": line.status.value if hasattr(line.status, "value") else line.status,
        "note": line.note,
    }


def _serialize_receiving_detail_line(line: OrderLine) -> dict[str, Any]:
    article = db.session.get(Article, line.article_id)
    ordered_qty = _decimal_from_model(line.ordered_qty)
    received_qty = _decimal_from_model(line.received_qty)
    remaining_qty = max(ordered_qty - received_qty, Decimal("0"))

    return {
        "id": line.id,
        "article_id": line.article_id,
        "article_no": article.article_no if article else None,
        "description": article.description if article else None,
        "has_batch": article.has_batch if article else False,
        "ordered_qty": float(ordered_qty),
        "received_qty": float(received_qty),
        "remaining_qty": float(_quantize_quantity(remaining_qty)),
        "status": line.status.value if hasattr(line.status, "value") else line.status,
        "is_open": line.status == OrderLineStatus.OPEN,
        "uom": line.uom,
        "unit_price": (
            float(_decimal_from_model(line.unit_price))
            if line.unit_price is not None
            else None
        ),
        "delivery_date": line.delivery_date.isoformat() if line.delivery_date else None,
    }


def _serialize_order_detail(order: Order) -> dict[str, Any]:
    supplier = db.session.get(Supplier, order.supplier_id)
    lines = (
        db.session.query(OrderLine)
        .filter(OrderLine.order_id == order.id)
        .order_by(OrderLine.id.asc())
        .all()
    )
    serialized_lines = [
        _serialize_detail_line(line, position=index)
        for index, line in enumerate(lines, start=1)
    ]
    total_value = _compute_total_value(lines)
    return {
        "id": order.id,
        "order_number": order.order_number,
        "supplier_id": order.supplier_id,
        "supplier_name": supplier.name if supplier else None,
        "supplier_address": supplier.address if supplier else None,
        "supplier_confirmation_number": order.supplier_confirmation_number,
        "status": order.status.value if hasattr(order.status, "value") else order.status,
        "note": order.note,
        "total_value": float(total_value),
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "lines": serialized_lines,
    }


def _serialize_receiving_detail(order: Order) -> dict[str, Any]:
    supplier = db.session.get(Supplier, order.supplier_id)
    lines = (
        db.session.query(OrderLine)
        .filter(
            OrderLine.order_id == order.id,
            OrderLine.status == OrderLineStatus.OPEN,
        )
        .order_by(OrderLine.id.asc())
        .all()
    )
    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status.value if hasattr(order.status, "value") else order.status,
        "supplier_id": order.supplier_id,
        "supplier_name": supplier.name if supplier else None,
        "supplier_confirmation_number": order.supplier_confirmation_number,
        "note": order.note,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "lines": [_serialize_receiving_detail_line(line) for line in lines],
    }


def list_orders(page: int, per_page: int) -> dict[str, Any]:
    """Return the paginated orders list."""
    ordering = case((Order.status == OrderStatus.OPEN, 0), else_=1)
    query = Order.query.order_by(ordering.asc(), Order.created_at.desc(), Order.id.desc())
    total = query.count()
    rows = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [_serialize_order_list_item(order) for order in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def find_order_by_number(query: str | None) -> dict[str, Any]:
    """Return the receiving-compatibility summary for an exact match."""
    normalized = (query or "").strip()
    if not normalized:
        raise OrderServiceError(
            "VALIDATION_ERROR",
            "Query parameter 'q' is required.",
            400,
        )

    order = (
        Order.query
        .filter(func.upper(Order.order_number) == normalized.upper())
        .first()
    )
    if order is None:
        raise OrderServiceError(
            "ORDER_NOT_FOUND",
            "Order not found.",
            404,
            {"order_number": normalized},
        )
    return _serialize_receiving_summary(order)


def get_order_detail(order_id: int, *, view: str | None = None) -> dict[str, Any]:
    """Return either canonical order detail or receiving compatibility detail."""
    if view not in (None, "", "receiving"):
        raise OrderServiceError(
            "VALIDATION_ERROR",
            "view must be 'receiving' when provided.",
            400,
            {"view": view},
        )

    order = _get_order(order_id)
    if view == "receiving":
        return _serialize_receiving_detail(order)
    return _serialize_order_detail(order)


def create_order(user_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Create a new order with at least one line."""
    body = payload or {}
    _validate_allowed_fields(
        body,
        allowed_fields={
            "order_number",
            "supplier_id",
            "supplier_confirmation_number",
            "note",
            "lines",
        },
    )

    supplier_id = _parse_int(body.get("supplier_id"), field_name="supplier_id")
    supplier = _get_supplier(supplier_id, require_active=True)

    note = _normalize_optional_text(body.get("note"))
    note_ok, note_error = validate_note(note)
    if not note_ok:
        raise OrderServiceError("VALIDATION_ERROR", note_error or "Invalid note.", 400)

    supplier_confirmation_number = _validate_optional_text(
        body.get("supplier_confirmation_number"),
        field_name="supplier_confirmation_number",
        max_length=255,
    )

    raw_lines = body.get("lines")
    if not isinstance(raw_lines, list):
        raise OrderServiceError("VALIDATION_ERROR", "lines must be a list.", 400)
    if not raw_lines:
        raise OrderServiceError(
            "VALIDATION_ERROR",
            "At least one line is required.",
            400,
        )

    prepared_lines = [
        _prepare_new_line(raw_line, supplier_id=supplier.id, line_index=index)
        for index, raw_line in enumerate(raw_lines)
    ]
    now = datetime.now(timezone.utc)
    order = Order(
        order_number=_resolve_order_number(body.get("order_number")),
        supplier_id=supplier.id,
        supplier_confirmation_number=supplier_confirmation_number,
        status=OrderStatus.OPEN,
        note=note,
        created_by=user_id,
        created_at=now,
        updated_at=now,
    )
    db.session.add(order)
    db.session.flush()

    for prepared in prepared_lines:
        db.session.add(
            OrderLine(
                order_id=order.id,
                article_id=prepared.article.id,
                supplier_article_code=prepared.supplier_article_code,
                ordered_qty=prepared.ordered_qty,
                received_qty=Decimal("0.000"),
                uom=prepared.uom,
                unit_price=prepared.unit_price,
                delivery_date=prepared.delivery_date,
                status=OrderLineStatus.OPEN,
                note=prepared.note,
            )
        )

    db.session.flush()
    recalculate_order_status(order, now)
    db.session.commit()

    return {
        "id": order.id,
        "order_number": order.order_number,
        "supplier_id": order.supplier_id,
        "supplier_name": supplier.name,
        "status": order.status.value if hasattr(order.status, "value") else order.status,
        "total_value": float(_compute_total_value(order.lines.order_by(OrderLine.id.asc()).all())),
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


def update_order_header(order_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Update editable header fields on an open order."""
    body = payload or {}
    _validate_allowed_fields(
        body,
        allowed_fields={"supplier_confirmation_number", "note"},
    )
    if not body:
        raise OrderServiceError(
            "VALIDATION_ERROR",
            "At least one editable field is required.",
            400,
        )

    order = _get_order(order_id, for_update=True)
    _ensure_order_open(order)

    if "supplier_confirmation_number" in body:
        order.supplier_confirmation_number = _validate_optional_text(
            body.get("supplier_confirmation_number"),
            field_name="supplier_confirmation_number",
            max_length=255,
        )

    if "note" in body:
        note = _normalize_optional_text(body.get("note"))
        note_ok, note_error = validate_note(note)
        if not note_ok:
            raise OrderServiceError(
                "VALIDATION_ERROR",
                note_error or "Invalid note.",
                400,
            )
        order.note = note

    order.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return _serialize_order_detail(order)


def add_order_line(order_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Add a new line to an open order."""
    order = _get_order(order_id, for_update=True)
    _ensure_order_open(order)
    prepared = _prepare_new_line(payload or {}, supplier_id=order.supplier_id, line_index=0)

    db.session.add(
        OrderLine(
            order_id=order.id,
            article_id=prepared.article.id,
            supplier_article_code=prepared.supplier_article_code,
            ordered_qty=prepared.ordered_qty,
            received_qty=Decimal("0.000"),
            uom=prepared.uom,
            unit_price=prepared.unit_price,
            delivery_date=prepared.delivery_date,
            status=OrderLineStatus.OPEN,
            note=prepared.note,
        )
    )

    now = datetime.now(timezone.utc)
    order.updated_at = now
    recalculate_order_status(order, now)
    db.session.commit()
    return _serialize_order_detail(order)


def update_order_line(
    order_id: int,
    line_id: int,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """Update an editable open order line."""
    body = payload or {}
    _validate_allowed_fields(
        body,
        allowed_fields={"supplier_article_code", "ordered_qty", "unit_price", "delivery_date", "note"},
    )
    if not body:
        raise OrderServiceError(
            "VALIDATION_ERROR",
            "At least one editable field is required.",
            400,
        )

    order = _get_order(order_id, for_update=True)
    _ensure_order_open(order)
    line = _get_order_line(order_id, line_id, for_update=True)
    _ensure_line_open(line)

    if "supplier_article_code" in body:
        line.supplier_article_code = _validate_optional_text(
            body.get("supplier_article_code"),
            field_name="supplier_article_code",
            max_length=255,
        )

    if "ordered_qty" in body:
        qty_ok, ordered_qty, qty_error = validate_quantity(body.get("ordered_qty"))
        if not qty_ok or ordered_qty is None:
            raise OrderServiceError(
                "VALIDATION_ERROR",
                qty_error or "ordered_qty is invalid.",
                400,
            )
        line.ordered_qty = _quantize_quantity(ordered_qty)

    if "unit_price" in body:
        line.unit_price = _parse_required_price(body.get("unit_price"), field_name="unit_price")

    if "delivery_date" in body:
        line.delivery_date = _parse_optional_date(
            body.get("delivery_date"),
            field_name="delivery_date",
        )

    if "note" in body:
        note = _normalize_optional_text(body.get("note"))
        note_ok, note_error = validate_note(note)
        if not note_ok:
            raise OrderServiceError("VALIDATION_ERROR", note_error or "Invalid note.", 400)
        line.note = note

    recalculate_order_line_status(line)
    now = datetime.now(timezone.utc)
    recalculate_order_status(order, now)
    db.session.commit()
    return _serialize_order_detail(order)


def remove_order_line(order_id: int, line_id: int) -> dict[str, Any]:
    """Soft-remove an open order line."""
    order = _get_order(order_id, for_update=True)
    _ensure_order_open(order)
    line = _get_order_line(order_id, line_id, for_update=True)
    _ensure_line_open(line)

    line.status = OrderLineStatus.REMOVED
    now = datetime.now(timezone.utc)
    recalculate_order_status(order, now)
    db.session.commit()
    return _serialize_order_detail(order)


def lookup_suppliers(query: str | None) -> dict[str, Any]:
    """Lookup active suppliers by name or internal code."""
    normalized = (query or "").strip()
    if not normalized:
        raise OrderServiceError(
            "VALIDATION_ERROR",
            "Query parameter 'q' is required.",
            400,
        )

    pattern = f"%{normalized.lower()}%"
    rows = (
        Supplier.query
        .filter(Supplier.is_active.is_(True))
        .filter(
            db.or_(
                func.lower(Supplier.name).like(pattern),
                func.lower(Supplier.internal_code).like(pattern),
            )
        )
        .order_by(Supplier.name.asc(), Supplier.id.asc())
        .limit(20)
        .all()
    )
    return {
        "items": [
            {
                "id": supplier.id,
                "internal_code": supplier.internal_code,
                "name": supplier.name,
            }
            for supplier in rows
        ]
    }


def lookup_articles(query: str | None, *, supplier_id: int | None = None) -> dict[str, Any]:
    """Lookup active articles by article number or description."""
    normalized = (query or "").strip()
    if not normalized:
        raise OrderServiceError(
            "VALIDATION_ERROR",
            "Query parameter 'q' is required.",
            400,
        )

    if supplier_id is not None:
        _get_supplier(supplier_id, require_active=True)

    pattern = f"%{normalized.lower()}%"
    rows = (
        Article.query
        .filter(Article.is_active.is_(True))
        .filter(
            db.or_(
                func.lower(Article.article_no).like(pattern),
                func.lower(Article.description).like(pattern),
            )
        )
        .order_by(Article.article_no.asc(), Article.id.asc())
        .limit(20)
        .all()
    )

    items = []
    for article in rows:
        uom = db.session.get(UomCatalog, article.base_uom)
        supplier_link = (
            _get_article_supplier_link(article.id, supplier_id)
            if supplier_id is not None
            else None
        )
        items.append(
            {
                "article_id": article.id,
                "article_no": article.article_no,
                "description": article.description,
                "uom": uom.code if uom else None,
                "supplier_article_code": (
                    supplier_link.supplier_article_code if supplier_link else None
                ),
                "last_price": (
                    float(_decimal_from_model(supplier_link.last_price))
                    if supplier_link and supplier_link.last_price is not None
                    else None
                ),
            }
        )
    return {"items": items}


def generate_order_pdf(order_id: int) -> tuple[bytes, str]:
    """Generate a generic PDF representation of an order."""
    order = _get_order(order_id)
    detail = _serialize_order_detail(order)
    subtotal = Decimal(str(detail["total_value"]))
    vat = Decimal("0.00")
    grand_total = subtotal + vat

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )
    styles = getSampleStyleSheet()

    story = [
        Paragraph(f"Purchase Order {detail['order_number']}", styles["Title"]),
        Spacer(1, 4 * mm),
        Paragraph(f"Date: {detail['created_at'] or 'N/A'}", styles["BodyText"]),
        Paragraph(f"Status: {detail['status']}", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Supplier", styles["Heading3"]),
        Paragraph(detail["supplier_name"] or "N/A", styles["BodyText"]),
        Paragraph(detail["supplier_address"] or "Address not provided.", styles["BodyText"]),
    ]

    if detail["supplier_confirmation_number"]:
        story.append(
            Paragraph(
                f"Supplier confirmation number: {detail['supplier_confirmation_number']}",
                styles["BodyText"],
            )
        )

    story.append(Spacer(1, 6 * mm))

    table_rows: list[list[str]] = [[
        "Pos",
        "Article",
        "Supplier code",
        "Qty",
        "UOM",
        "Unit price",
        "Total",
        "Delivery date",
    ]]
    for line in detail["lines"]:
        if line["status"] == OrderLineStatus.REMOVED.value:
            continue
        table_rows.append(
            [
                str(line["position"]),
                f"{line['article_no'] or ''} {line['description'] or ''}".strip(),
                line["supplier_article_code"] or "",
                f"{line['ordered_qty']:.3f}",
                line["uom"] or "",
                "" if line["unit_price"] is None else f"{line['unit_price']:.4f}",
                f"{line['total_price']:.4f}",
                line["delivery_date"] or "",
            ]
        )

    line_table = Table(
        table_rows,
        colWidths=[12 * mm, 58 * mm, 30 * mm, 18 * mm, 16 * mm, 24 * mm, 24 * mm, 28 * mm],
        repeatRows=1,
    )
    line_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e3f0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
            ]
        )
    )
    story.append(line_table)
    story.append(Spacer(1, 6 * mm))

    totals_rows = [
        ["Subtotal", f"{subtotal:.4f}"],
        ["VAT", f"{vat:.2f}"],
        ["Grand total", f"{grand_total:.4f}"],
    ]
    totals_table = Table(totals_rows, colWidths=[35 * mm, 28 * mm], hAlign="RIGHT")
    totals_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]
        )
    )
    story.append(totals_table)

    if detail["note"]:
        story.extend(
            [
                Spacer(1, 6 * mm),
                Paragraph("Note", styles["Heading3"]),
                Paragraph(detail["note"], styles["BodyText"]),
            ]
        )

    doc.build(story)
    return buffer.getvalue(), detail["order_number"]
