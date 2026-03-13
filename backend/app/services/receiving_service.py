"""Business logic for Phase 7 Receiving and its dependent order lookups."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func

from app.extensions import db
from app.models.article import Article
from app.models.batch import Batch
from app.models.enums import OrderLineStatus, OrderStatus, TxType
from app.models.location import Location
from app.models.order import Order
from app.models.order_line import OrderLine
from app.models.receiving import Receiving
from app.models.stock import Stock
from app.models.supplier import Supplier
from app.models.transaction import Transaction
from app.models.uom_catalog import UomCatalog
from app.models.user import User
from app.utils.validators import validate_batch_code, validate_note, validate_quantity

_V1_LOCATION_ID = 1
_QTY_QUANT = Decimal("0.001")
_PRICE_QUANT = Decimal("0.0001")


class ReceivingServiceError(Exception):
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
class _PreparedReceiptLine:
    """Validated receipt line ready for persistence."""

    article: Article
    quantity: Decimal
    uom: str
    batch: Batch | None
    unit_price: Decimal | None
    order: Order | None
    order_line: OrderLine | None


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
        return str(value)
    trimmed = value.strip()
    return trimmed or None


def _require_text(
    value: Any,
    *,
    field_name: str,
    max_length: int,
    details: dict[str, Any] | None = None,
) -> str:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        raise ReceivingServiceError(
            "VALIDATION_ERROR",
            f"{field_name} is required.",
            400,
            details,
        )
    if len(normalized) > max_length:
        raise ReceivingServiceError(
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
        raise ReceivingServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be a valid integer.",
            400,
            details,
        ) from None


def _parse_optional_decimal(
    value: Any,
    *,
    field_name: str,
    details: dict[str, Any] | None = None,
) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ReceivingServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be a valid number.",
            400,
            details,
        ) from None
    if parsed < 0:
        raise ReceivingServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be greater than or equal to zero.",
            400,
            details,
        )
    return _quantize_price(parsed)


def _parse_required_date(
    value: Any,
    *,
    field_name: str,
    details: dict[str, Any] | None = None,
) -> date:
    if value in (None, ""):
        raise ReceivingServiceError(
            "VALIDATION_ERROR",
            f"{field_name} is required.",
            400,
            details,
        )
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ReceivingServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be a valid ISO date.",
            400,
            details,
        ) from None


def _get_location() -> Location:
    location = db.session.get(Location, _V1_LOCATION_ID)
    if location is None:
        raise ReceivingServiceError(
            "INTERNAL_ERROR",
            "Primary location is not configured.",
            500,
        )
    return location


def _get_article_base_uom(article: Article) -> str:
    uom = db.session.get(UomCatalog, article.base_uom)
    if uom is None:
        raise ReceivingServiceError(
            "INTERNAL_ERROR",
            f"Article {article.article_no} has no valid base UOM.",
            500,
        )
    return uom.code


def _resolve_batch(
    article: Article,
    *,
    batch_code: str | None,
    expiry_date_value: Any,
    details: dict[str, Any],
) -> Batch | None:
    if not article.has_batch:
        return None

    if batch_code is None:
        raise ReceivingServiceError(
            "VALIDATION_ERROR",
            "batch_code is required for batch-tracked articles.",
            400,
            details,
        )
    if not validate_batch_code(batch_code):
        raise ReceivingServiceError(
            "VALIDATION_ERROR",
            "batch_code has an invalid format.",
            400,
            details,
        )

    expiry_date = _parse_required_date(
        expiry_date_value,
        field_name="expiry_date",
        details=details,
    )

    batch = Batch.query.filter_by(
        article_id=article.id,
        batch_code=batch_code,
    ).first()
    if batch is not None:
        if batch.expiry_date != expiry_date:
            raise ReceivingServiceError(
                "BATCH_EXPIRY_MISMATCH",
                f"Batch {batch_code} already exists with a different expiry date.",
                409,
                {
                    **details,
                    "article_id": article.id,
                    "batch_code": batch_code,
                    "existing_expiry_date": batch.expiry_date.isoformat(),
                    "received_expiry_date": expiry_date.isoformat(),
                },
            )
        return batch

    batch = Batch(
        article_id=article.id,
        batch_code=batch_code,
        expiry_date=expiry_date,
    )
    db.session.add(batch)
    db.session.flush()
    return batch


def _resolve_receipt_line(
    raw_line: Any,
    line_index: int,
) -> _PreparedReceiptLine | None:
    if not isinstance(raw_line, dict):
        raise ReceivingServiceError(
            "VALIDATION_ERROR",
            "Each receipt line must be an object.",
            400,
            {"line_index": line_index},
        )

    if raw_line.get("skip") is True:
        return None

    details = {"line_index": line_index}
    article_id = _parse_int(
        raw_line.get("article_id"),
        field_name="article_id",
        details=details,
    )

    qty_ok, quantity, qty_error = validate_quantity(raw_line.get("quantity"))
    if not qty_ok or quantity is None:
        raise ReceivingServiceError(
            "VALIDATION_ERROR",
            qty_error or "quantity is invalid.",
            400,
            details,
        )

    requested_uom = _require_text(
        raw_line.get("uom"),
        field_name="uom",
        max_length=50,
        details=details,
    )
    quantity = _quantize_quantity(quantity)
    line_unit_price = _parse_optional_decimal(
        raw_line.get("unit_price"),
        field_name="unit_price",
        details=details,
    )

    order_line_id = raw_line.get("order_line_id")
    if order_line_id in (None, ""):
        article = db.session.get(Article, article_id)
        if article is None or not article.is_active:
            raise ReceivingServiceError(
                "ARTICLE_NOT_FOUND",
                "Article not found.",
                404,
                details,
            )

        authoritative_uom = _get_article_base_uom(article)
        if requested_uom != authoritative_uom:
            raise ReceivingServiceError(
                "UOM_MISMATCH",
                f"uom must match article base UOM '{authoritative_uom}'.",
                400,
                {
                    **details,
                    "expected_uom": authoritative_uom,
                    "received_uom": requested_uom,
                },
            )

        batch = _resolve_batch(
            article,
            batch_code=_normalize_optional_text(raw_line.get("batch_code")),
            expiry_date_value=raw_line.get("expiry_date"),
            details=details,
        )

        return _PreparedReceiptLine(
            article=article,
            quantity=quantity,
            uom=authoritative_uom,
            batch=batch,
            unit_price=line_unit_price,
            order=None,
            order_line=None,
        )

    order_line = (
        db.session.query(OrderLine)
        .filter_by(id=_parse_int(order_line_id, field_name="order_line_id", details=details))
        .with_for_update()
        .first()
    )
    if order_line is None:
        raise ReceivingServiceError(
            "ORDER_LINE_NOT_FOUND",
            "Order line not found.",
            404,
            details,
        )

    order = (
        db.session.query(Order)
        .filter_by(id=order_line.order_id)
        .with_for_update()
        .first()
    )
    if order is None:
        raise ReceivingServiceError(
            "ORDER_NOT_FOUND",
            "Order not found.",
            404,
            details,
        )
    if order.status != OrderStatus.OPEN:
        raise ReceivingServiceError(
            "ORDER_CLOSED",
            "This order is already closed.",
            409,
            {**details, "order_id": order.id},
        )
    if order_line.status == OrderLineStatus.REMOVED:
        raise ReceivingServiceError(
            "ORDER_LINE_REMOVED",
            "Order line has been removed.",
            409,
            {**details, "order_line_id": order_line.id},
        )
    if order_line.status == OrderLineStatus.CLOSED:
        raise ReceivingServiceError(
            "ORDER_LINE_CLOSED",
            "Order line is already closed.",
            409,
            {**details, "order_line_id": order_line.id},
        )
    if order_line.article_id != article_id:
        raise ReceivingServiceError(
            "ARTICLE_MISMATCH",
            "article_id does not match the order line.",
            400,
            {
                **details,
                "expected_article_id": order_line.article_id,
                "received_article_id": article_id,
            },
        )

    article = db.session.get(Article, order_line.article_id)
    if article is None:
        raise ReceivingServiceError(
            "ARTICLE_NOT_FOUND",
            "Article not found.",
            404,
            details,
        )

    authoritative_uom = order_line.uom
    if requested_uom != authoritative_uom:
        raise ReceivingServiceError(
            "UOM_MISMATCH",
            f"uom must match order line UOM '{authoritative_uom}'.",
            400,
            {
                **details,
                "expected_uom": authoritative_uom,
                "received_uom": requested_uom,
            },
        )

    batch = _resolve_batch(
        article,
        batch_code=_normalize_optional_text(raw_line.get("batch_code")),
        expiry_date_value=raw_line.get("expiry_date"),
        details=details,
    )

    unit_price = line_unit_price
    if unit_price is None and order_line.unit_price is not None:
        unit_price = _quantize_price(Decimal(str(order_line.unit_price)))

    return _PreparedReceiptLine(
        article=article,
        quantity=quantity,
        uom=authoritative_uom,
        batch=batch,
        unit_price=unit_price,
        order=order,
        order_line=order_line,
    )


def _apply_stock_receipt(
    *,
    location_id: int,
    article: Article,
    batch: Batch | None,
    quantity: Decimal,
    uom: str,
    unit_price: Decimal | None,
    occurred_at: datetime,
) -> Stock:
    stock = (
        db.session.query(Stock)
        .filter_by(
            location_id=location_id,
            article_id=article.id,
            batch_id=batch.id if batch else None,
        )
        .with_for_update()
        .first()
    )

    current_quantity = _decimal_from_model(stock.quantity) if stock else Decimal("0")
    current_avg = _decimal_from_model(stock.average_price) if stock else Decimal("0")
    new_quantity = _quantize_quantity(current_quantity + quantity)

    if unit_price is None:
        if stock is not None:
            new_avg = current_avg
        else:
            new_avg = Decimal("0")
    else:
        new_avg = (
            (current_quantity * current_avg) + (quantity * unit_price)
        ) / (current_quantity + quantity)
        new_avg = _quantize_price(new_avg)

    if stock is None:
        stock = Stock(
            location_id=location_id,
            article_id=article.id,
            batch_id=batch.id if batch else None,
            quantity=new_quantity,
            uom=uom,
            average_price=_quantize_price(new_avg),
            last_updated=occurred_at,
        )
        db.session.add(stock)
        db.session.flush()
        return stock

    stock.quantity = new_quantity
    stock.uom = uom
    stock.average_price = _quantize_price(new_avg)
    stock.last_updated = occurred_at
    return stock


def _recalculate_order_status(order: Order, occurred_at: datetime) -> None:
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
    order.updated_at = occurred_at


def submit_receipt(user_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Validate and persist a new receipt with stock/order updates."""
    body = payload or {}
    location = _get_location()
    now = datetime.now(timezone.utc)

    delivery_note_number = _require_text(
        body.get("delivery_note_number"),
        field_name="delivery_note_number",
        max_length=100,
    )
    note = _normalize_optional_text(body.get("note"))
    note_ok, note_error = validate_note(note)
    if not note_ok:
        raise ReceivingServiceError("VALIDATION_ERROR", note_error or "Invalid note.", 400)

    raw_lines = body.get("lines")
    if not isinstance(raw_lines, list):
        raise ReceivingServiceError(
            "VALIDATION_ERROR",
            "lines must be a list.",
            400,
        )

    prepared_lines: list[_PreparedReceiptLine] = []
    has_ad_hoc = False
    for index, raw_line in enumerate(raw_lines):
        prepared = _resolve_receipt_line(raw_line, index)
        if prepared is None:
            continue
        prepared_lines.append(prepared)
        if prepared.order_line is None:
            has_ad_hoc = True

    if not prepared_lines:
        raise ReceivingServiceError(
            "VALIDATION_ERROR",
            "At least one line must be received.",
            400,
        )

    if has_ad_hoc and note is None:
        raise ReceivingServiceError(
            "VALIDATION_ERROR",
            "A note is required for ad-hoc receipts.",
            400,
        )

    receiving_ids: list[int] = []
    stock_updated: list[dict[str, Any]] = []
    affected_orders: dict[int, Order] = {}

    for prepared in prepared_lines:
        _apply_stock_receipt(
            location_id=location.id,
            article=prepared.article,
            batch=prepared.batch,
            quantity=prepared.quantity,
            uom=prepared.uom,
            unit_price=prepared.unit_price,
            occurred_at=now,
        )

        receiving = Receiving(
            order_line_id=prepared.order_line.id if prepared.order_line else None,
            article_id=prepared.article.id,
            batch_id=prepared.batch.id if prepared.batch else None,
            location_id=location.id,
            quantity=prepared.quantity,
            uom=prepared.uom,
            unit_price=prepared.unit_price,
            delivery_note_number=delivery_note_number,
            note=note,
            barcodes_printed=0,
            received_by=user_id,
            received_at=now,
        )
        db.session.add(receiving)
        db.session.flush()

        if prepared.order_line is not None:
            new_received_qty = _quantize_quantity(
                _decimal_from_model(prepared.order_line.received_qty) + prepared.quantity
            )
            prepared.order_line.received_qty = new_received_qty
            if new_received_qty >= _decimal_from_model(prepared.order_line.ordered_qty):
                prepared.order_line.status = OrderLineStatus.CLOSED
            affected_orders[prepared.order.id] = prepared.order

        transaction = Transaction(
            tx_type=TxType.STOCK_RECEIPT,
            occurred_at=now,
            location_id=location.id,
            article_id=prepared.article.id,
            batch_id=prepared.batch.id if prepared.batch else None,
            quantity=prepared.quantity,
            uom=prepared.uom,
            unit_price=prepared.unit_price,
            user_id=user_id,
            reference_type="receiving",
            reference_id=receiving.id,
            order_number=prepared.order.order_number if prepared.order else None,
            delivery_note_number=delivery_note_number,
        )
        db.session.add(transaction)

        receiving_ids.append(receiving.id)
        stock_updated.append(
            {
                "article_id": prepared.article.id,
                "article_no": prepared.article.article_no,
                "quantity_added": float(prepared.quantity),
                "uom": prepared.uom,
            }
        )

    for order in affected_orders.values():
        _recalculate_order_status(order, now)

    db.session.commit()
    return {
        "receiving_ids": receiving_ids,
        "stock_updated": stock_updated,
    }


