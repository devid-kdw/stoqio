"""Core business logic for Approvals (Phase 6)."""

from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, TypedDict

from sqlalchemy import func

from app.extensions import db
from app.models.article import Article
from app.models.batch import Batch
from app.models.draft import Draft
from app.models.draft_group import DraftGroup
from app.models.approval_action import ApprovalAction
from app.models.approval_override import ApprovalOverride
from app.models.enums import DraftStatus, DraftGroupStatus, ApprovalActionType, TxType
from app.models.stock import Stock
from app.models.surplus import Surplus
from app.models.transaction import Transaction
from app.models.user import User


class AggregatedRowDict(TypedDict):
    line_id: int
    article_id: int
    article_no: str
    description: str
    batch_id: Optional[int]
    batch_code: Optional[str]
    total_quantity: float
    uom: str
    entry_count: int


def _override_batch_key(batch_id: Optional[int]) -> str:
    return str(batch_id) if batch_id is not None else "__NO_BATCH__"


def _get_override_for_bucket(
    group_id: int,
    article_id: int,
    batch_id: Optional[int],
) -> Optional[ApprovalOverride]:
    return db.session.query(ApprovalOverride).filter_by(
        draft_group_id=group_id,
        article_id=article_id,
        batch_key=_override_batch_key(batch_id),
    ).first()


def get_pending_draft_groups():
    """Return all DraftGroups that have at least one DRAFT line."""
    # Subquery to find draft groups with at least one pending draft
    pending_groups = db.session.query(Draft.draft_group_id).filter(
        Draft.status == DraftStatus.DRAFT
    ).distinct().subquery()

    groups = db.session.query(DraftGroup).join(
        pending_groups, DraftGroup.id == pending_groups.c.draft_group_id
    ).order_by(DraftGroup.operational_date.desc()).all()

    return [get_draft_group_detail(group.id) for group in groups]


def get_history_draft_groups():
    """Return all DraftGroups that have NO DRAFT lines (fully resolved)."""
    # Subquery to find draft groups with at least one pending draft
    pending_groups = db.session.query(Draft.draft_group_id).filter(
        Draft.status == DraftStatus.DRAFT
    ).distinct().subquery()

    # We want groups NOT in the subquery
    groups = db.session.query(DraftGroup).outerjoin(
        pending_groups, DraftGroup.id == pending_groups.c.draft_group_id
    ).filter(
        pending_groups.c.draft_group_id.is_(None)
    ).order_by(DraftGroup.operational_date.desc()).all()

    # We need to compute their display status
    results = []
    for g in groups:
        # Determine if it's PARTIAL, APPROVED, or REJECTED
        status = _compute_group_display_status(g.id)
        results.append(_serialize_group(g, status))
    return results


def _compute_group_display_status(group_id: int) -> str:
    """
    Compute display status for a group based on its draft lines.
    - any DRAFT -> PENDING
    - all APPROVED -> APPROVED
    - all REJECTED -> REJECTED
    - mix of APPROVED and REJECTED with no DRAFT -> PARTIAL
    """
    stats = db.session.query(
        Draft.status, func.count(Draft.id)
    ).filter(
        Draft.draft_group_id == group_id
    ).group_by(Draft.status).all()

    counts = {s.value if hasattr(s, "value") else s: c for s, c in stats}
    pending = counts.get(DraftStatus.DRAFT.value, 0)
    approved = counts.get(DraftStatus.APPROVED.value, 0)
    rejected = counts.get(DraftStatus.REJECTED.value, 0)

    if pending > 0:
        return "PENDING"
    if approved > 0 and rejected > 0:
        return "PARTIAL"
    if approved > 0:
        return "APPROVED"
    if rejected > 0:
        return "REJECTED"
    
    # Empty group?
    return "PENDING"


def _serialize_groups(groups: List[DraftGroup], display_status: str) -> List[Dict[str, Any]]:
    return [_serialize_group(g, display_status) for g in groups]


def _serialize_group(group: DraftGroup, display_status: str) -> Dict[str, Any]:
    total_entries = db.session.query(func.count(Draft.id)).filter(
        Draft.draft_group_id == group.id
    ).scalar()

    return {
        "draft_group_id": group.id,
        "group_number": group.group_number,
        "operational_date": group.operational_date.isoformat(),
        "status": display_status,
        "draft_note": group.description,
        "total_entries": total_entries,
    }


