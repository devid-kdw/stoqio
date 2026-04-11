#!/usr/bin/env python3
"""Clone real STOQIO articles into an isolated DB and simulate 6 months to today.

This standalone script reads article master data from the configured source
PostgreSQL database, but writes only to a separate target database.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "standalone-real-article-sim-jwt-secret-2026-0001",
)

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
from app.models.enums import (
    DraftGroupStatus,
    DraftGroupType,
    DraftSource,
    DraftStatus,
    DraftType,
    UserRole,
)
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
from app.services import (
    approval_service,
    article_service,
    employee_service,
    order_service,
    receiving_service,
)
from app.utils.draft_numbering import next_izl_group_number


QTY_QUANT = Decimal("0.001")
PRICE_QUANT = Decimal("0.0001")
ORDER_NUMBERS = [f"260{i:03d}" for i in range(1, 7)]
TARGET_ZONE_SEQUENCE = ["RED", "RED", "YELLOW", "YELLOW", "YELLOW"] + [
    "NORMAL"
] * 5
ZONE_LABELS = {
    "RED": "crvena",
    "YELLOW": "narancasta",
    "NORMAL": "zelena",
}
ZONE_FACTORS = {
    "RED": Decimal("0.90"),
    "YELLOW": Decimal("1.05"),
    "NORMAL": Decimal("1.25"),
}
OUTBOUND_FACTORS = {
    "RED": Decimal("0.55"),
    "YELLOW": Decimal("0.42"),
    "NORMAL": Decimal("0.30"),
}
RECEIPT_FACTORS = {
    "RED": Decimal("0.18"),
    "YELLOW": Decimal("0.22"),
    "NORMAL": Decimal("0.20"),
}
KNOWN_UOMS = {
    "kg": ("kilogram", "kilogram", True),
    "kom": ("komad", "piece", False),
    "pár": ("par", "pair", False),
}
KNOWN_CATEGORIES = {
    "raw_material": ("Sirovine", "Raw Material", False),
    "safety_equipment": ("Zastitna oprema", "Safety Equipment", True),
    "operational_supplies": (
        "Operativni potrosni materijal",
        "Operational Supplies",
        False,
    ),
}


def dec(value: str | int | float | Decimal) -> Decimal:
    return Decimal(str(value))


def quantize_qty(value: Decimal) -> Decimal:
    return value.quantize(QTY_QUANT, rounding=ROUND_HALF_UP)


def quantize_price(value: Decimal) -> Decimal:
    return value.quantize(PRICE_QUANT, rounding=ROUND_HALF_UP)


def quantum_for_uom(uom: str) -> Decimal:
    return QTY_QUANT if uom == "kg" else Decimal("1")


def quantize_for_uom(value: Decimal, uom: str) -> Decimal:
    return value.quantize(quantum_for_uom(uom), rounding=ROUND_HALF_UP)


def scale_to_units(value: Decimal, quantum: Decimal) -> int:
    return int((value / quantum).to_integral_value(rounding=ROUND_HALF_UP))


def split_evenly(total: Decimal, count: int, quantum: Decimal) -> list[Decimal]:
    if count <= 0:
        return []
    total_units = scale_to_units(total, quantum)
    base = total_units // count
    remainder = total_units % count
    values = [Decimal(base) * quantum for _ in range(count)]
    for index in range(remainder):
        values[index] += quantum
    return values


def split_by_weights(
    total: Decimal,
    weights: list[Decimal],
    quantum: Decimal,
) -> list[Decimal]:
    if not weights:
        return []
    total_units = scale_to_units(total, quantum)
    if total_units == 0:
        return [Decimal("0")] * len(weights)

    normalized = [weight if weight > 0 else Decimal("0") for weight in weights]
    weight_sum = sum(normalized)
    if weight_sum <= 0:
        normalized = [Decimal("1")] * len(weights)
        weight_sum = Decimal(len(normalized))

    raw_units = [
        (Decimal(total_units) * weight) / weight_sum for weight in normalized
    ]
    floor_units = [int(unit) for unit in raw_units]
    remainder = total_units - sum(floor_units)
    ranked = sorted(
        range(len(raw_units)),
        key=lambda idx: (raw_units[idx] - floor_units[idx], normalized[idx]),
        reverse=True,
    )
    for idx in ranked[:remainder]:
        floor_units[idx] += 1
    return [Decimal(units) * quantum for units in floor_units]


def subtract_months(input_date: date, months: int) -> date:
    year = input_date.year
    month = input_date.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = min(
        input_date.day,
        (
            date(year + (month // 12), (month % 12) + 1, 1) - timedelta(days=1)
            if month < 12
            else date(year + 1, 1, 1) - timedelta(days=1)
        ).day,
    )
    return date(year, month, day)


def add_months(input_date: date, months: int) -> date:
    year = input_date.year
    month = input_date.month + months
    while month > 12:
        month -= 12
        year += 1
    day = min(
        input_date.day,
        (
            date(year + (month // 12), (month % 12) + 1, 1) - timedelta(days=1)
            if month < 12
            else date(year + 1, 1, 1) - timedelta(days=1)
        ).day,
    )
    return date(year, month, day)


def utc(dt_date: date, hour: int, minute: int = 0) -> datetime:
    return datetime(
        dt_date.year,
        dt_date.month,
        dt_date.day,
        hour,
        minute,
        tzinfo=timezone.utc,
    )


@dataclass(frozen=True)
class SourceBatch:
    batch_code: str | None
    expiry_date: date | None
    quantity: Decimal
    uom: str
    average_price: Decimal


@dataclass(frozen=True)
class SourceArticle:
    article_no: str
    description: str
    category_key: str
    base_uom: str
    has_batch: bool
    reorder_threshold: Decimal
    current_qty: Decimal
    unit_price: Decimal
    recent_consumed_qty: Decimal
    supplier_id: int | None
    supplier_article_code: str | None
    batches: tuple[SourceBatch, ...]


@dataclass(frozen=True)
class ArticlePlan:
    article_no: str
    target_zone: str
    end_qty: Decimal
    opening_qty: Decimal
    total_receipts: Decimal
    total_outbound: Decimal
    total_personal_issue: Decimal


@dataclass(frozen=True)
class MonthPlan:
    order_number: str
    order_at: datetime
    receipt_at: datetime
    outbound_at: datetime
    issuance_at: datetime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-database-url",
        help="Read-only source DATABASE_URL with real STOQIO articles.",
    )
    parser.add_argument(
        "--target-database-url",
        help="Isolated target DATABASE_URL for the simulation clone.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Run directly against the configured database instead of cloning to a target DB.",
    )
    parser.add_argument(
        "--end-date",
        help="Simulation end date in YYYY-MM-DD format. Defaults to local today.",
    )
    parser.add_argument(
        "--json-out",
        help="Optional path for the final JSON summary.",
    )
    return parser.parse_args()


def default_target_database_url(end_date: date) -> str:
    suffix = uuid.uuid4().hex[:8]
    return f"sqlite:////tmp/stoqio_real_articles_{end_date.isoformat()}_{suffix}.db"


def resolve_end_date(raw_value: str | None) -> date:
    if raw_value:
        return date.fromisoformat(raw_value)
    return date.today()


def build_months(end_date: date) -> list[MonthPlan]:
    start_date = subtract_months(end_date, 6)
    plans: list[MonthPlan] = []
    for index, order_number in enumerate(ORDER_NUMBERS):
        anchor = add_months(start_date, index)
        order_date = anchor + timedelta(days=2)
        receipt_date = anchor + timedelta(days=6)
        if index < len(ORDER_NUMBERS) - 1:
            outbound_date = anchor + timedelta(days=19)
            issuance_date = anchor + timedelta(days=24)
        else:
            outbound_date = end_date - timedelta(days=3)
            issuance_date = end_date
        plans.append(
            MonthPlan(
                order_number=order_number,
                order_at=utc(order_date, 8),
                receipt_at=utc(receipt_date, 10),
                outbound_at=utc(outbound_date, 14),
                issuance_at=utc(issuance_date, 15),
            )
        )
    return plans


def fetch_source_snapshot(
    source_db_url: str,
    *,
    window_start: date,
    window_end: date,
) -> tuple[dict[str, Any], list[SourceArticle]]:
    conn = psycopg2.connect(source_db_url)
    try:
        report: dict[str, Any] = {}
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("select current_database() as db, current_user as db_user;")
            report["db"] = dict(cur.fetchone())

            cur.execute(
                """
                select
                  (select count(*) from article) as article_count,
                  (select count(*) from article where is_active is true) as active_article_count,
                  (select count(*) from stock) as stock_rows,
                  (select count(*) from transaction) as transaction_count,
                  (select count(*) from transaction where occurred_at >= %s and occurred_at < %s) as tx_in_window,
                  (select count(*) from employee) as employee_count,
                  (select count(*) from "order") as order_count;
                """,
                (window_start, window_end + timedelta(days=1)),
            )
            report["counts"] = dict(cur.fetchone())

            cur.execute(
                """
                select tx_type, count(*) as cnt
                from transaction
                where occurred_at >= %s and occurred_at < %s
                group by tx_type
                order by cnt desc, tx_type;
                """,
                (window_start, window_end + timedelta(days=1)),
            )
            report["tx_types_in_window"] = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                with stock_agg as (
                  select article_id, coalesce(sum(quantity), 0) as stock_qty
                  from stock
                  group by article_id
                ), tx_agg as (
                  select article_id, coalesce(sum(abs(quantity)), 0) as consumed_qty
                  from transaction
                  where occurred_at >= %s
                    and occurred_at < %s
                    and quantity < 0
                  group by article_id
                )
                select
                  a.article_no,
                  a.description,
                  c.key as category_key,
                  u.code as base_uom,
                  a.has_batch,
                  coalesce(a.reorder_threshold, 0) as reorder_threshold,
                  coalesce(a.initial_average_price, 0) as unit_price,
                  coalesce(sa.stock_qty, 0) as current_qty,
                  coalesce(tx.consumed_qty, 0) as recent_consumed_qty,
                  supplier_link.supplier_id,
                  supplier_link.supplier_article_code
                from article a
                join category c on c.id = a.category_id
                join uom_catalog u on u.id = a.base_uom
                left join stock_agg sa on sa.article_id = a.id
                left join tx_agg tx on tx.article_id = a.id
                left join lateral (
                  select
                    aps.supplier_id,
                    aps.supplier_article_code
                  from article_supplier aps
                  join supplier s on s.id = aps.supplier_id
                  where aps.article_id = a.id
                    and s.is_active is true
                  order by aps.is_preferred desc, aps.id asc
                  limit 1
                ) supplier_link on true
                where a.is_active is true
                  and a.article_no not ilike 'SIM%%'
                  and a.article_no not ilike 'TEST%%'
                  and a.article_no not ilike 'DEMO%%'
                  and lower(a.description) not like '%%test%%'
                  and lower(a.description) not like '%%demo%%'
                order by a.article_no;
                """,
                (window_start, window_end + timedelta(days=1)),
            )
            article_rows = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                select
                  a.article_no,
                  b.batch_code,
                  b.expiry_date,
                  s.quantity,
                  s.uom,
                  s.average_price
                from stock s
                join article a on a.id = s.article_id
                left join batch b on b.id = s.batch_id
                where a.is_active is true
                  and a.article_no not ilike 'SIM%%'
                  and a.article_no not ilike 'TEST%%'
                  and a.article_no not ilike 'DEMO%%'
                  and lower(a.description) not like '%%test%%'
                  and lower(a.description) not like '%%demo%%'
                order by a.article_no, b.expiry_date nulls last, b.batch_code nulls last;
                """
            )
            batch_rows = [dict(row) for row in cur.fetchall()]

        batch_map: dict[str, list[SourceBatch]] = {}
        for row in batch_rows:
            batch_map.setdefault(row["article_no"], []).append(
                SourceBatch(
                    batch_code=row["batch_code"],
                    expiry_date=row["expiry_date"],
                    quantity=dec(row["quantity"]),
                    uom=str(row["uom"]),
                    average_price=quantize_price(dec(row["average_price"] or "0")),
                )
            )

        articles = [
            SourceArticle(
                article_no=row["article_no"],
                description=row["description"],
                category_key=row["category_key"],
                base_uom=row["base_uom"],
                has_batch=bool(row["has_batch"]),
                reorder_threshold=dec(row["reorder_threshold"] or "0"),
                current_qty=dec(row["current_qty"] or "0"),
                unit_price=quantize_price(dec(row["unit_price"] or "0")),
                recent_consumed_qty=dec(row["recent_consumed_qty"] or "0"),
                supplier_id=int(row["supplier_id"]) if row["supplier_id"] is not None else None,
                supplier_article_code=row["supplier_article_code"],
                batches=tuple(batch_map.get(row["article_no"], [])),
            )
            for row in article_rows
        ]
        return report, articles
    finally:
        conn.close()


def generate_clone_article_plans(articles: list[SourceArticle]) -> list[ArticlePlan]:
    if len(articles) != 10:
        raise RuntimeError(
            f"Expected 10 real active articles in source DB, found {len(articles)}."
        )

    plans: list[ArticlePlan] = []
    for source_article, zone in zip(
        sorted(articles, key=lambda item: item.article_no),
        TARGET_ZONE_SEQUENCE,
        strict=True,
    ):
        threshold = source_article.reorder_threshold
        base_uom = source_article.base_uom
        end_qty = quantize_for_uom(threshold * ZONE_FACTORS[zone], base_uom)
        if end_qty <= 0:
            end_qty = quantize_for_uom(Decimal("1"), base_uom)

        if source_article.category_key == "safety_equipment":
            total_personal_issue = quantize_for_uom(Decimal("4"), base_uom)
            total_outbound = Decimal("0")
            total_receipts = quantize_for_uom(Decimal("2"), base_uom)
        else:
            baseline_outbound = threshold * OUTBOUND_FACTORS[zone]
            if source_article.recent_consumed_qty > 0:
                baseline_outbound = max(
                    baseline_outbound,
                    source_article.recent_consumed_qty * Decimal("6"),
                )
            total_outbound = quantize_for_uom(baseline_outbound, base_uom)
            total_receipts = quantize_for_uom(
                threshold * RECEIPT_FACTORS[zone],
                base_uom,
            )
            total_personal_issue = Decimal("0")

        opening_qty = (
            end_qty
            + total_outbound
            + total_personal_issue
            - total_receipts
        )
        if opening_qty <= 0:
            opening_qty = end_qty + total_outbound + total_personal_issue
            total_receipts = Decimal("0")
        opening_qty = quantize_for_uom(opening_qty, base_uom)

        plans.append(
            ArticlePlan(
                article_no=source_article.article_no,
                target_zone=zone,
                end_qty=end_qty,
                opening_qty=opening_qty,
                total_receipts=total_receipts,
                total_outbound=total_outbound,
                total_personal_issue=total_personal_issue,
            )
        )
    return plans


def generate_in_place_article_plans(articles: list[SourceArticle]) -> list[ArticlePlan]:
    if len(articles) != 10:
        raise RuntimeError(
            f"Expected 10 real active articles in source DB, found {len(articles)}."
        )

    plans: list[ArticlePlan] = []
    for source_article, zone in zip(
        sorted(articles, key=lambda item: item.article_no),
        TARGET_ZONE_SEQUENCE,
        strict=True,
    ):
        threshold = source_article.reorder_threshold
        base_uom = source_article.base_uom
        opening_qty = quantize_for_uom(source_article.current_qty, base_uom)
        end_qty = quantize_for_uom(threshold * ZONE_FACTORS[zone], base_uom)
        if end_qty <= 0:
            end_qty = quantize_for_uom(
                Decimal("1") if base_uom != "kg" else Decimal("1.000"),
                base_uom,
            )

        if source_article.category_key == "safety_equipment":
            total_receipts = Decimal("0")
            total_outbound = Decimal("0")
            total_personal_issue = quantize_for_uom(
                max(opening_qty - end_qty, Decimal("1")),
                base_uom,
            )
        else:
            total_receipts = quantize_for_uom(
                threshold * RECEIPT_FACTORS[zone],
                base_uom,
            )
            total_personal_issue = Decimal("0")
            total_outbound = quantize_for_uom(
                opening_qty + total_receipts - end_qty,
                base_uom,
            )
            if total_outbound <= 0:
                total_receipts = Decimal("0")
                total_outbound = quantize_for_uom(
                    max(opening_qty - end_qty, Decimal("0")),
                    base_uom,
                )

        plans.append(
            ArticlePlan(
                article_no=source_article.article_no,
                target_zone=zone,
                end_qty=end_qty,
                opening_qty=opening_qty,
                total_receipts=total_receipts,
                total_outbound=total_outbound,
                total_personal_issue=total_personal_issue,
            )
        )
    return plans


def ensure_location() -> Location:
    location = db.session.get(Location, 1)
    if location is not None:
        return location
    location = Location(
        id=1,
        name="Standalone Real Article Simulation Warehouse",
        timezone="Europe/Berlin",
        is_active=True,
    )
    db.session.add(location)
    db.session.commit()
    return location


def ensure_uom(code: str) -> UomCatalog:
    existing = UomCatalog.query.filter_by(code=code).first()
    if existing is not None:
        return existing
    label_hr, label_en, decimal_display = KNOWN_UOMS.get(
        code,
        (code, code, False),
    )
    row = UomCatalog(
        code=code,
        label_hr=label_hr,
        label_en=label_en,
        decimal_display=decimal_display,
    )
    db.session.add(row)
    db.session.flush()
    return row


def ensure_category(key: str) -> Category:
    existing = Category.query.filter_by(key=key).first()
    if existing is not None:
        return existing
    label_hr, label_en, is_personal_issue = KNOWN_CATEGORIES[key]
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
    if User.query.filter_by(username=username).first() is not None:
        raise RuntimeError(f"User '{username}' already exists in target DB.")
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


def get_or_create_employee_record(
    employee_id: str,
    *,
    first_name: str,
    last_name: str,
    department: str,
    job_title: str,
) -> Employee:
    existing = Employee.query.filter_by(employee_id=employee_id).first()
    if existing is not None:
        return existing
    return ensure_employee_record(
        employee_id,
        first_name=first_name,
        last_name=last_name,
        department=department,
        job_title=job_title,
    )


def ensure_supplier() -> Supplier:
    internal_code = "REALSIM-SUP-01"
    existing = Supplier.query.filter_by(internal_code=internal_code).first()
    if existing is not None:
        raise RuntimeError(
            f"Supplier '{internal_code}' already exists in target DB."
        )
    supplier = Supplier(
        internal_code=internal_code,
        name="Real Article Simulation Supplier",
        contact_person="Standalone Procurement",
        email="real-sim-supplier@example.local",
        address="Standalone Demo Street 260",
        is_active=True,
    )
    db.session.add(supplier)
    db.session.commit()
    return supplier


def assert_clean_target_db() -> None:
    if Article.query.first() is not None:
        raise RuntimeError("Target DB already contains articles. Use a fresh target DB.")
    if Order.query.first() is not None:
        raise RuntimeError("Target DB already contains orders. Use a fresh target DB.")
    if Employee.query.first() is not None:
        raise RuntimeError(
            "Target DB already contains employees. Use a fresh target DB."
        )


def assert_clean_in_place_db() -> None:
    table_counts = {
        "order": Order.query.count(),
        "employee": Employee.query.count(),
        "draft": Draft.query.count(),
        "draft_group": DraftGroup.query.count(),
        "receiving": Receiving.query.count(),
        "personal_issuance": PersonalIssuance.query.count(),
        "transaction": Transaction.query.count(),
        "approval_action": ApprovalAction.query.count(),
    }
    non_empty = {table: count for table, count in table_counts.items() if count > 0}
    allowed_non_empty = {"employee"}
    disallowed = {
        table: count
        for table, count in non_empty.items()
        if table not in allowed_non_empty
    }
    if disallowed:
        raise RuntimeError(
            f"In-place simulation requires a clean baseline. Non-empty tables: {disallowed}"
        )


def get_existing_user(username: str) -> User:
    user = User.query.filter_by(username=username).first()
    if user is None:
        raise RuntimeError(f"Required user '{username}' was not found.")
    return user


def get_existing_articles(source_articles: list[SourceArticle]) -> dict[str, Article]:
    article_numbers = [article.article_no for article in source_articles]
    rows = (
        Article.query
        .filter(Article.article_no.in_(article_numbers))
        .all()
    )
    found = {article.article_no: article for article in rows}
    missing = sorted(set(article_numbers) - set(found.keys()))
    if missing:
        raise RuntimeError(f"Missing existing articles in target DB: {missing}")
    return found


def get_existing_batches(
    source_articles: list[SourceArticle],
    existing_articles: dict[str, Article],
) -> dict[str, dict[str | None, Batch | None]]:
    batch_map: dict[str, dict[str | None, Batch | None]] = {}
    for source_article in source_articles:
        if not source_article.has_batch:
            batch_map[source_article.article_no] = {None: None}
            continue
        article = existing_articles[source_article.article_no]
        rows = Batch.query.filter_by(article_id=article.id).all()
        current = {batch.batch_code: batch for batch in rows}
        expected_codes = {batch.batch_code for batch in source_article.batches}
        missing = sorted(code for code in expected_codes if code not in current)
        if missing:
            raise RuntimeError(
                f"Missing expected batches for article {source_article.article_no}: {missing}"
            )
        batch_map[source_article.article_no] = current
    return batch_map


def build_month_supplier_map(
    months: list[MonthPlan],
    source_articles: list[SourceArticle],
    plans: list[ArticlePlan],
) -> dict[str, int]:
    plan_map = {plan.article_no: plan for plan in plans}
    supplier_counts = Counter(
        article.supplier_id
        for article in source_articles
        if article.supplier_id is not None and plan_map[article.article_no].total_receipts > 0
    )
    if not supplier_counts:
        raise RuntimeError("No suppliers available for order generation.")

    ordered_supplier_ids = sorted(
        supplier_counts.keys(),
        key=lambda supplier_id: (-supplier_counts[supplier_id], supplier_id),
    )
    slot_counts = {supplier_id: 1 for supplier_id in ordered_supplier_ids}
    remaining_slots = len(months) - len(ordered_supplier_ids)
    index = 0
    while remaining_slots > 0:
        supplier_id = ordered_supplier_ids[index % len(ordered_supplier_ids)]
        slot_counts[supplier_id] += 1
        remaining_slots -= 1
        index += 1

    supplier_sequence: list[int] = []
    for supplier_id in ordered_supplier_ids:
        supplier_sequence.extend([supplier_id] * slot_counts[supplier_id])

    if len(supplier_sequence) != len(months):
        raise RuntimeError("Could not build supplier schedule for monthly orders.")

    return {
        month.order_number: supplier_sequence[index]
        for index, month in enumerate(months)
    }


def build_source_maps(
    source_articles: list[SourceArticle],
    plans: list[ArticlePlan],
) -> tuple[dict[str, SourceArticle], dict[str, ArticlePlan]]:
    article_map = {article.article_no: article for article in source_articles}
    plan_map = {plan.article_no: plan for plan in plans}
    return article_map, plan_map


def create_articles(
    source_articles: list[SourceArticle],
    plans: list[ArticlePlan],
    supplier: Supplier,
) -> dict[str, Article]:
    created: dict[str, Article] = {}
    article_map, _plan_map = build_source_maps(source_articles, plans)

    for source_article in sorted(article_map.values(), key=lambda item: item.article_no):
        ensure_uom(source_article.base_uom)
        category = ensure_category(source_article.category_key)
        payload = {
            "article_no": source_article.article_no,
            "description": source_article.description,
            "category_id": category.id,
            "base_uom": source_article.base_uom,
            "pack_size": None,
            "pack_uom": None,
            "barcode": None,
            "manufacturer": "Cloned from source snapshot",
            "manufacturer_art_number": source_article.article_no,
            "has_batch": source_article.has_batch,
            "initial_average_price": float(source_article.unit_price),
            "reorder_threshold": float(source_article.reorder_threshold),
            "reorder_coverage_days": 30,
            "density": 1.0,
            "is_active": True,
            "suppliers": [
                {
                    "supplier_id": supplier.id,
                    "supplier_article_code": f"REALSIM-{source_article.article_no}",
                    "is_preferred": True,
                }
            ],
        }
        detail = article_service.create_article(payload)
        article = db.session.get(Article, detail["id"])
        if article is None:
            raise RuntimeError(f"Could not load cloned article {source_article.article_no}.")
        link = ArticleSupplier.query.filter_by(
            article_id=article.id,
            supplier_id=supplier.id,
        ).first()
        if link is not None:
            link.last_price = source_article.unit_price
        created[source_article.article_no] = article

    db.session.commit()
    return created


def allocate_receipt_deduction(
    total_receipts: Decimal,
    end_allocations: list[Decimal],
    uom: str,
) -> list[Decimal]:
    deductions = [Decimal("0")] * len(end_allocations)
    remaining = total_receipts
    quantum = quantum_for_uom(uom)
    for index in range(len(end_allocations) - 1, -1, -1):
        if remaining <= 0:
            break
        available = end_allocations[index]
        deduction = min(available, remaining)
        deductions[index] = quantize_for_uom(deduction, uom)
        remaining -= deductions[index]
    if quantize_for_uom(remaining, uom) > 0:
        raise RuntimeError(
            "Receipt total is larger than target end quantity for a batch article."
        )
    return deductions


def seed_opening_stock(
    source_articles: list[SourceArticle],
    plans: list[ArticlePlan],
    cloned_articles: dict[str, Article],
    location: Location,
) -> dict[str, dict[str | None, Batch | None]]:
    source_map, plan_map = build_source_maps(source_articles, plans)
    cloned_batches: dict[str, dict[str | None, Batch | None]] = {}

    for article_no, cloned_article in cloned_articles.items():
        source_article = source_map[article_no]
        plan = plan_map[article_no]
        price = source_article.unit_price
        if source_article.has_batch:
            source_batches = sorted(
                source_article.batches,
                key=lambda batch: (batch.expiry_date or date.max, batch.batch_code or ""),
            )
            weights = [batch.quantity for batch in source_batches]
            end_allocations = split_by_weights(
                plan.end_qty,
                weights,
                quantum_for_uom(source_article.base_uom),
            )
            receipt_deductions = allocate_receipt_deduction(
                plan.total_receipts,
                end_allocations,
                source_article.base_uom,
            )
            batch_map: dict[str | None, Batch | None] = {}
            remaining_outbound = plan.total_outbound
            for index, source_batch in enumerate(source_batches):
                batch = Batch(
                    article_id=cloned_article.id,
                    batch_code=source_batch.batch_code,
                    expiry_date=source_batch.expiry_date,
                )
                db.session.add(batch)
                db.session.flush()
                batch_map[source_batch.batch_code] = batch

                outbound_buffer = Decimal("0")
                if index == 0:
                    outbound_buffer = remaining_outbound
                start_qty = (
                    end_allocations[index]
                    - receipt_deductions[index]
                    + outbound_buffer
                )
                db.session.add(
                    Stock(
                        location_id=location.id,
                        article_id=cloned_article.id,
                        batch_id=batch.id,
                        quantity=quantize_for_uom(start_qty, source_article.base_uom),
                        uom=source_article.base_uom,
                        average_price=price,
                        last_updated=utc(date(2025, 10, 1), 7),
                    )
                )
            cloned_batches[article_no] = batch_map
        else:
            db.session.add(
                Stock(
                    location_id=location.id,
                    article_id=cloned_article.id,
                    batch_id=None,
                    quantity=quantize_for_uom(
                        plan.opening_qty,
                        source_article.base_uom,
                    ),
                    uom=source_article.base_uom,
                    average_price=price,
                    last_updated=utc(date(2025, 10, 1), 7),
                )
            )
            cloned_batches[article_no] = {None: None}

    db.session.commit()
    return cloned_batches


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
    db.session.commit()


def backdate_approval_bundle(
    group_id: int,
    draft_ids: list[int],
    occurred_at: datetime,
) -> None:
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

    transaction = Transaction.query.filter_by(
        reference_type="issuance",
        reference_id=issuance_id,
    ).first()
    if transaction is not None:
        transaction.occurred_at = occurred_at
    db.session.commit()


def create_orders_and_receipts(
    months: list[MonthPlan],
    source_articles: list[SourceArticle],
    plans: list[ArticlePlan],
    cloned_articles: dict[str, Article],
    cloned_batches: dict[str, dict[str | None, Batch | None]],
    supplier: Supplier,
    admin_user: User,
) -> list[str]:
    plan_map = {plan.article_no: plan for plan in plans}
    source_map = {article.article_no: article for article in source_articles}
    monthly_receipts: dict[str, list[tuple[str, Decimal]]] = {
        month.order_number: [] for month in months
    }

    for plan in plans:
        if plan.total_receipts <= 0:
            continue
        source_article = source_map[plan.article_no]
        parts = split_evenly(
            plan.total_receipts,
            len(months),
            quantum_for_uom(source_article.base_uom),
        )
        for month, qty in zip(months, parts, strict=True):
            if qty > 0:
                monthly_receipts[month.order_number].append((plan.article_no, qty))

    created_orders: list[str] = []
    for month in months:
        lines = monthly_receipts[month.order_number]
        if not lines:
            raise RuntimeError(f"Order {month.order_number} has no receipt lines.")

        payload_lines: list[dict[str, Any]] = []
        article_order: list[str] = []
        for article_no, qty in lines:
            source_article = source_map[article_no]
            cloned_article = cloned_articles[article_no]
            payload_lines.append(
                {
                    "article_id": cloned_article.id,
                    "supplier_article_code": f"REALSIM-{article_no}",
                    "ordered_qty": float(qty),
                    "uom": source_article.base_uom,
                    "unit_price": float(source_article.unit_price),
                    "delivery_date": month.receipt_at.date().isoformat(),
                }
            )
            article_order.append(article_no)

        order_summary = order_service.create_order(
            admin_user.id,
            {
                "order_number": month.order_number,
                "supplier_id": supplier.id,
                "supplier_confirmation_number": f"{month.order_number}-CONF",
                "note": f"Real article simulation replenishment for {month.order_at.date()}",
                "lines": payload_lines,
            },
        )
        order = db.session.get(Order, order_summary["id"])
        if order is None:
            raise RuntimeError(f"Could not load order {month.order_number}.")
        order.created_at = month.order_at
        order.updated_at = month.order_at
        db.session.commit()

        line_rows = (
            OrderLine.query.filter_by(order_id=order.id)
            .order_by(OrderLine.id.asc())
            .all()
        )
        receipt_lines: list[dict[str, Any]] = []
        for line_row, article_no in zip(line_rows, article_order, strict=True):
            source_article = source_map[article_no]
            qty = next(qty for current_article_no, qty in lines if current_article_no == article_no)
            payload_line: dict[str, Any] = {
                "order_line_id": line_row.id,
                "article_id": cloned_articles[article_no].id,
                "quantity": float(qty),
                "uom": source_article.base_uom,
            }
            if source_article.has_batch:
                source_batches = sorted(
                    source_article.batches,
                    key=lambda batch: (batch.expiry_date or date.max, batch.batch_code or ""),
                )
                latest_source_batch = source_batches[-1]
                target_batch = cloned_batches[article_no][latest_source_batch.batch_code]
                if target_batch is None:
                    raise RuntimeError(f"Missing target batch for {article_no}.")
                payload_line["batch_code"] = latest_source_batch.batch_code
                payload_line["expiry_date"] = latest_source_batch.expiry_date.isoformat()
            receipt_lines.append(payload_line)

        receipt_result = receiving_service.submit_receipt(
            admin_user.id,
            {
                "delivery_note_number": f"{month.order_number}-DN",
                "note": f"Real article simulation linked receipt for {month.order_number}",
                "lines": receipt_lines,
            },
        )
        backdate_receipts(receipt_result["receiving_ids"], month.receipt_at)
        created_orders.append(month.order_number)

    return created_orders


def create_orders_and_receipts_in_place(
    months: list[MonthPlan],
    source_articles: list[SourceArticle],
    plans: list[ArticlePlan],
    existing_articles: dict[str, Article],
    existing_batches: dict[str, dict[str | None, Batch | None]],
    admin_user: User,
) -> list[str]:
    source_map = {article.article_no: article for article in source_articles}
    month_supplier_map = build_month_supplier_map(months, source_articles, plans)
    monthly_receipts: dict[str, list[tuple[str, Decimal]]] = {
        month.order_number: [] for month in months
    }

    supplier_months: dict[int, list[MonthPlan]] = {}
    for month in months:
        supplier_months.setdefault(month_supplier_map[month.order_number], []).append(month)

    for plan in plans:
        if plan.total_receipts <= 0:
            continue
        source_article = source_map[plan.article_no]
        if source_article.supplier_id is None:
            raise RuntimeError(f"Article {plan.article_no} has no supplier for in-place ordering.")
        eligible_months = supplier_months.get(source_article.supplier_id, [])
        if not eligible_months:
            raise RuntimeError(
                f"No month slot assigned to supplier {source_article.supplier_id}."
            )
        parts = split_evenly(
            plan.total_receipts,
            len(eligible_months),
            quantum_for_uom(source_article.base_uom),
        )
        for month, qty in zip(eligible_months, parts, strict=True):
            if qty > 0:
                monthly_receipts[month.order_number].append((plan.article_no, qty))

    created_orders: list[str] = []
    for month in months:
        supplier_id = month_supplier_map[month.order_number]
        lines = monthly_receipts[month.order_number]
        if not lines:
            raise RuntimeError(
                f"Order {month.order_number} for supplier {supplier_id} has no receipt lines."
            )

        payload_lines: list[dict[str, Any]] = []
        article_order: list[str] = []
        for article_no, qty in lines:
            source_article = source_map[article_no]
            payload_lines.append(
                {
                    "article_id": existing_articles[article_no].id,
                    "supplier_article_code": source_article.supplier_article_code,
                    "ordered_qty": float(qty),
                    "uom": source_article.base_uom,
                    "unit_price": float(source_article.unit_price),
                    "delivery_date": month.receipt_at.date().isoformat(),
                }
            )
            article_order.append(article_no)

        order_summary = order_service.create_order(
            admin_user.id,
            {
                "order_number": month.order_number,
                "supplier_id": supplier_id,
                "supplier_confirmation_number": f"{month.order_number}-CONF",
                "note": f"Presentation replenishment for {month.order_at.date()}",
                "lines": payload_lines,
            },
        )
        order = db.session.get(Order, order_summary["id"])
        if order is None:
            raise RuntimeError(f"Could not load order {month.order_number}.")
        order.created_at = month.order_at
        order.updated_at = month.order_at
        db.session.commit()

        line_rows = (
            OrderLine.query.filter_by(order_id=order.id)
            .order_by(OrderLine.id.asc())
            .all()
        )
        receipt_lines: list[dict[str, Any]] = []
        for line_row, article_no in zip(line_rows, article_order, strict=True):
            source_article = source_map[article_no]
            qty = next(
                current_qty
                for current_article_no, current_qty in lines
                if current_article_no == article_no
            )
            payload_line: dict[str, Any] = {
                "order_line_id": line_row.id,
                "article_id": existing_articles[article_no].id,
                "quantity": float(qty),
                "uom": source_article.base_uom,
            }
            if source_article.has_batch:
                latest_source_batch = sorted(
                    source_article.batches,
                    key=lambda batch: (batch.expiry_date or date.max, batch.batch_code or ""),
                )[-1]
                payload_line["batch_code"] = latest_source_batch.batch_code
                payload_line["expiry_date"] = latest_source_batch.expiry_date.isoformat()
            receipt_lines.append(payload_line)

        receipt_result = receiving_service.submit_receipt(
            admin_user.id,
            {
                "delivery_note_number": f"{month.order_number}-DN",
                "note": f"Presentation linked receipt for {month.order_number}",
                "lines": receipt_lines,
            },
        )
        backdate_receipts(receipt_result["receiving_ids"], month.receipt_at)
        created_orders.append(month.order_number)

    return created_orders


def current_available_batches(article_id: int) -> list[tuple[Batch, Decimal]]:
    rows = (
        db.session.query(Batch, Stock.quantity)
        .join(Stock, Stock.batch_id == Batch.id)
        .filter(Stock.article_id == article_id, Stock.quantity > 0)
        .order_by(Batch.expiry_date.asc().nulls_last(), Batch.batch_code.asc())
        .all()
    )
    return [(batch, dec(quantity)) for batch, quantity in rows]


def build_batch_outbound_allocations(article_id: int, quantity: Decimal) -> list[tuple[int, Decimal]]:
    remaining = quantity
    allocations: list[tuple[int, Decimal]] = []
    for batch, available in current_available_batches(article_id):
        if remaining <= 0:
            break
        take = min(available, remaining)
        if take > 0:
            allocations.append((batch.id, take))
            remaining -= take
    if quantize_qty(remaining) > 0:
        raise RuntimeError(
            f"Not enough batch stock available for article_id={article_id}. Missing {remaining}."
        )
    return allocations


def create_monthly_outbounds(
    months: list[MonthPlan],
    source_articles: list[SourceArticle],
    plans: list[ArticlePlan],
    cloned_articles: dict[str, Article],
    admin_user: User,
    operator_user: User,
) -> None:
    source_map = {article.article_no: article for article in source_articles}
    monthly_outbounds: dict[str, list[tuple[str, Decimal]]] = {
        month.order_number: [] for month in months
    }
    for plan in plans:
        if plan.total_outbound <= 0:
            continue
        source_article = source_map[plan.article_no]
        parts = split_evenly(
            plan.total_outbound,
            len(months),
            quantum_for_uom(source_article.base_uom),
        )
        for month, qty in zip(months, parts, strict=True):
            if qty > 0:
                monthly_outbounds[month.order_number].append((plan.article_no, qty))

    for month in months:
        lines = monthly_outbounds[month.order_number]
        group = DraftGroup(
            group_number=next_izl_group_number(),
            description=f"Real article simulation outbound for {month.outbound_at.date()}",
            status=DraftGroupStatus.PENDING,
            group_type=DraftGroupType.DAILY_OUTBOUND,
            operational_date=month.outbound_at.date(),
            created_by=operator_user.id,
            created_at=month.outbound_at,
        )
        db.session.add(group)
        db.session.flush()

        draft_ids: list[int] = []
        for article_no, qty in lines:
            source_article = source_map[article_no]
            cloned_article = cloned_articles[article_no]
            if source_article.has_batch:
                allocations = build_batch_outbound_allocations(cloned_article.id, qty)
            else:
                allocations = [(None, qty)]

            for batch_id, alloc_qty in allocations:
                draft = Draft(
                    draft_group_id=group.id,
                    location_id=1,
                    article_id=cloned_article.id,
                    batch_id=batch_id,
                    quantity=quantize_for_uom(alloc_qty, source_article.base_uom),
                    uom=source_article.base_uom,
                    status=DraftStatus.DRAFT,
                    draft_type=DraftType.OUTBOUND,
                    source=DraftSource.manual,
                    client_event_id=f"real-sim-{month.order_number}-{article_no}-{uuid.uuid4()}",
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
                f"Outbound approval for {month.order_number} skipped unexpectedly: {result['skipped']}"
            )
        backdate_approval_bundle(group.id, draft_ids, month.outbound_at)


def create_personal_issues(
    months: list[MonthPlan],
    source_articles: list[SourceArticle],
    plans: list[ArticlePlan],
    cloned_articles: dict[str, Article],
    admin_user: User,
    pero: Employee,
    ivan: Employee,
) -> None:
    source_map = {article.article_no: article for article in source_articles}
    employee_cycle = [pero, ivan, pero, ivan, pero, ivan]
    for plan in plans:
        if plan.total_personal_issue <= 0:
            continue
        source_article = source_map[plan.article_no]
        parts = split_evenly(
            plan.total_personal_issue,
            len(months),
            quantum_for_uom(source_article.base_uom),
        )
        for month, qty, employee in zip(months, parts, employee_cycle, strict=True):
            if qty <= 0:
                continue
            issuance, warning = employee_service.create_issuance(
                employee.id,
                {
                    "article_id": cloned_articles[plan.article_no].id,
                    "quantity": float(qty),
                    "uom": source_article.base_uom,
                    "note": f"Real article simulation issue for {employee.first_name} {employee.last_name}",
                },
                admin_user,
            )
            if warning is not None:
                raise RuntimeError(f"Unexpected quota warning: {warning}")
            backdate_issuance(issuance["id"], month.issuance_at)


def summarize(
    source_report: dict[str, Any],
    source_articles: list[SourceArticle],
    plans: list[ArticlePlan],
    cloned_articles: dict[str, Article],
    employees: list[Employee],
    order_numbers: list[str],
    *,
    source_db_url: str,
    target_db_url: str,
    window_start: date,
    window_end: date,
    read_only_source_used: bool,
    source_db_untouched: bool,
) -> dict[str, Any]:
    article_ids = [article.id for article in cloned_articles.values()]
    totals_map = article_service._build_article_totals_map(article_ids)
    plan_map = {plan.article_no: plan for plan in plans}
    source_map = {article.article_no: article for article in source_articles}

    counts = Counter()
    items: list[dict[str, Any]] = []
    for article_no in sorted(cloned_articles.keys()):
        cloned_article = cloned_articles[article_no]
        plan = plan_map[article_no]
        source_article = source_map[article_no]
        stock_total, surplus_total = totals_map.get(
            cloned_article.id,
            (Decimal("0"), Decimal("0")),
        )
        available = stock_total + surplus_total
        zone = article_service._get_reorder_status(
            stock_total,
            surplus_total,
            source_article.reorder_threshold,
        )
        counts[zone] += 1
        items.append(
            {
                "article_no": article_no,
                "description": cloned_article.description,
                "uom": source_article.base_uom,
                "source_current_qty": float(quantize_for_uom(source_article.current_qty, source_article.base_uom)),
                "target_end_qty": float(plan.end_qty),
                "available_qty": float(quantize_for_uom(available, source_article.base_uom)),
                "opening_qty": float(plan.opening_qty),
                "planned_receipts": float(plan.total_receipts),
                "planned_outbound": float(plan.total_outbound),
                "planned_personal_issue": float(plan.total_personal_issue),
                "zone": ZONE_LABELS[zone],
            }
        )

    counts_hr = {
        "crvena": counts["RED"],
        "narancasta": counts["YELLOW"],
        "zelena": counts["NORMAL"],
    }
    expected_counts = {"crvena": 2, "narancasta": 3, "zelena": 5}
    if counts_hr != expected_counts:
        raise RuntimeError(
            f"Unexpected zone distribution: {counts_hr}. Expected {expected_counts}."
        )
    if order_numbers != ORDER_NUMBERS:
        raise RuntimeError(f"Unexpected order sequence: {order_numbers}.")

    personal_issue_articles = [
        article.article_no
        for article in source_articles
        if article.category_key == "safety_equipment"
    ]

    return {
        "source_db": {
            "database_url_redacted": source_db_url.rsplit("/", 1)[0] + "/***",
            "db_name": source_report["db"]["db"],
            "read_only_source_used": read_only_source_used,
            "counts": source_report["counts"],
            "tx_types_in_window": source_report["tx_types_in_window"],
        },
        "target_db": {
            "database_url": target_db_url,
            "source_db_untouched": source_db_untouched,
        },
        "simulation_window": {
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
        },
        "orders": order_numbers,
        "employees": [
            {
                "employee_id": employee.employee_id,
                "name": f"{employee.first_name} {employee.last_name}",
            }
            for employee in employees
        ],
        "source_constraints": {
            "real_article_count": len(source_articles),
            "personal_issue_article_count": len(personal_issue_articles),
            "personal_issue_articles": personal_issue_articles,
        },
        "zone_counts": counts_hr,
        "articles": items,
        "validation": {
            "zone_target_met": True,
            "order_numbers_sequential": True,
            "article_count": len(items),
            "target_used_real_source_articles": True,
        },
    }


def main() -> int:
    args = parse_args()
    end_date = resolve_end_date(args.end_date)
    window_start = subtract_months(end_date, 6)
    source_db_url = args.source_database_url or os.getenv("DATABASE_URL", "").strip()
    if not source_db_url:
        raise RuntimeError("Missing source DATABASE_URL.")
    target_db_url = (
        source_db_url
        if args.in_place
        else args.target_database_url or default_target_database_url(end_date)
    )
    if source_db_url == target_db_url and not args.in_place:
        raise RuntimeError("Source and target DATABASE_URL must not be the same.")

    source_report, source_articles = fetch_source_snapshot(
        source_db_url,
        window_start=window_start,
        window_end=end_date,
    )
    plans = (
        generate_in_place_article_plans(source_articles)
        if args.in_place
        else generate_clone_article_plans(source_articles)
    )
    months = build_months(end_date)

    os.environ["DATABASE_URL"] = target_db_url
    app = create_app()
    with app.app_context():
        db.create_all()
        ensure_location()
        for source_article in source_articles:
            ensure_uom(source_article.base_uom)
            ensure_category(source_article.category_key)
        db.session.commit()

        if args.in_place:
            assert_clean_in_place_db()
            admin_user = get_existing_user("admin")
            operator_user = get_existing_user("demo_operator")
            pero = get_or_create_employee_record(
                "REALSIM-EMP-001",
                first_name="Pero",
                last_name="Perić",
                department="Skladiste",
                job_title="Skladistar",
            )
            ivan = get_or_create_employee_record(
                "REALSIM-EMP-002",
                first_name="Ivan",
                last_name="Ivanović",
                department="Lakirnica",
                job_title="Operater",
            )
            cloned_articles = get_existing_articles(source_articles)
            cloned_batches = get_existing_batches(source_articles, cloned_articles)
            order_numbers = create_orders_and_receipts_in_place(
                months,
                source_articles,
                plans,
                cloned_articles,
                cloned_batches,
                admin_user,
            )
        else:
            assert_clean_target_db()
            admin_user = ensure_user(
                "realsim_admin",
                "RealSim!260Admin",
                UserRole.ADMIN,
            )
            operator_user = ensure_user(
                "realsim_operator",
                "RealSim!260Operator",
                UserRole.OPERATOR,
            )
            supplier = ensure_supplier()
            pero = ensure_employee_record(
                "REALSIM-EMP-001",
                first_name="Pero",
                last_name="Perić",
                department="Skladiste",
                job_title="Skladistar",
            )
            ivan = ensure_employee_record(
                "REALSIM-EMP-002",
                first_name="Ivan",
                last_name="Ivanović",
                department="Lakirnica",
                job_title="Operater",
            )

            cloned_articles = create_articles(source_articles, plans, supplier)
            cloned_batches = seed_opening_stock(
                source_articles,
                plans,
                cloned_articles,
                ensure_location(),
            )
            order_numbers = create_orders_and_receipts(
                months,
                source_articles,
                plans,
                cloned_articles,
                cloned_batches,
                supplier,
                admin_user,
            )
        create_monthly_outbounds(
            months,
            source_articles,
            plans,
            cloned_articles,
            admin_user,
            operator_user,
        )
        create_personal_issues(
            months,
            source_articles,
            plans,
            cloned_articles,
            admin_user,
            pero,
            ivan,
        )

        summary = summarize(
            source_report,
            source_articles,
            plans,
            cloned_articles,
            [pero, ivan],
            order_numbers,
            source_db_url=source_db_url,
            target_db_url=target_db_url,
            window_start=window_start,
            window_end=end_date,
            read_only_source_used=not args.in_place,
            source_db_untouched=not args.in_place,
        )
        rendered = json.dumps(summary, indent=2, ensure_ascii=False)
        print(rendered)
        if args.json_out:
            Path(args.json_out).write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