def _serialize_order_summary(order: Order) -> dict[str, Any]:
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


def find_order_by_number(query: str | None) -> dict[str, Any]:
    """Return the summary record for an exact order-number match."""
    normalized = (query or "").strip()
    if not normalized:
        raise ReceivingServiceError(
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
        raise ReceivingServiceError(
            "ORDER_NOT_FOUND",
            "Order not found.",
            404,
        )
    return _serialize_order_summary(order)


def get_order_detail(order_id: int) -> dict[str, Any]:
    """Return order data plus the open, receiving-eligible lines."""
    order = db.session.get(Order, order_id)
    if order is None:
        raise ReceivingServiceError(
            "ORDER_NOT_FOUND",
            "Order not found.",
            404,
        )

    supplier = db.session.get(Supplier, order.supplier_id)
    line_rows = (
        db.session.query(OrderLine)
        .filter(
            OrderLine.order_id == order.id,
            OrderLine.status == OrderLineStatus.OPEN,
        )
        .order_by(OrderLine.id.asc())
        .all()
    )

    lines: list[dict[str, Any]] = []
    for line in line_rows:
        article = db.session.get(Article, line.article_id)
        if article is None:
            continue
        ordered_qty = _decimal_from_model(line.ordered_qty)
        received_qty = _decimal_from_model(line.received_qty)
        remaining_qty = max(ordered_qty - received_qty, Decimal("0"))

        lines.append(
            {
                "id": line.id,
                "article_id": line.article_id,
                "article_no": article.article_no,
                "description": article.description,
                "has_batch": article.has_batch,
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
        "lines": lines,
    }


def list_receiving_history(page: int, per_page: int) -> dict[str, Any]:
    """Return paginated receiving history ordered newest first."""
    query = Receiving.query.order_by(Receiving.received_at.desc(), Receiving.id.desc())
    total = query.count()
    rows = query.offset((page - 1) * per_page).limit(per_page).all()

    article_ids = {row.article_id for row in rows}
    batch_ids = {row.batch_id for row in rows if row.batch_id is not None}
    user_ids = {row.received_by for row in rows}
    order_line_ids = {row.order_line_id for row in rows if row.order_line_id is not None}

    articles = {
        article.id: article
        for article in db.session.query(Article).filter(Article.id.in_(article_ids)).all()
    } if article_ids else {}
    batches = {
        batch.id: batch
        for batch in db.session.query(Batch).filter(Batch.id.in_(batch_ids)).all()
    } if batch_ids else {}
    users = {
        user.id: user
        for user in db.session.query(User).filter(User.id.in_(user_ids)).all()
    } if user_ids else {}
    order_lines = {
        line.id: line
        for line in db.session.query(OrderLine).filter(OrderLine.id.in_(order_line_ids)).all()
    } if order_line_ids else {}
    orders = {
        order.id: order
        for order in db.session.query(Order)
        .filter(Order.id.in_({line.order_id for line in order_lines.values()}))
        .all()
    } if order_lines else {}

    items = []
    for row in rows:
        article = articles.get(row.article_id)
        batch = batches.get(row.batch_id) if row.batch_id else None
        receiver = users.get(row.received_by)
        order_line = order_lines.get(row.order_line_id) if row.order_line_id else None
        order = orders.get(order_line.order_id) if order_line else None

        items.append(
            {
                "id": row.id,
                "received_at": row.received_at.isoformat() if row.received_at else None,
                "order_number": order.order_number if order else "Ad-hoc",
                "article_id": row.article_id,
                "article_no": article.article_no if article else None,
                "description": article.description if article else None,
                "quantity": float(_decimal_from_model(row.quantity)),
                "uom": row.uom,
                "batch_code": batch.batch_code if batch else None,
                "delivery_note_number": row.delivery_note_number,
                "received_by": receiver.username if receiver else None,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }
