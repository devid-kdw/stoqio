"""Draft Entry routes.

Provides:
  GET    /api/v1/drafts?date=today  — today's draft lines
  POST   /api/v1/drafts             — add a draft line
  PATCH  /api/v1/drafts/{id}        — update quantity
  DELETE /api/v1/drafts/{id}        — remove a draft line
"""

from datetime import datetime, timezone
from time import sleep

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.article import Article
from app.models.batch import Batch
from app.models.draft import Draft
from app.models.draft_group import DraftGroup
from app.models.enums import (
    DraftGroupStatus,
    DraftSource,
    DraftStatus,
    DraftType,
)
from app.models.location import Location
from app.models.uom_catalog import UomCatalog
from app.models.user import User
from app.utils.auth import get_current_user, require_role
from app.utils.validators import validate_note, validate_quantity

drafts_bp = Blueprint("drafts", __name__)

# v1: single location, id = 1
_V1_LOCATION_ID = 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _error(error: str, message: str, status_code: int, details=None):
    """Return a standard API error response."""
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
    """Find today's DraftGroup or create a new one.

    Returns the DraftGroup instance.
    """
    group = DraftGroup.query.filter_by(operational_date=op_date).first()
    if group is not None:
        return group

    # Generate next group_number: IZL-0001, IZL-0002, …
    last = (
        DraftGroup.query
        .order_by(DraftGroup.id.desc())
        .first()
    )
    next_seq = (last.id + 1) if last else 1
    group_number = f"IZL-{next_seq:04d}"

    group = DraftGroup(
        group_number=group_number,
        status=DraftGroupStatus.PENDING,
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


def _serialize_draft(draft: Draft) -> dict:
    """Build the response dict for a single draft line.

    Eagerly resolves article, batch, UOM, and creator to avoid N+1 issues
    since we typically serialise the full day's list.
    """
    article = db.session.get(Article, draft.article_id)
    batch = db.session.get(Batch, draft.batch_id) if draft.batch_id else None
    creator = db.session.get(User, draft.created_by)

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
        "status": draft.status.value if hasattr(draft.status, "value") else draft.status,
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
    group = DraftGroup.query.filter_by(operational_date=op_date).first()

    if group is None:
        return jsonify({"items": [], "draft_group": None}), 200

    drafts = (
        Draft.query
        .filter_by(draft_group_id=group.id)
        .order_by(Draft.created_at.desc())
        .all()
    )

    return (
        jsonify(
            {
                "items": [_serialize_draft(d) for d in drafts],
                "draft_group": _serialize_draft_group(group),
            }
        ),
        200,
    )


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
    group = DraftGroup.query.filter_by(operational_date=op_date).first()
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
