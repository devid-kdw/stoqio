"""Draft Entry routes.

Provides:
  GET    /api/v1/drafts?date=today  — today's draft lines (shared)
  GET    /api/v1/drafts/my          — authenticated user's own lines
  POST   /api/v1/drafts             — add a draft line
  PATCH  /api/v1/drafts/{id}        — update quantity
  DELETE /api/v1/drafts/{id}        — remove a draft line

Query strategy:
  List endpoints (GET /drafts and GET /drafts/my) use joinedload for the
  article, batch, and creator relationships so that an entire batch of draft
  rows resolves those foreign keys in a bounded number of queries rather than
  N individual lookups.  Rejection reasons are fetched in one extra query
  keyed by draft_id via _build_rejection_map().  Together, this keeps the
  hot list-serialization path at O(1) extra queries regardless of how many
  draft lines exist for the day.

  Single-row mutation responses (POST idempotency return, PATCH update) still
  use the plain _serialize_draft() helper because they touch exactly one row
  with no list-iteration; the N+1 risk does not apply there.
"""

from datetime import datetime, timezone
from time import sleep

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.article import Article
from app.models.batch import Batch
from app.models.draft import Draft
from app.models.draft_group import DraftGroup
from app.models.approval_action import ApprovalAction
from app.models.enums import (
    ApprovalActionType,
    DraftGroupStatus,
    DraftGroupType,
    DraftSource,
    DraftStatus,
    DraftType,
)
from app.models.location import Location
from app.models.uom_catalog import UomCatalog
from app.models.user import User
from app.utils.auth import get_current_user, require_role
from app.utils.draft_numbering import next_izl_group_number
from app.utils.validators import validate_note, validate_quantity
from app.utils.errors import api_error as _error

drafts_bp = Blueprint("drafts", __name__)

# v1: single location, id = 1
_V1_LOCATION_ID = 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_operational_today():
    """Return today's date based on the location's configured timezone.

    Falls back to UTC if pytz/zoneinfo is unavailable or the timezone
    string is invalid.
    """
    location = db.session.get(Location, _V1_LOCATION_ID)
    tz_name = location.timezone if location else "UTC"

    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc

    return datetime.now(tz).date()


def _get_or_create_draft_group(user_id: int, op_date):
    """Find today's pending daily-outbound DraftGroup or create a new one.

    Returns the DraftGroup instance.
    """
    group = (
        DraftGroup.query.filter_by(
            operational_date=op_date,
            status=DraftGroupStatus.PENDING,
            group_type=DraftGroupType.DAILY_OUTBOUND,
        )
        .order_by(DraftGroup.created_at.asc(), DraftGroup.id.asc())
        .first()
    )
    if group is not None:
        return group

    group = DraftGroup(
        group_number=next_izl_group_number(),
        status=DraftGroupStatus.PENDING,
        group_type=DraftGroupType.DAILY_OUTBOUND,
        operational_date=op_date,
        created_by=user_id,
    )
    db.session.add(group)
    db.session.flush()
    return group


def _get_article_uom_code(article: Article) -> str | None:
    """Return the article's base UOM code."""
    uom_ref = db.session.get(UomCatalog, article.base_uom)
    return uom_ref.code if uom_ref else None