def get_draft_group_detail(group_id: int) -> Optional[Dict[str, Any]]:
    """Return group detail including aggregated rows with nested entries."""
    group = db.session.get(DraftGroup, group_id)
    if not group:
        return None

    display_status = _compute_group_display_status(group_id)
    base_data = _serialize_group(group, display_status)

    base_data["rows"] = _build_group_rows(group_id)
    return base_data


def _build_group_rows(group_id: int) -> List[Dict[str, Any]]:
    drafts = db.session.query(Draft).filter(Draft.draft_group_id == group_id).all()
    if not drafts:
        return []

    overrides = db.session.query(ApprovalOverride).filter(
        ApprovalOverride.draft_group_id == group_id
    ).all()
    override_map = {
        (override.article_id, override.batch_id): float(override.override_quantity)
        for override in overrides
    }

    article_ids = {draft.article_id for draft in drafts}
    batch_ids = {draft.batch_id for draft in drafts if draft.batch_id is not None}
    user_ids = {draft.created_by for draft in drafts}

    articles = {
        article.id: article
        for article in db.session.query(Article).filter(Article.id.in_(article_ids)).all()
    }
    batches = {
        batch.id: batch
        for batch in db.session.query(Batch).filter(Batch.id.in_(batch_ids)).all()
    }
    users = {
        user.id: user
        for user in db.session.query(User).filter(User.id.in_(user_ids)).all()
    }

    buckets = defaultdict(list)
    for draft in drafts:
        buckets[(draft.article_id, draft.batch_id)].append(draft)

    rows = []
    for (article_id, batch_id), bucket_drafts in buckets.items():
        sorted_drafts = sorted(bucket_drafts, key=lambda draft: draft.id)
        line_id = sorted_drafts[0].id
        article = articles.get(article_id)
        batch = batches.get(batch_id) if batch_id is not None else None

        override_qty = override_map.get((article_id, batch_id))
        total_quantity = (
            override_qty
            if override_qty is not None
            else sum(float(draft.quantity) for draft in sorted_drafts)
        )

        entry_status_counts = defaultdict(int)
        for draft in sorted_drafts:
            status_value = draft.status.value if hasattr(draft.status, "value") else draft.status
            entry_status_counts[status_value] += 1

        if entry_status_counts.get("DRAFT", 0) > 0:
            row_status = "PENDING"
        elif (
            entry_status_counts.get("APPROVED", 0) > 0
            and entry_status_counts.get("REJECTED", 0) > 0
        ):
            row_status = "PARTIAL"
        elif entry_status_counts.get("APPROVED", 0) > 0:
            row_status = "APPROVED"
        else:
            row_status = "REJECTED"

        entries = []
        for draft in sorted_drafts:
            creator = users.get(draft.created_by)
            status_value = draft.status.value if hasattr(draft.status, "value") else draft.status
            entries.append(
                {
                    "id": draft.id,
                    "created_at": draft.created_at.isoformat() if draft.created_at else None,
                    "operator": creator.username if creator else None,
                    "quantity": float(draft.quantity),
                    "employee_id_ref": draft.employee_id_ref,
                    "status": status_value,
                }
            )

        rows.append(
            {
                "line_id": line_id,
                "article_id": article_id,
                "article_no": article.article_no if article else None,
                "description": article.description if article else None,
                "batch_id": batch_id,
                "batch_code": batch.batch_code if batch else "—",
                "total_quantity": total_quantity,
                "uom": sorted_drafts[0].uom,
                "status": row_status,
                "entry_count": len(sorted_drafts),
                "entries": entries,
            }
        )

    rows.sort(key=lambda row: (row["article_no"] or "", row["batch_code"] or ""))
    return rows


def edit_aggregated_line(group_id: int, line_id: int, new_quantity: Decimal) -> Optional[Dict[str, Any]]:
    """Upsert an ApprovalOverride for the bucket represented by line_id."""
    # Find the representative draft
    draft = db.session.get(Draft, line_id)
    if not draft or draft.draft_group_id != group_id:
        return None

    # Upsert the override
    override = _get_override_for_bucket(group_id, draft.article_id, draft.batch_id)

    if override:
        override.override_quantity = new_quantity
    else:
        override = ApprovalOverride(
            draft_group_id=group_id,
            article_id=draft.article_id,
            batch_id=draft.batch_id,
            batch_key=_override_batch_key(draft.batch_id),
            override_quantity=new_quantity
        )
        db.session.add(override)
    
    db.session.commit()
    # return the updated group detail
    return get_draft_group_detail(group_id)


