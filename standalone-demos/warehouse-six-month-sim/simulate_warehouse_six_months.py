#!/usr/bin/env python3
"""Standalone six-month warehouse simulation for STOQIO.

This script lives under standalone-demos on purpose. It uses the existing
backend models and service layer from the outside, but does not modify the
main application code.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "standalone-demo-jwt-secret-key-2026-0001",
)

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models.approval_action import ApprovalAction
from app.models.article import Article
from app.models.article_supplier import ArticleSupplier
from app.models.batch import Batch
from app.models.category import Category
from app.models.draft import Draft
from app.models.draft_group import DraftGroup
from app.models.employee import Employee
from app.models.enums import DraftGroupStatus, DraftGroupType, DraftSource, DraftStatus, DraftType, UserRole
from app.models.location import Location
from app.models.order import Order
from app.models.order_line import OrderLine
from app.models.personal_issuance import PersonalIssuance
from app.models.receiving import Receiving
from app.models.stock import Stock
from app.models.supplier import Supplier
from app.models.transaction import Transaction
from app.models.uom_catalog import UomCatalog
from app.models.user import User
from app.services import approval_service, article_service, employee_service, order_service, receiving_service
from app.utils.draft_numbering import next_izl_group_number


QTY_QUANT = Decimal("0.001")
PRICE_QUANT = Decimal("0.0001")
ORDER_NUMBERS = [f"260{i:03d}" for i in range(1, 7)]
ZONE_LABELS = {
    "RED": "crvena",
    "YELLOW": "narancasta",
    "NORMAL": "zelena",
}


def dec(value: str | int | float) -> Decimal:
    return Decimal(str(value))


def utc(year: int, month: int, day: int, hour: int = 9, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


@dataclass(frozen=True)
class ArticleSpec:
    slot: int
    description: str
    category_key: str
    base_uom: str
    has_batch: bool
    reorder_threshold: Decimal
    opening_qty: Decimal
    total_receipts: Decimal
    total_outbound: Decimal
    total_personal_issue: Decimal
    unit_price: Decimal


@dataclass(frozen=True)
class MonthPlan:
    order_number: str
    order_at: datetime
    receipt_at: datetime
    outbound_at: datetime
    issuance_at: datetime


ARTICLE_SPECS = [
    ArticleSpec(1, "Epoxy base A", "raw_material", "kg", True, dec("120"), dec("220"), dec("50"), dec("180"), dec("0"), dec("12.5000")),
    ArticleSpec(2, "Hardener B", "raw_material", "kg", False, dec("80"), dec("160"), dec("20"), dec("100"), dec("0"), dec("9.8000")),
    ArticleSpec(3, "Labels 90x45", "packaging_material", "kom", False, dec("60"), dec("110"), dec("20"), dec("75"), dec("0"), dec("0.4500")),
    ArticleSpec(4, "Industrial thinner", "maintenance_material", "kg", True, dec("100"), dec("180"), dec("30"), dec("105"), dec("0"), dec("6.2000")),
    ArticleSpec(5, "Shipping box M", "packaging_material", "kom", False, dec("90"), dec("170"), dec("10"), dec("85"), dec("0"), dec("1.1000")),
    ArticleSpec(6, "Line cleaner", "operational_supplies", "kg", False, dec("70"), dec("140"), dec("15"), dec("80"), dec("0"), dec("5.4000")),
    ArticleSpec(7, "Assembly bolt M8", "assembly_material", "kom", False, dec("50"), dec("100"), dec("20"), dec("66"), dec("0"), dec("0.2500")),
    ArticleSpec(8, "Blue pigment paste", "raw_material", "kg", True, dec("110"), dec("180"), dec("20"), dec("82"), dec("0"), dec("14.3000")),
    ArticleSpec(9, "Polyurethane resin", "raw_material", "kg", True, dec("100"), dec("180"), dec("40"), dec("90"), dec("0"), dec("11.7000")),
    ArticleSpec(10, "Filter insert 10in", "auxiliary_operating_materials", "kom", False, dec("80"), dec("140"), dec("20"), dec("60"), dec("0"), dec("2.7000")),
    ArticleSpec(11, "Protective gloves XL", "safety_equipment", "kom", False, dec("12"), dec("24"), dec("8"), dec("0"), dec("16"), dec("3.2000")),
    ArticleSpec(12, "Protective glasses", "safety_equipment", "kom", False, dec("10"), dec("18"), dec("8"), dec("0"), dec("12"), dec("8.5000")),
    ArticleSpec(13, "Respirator FFP2", "safety_equipment", "kom", False, dec("8"), dec("16"), dec("6"), dec("0"), dec("10"), dec("1.9000")),
    ArticleSpec(14, "Brush 50 mm", "maintenance_material", "kom", False, dec("70"), dec("120"), dec("20"), dec("50"), dec("0"), dec("4.3000")),
]

ARTICLE_BY_SLOT = {spec.slot: spec for spec in ARTICLE_SPECS}

MONTHS = [
    MonthPlan("260001", utc(2025, 10, 3, 8), utc(2025, 10, 7, 10), utc(2025, 10, 18, 14), utc(2025, 10, 24, 15)),
    MonthPlan("260002", utc(2025, 11, 3, 8), utc(2025, 11, 7, 10), utc(2025, 11, 18, 14), utc(2025, 11, 24, 15)),
    MonthPlan("260003", utc(2025, 12, 2, 8), utc(2025, 12, 6, 10), utc(2025, 12, 18, 14), utc(2025, 12, 23, 15)),
    MonthPlan("260004", utc(2026, 1, 5, 8), utc(2026, 1, 9, 10), utc(2026, 1, 19, 14), utc(2026, 1, 26, 15)),
    MonthPlan("260005", utc(2026, 2, 4, 8), utc(2026, 2, 8, 10), utc(2026, 2, 18, 14), utc(2026, 2, 24, 15)),
    MonthPlan("260006", utc(2026, 3, 5, 8), utc(2026, 3, 9, 10), utc(2026, 3, 19, 14), utc(2026, 3, 25, 15)),
]

ORDER_ALLOCATIONS = {
    "260001": {1: dec("20"), 4: dec("10"), 11: dec("4"), 12: dec("4")},
    "260002": {2: dec("20"), 7: dec("10"), 13: dec("3")},
    "260003": {1: dec("30"), 8: dec("10"), 9: dec("20"), 14: dec("10")},
    "260004": {3: dec("20"), 5: dec("10"), 6: dec("15")},
    "260005": {7: dec("10"), 8: dec("10"), 9: dec("20"), 10: dec("20")},
    "260006": {4: dec("20"), 11: dec("4"), 12: dec("4"), 13: dec("3"), 14: dec("10")},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        help="Optional DATABASE_URL override for this standalone run.",
    )
    parser.add_argument(
        "--namespace",
        default="SIM6M",
        help="Namespace for article numbers, supplier code, employees and users.",
    )
    parser.add_argument(
        "--json-out",
        help="Optional path where the final JSON summary should be written.",
    )
    return parser.parse_args()


def sanitize_namespace(value: str) -> str:
    cleaned = re.sub(r"[^A-Z0-9]", "", (value or "").upper())
    return cleaned or "SIM6M"


def article_no(namespace: str, slot: int) -> str:
    return f"{namespace}-{slot:03d}"


def supplier_article_code(namespace: str, slot: int) -> str:
    return f"{namespace}-SUP-{slot:03d}"


def batch_code(slot: int) -> str:
    return str(610000000 + slot)


def batch_expiry(slot: int) -> date:
    return date(2027, min(slot if slot <= 12 else 12, 12), 28)


def quantize_qty(value: Decimal) -> Decimal:
    return value.quantize(QTY_QUANT)


def quantize_price(value: Decimal) -> Decimal:
    return value.quantize(PRICE_QUANT)


def distribute_evenly(total: Decimal, bucket_count: int) -> list[Decimal]:
    if total == 0:
        return [Decimal("0")] * bucket_count
    total_int = int(total)
    base = total_int // bucket_count
    remainder = total_int % bucket_count
    values = [Decimal(base)] * bucket_count
    for index in range(remainder):
        values[index] += Decimal("1")
    return values


def ensure_location() -> Location:
    location = db.session.get(Location, 1)
    if location is not None:
        return location
    location = Location(id=1, name="Standalone Demo Warehouse", timezone="Europe/Berlin", is_active=True)
    db.session.add(location)
    db.session.commit()
    return location


def ensure_uom(code: str, *, decimal_display: bool) -> UomCatalog:
    row = UomCatalog.query.filter_by(code=code).first()
    if row is not None:
        return row
    labels = {"kg": ("kilogram", "kilogram"), "kom": ("komad", "piece")}
    label_hr, label_en = labels[code]
    row = UomCatalog(code=code, label_hr=label_hr, label_en=label_en, decimal_display=decimal_display)
    db.session.add(row)
    db.session.flush()
    return row


def ensure_category(key: str) -> Category:
    row = Category.query.filter_by(key=key).first()
    if row is not None:
        return row
    labels = {
        "raw_material": ("Sirovine", "Raw Material", False),
        "packaging_material": ("Ambalazni materijal", "Packaging Material", False),
        "maintenance_material": ("Materijal za odrzavanje", "Maintenance Material", False),
        "operational_supplies": ("Operativni potrosni materijal", "Operational Supplies", False),
        "assembly_material": ("Montazni materijal", "Assembly Material", False),
        "auxiliary_operating_materials": ("Pomocna sredstva", "Auxiliary Materials", False),
        "safety_equipment": ("Zastitna oprema", "Safety Equipment", True),
    }
    label_hr, label_en, is_personal_issue = labels[key]
    row = Category(
        key=key,
        label_hr=label_hr,
        label_en=label_en,
        is_personal_issue=is_personal_issue,
        is_active=True,
    )
    db.session.add(row)
    db.session.flush()
    return row


def ensure_user(username: str, password: str, role: UserRole) -> User:
    existing = User.query.filter_by(username=username).first()
    if existing is not None:
        raise RuntimeError(f"User '{username}' already exists. Use a clean demo DB.")
    user = User(
        username=username,
        password_hash=generate_password_hash(password, method="pbkdf2:sha256"),
        role=role,
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


def ensure_employee_record(
    employee_id: str,
    *,
    first_name: str,
    last_name: str,
    department: str,
    job_title: str,
) -> Employee:
    existing = Employee.query.filter_by(employee_id=employee_id).first()
    if existing is not None:
        raise RuntimeError(
            f"Employee '{employee_id}' already exists. Use a clean demo DB."
        )
    payload = {
        "employee_id": employee_id,
        "first_name": first_name,
        "last_name": last_name,
        "department": department,
        "job_title": job_title,
        "is_active": True,
    }
    created = employee_service.create_employee(payload)
    employee = db.session.get(Employee, created["id"])
    if employee is None:
        raise RuntimeError(f"Could not load employee '{employee_id}' after creation.")
    return employee


def ensure_supplier(namespace: str) -> Supplier:
    internal_code = f"{namespace}-SUP-01"
    existing = Supplier.query.filter_by(internal_code=internal_code).first()
    if existing is not None:
        raise RuntimeError(
            f"Supplier '{internal_code}' already exists. Use a clean demo DB."
        )
    supplier = Supplier(
        internal_code=internal_code,
        name=f"{namespace} Demo Supplier",
        contact_person="Demo Procurement",
        email="demo-supplier@example.local",
        address="Standalone Demo Street 260",
        is_active=True,
    )
    db.session.add(supplier)
    db.session.commit()
    return supplier


def assert_clean_namespace(namespace: str) -> None:
    article_numbers = [article_no(namespace, spec.slot) for spec in ARTICLE_SPECS]
    existing_articles = (
        Article.query
        .filter(Article.article_no.in_(article_numbers))
        .with_entities(Article.article_no)
        .all()
    )
    if existing_articles:
        raise RuntimeError(
            "Simulation article numbers already exist: "
            + ", ".join(sorted(value for (value,) in existing_articles))
        )

    existing_orders = (
        Order.query
        .filter(Order.order_number.in_(ORDER_NUMBERS))
        .with_entities(Order.order_number)
        .all()
    )
    if existing_orders:
        raise RuntimeError(
            "Reserved simulation order numbers already exist: "
            + ", ".join(sorted(value for (value,) in existing_orders))
        )

    reserved_usernames = [f"{namespace.lower()}_admin", f"{namespace.lower()}_operator"]
    existing_users = (
        User.query
        .filter(User.username.in_(reserved_usernames))
        .with_entities(User.username)
        .all()
    )
    if existing_users:
        raise RuntimeError(
            "Simulation usernames already exist: "
            + ", ".join(sorted(value for (value,) in existing_users))
        )

    reserved_employee_ids = [f"{namespace}-EMP-001", f"{namespace}-EMP-002"]
    existing_employees = (
        Employee.query
        .filter(Employee.employee_id.in_(reserved_employee_ids))
        .with_entities(Employee.employee_id)
        .all()
    )
    if existing_employees:
        raise RuntimeError(
            "Simulation employee IDs already exist: "
            + ", ".join(sorted(value for (value,) in existing_employees))
        )

    supplier_code = f"{namespace}-SUP-01"
    if Supplier.query.filter_by(internal_code=supplier_code).first() is not None:
        raise RuntimeError(
            f"Simulation supplier '{supplier_code}' already exists. Use a clean demo DB."
        )


def create_articles(namespace: str, supplier: Supplier) -> dict[int, Article]:
    created: dict[int, Article] = {}
    categories = {spec.category_key: ensure_category(spec.category_key) for spec in ARTICLE_SPECS}
    ensure_uom("kg", decimal_display=True)
    ensure_uom("kom", decimal_display=False)
    db.session.commit()

    for spec in ARTICLE_SPECS:
        payload = {
            "article_no": article_no(namespace, spec.slot),
            "description": spec.description,
            "category_id": categories[spec.category_key].id,
            "base_uom": spec.base_uom,
            "pack_size": None,
            "pack_uom": None,
            "barcode": None,
            "manufacturer": "Standalone Demo Manufacturer",
            "manufacturer_art_number": f"{namespace}-MFG-{spec.slot:03d}",
            "has_batch": spec.has_batch,
            "initial_average_price": float(spec.unit_price),
            "reorder_threshold": float(spec.reorder_threshold),
            "reorder_coverage_days": 30,
            "density": 1.0,
            "is_active": True,
            "suppliers": [
                {
                    "supplier_id": supplier.id,
                    "supplier_article_code": supplier_article_code(namespace, spec.slot),
                    "is_preferred": True,
                }
            ],
        }
        detail = article_service.create_article(payload)
        article = db.session.get(Article, detail["id"])
        if article is None:
            raise RuntimeError(f"Could not load article {payload['article_no']} after creation.")
        link = ArticleSupplier.query.filter_by(article_id=article.id, supplier_id=supplier.id).first()
        if link is not None:
            link.last_price = quantize_price(spec.unit_price)
        created[spec.slot] = article

    db.session.commit()
    return created


def seed_opening_stock(namespace: str, articles: dict[int, Article], location: Location) -> dict[int, Batch]:
    batches: dict[int, Batch] = {}
    for spec in ARTICLE_SPECS:
        article = articles[spec.slot]
        batch: Batch | None = None
        if spec.has_batch:
            batch = Batch(
                article_id=article.id,
                batch_code=batch_code(spec.slot),
                expiry_date=batch_expiry(spec.slot),
            )
            db.session.add(batch)
            db.session.flush()
            batches[spec.slot] = batch

        stock = Stock(
            location_id=location.id,
            article_id=article.id,
            batch_id=batch.id if batch else None,
            quantity=quantize_qty(spec.opening_qty),
            uom=spec.base_uom,
            average_price=quantize_price(spec.unit_price),
            last_updated=utc(2025, 10, 1, 7),
        )
        db.session.add(stock)
    db.session.commit()
    return batches


def backdate_receipts(receiving_ids: list[int], occurred_at: datetime) -> None:
    receivings = Receiving.query.filter(Receiving.id.in_(receiving_ids)).all()
    for row in receivings:
        row.received_at = occurred_at
        stock = Stock.query.filter_by(
            location_id=row.location_id,
            article_id=row.article_id,
            batch_id=row.batch_id,
        ).first()
        if stock is not None:
            stock.last_updated = occurred_at

    transactions = Transaction.query.filter(
        Transaction.reference_type == "receiving",
        Transaction.reference_id.in_(receiving_ids),
    ).all()
    for tx in transactions:
        tx.occurred_at = occurred_at

    touched_order_ids = {
        row.order_line.order_id
        for row in receivings
        if row.order_line is not None
    }
    for order_id in touched_order_ids:
        order = db.session.get(Order, order_id)
        if order is not None:
            order.updated_at = occurred_at
    db.session.commit()


def backdate_approval_bundle(group_id: int, draft_ids: list[int], occurred_at: datetime) -> None:
    group = db.session.get(DraftGroup, group_id)
    if group is not None:
        group.created_at = occurred_at

    drafts = Draft.query.filter(Draft.id.in_(draft_ids)).all()
    for draft in drafts:
        draft.created_at = occurred_at

    actions = ApprovalAction.query.filter(ApprovalAction.draft_id.in_(draft_ids)).all()
    for action in actions:
        action.acted_at = occurred_at

    transactions = Transaction.query.filter(
        Transaction.reference_type == "draft",
        Transaction.reference_id.in_(draft_ids),
    ).all()
    for tx in transactions:
        tx.occurred_at = occurred_at
    db.session.commit()


def backdate_issuance(issuance_id: int, occurred_at: datetime) -> None:
    issuance = db.session.get(PersonalIssuance, issuance_id)
    if issuance is None:
        raise RuntimeError(f"Could not load issuance {issuance_id} for backdating.")
    issuance.issued_at = occurred_at

    stock = Stock.query.filter_by(
        article_id=issuance.article_id,
        batch_id=issuance.batch_id,
    ).first()
    if stock is not None:
        stock.last_updated = occurred_at

    tx = Transaction.query.filter_by(reference_type="issuance", reference_id=issuance_id).first()
    if tx is not None:
        tx.occurred_at = occurred_at
    db.session.commit()


def create_orders_and_receipts(
    namespace: str,
    supplier: Supplier,
    articles: dict[int, Article],
    opening_batches: dict[int, Batch],
    admin_user: User,
) -> list[str]:
    created_order_numbers: list[str] = []

    for month in MONTHS:
        allocation = ORDER_ALLOCATIONS[month.order_number]
        lines_payload: list[dict[str, Any]] = []
        slots_in_order: list[int] = []
        for slot, qty in allocation.items():
            spec = ARTICLE_BY_SLOT[slot]
            article = articles[slot]
            lines_payload.append(
                {
                    "article_id": article.id,
                    "supplier_article_code": supplier_article_code(namespace, slot),
                    "ordered_qty": float(qty),
                    "uom": spec.base_uom,
                    "unit_price": float(spec.unit_price),
                    "delivery_date": month.receipt_at.date().isoformat(),
                }
            )
            slots_in_order.append(slot)

        order_summary = order_service.create_order(
            admin_user.id,
            {
                "order_number": month.order_number,
                "supplier_id": supplier.id,
                "supplier_confirmation_number": f"{month.order_number}-CONF",
                "note": f"{namespace} monthly replenishment for {month.order_at.date().isoformat()}",
                "lines": lines_payload,
            },
        )
        order = db.session.get(Order, order_summary["id"])
        if order is None:
            raise RuntimeError(f"Could not load order {month.order_number} after creation.")
        order.created_at = month.order_at
        order.updated_at = month.order_at
        db.session.commit()

        line_rows = OrderLine.query.filter_by(order_id=order.id).order_by(OrderLine.id.asc()).all()
        receipt_lines: list[dict[str, Any]] = []
        for line_row, slot in zip(line_rows, slots_in_order, strict=True):
            spec = ARTICLE_BY_SLOT[slot]
            qty = allocation[slot]
            payload_line: dict[str, Any] = {
                "order_line_id": line_row.id,
                "article_id": articles[slot].id,
                "quantity": float(qty),
                "uom": spec.base_uom,
            }
            if spec.has_batch:
                batch = opening_batches[slot]
                payload_line["batch_code"] = batch.batch_code
                payload_line["expiry_date"] = batch.expiry_date.isoformat()
            receipt_lines.append(payload_line)

        receipt_result = receiving_service.submit_receipt(
            admin_user.id,
            {
                "delivery_note_number": f"{month.order_number}-DN",
                "note": f"{namespace} linked receipt for {month.order_number}",
                "lines": receipt_lines,
            },
        )
        backdate_receipts(receipt_result["receiving_ids"], month.receipt_at)
        created_order_numbers.append(month.order_number)

    return created_order_numbers


def create_monthly_outbounds(
    namespace: str,
    articles: dict[int, Article],
    opening_batches: dict[int, Batch],
    admin_user: User,
    operator_user: User,
) -> None:
    monthly_lines: dict[str, list[dict[str, Any]]] = {month.order_number: [] for month in MONTHS}

    for spec in ARTICLE_SPECS:
        if spec.total_outbound <= 0:
            continue
        quantities = distribute_evenly(spec.total_outbound, len(MONTHS))
        for month, quantity in zip(MONTHS, quantities, strict=True):
            if quantity <= 0:
                continue
            monthly_lines[month.order_number].append(
                {
                    "slot": spec.slot,
                    "quantity": quantity,
                    "batch_id": opening_batches[spec.slot].id if spec.has_batch else None,
                }
            )

    for month in MONTHS:
        lines = monthly_lines[month.order_number]
        group = DraftGroup(
            group_number=next_izl_group_number(),
            description=f"{namespace} outbound for {month.outbound_at.date().isoformat()}",
            status=DraftGroupStatus.PENDING,
            group_type=DraftGroupType.DAILY_OUTBOUND,
            operational_date=month.outbound_at.date(),
            created_by=operator_user.id,
            created_at=month.outbound_at,
        )
        db.session.add(group)
        db.session.flush()

        draft_ids: list[int] = []
        for line in lines:
            slot = line["slot"]
            spec = ARTICLE_BY_SLOT[slot]
            draft = Draft(
                draft_group_id=group.id,
                location_id=1,
                article_id=articles[slot].id,
                batch_id=line["batch_id"],
                quantity=quantize_qty(line["quantity"]),
                uom=spec.base_uom,
                status=DraftStatus.DRAFT,
                draft_type=DraftType.OUTBOUND,
                source=DraftSource.manual,
                client_event_id=f"{namespace.lower()}-{month.order_number}-out-{slot}-{uuid.uuid4()}",
                employee_id_ref=None,
                created_by=operator_user.id,
                created_at=month.outbound_at,
            )
            db.session.add(draft)
            db.session.flush()
            draft_ids.append(draft.id)

        db.session.commit()
        result = approval_service.approve_all(admin_user.id, group.id)
        if result.get("skipped"):
            raise RuntimeError(
                f"Outbound approval for {month.order_number} skipped lines unexpectedly: "
                f"{result['skipped']}"
            )
        backdate_approval_bundle(group.id, draft_ids, month.outbound_at)


def create_personal_issues(
    articles: dict[int, Article],
    admin_user: User,
    per_employee: Employee,
    ivan_employee: Employee,
) -> None:
    employee_cycle = {
        11: [per_employee, ivan_employee, per_employee, ivan_employee, per_employee, ivan_employee],
        12: [ivan_employee, per_employee, ivan_employee, per_employee, ivan_employee, per_employee],
        13: [per_employee, per_employee, ivan_employee, ivan_employee, per_employee, ivan_employee],
    }

    for slot in (11, 12, 13):
        spec = ARTICLE_BY_SLOT[slot]
        quantities = distribute_evenly(spec.total_personal_issue, len(MONTHS))
        for month, quantity, employee in zip(MONTHS, quantities, employee_cycle[slot], strict=True):
            if quantity <= 0:
                continue
            issuance, warning = employee_service.create_issuance(
                employee.id,
                {
                    "article_id": articles[slot].id,
                    "quantity": float(quantity),
                    "uom": spec.base_uom,
                    "note": f"Standalone issue for {employee.first_name} {employee.last_name}",
                },
                admin_user,
            )
            if warning is not None:
                raise RuntimeError(
                    f"Unexpected quota warning for article slot {slot}: {warning}"
                )
            backdate_issuance(issuance["id"], month.issuance_at)


def summarize(namespace: str, articles: dict[int, Article], employees: list[Employee], order_numbers: list[str]) -> dict[str, Any]:
    article_ids = [article.id for article in articles.values()]
    totals_map = article_service._build_article_totals_map(article_ids)

    counts = Counter()
    items: list[dict[str, Any]] = []
    for spec in ARTICLE_SPECS:
        article = articles[spec.slot]
        stock_total, surplus_total = totals_map.get(article.id, (Decimal("0"), Decimal("0")))
        available = stock_total + surplus_total
        zone = article_service._get_reorder_status(
            stock_total,
            surplus_total,
            spec.reorder_threshold,
        )
        counts[zone] += 1
        expected_final = spec.opening_qty + spec.total_receipts - spec.total_outbound - spec.total_personal_issue
        items.append(
            {
                "article_no": article.article_no,
                "description": article.description,
                "uom": spec.base_uom,
                "reorder_threshold": float(spec.reorder_threshold),
                "available_qty": float(quantize_qty(available)),
                "expected_final_qty": float(quantize_qty(expected_final)),
                "zone": ZONE_LABELS[zone],
            }
        )

    counts_hr = {
        "crvena": counts["RED"],
        "narancasta": counts["YELLOW"],
        "zelena": counts["NORMAL"],
    }
    if counts_hr != {"crvena": 3, "narancasta": 5, "zelena": 6}:
        raise RuntimeError(
            f"Unexpected zone distribution: {counts_hr}. Expected 3/5/6."
        )

    if order_numbers != ORDER_NUMBERS:
        raise RuntimeError(
            f"Unexpected order sequence: {order_numbers}. Expected {ORDER_NUMBERS}."
        )

    return {
        "namespace": namespace,
        "simulation_window": {
            "start": MONTHS[0].order_at.date().isoformat(),
            "end": MONTHS[-1].issuance_at.date().isoformat(),
        },
        "orders": order_numbers,
        "employees": [
            {
                "employee_id": employee.employee_id,
                "name": f"{employee.first_name} {employee.last_name}",
            }
            for employee in employees
        ],
        "zone_counts": counts_hr,
        "articles": items,
        "validation": {
            "zone_target_met": True,
            "order_numbers_sequential": True,
            "article_count": len(items),
        },
    }


def main() -> int:
    args = parse_args()
    namespace = sanitize_namespace(args.namespace)
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    app = create_app()
    with app.app_context():
        db.create_all()
        ensure_location()
        ensure_uom("kg", decimal_display=True)
        ensure_uom("kom", decimal_display=False)
        for category_key in {spec.category_key for spec in ARTICLE_SPECS}:
            ensure_category(category_key)
        db.session.commit()

        assert_clean_namespace(namespace)

        admin_user = ensure_user(
            f"{namespace.lower()}_admin",
            "Standalone!260Admin",
            UserRole.ADMIN,
        )
        operator_user = ensure_user(
            f"{namespace.lower()}_operator",
            "Standalone!260Operator",
            UserRole.OPERATOR,
        )
        supplier = ensure_supplier(namespace)
        pero = ensure_employee_record(
            f"{namespace}-EMP-001",
            first_name="Pero",
            last_name="Perić",
            department="Skladiste",
            job_title="Skladistar",
        )
        ivan = ensure_employee_record(
            f"{namespace}-EMP-002",
            first_name="Ivan",
            last_name="Ivanović",
            department="Lakirnica",
            job_title="Operater",
        )

        articles = create_articles(namespace, supplier)
        opening_batches = seed_opening_stock(namespace, articles, ensure_location())
        order_numbers = create_orders_and_receipts(
            namespace,
            supplier,
            articles,
            opening_batches,
            admin_user,
        )
        create_monthly_outbounds(
            namespace,
            articles,
            opening_batches,
            admin_user,
            operator_user,
        )
        create_personal_issues(articles, admin_user, pero, ivan)

        summary = summarize(namespace, articles, [pero, ivan], order_numbers)
        rendered = json.dumps(summary, indent=2, ensure_ascii=False)
        print(rendered)

        if args.json_out:
            target = Path(args.json_out)
            target.write_text(rendered + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
