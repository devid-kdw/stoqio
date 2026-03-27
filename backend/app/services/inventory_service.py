"""Inventory Count module business logic (Phase 12).

Discrepancy processing on completion:
  counted == system  → NO_CHANGE
  counted >  system  → add difference to Surplus + INVENTORY_ADJUSTMENT Transaction
  counted <  system  → create shortage Draft (INVENTORY_SHORTAGE) in a DraftGroup

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

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.extensions import db
from app.models.article import Article
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

_GROUP_NUMBER_RE = re.compile(r"^IZL-(\d+)$")


def _next_group_number() -> str:
    """Return the next IZL-#### number based on the max existing suffix."""
    max_suffix = 0
    rows = db.session.query(DraftGroup.group_number).all()
    for (gn,) in rows:
        if not gn:
            continue
        m = _GROUP_NUMBER_RE.match(gn)
        if m:
            max_suffix = max(max_suffix, int(m.group(1)))
    return f"IZL-{max_suffix + 1:04d}"


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

    existing = (
        db.session.query(InventoryCount)
        .filter_by(status=InventoryCountStatus.IN_PROGRESS)
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
    db.session.add(count)
    db.session.flush()  # get count.id

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
        surplus_rows = (
            db.session.query(Surplus.article_id, Surplus.batch_id, Surplus.quantity)
            .filter(Surplus.location_id == location.id)
            .all()
        )

        for article_id, batch_id, quantity in stock_rows:
            key = (article_id, batch_id)
            quantity_by_key[key] = quantity_by_key.get(key, Decimal("0")) + Decimal(
                str(quantity)
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
        total_lines = count.lines.count()
        discrepancies = (
            count.lines.filter(
                InventoryCountLine.counted_quantity.isnot(None),
                InventoryCountLine.difference != 0,
            ).count()
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

    total_lines = count.lines.count()
    counted_lines = (
        count.lines.filter(InventoryCountLine.counted_quantity.isnot(None)).count()
    )

    all_lines = count.lines.all()
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

    all_lines = count.lines.all()
    no_change = sum(
        1 for l in all_lines if l.resolution == InventoryCountLineResolution.NO_CHANGE
    )
    surplus_added = sum(
        1 for l in all_lines if l.resolution == InventoryCountLineResolution.SURPLUS_ADDED
    )
    shortage_drafts = sum(
        1
        for l in all_lines
        if l.resolution == InventoryCountLineResolution.SHORTAGE_DRAFT_CREATED
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
        "summary": {
            "total_lines": len(all_lines),
            "no_change": no_change,
            "surplus_added": surplus_added,
            "shortage_drafts_created": shortage_drafts,
        },
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
# Complete count
# ---------------------------------------------------------------------------

def complete_count(count_id: int, current_user: User) -> dict:
    """Process all lines and mark count as COMPLETED."""
    count = db.session.get(InventoryCount, count_id)
    if count is None:
        raise InventoryServiceError("COUNT_NOT_FOUND", "Inventory count not found.", 404)
    if count.status != InventoryCountStatus.IN_PROGRESS:
        raise InventoryServiceError(
            "COUNT_NOT_IN_PROGRESS", "Count is not in progress.", 400
        )

    all_lines = count.lines.all()

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

    # Determine if we need a DraftGroup (any shortages?)
    shortage_lines = [
        l
        for l in all_lines
        if Decimal(str(l.counted_quantity)) < Decimal(str(l.system_quantity))
    ]

    draft_group: DraftGroup | None = None
    if shortage_lines and location:
        draft_group = DraftGroup(
            group_number=_next_group_number(),
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
        },
    }