def approve_line(user_id: int, group_id: int, line_id: int) -> dict:
    """
    Approve an aggregated row.
    Finds all drafts for this (article, batch).
    Calculates total needed (override if exists, else sum).
    Applies surplus-first logic. Raises ValueError if insufficient stock.
    Creates transactions and updates draft statuses.
    """
    draft = db.session.get(Draft, line_id)
    if not draft or draft.draft_group_id != group_id:
        raise ValueError("Line not found in this group.")

    # Get all drafts in this bucket
    bucket_drafts = db.session.query(Draft).filter_by(
        draft_group_id=group_id,
        article_id=draft.article_id,
        batch_id=draft.batch_id,
        status=DraftStatus.DRAFT
    ).all()

    if not bucket_drafts:
        raise ValueError("This line has already been approved or rejected.")

    # Is there an override?
    override = _get_override_for_bucket(group_id, draft.article_id, draft.batch_id)

    if override:
        total_quantity = Decimal(str(override.override_quantity))
    else:
        total_quantity = sum(Decimal(str(d.quantity)) for d in bucket_drafts)

    location_id = bucket_drafts[0].location_id # Assume all in same location for this line
    uom = bucket_drafts[0].uom

    # Lock stock and surplus
    surplus = db.session.query(Surplus).filter_by(
        location_id=location_id,
        article_id=draft.article_id,
        batch_id=draft.batch_id
    ).with_for_update().first()

    stock = db.session.query(Stock).filter_by(
        location_id=location_id,
        article_id=draft.article_id,
        batch_id=draft.batch_id
    ).with_for_update().first()

    # Calculate current stock
    cur_stock = Decimal(str(stock.quantity)) if stock else Decimal("0.0")
    cur_surplus = Decimal(str(surplus.quantity)) if surplus else Decimal("0.0")

    if cur_stock + cur_surplus < total_quantity:
        raise ValueError("Insufficient stock.")

    # Deducting math
    to_deduct = total_quantity
    deducted_from_surplus = Decimal("0.0")
    deducted_from_stock = Decimal("0.0")

    if cur_surplus > 0:
        if cur_surplus >= to_deduct:
            deducted_from_surplus = to_deduct
            to_deduct = Decimal("0.0")
        else:
            deducted_from_surplus = cur_surplus
            to_deduct -= cur_surplus

    if to_deduct > 0:
        deducted_from_stock = to_deduct

    # Apply deductions
    if deducted_from_surplus > 0:
        surplus.quantity = float(Decimal(str(surplus.quantity)) - deducted_from_surplus)
        if surplus.quantity == 0:
            db.session.delete(surplus)
        
        # Transaction for surplus
        db.session.add(Transaction(
            tx_type=TxType.SURPLUS_CONSUMED,
            location_id=location_id,
            article_id=draft.article_id,
            batch_id=draft.batch_id,
            quantity=float(-deducted_from_surplus),
            uom=uom,
            user_id=user_id,
            reference_type="draft",
            reference_id=line_id,
            unit_price=stock.average_price if stock else 0
        ))

    if deducted_from_stock > 0:
        stock.quantity = float(Decimal(str(stock.quantity)) - deducted_from_stock)
        # Transaction for stock
        db.session.add(Transaction(
            tx_type=TxType.STOCK_CONSUMED,
            location_id=location_id,
            article_id=draft.article_id,
            batch_id=draft.batch_id,
            quantity=float(-deducted_from_stock),
            uom=uom,
            user_id=user_id,
            reference_type="draft",
            reference_id=line_id,
            unit_price=stock.average_price
        ))

    stock_after = float(stock.quantity) if stock else 0.0

    # Mark drafts as APPROVED and create actions
    for d in bucket_drafts:
        d.status = DraftStatus.APPROVED
        db.session.add(ApprovalAction(
            draft_id=d.id,
            actor_id=user_id,
            action=ApprovalActionType.APPROVED
        ))

    # Reorder Warning
    article = db.session.get(Article, draft.article_id)
    reorder_warning = False
    if article and article.reorder_threshold is not None:
        if Decimal(str(stock_after)) < Decimal(str(article.reorder_threshold)):
            reorder_warning = True

    db.session.commit()
    _update_group_status_if_done(group_id)

    return {
        "line_id": line_id,
        "article_id": article.id if article else None,
        "article_no": article.article_no if article else None,
        "approved_quantity": float(total_quantity),
        "uom": uom,
        "stock_after": stock_after,
        "surplus_consumed": float(deducted_from_surplus),
        "stock_consumed": float(deducted_from_stock),
        "reorder_warning": reorder_warning
    }


