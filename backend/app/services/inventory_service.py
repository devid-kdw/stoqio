"""Inventory Count module business logic (Phase 12).

Discrepancy processing on completion:
  REGULAR counts:
    counted == system  → NO_CHANGE
    counted >  system  → add difference to Surplus + INVENTORY_ADJUSTMENT Transaction
    counted <  system  → create shortage Draft (INVENTORY_SHORTAGE) in a DraftGroup
  OPENING counts:
    counted values establish the initial stock baseline and resolve as OPENING_STOCK_SET.

Group-number semantics (DEC-INV-001):
  One DraftGroup per count completion, reusing the IZL-#### sequence from the
  Drafts module.  This makes all shortage drafts from a single count appear
  together in Approvals as one pending group — consistent with existing approvals
  grouping behaviour.

Batch snapshot rule:
  Non-batch articles  → one line per article (batch_id=NULL, qty from stock or 0).
  Batch articles      → one line per existing Stock row with non-NULL batch.
                        If no such rows exist, one line with batch_id=NULL, qty=0
                        so the article is not silently excluded from the count.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.article import Article
from app.models.batch import Batch
from app.models.draft import Draft
from app.models.draft_group import DraftGroup
from app.models.enums import (
    DraftGroupStatus,
    DraftGroupType,
    DraftSource,
    DraftStatus,
    DraftType,
    InventoryCountLineResolution,
    InventoryCountStatus,
    InventoryCountType,
    TxType,
)
from app.models.inventory_count import InventoryCount, InventoryCountLine
from app.models.location import Location
from app.models.stock import Stock
from app.models.surplus import Surplus
from app.models.transaction import Transaction
from app.models.uom_catalog import UomCatalog
from app.models.user import User
from app.utils.draft_numbering import next_izl_group_number
from app.utils.validators import validate_batch_code


# ---------------------------------------------------------------------------
# Structured error
# ---------------------------------------------------------------------------

class InventoryServiceError(Exception):
    """Maps directly to an API error response."""

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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_shortage_drafts_summary(count_id: int) -> dict:
    """Derive shortage-draft approval summary for a completed inventory count.

    Links drafts to a count via the explicit ``Draft.inventory_count_id`` FK
    populated during ``complete_count(...)``.
    """
    drafts = (
        db.session.query(Draft.status)
        .filter(
            Draft.draft_type == DraftType.INVENTORY_SHORTAGE,
            Draft.inventory_count_id == count_id,
        )
        .all()
    )
    approved = sum(1 for (s,) in drafts if s == DraftStatus.APPROVED)
    rejected = sum(1 for (s,) in drafts if s == DraftStatus.REJECTED)
    pending = sum(1 for (s,) in drafts if s == DraftStatus.DRAFT)
    return {
        "total": len(drafts),
        "approved": approved,
        "rejected": rejected,
        "pending": pending,
    }


def _get_default_location() -> Location | None:
    return db.session.get(Location, 1) or db.session.query(Location).first()


def _get_operational_date(
    location: Location | None,
    *,
    at: datetime | None = None,
):
    """Return the location-aware operational date for *at* (defaults to now UTC)."""
    tz_name = location.timezone if location and location.timezone else "UTC"
    current = at or datetime.now(timezone.utc)

    try:
        import zoneinfo

        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc

    return current.astimezone(tz).date()


def _uom_code(article: Article) -> str:
    uom_obj = db.session.get(UomCatalog, article.base_uom)
    return uom_obj.code if uom_obj else "kom"


def _uom_decimal_display(uom_code: str) -> bool:
    uom_obj = UomCatalog.query.filter_by(code=uom_code).first()
    return bool(uom_obj.decimal_display) if uom_obj else False


def _serialize_line(line: InventoryCountLine) -> dict:
    article = line.article
    batch = line.batch
    return {
        "line_id": line.id,
        "article_id": line.article_id,
        "article_no": article.article_no if article else None,
        "description": article.description if article else None,
        "batch_id": line.batch_id,
        "batch_code": batch.batch_code if batch else None,
        "expiry_date": (
            batch.expiry_date.isoformat() if batch and batch.expiry_date else None
        ),
        "system_quantity": float(line.system_quantity),
        "counted_quantity": (
            float(line.counted_quantity) if line.counted_quantity is not None else None
        ),
        "difference": (
            float(line.difference) if line.difference is not None else None
        ),
        "uom": line.uom,
        "decimal_display": _uom_decimal_display(line.uom),
        "resolution": line.resolution.value if line.resolution else None,
    }


def _serialize_count_summary(
    count: InventoryCount,
    all_lines: list[InventoryCountLine],
) -> dict[str, int]:
    summary = {
        "total_lines": len(all_lines),
        "no_change": 0,
        "surplus_added": 0,
        "shortage_drafts_created": 0,
        "opening_stock_set": 0,
    }
    for line in all_lines:
        if line.resolution == InventoryCountLineResolution.NO_CHANGE:
            summary["no_change"] += 1
        elif line.resolution == InventoryCountLineResolution.SURPLUS_ADDED:
            summary["surplus_added"] += 1
        elif line.resolution == InventoryCountLineResolution.SHORTAGE_DRAFT_CREATED:
            summary["shortage_drafts_created"] += 1
        elif line.resolution == InventoryCountLineResolution.OPENING_STOCK_SET:
            summary["opening_stock_set"] += 1

    if count.type == InventoryCountType.OPENING and summary["opening_stock_set"] == 0:
        summary["opening_stock_set"] = len(all_lines)

    return summary


def _resolve_batch_for_opening(
    article: Article,
    *,
    batch_code: str | None,
    expiry_date_value: Any,
    details: dict[str, Any],
) -> Batch | None:
    if not article.has_batch:
        return None

    if batch_code is None:
        raise InventoryServiceError(
            "VALIDATION_ERROR",
            "batch_code is required for batch-tracked articles.",
            400,
            details,
        )
    if not validate_batch_code(batch_code):
        raise InventoryServiceError(
            "VALIDATION_ERROR",
            "batch_code has an invalid format.",
            400,
            details,
        )
    if expiry_date_value in (None, ""):
        raise InventoryServiceError(
            "VALIDATION_ERROR",
            "expiry_date is required.",
            400,
            details,
        )
    if isinstance(expiry_date_value, date):
        expiry_date = expiry_date_value
    else:
        try:
            expiry_date = date.fromisoformat(str(expiry_date_value))
        except ValueError:
            raise InventoryServiceError(
                "VALIDATION_ERROR",
                "expiry_date must be a valid ISO date.",
                400,
                details,
            ) from None

    batch = Batch.query.filter_by(article_id=article.id, batch_code=batch_code).first()
    if batch is not None:
        if batch.expiry_date != expiry_date:
            raise InventoryServiceError(
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


def _opening_stock_average_price(
    article: Article,
    *,
    stock_row: Stock | None,
) -> Decimal:
    if article.initial_average_price is not None:
        return Decimal(str(article.initial_average_price))
    if stock_row is not None:
        return Decimal(str(stock_row.average_price))
    return Decimal("0")


def _upsert_opening_stock(
    *,
    location_id: int,
    article: Article,
    batch: Batch | None,
    counted_quantity: Decimal,
    uom: str,
    occurred_at: datetime,
) -> Stock | None:
    if article.has_batch and batch is None and counted_quantity == 0:
        return None

    stock_row = (
        db.session.query(Stock)
        .filter_by(
            location_id=location_id,
            article_id=article.id,
            batch_id=batch.id if batch else None,
        )
        .with_for_update()
        .first()
    )

    average_price = _opening_stock_average_price(article, stock_row=stock_row)
    if stock_row is None:
        stock_row = Stock(
            location_id=location_id,
            article_id=article.id,
            batch_id=batch.id if batch else None,
            quantity=counted_quantity,
            uom=uom,
            average_price=average_price,
            last_updated=occurred_at,
        )
        db.session.add(stock_row)
    else:
        stock_row.quantity = counted_quantity
        stock_row.uom = uom
        stock_row.average_price = average_price
        stock_row.last_updated = occurred_at

    return stock_row


# ---------------------------------------------------------------------------
# Start count
# ---------------------------------------------------------------------------

def start_count(current_user: User, count_type: InventoryCountType = InventoryCountType.REGULAR) -> dict:
    """Snapshot all active articles and open a new IN_PROGRESS count."""
    if count_type == InventoryCountType.OPENING:
        opening_exists = (
            db.session.query(InventoryCount)
            .filter_by(type=InventoryCountType.OPENING)
            .first()
        )
        if opening_exists:
            raise InventoryServiceError(
                "OPENING_COUNT_EXISTS",
                "Opening stock count already exists.",
                400,
            )

    # H-3 / Wave 7 Phase 1: use with_for_update() on the IN_PROGRESS check so
    # concurrent start_count() calls contend on the same row rather than both
    # seeing no IN_PROGRESS count and both inserting. When no IN_PROGRESS row
    # exists there is nothing to lock, so a small race window remains; a
    # DB-level unique constraint on IN_PROGRESS state (Phase 2 scope) would
    # fully close this window.
    existing = (
        db.session.query(InventoryCount)
        .filter_by(status=InventoryCountStatus.IN_PROGRESS)
        .with_for_update()
        .first()
    )
    if existing:
        raise InventoryServiceError(
            "COUNT_IN_PROGRESS",
            "An inventory count is already in progress.",
            400,
            {"count_id": existing.id},
        )

    location = _get_default_location()
    now = datetime.now(timezone.utc)

    count = InventoryCount(
        status=InventoryCountStatus.IN_PROGRESS,
        type=count_type,
        started_by=current_user.id,
        started_at=now,
    )
    try:
        db.session.add(count)
        db.session.flush()  # get count.id
    except IntegrityError as exc:
        db.session.rollback()
        raise InventoryServiceError(
            "COUNT_IN_PROGRESS",
            "An inventory count is already in progress.",
            400,
        ) from exc

    active_articles = (
        db.session.query(Article).filter_by(is_active=True).order_by(Article.article_no).all()
    )

    quantity_by_key: dict[tuple[int, int | None], Decimal] = {}
    if location:
        stock_rows = (
            db.session.query(Stock.article_id, Stock.batch_id, Stock.quantity)
            .filter(Stock.location_id == location.id)
            .all()
        )
        for article_id, batch_id, quantity in stock_rows:
            key = (article_id, batch_id)
            quantity_by_key[key] = quantity_by_key.get(key, Decimal("0")) + Decimal(
                str(quantity)
            )

        if count_type != InventoryCountType.OPENING:
            surplus_rows = (
                db.session.query(Surplus.article_id, Surplus.batch_id, Surplus.quantity)
                .filter(Surplus.location_id == location.id)
                .all()
            )

            for article_id, batch_id, quantity in surplus_rows:
                key = (article_id, batch_id)
                quantity_by_key[key] = quantity_by_key.get(key, Decimal("0")) + Decimal(
                    str(quantity)
                )

    line_count = 0
    for article in active_articles:
        uom = _uom_code(article)

        if not article.has_batch:
            qty = quantity_by_key.get((article.id, None), Decimal("0"))
            db.session.add(
                InventoryCountLine(
                    inventory_count_id=count.id,
                    article_id=article.id,
                    batch_id=None,
                    system_quantity=qty,
                    uom=uom,
                )
            )
            line_count += 1
        else:
            batch_ids = sorted(
                batch_id
                for (article_id, batch_id), _qty in quantity_by_key.items()
                if article_id == article.id and batch_id is not None
            )

            if batch_ids:
                for batch_id in batch_ids:
                    db.session.add(
                        InventoryCountLine(
                            inventory_count_id=count.id,
                            article_id=article.id,
                            batch_id=batch_id,
                            system_quantity=quantity_by_key[(article.id, batch_id)],
                            uom=uom,
                        )
                    )
                    line_count += 1
            else:
                # batch article with no stock yet — include with qty=0
                db.session.add(
                    InventoryCountLine(
                        inventory_count_id=count.id,
                        article_id=article.id,
                        batch_id=None,
                        system_quantity=quantity_by_key.get((article.id, None), Decimal("0")),
                        uom=uom,
                    )
                )
                line_count += 1

    db.session.commit()

    return {
        "id": count.id,
        "status": count.status.value,
        "type": count.type.value,
        "started_by": current_user.username,
        "started_at": count.started_at.isoformat(),
        "total_lines": line_count,
    }


# ---------------------------------------------------------------------------
# History (list completed counts)
# ---------------------------------------------------------------------------

def list_counts(page: int, per_page: int) -> dict:
    # V-3 / Wave 6 Phase 1: cap per_page to prevent DoS via large result sets
    per_page = min(per_page, 200)
    query = (
        db.session.query(InventoryCount)
        .filter_by(status=InventoryCountStatus.COMPLETED)
        .order_by(InventoryCount.started_at.desc())
    )
    total = query.count()
    counts = query.offset((page - 1) * per_page).limit(per_page).all()

    opening_count_exists = (
        db.session.query(InventoryCount)
        .filter_by(type=InventoryCountType.OPENING)
        .first()
    ) is not None

    items = []
    for count in counts:
        total_lines = (
            db.session.query(InventoryCountLine)
            .filter_by(inventory_count_id=count.id)
            .count()
        )
        all_lines = (
            db.session.query(InventoryCountLine)
            .filter_by(inventory_count_id=count.id)
            .all()
        )
        opening_stock_set = sum(
            1
            for line in all_lines
            if line.resolution == InventoryCountLineResolution.OPENING_STOCK_SET
        )
        discrepancies = 0
        if count.type == InventoryCountType.REGULAR:
            discrepancies = sum(
                1
                for line in all_lines
                if line.counted_quantity is not None and line.difference != 0
            )
        starter = count.starter
        items.append(
            {
                "id": count.id,
                "status": count.status.value,
                "type": count.type.value,
                "started_by": starter.username if starter else None,
                "started_at": (
                    count.started_at.isoformat() if count.started_at else None
                ),
                "completed_at": (
                    count.completed_at.isoformat() if count.completed_at else None
                ),
                "total_lines": total_lines,
                "discrepancies": discrepancies,
                "opening_stock_set": opening_stock_set,
                "shortage_drafts_summary": _get_shortage_drafts_summary(count.id),
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "opening_count_exists": opening_count_exists,
    }


# ---------------------------------------------------------------------------
# Active count
# ---------------------------------------------------------------------------

def get_active_count() -> dict | None:
    """Return the active IN_PROGRESS count with all lines, or None."""
    count = (
        db.session.query(InventoryCount)
        .filter_by(status=InventoryCountStatus.IN_PROGRESS)
        .first()
    )
    if count is None:
        return None

    total_lines = (
        db.session.query(InventoryCountLine)
        .filter_by(inventory_count_id=count.id)
        .count()
    )
    counted_lines = (
        db.session.query(InventoryCountLine)
        .filter_by(inventory_count_id=count.id)
        .filter(InventoryCountLine.counted_quantity.isnot(None))
        .count()
    )

    all_lines = (
        db.session.query(InventoryCountLine)
        .filter_by(inventory_count_id=count.id)
        .all()
    )
    starter = count.starter

    return {
        "id": count.id,
        "status": count.status.value,
        "type": count.type.value,
        "started_by": starter.username if starter else None,
        "started_at": count.started_at.isoformat() if count.started_at else None,
        "completed_at": None,
        "total_lines": total_lines,
        "counted_lines": counted_lines,
        "lines": [_serialize_line(line) for line in all_lines],
    }


# ---------------------------------------------------------------------------
# Count detail (read-only)
# ---------------------------------------------------------------------------

def get_count_detail(count_id: int) -> dict:
    count = db.session.get(InventoryCount, count_id)
    if count is None:
        raise InventoryServiceError("COUNT_NOT_FOUND", "Inventory count not found.", 404)

    all_lines = (
        db.session.query(InventoryCountLine)
        .filter_by(inventory_count_id=count_id)
        .all()
    )
    starter = count.starter

    return {
        "id": count.id,
        "status": count.status.value,
        "type": count.type.value,
        "started_by": starter.username if starter else None,
        "started_at": count.started_at.isoformat() if count.started_at else None,
        "completed_at": (
            count.completed_at.isoformat() if count.completed_at else None
        ),
        "summary": _serialize_count_summary(count, all_lines),
        "shortage_drafts_summary": _get_shortage_drafts_summary(count_id),
        "lines": [_serialize_line(l) for l in all_lines],
    }


# ---------------------------------------------------------------------------
# Update counted quantity
# ---------------------------------------------------------------------------

def update_line(count_id: int, line_id: int, data: dict) -> dict:
    count = db.session.get(InventoryCount, count_id)
    if count is None:
        raise InventoryServiceError("COUNT_NOT_FOUND", "Inventory count not found.", 404)
    if count.status != InventoryCountStatus.IN_PROGRESS:
        raise InventoryServiceError(
            "COUNT_NOT_IN_PROGRESS", "Count is not in progress.", 400
        )

    line = db.session.get(InventoryCountLine, line_id)
    if line is None or line.inventory_count_id != count_id:
        raise InventoryServiceError("LINE_NOT_FOUND", "Count line not found.", 404)

    if "counted_quantity" not in data:
        raise InventoryServiceError(
            "VALIDATION_ERROR", "'counted_quantity' is required.", 400
        )

    raw = data["counted_quantity"]
    if raw is None:
        raise InventoryServiceError(
            "VALIDATION_ERROR", "'counted_quantity' must be a number.", 400
        )
    try:
        qty = Decimal(str(raw))
    except Exception:
        raise InventoryServiceError(
            "VALIDATION_ERROR", "'counted_quantity' must be a number.", 400
        )

    if qty < 0:
        raise InventoryServiceError(
            "VALIDATION_ERROR", "'counted_quantity' must be >= 0.", 400
        )

    # Integer-only enforcement for non-decimal UOMs
    uom_obj = UomCatalog.query.filter_by(code=line.uom).first()
    if uom_obj and not uom_obj.decimal_display:
        if qty != qty.to_integral_value():
            raise InventoryServiceError(
                "VALIDATION_ERROR",
                f"UOM '{line.uom}' requires a whole number.",
                400,
            )

    line.counted_quantity = qty
    line.difference = qty - Decimal(str(line.system_quantity))
    db.session.commit()

    return _serialize_line(line)


# ---------------------------------------------------------------------------
# Opening batch line
# ---------------------------------------------------------------------------

def add_opening_batch_line(count_id: int, data: dict) -> dict:
    count = db.session.query(InventoryCount).filter_by(id=count_id).with_for_update().first()
    if count is None:
        raise InventoryServiceError("COUNT_NOT_FOUND", "Inventory count not found.", 404)
    if count.status != InventoryCountStatus.IN_PROGRESS:
        raise InventoryServiceError(
            "COUNT_NOT_IN_PROGRESS", "Count is not in progress.", 400
        )
    if count.type != InventoryCountType.OPENING:
        raise InventoryServiceError(
            "OPENING_COUNT_ONLY",
            "Batch lines can only be added to an opening inventory count.",
            400,
        )

    if not isinstance(data, dict):
        raise InventoryServiceError("VALIDATION_ERROR", "Request body must be an object.", 400)

    if "article_id" not in data:
        raise InventoryServiceError(
            "VALIDATION_ERROR", "'article_id' is required.", 400
        )
    if "counted_quantity" not in data:
        raise InventoryServiceError(
            "VALIDATION_ERROR", "'counted_quantity' is required.", 400
        )

    try:
        article_id = int(data["article_id"])
    except (TypeError, ValueError):
        raise InventoryServiceError(
            "VALIDATION_ERROR", "'article_id' must be a valid integer.", 400
        ) from None

    raw_quantity = data["counted_quantity"]
    try:
        counted_quantity = Decimal(str(raw_quantity))
    except Exception:
        raise InventoryServiceError(
            "VALIDATION_ERROR", "'counted_quantity' must be a number.", 400
        ) from None
    if counted_quantity < 0:
        raise InventoryServiceError(
            "VALIDATION_ERROR", "'counted_quantity' must be >= 0.", 400
        )

    article = (
        db.session.query(Article)
        .filter(Article.id == article_id, Article.is_active.is_(True))
        .first()
    )
    if article is None:
        raise InventoryServiceError(
            "ARTICLE_NOT_FOUND",
            "Article not found.",
            404,
            {"article_id": article_id},
        )
    if not article.has_batch:
        raise InventoryServiceError(
            "VALIDATION_ERROR",
            "Article is not batch-tracked.",
            400,
            {"article_id": article_id},
        )

    uom = _uom_code(article)
    details = {"count_id": count_id, "article_id": article.id}
    batch = _resolve_batch_for_opening(
        article,
        batch_code=data.get("batch_code"),
        expiry_date_value=data.get("expiry_date"),
        details=details,
    )

    placeholder_line = (
        db.session.query(InventoryCountLine)
        .filter_by(
            inventory_count_id=count.id,
            article_id=article.id,
            batch_id=None,
        )
        .first()
    )
    if (
        placeholder_line is not None
        and placeholder_line.counted_quantity is None
        and Decimal(str(placeholder_line.system_quantity)) == 0
    ):
        db.session.delete(placeholder_line)

    line = (
        db.session.query(InventoryCountLine)
        .filter_by(
            inventory_count_id=count.id,
            article_id=article.id,
            batch_id=batch.id if batch else None,
        )
        .first()
    )
    if line is None:
        line = InventoryCountLine(
            inventory_count_id=count.id,
            article_id=article.id,
            batch_id=batch.id if batch else None,
            system_quantity=Decimal("0"),
            counted_quantity=counted_quantity,
            uom=uom,
            difference=counted_quantity,
            resolution=None,
        )
        db.session.add(line)
    else:
        line.system_quantity = Decimal("0")
        line.counted_quantity = counted_quantity
        line.uom = uom
        line.difference = counted_quantity
        line.resolution = None

    db.session.commit()
    return get_active_count() or {
        "id": count.id,
        "status": count.status.value,
        "type": count.type.value,
        "started_by": count.starter.username if count.starter else None,
        "started_at": count.started_at.isoformat() if count.started_at else None,
        "completed_at": None,
        "total_lines": (
            db.session.query(InventoryCountLine)
            .filter_by(inventory_count_id=count.id)
            .count()
        ),
        "counted_lines": (
            db.session.query(InventoryCountLine)
            .filter_by(inventory_count_id=count.id)
            .filter(InventoryCountLine.counted_quantity.isnot(None))
            .count()
        ),
        "lines": [_serialize_line(line)],
    }


# ---------------------------------------------------------------------------
# Complete count
# ---------------------------------------------------------------------------

def complete_count(count_id: int, current_user: User) -> dict:
    """Process all lines and mark count as COMPLETED."""
    # H-3 / Wave 7 Phase 1: acquire a row-level lock on the InventoryCount row
    # BEFORE reading its status or processing any side effects. Without this
    # lock, two concurrent complete_count() calls can both pass the status check
    # (seeing IN_PROGRESS) and both proceed to create surplus rows, shortage
    # drafts, and transactions — doubling side effects.
    count = (
        db.session.query(InventoryCount)
        .filter_by(id=count_id)
        .with_for_update()
        .first()
    )
    if count is None:
        raise InventoryServiceError("COUNT_NOT_FOUND", "Inventory count not found.", 404)
    if count.status != InventoryCountStatus.IN_PROGRESS:
        raise InventoryServiceError(
            "COUNT_NOT_IN_PROGRESS", "Count is not in progress.", 400
        )

    all_lines = (
        db.session.query(InventoryCountLine)
        .filter_by(inventory_count_id=count_id)
        .all()
    )

    uncounted = [l for l in all_lines if l.counted_quantity is None]
    if uncounted:
        raise InventoryServiceError(
            "UNCOUNTED_LINES",
            "All lines must be counted before completing.",
            400,
            {"uncounted_count": len(uncounted)},
        )

    location = _get_default_location()
    now = datetime.now(timezone.utc)

    if count.type == InventoryCountType.OPENING:
        opening_stock_set = 0
        for line in all_lines:
            counted = Decimal(str(line.counted_quantity))
            system = Decimal(str(line.system_quantity))
            line.difference = counted - system

            if line.article and line.article.has_batch and line.batch_id is None and counted > 0:
                raise InventoryServiceError(
                    "OPENING_BATCH_REQUIRED",
                    "Batch-tracked opening lines must use a batch.",
                    400,
                    {"line_id": line.id, "article_id": line.article_id},
                )

            if not (
                line.article
                and line.article.has_batch
                and line.batch_id is None
                and counted == 0
            ):
                _upsert_opening_stock(
                    location_id=location.id if location else 1,
                    article=line.article,
                    batch=line.batch,
                    counted_quantity=counted,
                    uom=line.uom,
                    occurred_at=now,
                )

            line.resolution = InventoryCountLineResolution.OPENING_STOCK_SET
            opening_stock_set += 1

        count.status = InventoryCountStatus.COMPLETED
        count.completed_at = now
        db.session.commit()

        return {
            "id": count.id,
            "status": count.status.value,
            "completed_at": count.completed_at.isoformat(),
            "summary": {
                "total_lines": len(all_lines),
                "no_change": 0,
                "surplus_added": 0,
                "shortage_drafts_created": 0,
                "opening_stock_set": opening_stock_set,
            },
        }

    # Determine if we need a DraftGroup (any shortages?)
    shortage_lines = [
        l
        for l in all_lines
        if Decimal(str(l.counted_quantity)) < Decimal(str(l.system_quantity))
    ]

    draft_group: DraftGroup | None = None
    if shortage_lines and location:
        draft_group = DraftGroup(
            group_number=next_izl_group_number(),
            status=DraftGroupStatus.PENDING,
            group_type=DraftGroupType.INVENTORY_SHORTAGE,
            operational_date=_get_operational_date(location, at=now),
            created_by=current_user.id,
            description=f"Inventory count #{count_id} shortages",
        )
        db.session.add(draft_group)
        db.session.flush()

    counters = {"no_change": 0, "surplus_added": 0, "shortage_drafts_created": 0}

    for line in all_lines:
        counted = Decimal(str(line.counted_quantity))
        system = Decimal(str(line.system_quantity))
        diff = counted - system

        # Always persist the final difference
        line.difference = diff

        if diff == 0:
            line.resolution = InventoryCountLineResolution.NO_CHANGE
            counters["no_change"] += 1

        elif diff > 0:
            # Surplus found — update or create Surplus row + Transaction
            if location:
                surplus_row = (
                    db.session.query(Surplus)
                    .filter(
                        Surplus.location_id == location.id,
                        Surplus.article_id == line.article_id,
                        Surplus.batch_id == line.batch_id,
                    )
                    .first()
                )
                if surplus_row:
                    surplus_row.quantity += diff
                else:
                    surplus_row = Surplus(
                        location_id=location.id,
                        article_id=line.article_id,
                        batch_id=line.batch_id,
                        quantity=diff,
                        uom=line.uom,
                    )
                    db.session.add(surplus_row)

                tx = Transaction(
                    tx_type=TxType.INVENTORY_ADJUSTMENT,
                    occurred_at=now,
                    location_id=location.id,
                    article_id=line.article_id,
                    batch_id=line.batch_id,
                    quantity=diff,  # positive = surplus added
                    uom=line.uom,
                    user_id=current_user.id,
                    reference_type="inventory_count",
                    reference_id=count.id,
                    meta={"line_id": line.id, "resolution": "SURPLUS_ADDED"},
                )
                db.session.add(tx)

            line.resolution = InventoryCountLineResolution.SURPLUS_ADDED
            counters["surplus_added"] += 1

        else:
            # Shortage — create Draft
            shortage_qty = abs(diff)
            if location and draft_group:
                client_event_id = f"inv-count-{count_id}-line-{line.id}"
                draft = Draft(
                    draft_group_id=draft_group.id,
                    location_id=location.id,
                    article_id=line.article_id,
                    batch_id=line.batch_id,
                    inventory_count_id=count.id,
                    quantity=shortage_qty,
                    uom=line.uom,
                    status=DraftStatus.DRAFT,
                    draft_type=DraftType.INVENTORY_SHORTAGE,
                    source=DraftSource.manual,
                    client_event_id=client_event_id,
                    created_by=current_user.id,
                )
                db.session.add(draft)

            line.resolution = InventoryCountLineResolution.SHORTAGE_DRAFT_CREATED
            counters["shortage_drafts_created"] += 1

    count.status = InventoryCountStatus.COMPLETED
    count.completed_at = now

    db.session.commit()

    return {
        "id": count.id,
        "status": count.status.value,
        "completed_at": count.completed_at.isoformat(),
        "summary": {
            "total_lines": len(all_lines),
            "no_change": counters["no_change"],
            "surplus_added": counters["surplus_added"],
            "shortage_drafts_created": counters["shortage_drafts_created"],
            "opening_stock_set": 0,
        },
    }