def _normalize_optional_text(value):
    """Trim optional text input; empty strings become ``None``."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    trimmed = value.strip()
    return trimmed or None


def _serialize_draft_group(group: DraftGroup) -> dict:
    """Serialize the shared daily draft group."""
    return {
        "id": group.id,
        "group_number": group.group_number,
        "status": group.status.value if hasattr(group.status, "value") else group.status,
        "operational_date": group.operational_date.isoformat(),
        "draft_note": group.description,
    }


def _build_rejection_map(draft_ids: list[int]) -> dict[int, str | None]:
    """Return a dict mapping draft_id → latest rejection note for REJECTED lines.

    Fetches all matching ApprovalAction rows in a single query.  Only the
    most-recent REJECTED action per draft is kept (same semantics as the old
    per-row _get_rejection_reason call).

    Callers that process a batch of drafts should use this helper instead of
    calling the DB once per row.
    """
    if not draft_ids:
        return {}

    actions = (
        db.session.query(ApprovalAction)
        .filter(
            ApprovalAction.draft_id.in_(draft_ids),
            ApprovalAction.action == ApprovalActionType.REJECTED,
        )
        .order_by(ApprovalAction.draft_id, ApprovalAction.acted_at.desc())
        .all()
    )

    # Keep only the latest action per draft_id (results are already DESC by
    # acted_at within each draft_id group because of the ORDER BY above).
    rejection_map: dict[int, str | None] = {}
    for action in actions:
        if action.draft_id not in rejection_map:
            rejection_map[action.draft_id] = action.note

    return rejection_map


def _serialize_draft(
    draft: Draft,
    *,
    rejection_map: dict[int, str | None] | None = None,
) -> dict:
    """Build the response dict for a single draft line.

    When serialising a batch of drafts (e.g. the full day's list), callers
    should:
      1. Load drafts with joinedload(Draft.article), joinedload(Draft.batch),
         and joinedload(Draft.creator) so SQLAlchemy resolves those
         relationships in bounded queries rather than per-row lookups.
      2. Build a rejection_map via _build_rejection_map([d.id for d in drafts])
         and pass it in here so rejection reasons are resolved in one query
         rather than one per rejected line.

    For single-row mutation responses (POST idempotency, PATCH update) the
    relationships are resolved by SQLAlchemy's lazy-select default without
    list-level batching, which is fine because those paths touch exactly one
    row.
    """
    # Relationships resolved via SQLAlchemy (either pre-loaded via joinedload
    # by the caller or lazy-loaded for single-row paths).
    article = draft.article
    batch = draft.batch
    creator = draft.creator

    status_val = draft.status.value if hasattr(draft.status, "value") else draft.status

    # Resolve rejection reason from the preloaded map when available; fall back
    # to None for non-rejected lines (the map only contains REJECTED actions).
    if status_val == DraftStatus.REJECTED.value:
        if rejection_map is not None:
            rejection_reason = rejection_map.get(draft.id)
        else:
            # Single-row fallback: query directly (acceptable for mutation responses).
            action = (
                db.session.query(ApprovalAction)
                .filter_by(draft_id=draft.id, action=ApprovalActionType.REJECTED)
                .order_by(ApprovalAction.acted_at.desc())
                .first()
            )
            rejection_reason = action.note if action else None
    else:
        rejection_reason = None

    return {
        "id": draft.id,
        "draft_group_id": draft.draft_group_id,
        "article_id": draft.article_id,
        "article_no": article.article_no if article else None,
        "description": article.description if article else None,
        "batch_id": draft.batch_id,
        "batch_code": batch.batch_code if batch else None,
        "quantity": float(draft.quantity),
        "uom": draft.uom,
        "employee_id_ref": draft.employee_id_ref,
        "status": status_val,
        "rejection_reason": rejection_reason,
        "source": draft.source.value if hasattr(draft.source, "value") else draft.source,
        "created_by": creator.username if creator else None,
        "created_at": (
            draft.created_at.isoformat()
            if draft.created_at
            else None
        ),
    }


# ---------------------------------------------------------------------------
# GET /drafts?date=today
# ---------------------------------------------------------------------------


@drafts_bp.route("/drafts", methods=["GET"])
@require_role("OPERATOR", "ADMIN")
def get_drafts():
    """Return today's draft lines, newest first."""
    op_date = _get_operational_today()
    group = (
        DraftGroup.query.filter_by(
            operational_date=op_date,
            status=DraftGroupStatus.PENDING,
            group_type=DraftGroupType.DAILY_OUTBOUND,
        )
        .order_by(DraftGroup.created_at.asc(), DraftGroup.id.asc())
        .first()
    )

    if group is None:
        items = []
        draft_group_data = None
        pending_drafts = []
    else:
        # Load pending group drafts with joinedload to avoid per-row
        # Article / Batch / User lookups.
        pending_drafts = (
            db.session.query(Draft)
            .filter_by(draft_group_id=group.id)
            .options(
                joinedload(Draft.article),
                joinedload(Draft.batch),
                joinedload(Draft.creator),
            )
            .order_by(Draft.created_at.desc())
            .all()
        )
        draft_group_data = _serialize_draft_group(group)

    # Same-day lines: all DAILY_OUTBOUND groups for the operational day
    # (pending + resolved), excluding INVENTORY_SHORTAGE groups, newest first.
    same_day_groups = (
        DraftGroup.query.filter_by(
            operational_date=op_date,
            group_type=DraftGroupType.DAILY_OUTBOUND,
        )
        .all()
    )
    same_day_group_ids = [g.id for g in same_day_groups]
    if same_day_group_ids:
        # Load all same-day drafts with joinedload to resolve relationships in
        # a bounded number of queries instead of one lookup per row.
        same_day_drafts = (
            db.session.query(Draft)
            .filter(Draft.draft_group_id.in_(same_day_group_ids))
            .options(
                joinedload(Draft.article),
                joinedload(Draft.batch),
                joinedload(Draft.creator),
            )
            .order_by(Draft.created_at.desc())
            .all()
        )
    else:
        same_day_drafts = []

    # Build rejection maps for both collections in one query each so we never
    # issue a per-row ApprovalAction lookup.
    all_drafts_for_items = pending_drafts  # may be a subset of same_day_drafts
    pending_ids = [d.id for d in all_drafts_for_items]
    same_day_ids = [d.id for d in same_day_drafts]

    # same_day_drafts is a superset of pending_drafts on a normal day, so one
    # map covers both; build separate maps to keep the logic explicit and
    # avoid assuming containment across all edge-case test fixtures.
    items_rejection_map = _build_rejection_map(pending_ids)
    same_day_rejection_map = _build_rejection_map(same_day_ids)

    items = [
        _serialize_draft(d, rejection_map=items_rejection_map)
        for d in all_drafts_for_items
    ]

    return (
        jsonify(
            {
                "items": items,
                "draft_group": draft_group_data,
                "same_day_lines": [
                    _serialize_draft(d, rejection_map=same_day_rejection_map)
                    for d in same_day_drafts
                ],
            }
        ),
        200,
    )



# ---------------------------------------------------------------------------
# GET /drafts/my
# ---------------------------------------------------------------------------


@drafts_bp.route("/drafts/my", methods=["GET"])
@require_role("OPERATOR", "ADMIN")
def get_my_drafts():
    """Return the authenticated user's own DAILY_OUTBOUND draft lines.

    Accepts an optional ``?date=YYYY-MM-DD`` query parameter (ISO format).
    Omitting ``date`` defaults to the current operational date.

    Only ``DAILY_OUTBOUND`` draft groups are considered; ``INVENTORY_SHORTAGE``
    groups are never included in this response.
    """
    user = get_current_user()

    date_param = request.args.get("date")
    if date_param:
        try:
            from datetime import date as _date
            op_date = _date.fromisoformat(date_param)
        except ValueError:
            return _error(
                "VALIDATION_ERROR",
                f"Invalid date '{date_param}'. Expected ISO format YYYY-MM-DD.",
                400,
            )
    else:
        op_date = _get_operational_today()

    # All DAILY_OUTBOUND groups for the operational date (any status).
    same_day_groups = (
        DraftGroup.query.filter_by(
            operational_date=op_date,
            group_type=DraftGroupType.DAILY_OUTBOUND,
        )
        .all()
    )
    same_day_group_ids = [g.id for g in same_day_groups]

    if same_day_group_ids:
        # Load the user's own drafts with joinedload so article/batch/creator
        # are resolved in bounded queries rather than per row.
        my_drafts = (
            db.session.query(Draft)
            .filter(
                Draft.draft_group_id.in_(same_day_group_ids),
                Draft.created_by == user.id,
            )
            .options(
                joinedload(Draft.article),
                joinedload(Draft.batch),
                joinedload(Draft.creator),
            )
            .order_by(Draft.created_at.desc())
            .all()
        )
    else:
        my_drafts = []

    # Resolve rejection reasons for the whole batch in one query.
    my_draft_ids = [d.id for d in my_drafts]
    my_rejection_map = _build_rejection_map(my_draft_ids)

    return jsonify(
        {"lines": [_serialize_draft(d, rejection_map=my_rejection_map) for d in my_drafts]}
    ), 200


# ---------------------------------------------------------------------------
# POST /drafts
# ---------------------------------------------------------------------------


@drafts_bp.route("/drafts", methods=["POST"])
@require_role("OPERATOR", "ADMIN")
def create_draft():
    """Add a new draft line to today's draft group."""
    user = get_current_user()
    body = request.get_json(silent=True) or {}

    # --- required fields ---------------------------------------------------
    article_id = body.get("article_id")
    client_event_id = body.get("client_event_id")
    raw_quantity = body.get("quantity")
    requested_uom = body.get("uom")
    source_str = body.get("source")

    if not article_id:
        return _error("VALIDATION_ERROR", "article_id is required.", 400)
    if not client_event_id:
        return _error("VALIDATION_ERROR", "client_event_id is required.", 400)
    if not source_str:
        return _error("VALIDATION_ERROR", "source is required.", 400)

    # validate source enum
    try:
        source_enum = DraftSource(source_str)
    except ValueError:
        return _error(
            "VALIDATION_ERROR",
            f"Invalid source '{source_str}'. Must be 'scale' or 'manual'.",
            400,
        )

    # validate quantity
    qty_ok, quantity, qty_err = validate_quantity(raw_quantity)
    if not qty_ok:
        return _error("VALIDATION_ERROR", qty_err, 400)

    # validate shared daily draft note
    draft_note = body.get("draft_note")
    note_ok, note_err = validate_note(draft_note)
    if not note_ok:
        return _error("VALIDATION_ERROR", note_err, 400)

    # --- idempotency check -------------------------------------------------
    existing = Draft.query.filter_by(client_event_id=client_event_id).first()
    if existing is not None:
        return jsonify(_serialize_draft(existing)), 200

    # --- article validation ------------------------------------------------
    article = db.session.get(Article, article_id)
    if article is None or not article.is_active:
        return _error("ARTICLE_NOT_FOUND", "Article not found.", 404)

    article_uom = _get_article_uom_code(article)
    if not article_uom:
        return _error(
            "VALIDATION_ERROR",
            "Article base UOM could not be resolved.",
            400,
        )

    if requested_uom and requested_uom != article_uom:
        return _error(
            "VALIDATION_ERROR",
            "uom must match the article base UOM.",
            400,
            {"expected_uom": article_uom},
        )

    # --- batch validation --------------------------------------------------
    batch_id = body.get("batch_id")
    if article.has_batch:
        if not batch_id:
            return _error(
                "VALIDATION_ERROR",
                "batch_id is required for batch-tracked articles.",
                400,
                {"_msg_key": "DRAFT_BATCH_ID_REQUIRED"},
            )
        batch = db.session.get(Batch, batch_id)
        if batch is None or batch.article_id != article.id:
            return _error(
                "VALIDATION_ERROR",
                "Batch not found or does not belong to this article.",
                400,
            )
    else:
        batch_id = None  # ignore batch_id for non-batch articles

    # --- create / find draft group + draft line ----------------------------
    op_date = _get_operational_today()

    for attempt in range(3):
        try:
            group = _get_or_create_draft_group(user.id, op_date)
            if "draft_note" in body:
                group.description = _normalize_optional_text(draft_note)

            draft = Draft(
                draft_group_id=group.id,
                location_id=_V1_LOCATION_ID,
                article_id=article.id,
                batch_id=batch_id,
                quantity=quantity,
                uom=article_uom,
                status=DraftStatus.DRAFT,
                draft_type=DraftType.OUTBOUND,
                source=source_enum,
                client_event_id=client_event_id,
                employee_id_ref=_normalize_optional_text(body.get("employee_id_ref")),
                created_by=user.id,
            )
            db.session.add(draft)
            db.session.commit()
            return jsonify(_serialize_draft(draft)), 201
        except IntegrityError:
            db.session.rollback()

            # Idempotency race — another request already stored this event.
            existing = Draft.query.filter_by(client_event_id=client_event_id).first()
            if existing is not None:
                return jsonify(_serialize_draft(existing)), 200

            # DraftGroup creation raced with another request. Retry after a
            # short backoff so the concurrent transaction can commit.
            if attempt < 2:
                sleep(0.01 * (attempt + 1))
                continue

            return _error(
                "CONFLICT",
                "Could not create draft line due to a conflict.",
                409,
            )


# ---------------------------------------------------------------------------
# PATCH /drafts/group
# ---------------------------------------------------------------------------


@drafts_bp.route("/drafts/group", methods=["PATCH"])
@require_role("OPERATOR", "ADMIN")
def update_draft_group():
    """Update today's shared draft note."""
    op_date = _get_operational_today()
    group = (
        DraftGroup.query.filter_by(
            operational_date=op_date,
            status=DraftGroupStatus.PENDING,
            group_type=DraftGroupType.DAILY_OUTBOUND,
        )
        .order_by(DraftGroup.created_at.asc(), DraftGroup.id.asc())
        .first()
    )
    if group is None:
        return _error(
            "NOT_FOUND",
            "Today's draft does not exist yet.",
            404,
        )

    body = request.get_json(silent=True) or {}
    if "draft_note" not in body:
        return _error("VALIDATION_ERROR", "draft_note is required.", 400)
    draft_note = body.get("draft_note")
    note_ok, note_err = validate_note(draft_note)
    if not note_ok:
        return _error("VALIDATION_ERROR", note_err, 400)

    group.description = _normalize_optional_text(draft_note)
    db.session.commit()

    return jsonify(_serialize_draft_group(group)), 200


# ---------------------------------------------------------------------------
# PATCH /drafts/<id>
# ---------------------------------------------------------------------------


@drafts_bp.route("/drafts/<int:draft_id>", methods=["PATCH"])
@require_role("OPERATOR", "ADMIN")
def update_draft(draft_id: int):
    """Update the quantity of an existing draft line."""
    draft = db.session.get(Draft, draft_id)
    if draft is None:
        return _error("NOT_FOUND", "Draft line not found.", 404)

    # Only DRAFT lines may be edited
    status_val = draft.status.value if hasattr(draft.status, "value") else draft.status
    if status_val != DraftStatus.DRAFT.value:
        return _error(
            "INVALID_STATUS",
            "Only draft lines with status DRAFT can be edited.",
            400,
        )

    body = request.get_json(silent=True) or {}
    raw_quantity = body.get("quantity")
    if raw_quantity is None:
        return _error("VALIDATION_ERROR", "quantity is required.", 400)

    qty_ok, quantity, qty_err = validate_quantity(raw_quantity)
    if not qty_ok:
        return _error("VALIDATION_ERROR", qty_err, 400)

    draft.quantity = quantity
    db.session.commit()

    return jsonify(_serialize_draft(draft)), 200


# ---------------------------------------------------------------------------
# DELETE /drafts/<id>
# ---------------------------------------------------------------------------


@drafts_bp.route("/drafts/<int:draft_id>", methods=["DELETE"])
@require_role("OPERATOR", "ADMIN")
def delete_draft(draft_id: int):
    """Delete a draft line (hard delete)."""
    draft = db.session.get(Draft, draft_id)
    if draft is None:
        return _error("NOT_FOUND", "Draft line not found.", 404)

    # Only DRAFT lines may be deleted
    status_val = draft.status.value if hasattr(draft.status, "value") else draft.status
    if status_val != DraftStatus.DRAFT.value:
        return _error(
            "INVALID_STATUS",
            "Only draft lines with status DRAFT can be deleted.",
            400,
        )

    db.session.delete(draft)
    db.session.commit()

    return jsonify({"message": "Draft line deleted."}), 200