def approve_all(user_id: int, group_id: int) -> dict:
    """
    Approve all pending buckets in the group.
    Survives ValueError("Insufficient stock") for individual lines, marking them skipped.
    """
    # 1. find all representative lines
    drafts = db.session.query(Draft).filter_by(
        draft_group_id=group_id,
        status=DraftStatus.DRAFT
    ).all()
    
    # Bucket to find distinct group
    buckets = defaultdict(list)
    for d in drafts:
        buckets[(d.article_id, d.batch_id)].append(d)

    approved = []
    skipped = []

    for bucket_key, bucket_drafts in buckets.items():
        sorted_drafts = sorted(bucket_drafts, key=lambda d: d.id)
        line_id = sorted_drafts[0].id

        try:
            # We must run this logic within its own nested savepoint or sequentially
            # Since approve_line handles its own commit(), doing this in a loop is fine
            # as long as we evaluate them one by one.
            res = approve_line(user_id, group_id, line_id)
            approved.append(res)
        except ValueError as e:
            if str(e) == "Insufficient stock.":
                skipped.append(line_id)
            else:
                # E.g. "This line has already been approved"
                pass

    _update_group_status_if_done(group_id)

    return {"approved": approved, "skipped": skipped}


def reject_line(user_id: int, group_id: int, line_id: int, reason: str) -> dict:
    """
    Reject an aggregated line. Needs reason.
    """
    draft = db.session.get(Draft, line_id)
    if not draft or draft.draft_group_id != group_id:
        raise ValueError("Line not found in this group.")

    bucket_drafts = db.session.query(Draft).filter_by(
        draft_group_id=group_id,
        article_id=draft.article_id,
        batch_id=draft.batch_id,
        status=DraftStatus.DRAFT
    ).all()

    if not bucket_drafts:
        raise ValueError("Line already processed.")

    for d in bucket_drafts:
        d.status = DraftStatus.REJECTED
        db.session.add(ApprovalAction(
            draft_id=d.id,
            actor_id=user_id,
            action=ApprovalActionType.REJECTED,
            note=reason
        ))
    
    db.session.commit()
    _update_group_status_if_done(group_id)

    return {"status": "REJECTED", "reason": reason}


def reject_group(user_id: int, group_id: int, reason: str) -> dict:
    group = db.session.get(DraftGroup, group_id)
    if not group:
        raise ValueError("Group not found.")
    
    drafts = db.session.query(Draft).filter_by(
        draft_group_id=group_id,
        status=DraftStatus.DRAFT
    ).all()

    for d in drafts:
        d.status = DraftStatus.REJECTED
        db.session.add(ApprovalAction(
            draft_id=d.id,
            actor_id=user_id,
            action=ApprovalActionType.REJECTED,
            note=reason
        ))

    db.session.commit()
    _update_group_status_if_done(group_id)

    return {"status": "REJECTED", "reason": reason}


def _update_group_status_if_done(group_id: int):
    # Determine the status and store it compatible with DraftGroupStatus
    # But ONLY update real model status if there's NO MORE PENDING.
    group = db.session.get(DraftGroup, group_id)
    if not group:
        return
    status = _compute_group_display_status(group_id)
    if status != "PENDING":
        if status == "PARTIAL":
            # Just stay PENDING visually on model or whatever, but the display status computes to PARTIAL in history view
            # WMS ui asks to not add PARTIAL to Enum. So we leave it PENDING maybe, or pick something? 
            # The UI docs say "History = only fully resolved groups with no remaining DRAFT lines".
            # So if status is PARTIAL, it means no DRAFTs are left, but it's mixed.
            # We can't save "PARTIAL". The easiest is to not write to DB and let group display compute it, or
            # the docs say: "recompute draft-group stored status if possible with existing enum; if mixed resolved state cannot be stored, keep storage compatible and return computed display status from API".
            pass
        elif status == "APPROVED":
            group.status = DraftGroupStatus.APPROVED
            db.session.commit()
        elif status == "REJECTED":
            group.status = DraftGroupStatus.REJECTED
            db.session.commit()
