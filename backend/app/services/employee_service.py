"""Employee module business logic (Phase 11).

Quota priority (locked):
  1. employee_id + article_id override
  2. article_id override (any employee)
  3. job_title + category_id default

Warning threshold: received >= quota * 0.80

Stock decrement decision (DEC-EMP-001, revised by DEC-EMP-003):
PersonalIssuance decrements the matching Stock row inside the same
transaction so inventory remains accurate. The issuance is rejected
with `INSUFFICIENT_STOCK` when the selected stock row is missing or the
available quantity is lower than the requested issuance quantity.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.annual_quota import AnnualQuota
from app.models.article import Article
from app.models.batch import Batch
from app.models.category import Category
from app.models.employee import Employee
from app.models.enums import QuotaEnforcement, TxType
from app.models.location import Location
from app.models.personal_issuance import PersonalIssuance
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.models.uom_catalog import UomCatalog
from app.models.user import User


# ---------------------------------------------------------------------------
# Structured error
# ---------------------------------------------------------------------------

class EmployeeServiceError(Exception):
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

def _employee_or_404(employee_id: int) -> Employee:
    emp = db.session.get(Employee, employee_id)
    if emp is None:
        raise EmployeeServiceError("EMPLOYEE_NOT_FOUND", "Employee not found.", 404)
    return emp


def _serialize_employee(emp: Employee) -> dict:
    return {
        "id": emp.id,
        "employee_id": emp.employee_id,
        "first_name": emp.first_name,
        "last_name": emp.last_name,
        "department": emp.department,
        "job_title": emp.job_title,
        "is_active": emp.is_active,
        "created_at": emp.created_at.isoformat() if emp.created_at else None,
    }


def _quota_period_start(reset_month: int) -> date:
    """Return start of the current quota period given the reset month."""
    today = date.today()
    candidate = date(today.year, reset_month, 1)
    if candidate > today:
        candidate = date(today.year - 1, reset_month, 1)
    return candidate


def _quota_status(received: Decimal, quota: Decimal) -> str:
    if received >= quota:
        return "EXCEEDED"
    if received >= quota * Decimal("0.80"):
        return "WARNING"
    return "OK"


def _enforcement_str(e) -> str:
    return e.value if hasattr(e, "value") else str(e)


def _get_default_location() -> Location | None:
    return db.session.get(Location, 1) or db.session.query(Location).first()


def _issuance_stock_row(
    article: Article,
    *,
    location: Location | None,
    batch_id: int | None,
    for_update: bool = False,
) -> Stock | None:
    if location is None:
        return None

    query = db.session.query(Stock).filter(
        Stock.location_id == location.id,
        Stock.article_id == article.id,
    )
    if article.has_batch:
        query = query.filter(Stock.batch_id == batch_id)
    else:
        query = query.filter(Stock.batch_id.is_(None))
    if for_update:
        query = query.with_for_update()
    return query.first()


def _insufficient_stock_error(
    *,
    article: Article,
    available: Decimal,
    requested: Decimal,
    uom: str,
    batch: Batch | None = None,
) -> EmployeeServiceError:
    if article.has_batch and batch is not None:
        message = (
            f"Insufficient stock for batch {batch.batch_code}. "
            f"Available: {float(available)} {uom}, requested: {float(requested)} {uom}."
        )
    else:
        message = (
            f"Insufficient stock for this article. "
            f"Available: {float(available)} {uom}, requested: {float(requested)} {uom}."
        )
    return EmployeeServiceError(
        "INSUFFICIENT_STOCK",
        message,
        400,
        {
            "available": float(available),
            "requested": float(requested),
            "uom": uom,
            "article_id": article.id,
            "batch_id": batch.id if batch else None,
        },
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def list_employees(
    page: int,
    per_page: int,
    q: str | None,
    include_inactive: bool,
) -> dict:
    # V-3 / Wave 6 Phase 1: cap per_page to prevent DoS via large result sets
    per_page = min(per_page, 200)
    query = db.session.query(Employee)
    if not include_inactive:
        query = query.filter(Employee.is_active.is_(True))
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Employee.employee_id.ilike(term),
                Employee.first_name.ilike(term),
                Employee.last_name.ilike(term),
            )
        )
    total = query.count()
    items = (
        query.order_by(Employee.last_name, Employee.first_name)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [_serialize_employee(e) for e in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def get_employee(employee_id: int) -> dict:
    return _serialize_employee(_employee_or_404(employee_id))


def create_employee(data: dict) -> dict:
    for field in ("employee_id", "first_name", "last_name"):
        val = str(data.get(field) or "").strip()
        if not val:
            raise EmployeeServiceError(
                "VALIDATION_ERROR", f"'{field}' is required.", 400
            )

    eid = data["employee_id"].strip()
    if Employee.query.filter_by(employee_id=eid).first():
        raise EmployeeServiceError(
            "EMPLOYEE_ID_EXISTS", "Employee ID already exists.", 409
        )

    emp = Employee(
        employee_id=eid,
        first_name=data["first_name"].strip(),
        last_name=data["last_name"].strip(),
        department=str(data.get("department") or "").strip() or None,
        job_title=str(data.get("job_title") or "").strip() or None,
        is_active=bool(data.get("is_active", True)),
    )
    db.session.add(emp)
    db.session.commit()
    return _serialize_employee(emp)


def update_employee(employee_id: int, data: dict) -> dict:
    emp = _employee_or_404(employee_id)

    if "employee_id" in data:
        new_eid = str(data["employee_id"] or "").strip()
        if not new_eid:
            raise EmployeeServiceError(
                "VALIDATION_ERROR", "'employee_id' is required.", 400
            )
        if new_eid != emp.employee_id:
            if Employee.query.filter_by(employee_id=new_eid).first():
                raise EmployeeServiceError(
                    "EMPLOYEE_ID_EXISTS", "Employee ID already exists.", 409
                )
            emp.employee_id = new_eid

    if "first_name" in data:
        val = str(data["first_name"] or "").strip()
        if not val:
            raise EmployeeServiceError(
                "VALIDATION_ERROR", "'first_name' is required.", 400
            )
        emp.first_name = val

    if "last_name" in data:
        val = str(data["last_name"] or "").strip()
        if not val:
            raise EmployeeServiceError(
                "VALIDATION_ERROR", "'last_name' is required.", 400
            )
        emp.last_name = val

    if "department" in data:
        emp.department = str(data["department"] or "").strip() or None

    if "job_title" in data:
        emp.job_title = str(data["job_title"] or "").strip() or None

    if "is_active" in data:
        emp.is_active = bool(data["is_active"])

    db.session.commit()
    return _serialize_employee(emp)


def deactivate_employee(employee_id: int) -> dict:
    emp = _employee_or_404(employee_id)
    emp.is_active = False
    db.session.commit()
    return _serialize_employee(emp)


# ---------------------------------------------------------------------------
# Quota overview
# ---------------------------------------------------------------------------

def _received_for_article(emp_db_id: int, article_id: int, period_start_dt: datetime) -> Decimal:
    raw = (
        db.session.query(func.coalesce(func.sum(PersonalIssuance.quantity), 0))
        .filter(
            PersonalIssuance.employee_id == emp_db_id,
            PersonalIssuance.article_id == article_id,
            PersonalIssuance.issued_at >= period_start_dt,
        )
        .scalar()
    )
    return Decimal(str(raw))


def _received_for_category(emp_db_id: int, category_id: int, period_start_dt: datetime) -> Decimal:
    raw = (
        db.session.query(func.coalesce(func.sum(PersonalIssuance.quantity), 0))
        .join(Article, PersonalIssuance.article_id == Article.id)
        .filter(
            PersonalIssuance.employee_id == emp_db_id,
            Article.category_id == category_id,
            PersonalIssuance.issued_at >= period_start_dt,
        )
        .scalar()
    )
    return Decimal(str(raw))


def get_quota_overview(employee_id: int) -> dict:
    emp = _employee_or_404(employee_id)
    today = date.today()

    # ── level 1: employee + article overrides ──────────────────────────────
    emp_article_quotas = (
        db.session.query(AnnualQuota)
        .filter(
            AnnualQuota.employee_id == emp.id,
            AnnualQuota.article_id.isnot(None),
        )
        .all()
    )

    # ── level 2: global article overrides ──────────────────────────────────
    global_article_quotas = (
        db.session.query(AnnualQuota)
        .filter(
            AnnualQuota.employee_id.is_(None),
            AnnualQuota.article_id.isnot(None),
        )
        .all()
    )

    # ── level 3: job_title + category defaults ─────────────────────────────
    cat_quotas: list[AnnualQuota] = []
    if emp.job_title:
        cat_quotas = (
            db.session.query(AnnualQuota)
            .filter(
                AnnualQuota.job_title == emp.job_title,
                AnnualQuota.category_id.isnot(None),
                AnnualQuota.article_id.is_(None),
                AnnualQuota.employee_id.is_(None),
            )
            .all()
        )

    # Apply priority: emp+article wins over global article for the same article
    resolved: dict[int, AnnualQuota] = {}
    for q in global_article_quotas:
        resolved[q.article_id] = q
    for q in emp_article_quotas:
        resolved[q.article_id] = q  # override

    rows = []

    # ── Article-level rows ──────────────────────────────────────────────────
    for art_id, quota_row in resolved.items():
        article = db.session.get(Article, art_id)
        if article is None:
            continue
        period_start = _quota_period_start(quota_row.reset_month)
        period_start_dt = datetime(
            period_start.year, period_start.month, period_start.day, tzinfo=timezone.utc
        )
        received = _received_for_article(emp.id, art_id, period_start_dt)
        quota_qty = Decimal(str(quota_row.quantity))
        remaining = quota_qty - received

        cat = article.category
        rows.append(
            {
                "article_id": article.id,
                "article_no": article.article_no,
                "description": article.description,
                "category_id": article.category_id,
                "category_label_hr": cat.label_hr if cat else None,
                "quota": float(quota_qty),
                "received": float(received),
                "remaining": float(remaining),
                "uom": quota_row.uom,
                "enforcement": _enforcement_str(quota_row.enforcement),
                "status": _quota_status(received, quota_qty),
            }
        )

    # ── Category-level rows ─────────────────────────────────────────────────
    for quota_row in cat_quotas:
        cat = db.session.get(Category, quota_row.category_id)
        if cat is None:
            continue
        period_start = _quota_period_start(quota_row.reset_month)
        period_start_dt = datetime(
            period_start.year, period_start.month, period_start.day, tzinfo=timezone.utc
        )
        received = _received_for_category(emp.id, quota_row.category_id, period_start_dt)
        quota_qty = Decimal(str(quota_row.quantity))
        remaining = quota_qty - received

        rows.append(
            {
                "article_id": None,
                "article_no": None,
                "description": None,
                "category_id": quota_row.category_id,
                "category_label_hr": cat.label_hr,
                "quota": float(quota_qty),
                "received": float(received),
                "remaining": float(remaining),
                "uom": quota_row.uom,
                "enforcement": _enforcement_str(quota_row.enforcement),
                "status": _quota_status(received, quota_qty),
            }
        )

    return {"year": today.year, "quotas": rows}


# ---------------------------------------------------------------------------
# Issuance history
# ---------------------------------------------------------------------------

def list_issuances(employee_id: int, page: int, per_page: int) -> dict:
    # V-3 / Wave 6 Phase 1: cap per_page to prevent DoS via large result sets
    per_page = min(per_page, 200)
    _employee_or_404(employee_id)

    query = (
        db.session.query(PersonalIssuance)
        .filter(PersonalIssuance.employee_id == employee_id)
    )
    total = query.count()
    issuances = (
        query.order_by(PersonalIssuance.issued_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    items = []
    for iso in issuances:
        article = iso.article
        batch = iso.batch
        issuer = iso.issuer
        items.append(
            {
                "id": iso.id,
                "issued_at": iso.issued_at.isoformat() if iso.issued_at else None,
                "article_id": iso.article_id,
                "article_no": article.article_no if article else None,
                "description": article.description if article else None,
                "batch_id": iso.batch_id,
                "batch_code": batch.batch_code if batch else None,
                "quantity": float(iso.quantity),
                "uom": iso.uom,
                "issued_by": issuer.username if issuer else None,
                "note": iso.note,
            }
        )

    return {"items": items, "total": total, "page": page, "per_page": per_page}


# ---------------------------------------------------------------------------
# Article lookup (personal-issue only)
# ---------------------------------------------------------------------------

def lookup_issuance_articles(q: str | None) -> list[dict]:
    """Return active personal-issue articles matching the search term."""
    query = (
        db.session.query(Article)
        .join(Category, Article.category_id == Category.id)
        .filter(
            Article.is_active.is_(True),
            Category.is_personal_issue.is_(True),
        )
    )
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Article.article_no.ilike(term),
                Article.description.ilike(term),
            )
        )
    articles = query.order_by(Article.article_no).limit(50).all()

    result = []
    for article in articles:
        base_uom = db.session.get(UomCatalog, article.base_uom)
        row: dict[str, Any] = {
            "id": article.id,
            "article_no": article.article_no,
            "description": article.description,
            "base_uom": base_uom.code if base_uom else None,
            "decimal_display": base_uom.decimal_display if base_uom else False,
            "has_batch": article.has_batch,
        }
        if article.has_batch:
            # FEFO-ordered batches with positive available stock
            batches_with_stock = (
                db.session.query(Batch, func.coalesce(func.sum(Stock.quantity), 0).label("available"))
                .join(Stock, Stock.batch_id == Batch.id)
                .filter(
                    Batch.article_id == article.id,
                    Stock.quantity > 0,
                )
                .group_by(Batch.id)
                .having(func.sum(Stock.quantity) > 0)
                .order_by(Batch.expiry_date.asc())
                .all()
            )
            row["batches"] = [
                {
                    "id": b.id,
                    "batch_code": b.batch_code,
                    "expiry_date": b.expiry_date.isoformat(),
                    "available": float(avail),
                }
                for b, avail in batches_with_stock
            ]
        result.append(row)
    return result


# ---------------------------------------------------------------------------
# Quota check helper (shared by check and create)
# ---------------------------------------------------------------------------

def _find_applicable_quota(emp: Employee, article: Article) -> AnnualQuota | None:
    """Return the highest-priority AnnualQuota for this employee+article pair."""
    # Level 1: employee + article
    q = (
        db.session.query(AnnualQuota)
        .filter(
            AnnualQuota.employee_id == emp.id,
            AnnualQuota.article_id == article.id,
        )
        .first()
    )
    if q:
        return q

    # Level 2: global article override
    q = (
        db.session.query(AnnualQuota)
        .filter(
            AnnualQuota.employee_id.is_(None),
            AnnualQuota.article_id == article.id,
        )
        .first()
    )
    if q:
        return q

    # Level 3: job_title + category
    if emp.job_title:
        q = (
            db.session.query(AnnualQuota)
            .filter(
                AnnualQuota.job_title == emp.job_title,
                AnnualQuota.category_id == article.category_id,
                AnnualQuota.article_id.is_(None),
                AnnualQuota.employee_id.is_(None),
            )
            .first()
        )
        if q:
            return q

    return None


def _compute_quota_check(
    emp: Employee,
    article: Article,
    quantity: Decimal,
    quota_row: AnnualQuota,
) -> dict:
    """Compute quota check result dict given a resolved quota row."""
    period_start = _quota_period_start(quota_row.reset_month)
    period_start_dt = datetime(
        period_start.year, period_start.month, period_start.day, tzinfo=timezone.utc
    )

    # For category-level quotas received is summed across the category
    if quota_row.article_id is not None:
        received = _received_for_article(emp.id, article.id, period_start_dt)
    else:
        received = _received_for_category(emp.id, quota_row.category_id, period_start_dt)

    quota_qty = Decimal(str(quota_row.quantity))
    remaining = quota_qty - received
    projected = received + quantity

    if projected >= quota_qty:
        if _enforcement_str(quota_row.enforcement) == "BLOCK":
            status = "BLOCKED"
        else:
            status = "WARNING"
    elif projected >= quota_qty * Decimal("0.80"):
        status = "WARNING"
    else:
        status = "OK"

    return {
        "status": status,
        "message": _check_message(status, quota_qty, remaining, quota_row.uom, article.description),
        "quota": float(quota_qty),
        "received": float(received),
        "remaining": float(remaining),
        "uom": quota_row.uom,
        "enforcement": _enforcement_str(quota_row.enforcement),
    }


def _check_message(status: str, quota: Decimal, remaining: Decimal, uom: str, article_desc: str) -> str:
    if status == "OK":
        return "Quota check passed."
    if status == "WARNING":
        return (
            f"This issuance will exceed the annual quota for {article_desc}. "
            f"Remaining quota: {float(remaining)} {uom}."
        )
    if status == "BLOCKED":
        return (
            f"Annual quota exceeded for {article_desc}. "
            f"Remaining quota: {float(remaining)} {uom}."
        )
    return "No quota defined."


# ---------------------------------------------------------------------------
# Quota dry-run check
# ---------------------------------------------------------------------------

def check_issuance(employee_id: int, data: dict) -> dict:
    """Validate and quota-check without persisting. Returns check result."""
    emp = _employee_or_404(employee_id)

    article_id = data.get("article_id")
    if not article_id:
        raise EmployeeServiceError("VALIDATION_ERROR", "'article_id' is required.", 400)

    article = db.session.get(Article, article_id)
    if article is None or not article.is_active:
        raise EmployeeServiceError("ARTICLE_NOT_FOUND", "Article not found or inactive.", 400)

    if not article.category or not article.category.is_personal_issue:
        raise EmployeeServiceError(
            "NOT_PERSONAL_ISSUE",
            "Article is not in a personal-issue category.",
            400,
        )

    try:
        quantity = Decimal(str(data.get("quantity", 0)))
    except Exception:
        raise EmployeeServiceError("VALIDATION_ERROR", "'quantity' must be a number.", 400)
    if quantity <= 0:
        raise EmployeeServiceError("VALIDATION_ERROR", "'quantity' must be greater than 0.", 400)

    base_uom_obj = db.session.get(UomCatalog, article.base_uom)
    authoritative_uom = base_uom_obj.code if base_uom_obj else "kom"
    # M-3 / Wave 7 Phase 1: validate client-supplied UOM against article base UOM.
    # Mirrors the pattern in receiving_service.py (lines 318-329, 417-428).
    requested_uom = str(data.get("uom") or "").strip()
    if requested_uom and requested_uom != authoritative_uom:
        raise EmployeeServiceError(
            "UOM_MISMATCH",
            f"uom must match article base UOM '{authoritative_uom}'.",
            400,
            {
                "expected_uom": authoritative_uom,
                "received_uom": requested_uom,
            },
        )
    uom = requested_uom or authoritative_uom
    location = _get_default_location()

    # Batch validation
    batch_id = data.get("batch_id")
    batch = None
    if article.has_batch:
        if not batch_id:
            raise EmployeeServiceError(
                "BATCH_REQUIRED", "A batch is required for this article.", 400
            )
        batch = db.session.get(Batch, batch_id)
        if batch is None or batch.article_id != article.id:
            raise EmployeeServiceError("BATCH_NOT_FOUND", "Batch not found for this article.", 400)
        stock = _issuance_stock_row(
            article,
            location=location,
            batch_id=batch_id,
        )
        if stock is None or stock.quantity <= 0:
            raise EmployeeServiceError(
                "NO_BATCHES_AVAILABLE",
                "No batches available for this article.",
                400,
            )
        if Decimal(str(stock.quantity)) < quantity:
            raise _insufficient_stock_error(
                article=article,
                available=Decimal(str(stock.quantity)),
                requested=quantity,
                uom=uom,
                batch=batch,
            )
    else:
        stock = _issuance_stock_row(
            article,
            location=location,
            batch_id=None,
        )
        available = Decimal(str(stock.quantity)) if stock is not None else Decimal("0")
        if available < quantity:
            raise _insufficient_stock_error(
                article=article,
                available=available,
                requested=quantity,
                uom=uom,
            )

    quota_row = _find_applicable_quota(emp, article)
    if quota_row is None:
        return {
            "status": "NO_QUOTA",
            "message": "No quota configured for this employee/article combination.",
            "quota": None,
            "received": None,
            "remaining": None,
            "uom": None,
            "enforcement": None,
        }

    result = _compute_quota_check(emp, article, quantity, quota_row)
    if result["status"] == "BLOCKED":
        raise EmployeeServiceError("QUOTA_EXCEEDED", result["message"], 400, {"check": result})

    return result


# ---------------------------------------------------------------------------
# Create issuance
# ---------------------------------------------------------------------------

def create_issuance(employee_id: int, data: dict, issued_by_user: User) -> tuple[dict, dict | None]:
    """Create a PersonalIssuance + Transaction.

    Returns (issuance_dict, warning_dict_or_None).
    Raises EmployeeServiceError for validation / block violations.
    """
    emp = _employee_or_404(employee_id)

    article_id = data.get("article_id")
    if not article_id:
        raise EmployeeServiceError("VALIDATION_ERROR", "'article_id' is required.", 400)

    article = db.session.get(Article, article_id)
    if article is None or not article.is_active:
        raise EmployeeServiceError("ARTICLE_NOT_FOUND", "Article not found or inactive.", 400)

    if not article.category or not article.category.is_personal_issue:
        raise EmployeeServiceError(
            "NOT_PERSONAL_ISSUE",
            "Article is not in a personal-issue category.",
            400,
        )

    try:
        quantity = Decimal(str(data.get("quantity", 0)))
    except Exception:
        raise EmployeeServiceError("VALIDATION_ERROR", "'quantity' must be a number.", 400)
    if quantity <= 0:
        raise EmployeeServiceError("VALIDATION_ERROR", "'quantity' must be greater than 0.", 400)

    # UOM — use provided or fall back to article's base uom code.
    # M-3 / Wave 7 Phase 1: validate client-supplied UOM against article base UOM.
    # Mirrors the pattern in receiving_service.py (lines 318-329, 417-428).
    base_uom_obj = db.session.get(UomCatalog, article.base_uom)
    authoritative_uom = base_uom_obj.code if base_uom_obj else "kom"
    requested_uom = str(data.get("uom") or "").strip()
    if requested_uom and requested_uom != authoritative_uom:
        raise EmployeeServiceError(
            "UOM_MISMATCH",
            f"uom must match article base UOM '{authoritative_uom}'.",
            400,
            {
                "expected_uom": authoritative_uom,
                "received_uom": requested_uom,
            },
        )
    uom = requested_uom or authoritative_uom

    batch_id = data.get("batch_id")
    batch = None
    location = _get_default_location()

    # H-4 / Wave 7 Phase 1: lock the stock row with with_for_update() at the
    # point of the availability check and hold the lock through the decrement.
    # Do NOT re-query the stock row unlocked between the check and the update.
    # Any IntegrityError from a CHECK constraint race (quantity < 0) is mapped
    # to the same "insufficient stock" business error so users see a clean message.
    if article.has_batch:
        if not batch_id:
            raise EmployeeServiceError(
                "BATCH_REQUIRED", "A batch is required for this article.", 400
            )
        batch = db.session.get(Batch, batch_id)
        if batch is None or batch.article_id != article.id:
            raise EmployeeServiceError("BATCH_NOT_FOUND", "Batch not found for this article.", 400)
        stock_row = _issuance_stock_row(
            article,
            location=location,
            batch_id=batch_id,
            for_update=True,
        )
        if stock_row is None or stock_row.quantity <= 0:
            raise EmployeeServiceError(
                "NO_BATCHES_AVAILABLE",
                "No batches available for this article.",
                400,
            )
        if Decimal(str(stock_row.quantity)) < quantity:
            raise _insufficient_stock_error(
                article=article,
                available=Decimal(str(stock_row.quantity)),
                requested=quantity,
                uom=uom,
                batch=batch,
            )
    else:
        stock_row = _issuance_stock_row(
            article,
            location=location,
            batch_id=None,
            for_update=True,
        )
        available = Decimal(str(stock_row.quantity)) if stock_row is not None else Decimal("0")
        if available < quantity:
            raise _insufficient_stock_error(
                article=article,
                available=available,
                requested=quantity,
                uom=uom,
            )

    note = str(data.get("note") or "").strip() or None

    # ── Quota check ──────────────────────────────────────────────────────────
    quota_row = _find_applicable_quota(emp, article)
    warning: dict | None = None

    if quota_row is not None:
        check_result = _compute_quota_check(emp, article, quantity, quota_row)
        if check_result["status"] == "BLOCKED":
            raise EmployeeServiceError(
                "QUOTA_EXCEEDED", check_result["message"], 400, {"check": check_result}
            )
        if check_result["status"] == "WARNING":
            warning = {"code": "QUOTA_WARNING", "message": check_result["message"], "check": check_result}

    # ── Persist ──────────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)

    iso = PersonalIssuance(
        employee_id=emp.id,
        article_id=article.id,
        batch_id=batch_id if article.has_batch else None,
        quantity=quantity,
        uom=uom,
        issued_by=issued_by_user.id,
        issued_at=now,
        note=note,
    )
    db.session.add(iso)
    db.session.flush()  # get iso.id before commit

    # ── Stock decrement (see module docstring, DEC-EMP-001) ──────────────────
    # stock_row is already locked from the availability check above; reuse it.
    if location and stock_row is not None:
        try:
            stock_row.quantity -= quantity
            stock_row.last_updated = now
            db.session.flush()  # flush to trigger CHECK constraint early
        except IntegrityError:
            db.session.rollback()
            raise _insufficient_stock_error(
                article=article,
                available=Decimal("0"),
                requested=quantity,
                uom=uom,
                batch=batch if article.has_batch else None,
            )

        # ── Transaction audit trail ──────────────────────────────────────────
        tx = Transaction(
            tx_type=TxType.PERSONAL_ISSUE,
            occurred_at=now,
            location_id=location.id,
            article_id=article.id,
            batch_id=batch_id if article.has_batch else None,
            quantity=-quantity,  # negative = outbound
            uom=uom,
            unit_price=None,
            user_id=issued_by_user.id,
            reference_type="issuance",
            reference_id=iso.id,
        )
        db.session.add(tx)

    db.session.commit()

    result = {
        "id": iso.id,
        "employee_id": emp.id,
        "article_id": article.id,
        "article_no": article.article_no,
        "description": article.description,
        "batch_id": iso.batch_id,
        "batch_code": batch.batch_code if batch else None,
        "quantity": float(iso.quantity),
        "uom": iso.uom,
        "issued_by": issued_by_user.username,
        "issued_at": iso.issued_at.isoformat(),
        "note": iso.note,
    }
    return result, warning
