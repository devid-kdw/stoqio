#!/usr/bin/env python3
"""Reset a STOQIO database to the latest completed opening inventory baseline.

This tool is intended for presentation/demo preparation. It removes operational
movements created after the opening inventory and restores stock quantities to
the counted values captured by that opening count.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV = REPO_ROOT / "backend" / ".env"
load_dotenv(BACKEND_ENV)

RESET_TABLES = [
    "approval_action",
    "approval_override",
    "draft",
    "draft_group",
    "transaction",
    "personal_issuance",
    "receiving",
    "order_line",
    '"order"',
    "surplus",
]


@dataclass(frozen=True)
class OpeningCount:
    id: int
    completed_at: datetime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        help="Target DATABASE_URL. Defaults to backend/.env DATABASE_URL.",
    )
    parser.add_argument(
        "--opening-count-id",
        type=int,
        help="Optional explicit opening inventory_count.id to reset to.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit changes. Without this flag the script performs a dry-run and rolls back.",
    )
    parser.add_argument(
        "--json-out",
        help="Optional path for the JSON report.",
    )
    return parser.parse_args()


def load_database_url(raw_value: str | None) -> str:
    database_url = (raw_value or os.getenv("DATABASE_URL") or "").strip()
    if not database_url:
        raise RuntimeError("Missing DATABASE_URL.")
    return database_url


def load_opening_count(
    cur: RealDictCursor,
    opening_count_id: int | None,
) -> OpeningCount:
    if opening_count_id is not None:
        cur.execute(
            """
            select id, completed_at
            from inventory_count
            where id = %s
              and type = 'OPENING'
              and status = 'COMPLETED'
            """,
            (opening_count_id,),
        )
    else:
        cur.execute(
            """
            select id, completed_at
            from inventory_count
            where type = 'OPENING'
              and status = 'COMPLETED'
            order by completed_at desc, id desc
            limit 1
            """
        )

    row = cur.fetchone()
    if row is None:
        raise RuntimeError("No completed OPENING inventory count found.")
    if row["completed_at"] is None:
        raise RuntimeError("Opening inventory count has no completed_at timestamp.")
    return OpeningCount(id=int(row["id"]), completed_at=row["completed_at"])


def collect_pre_reset_counts(cur: RealDictCursor) -> dict[str, int]:
    results: dict[str, int] = {}
    for table_name in RESET_TABLES + ["inventory_count", "inventory_count_line", "stock"]:
        cur.execute(f"select count(*) as cnt from {table_name}")
        results[table_name] = int(cur.fetchone()["cnt"])
    return results


def create_temp_opening_snapshot(cur: RealDictCursor, opening_count: OpeningCount) -> None:
    cur.execute("drop table if exists tmp_opening_stock")
    cur.execute(
        """
        create temporary table tmp_opening_stock as
        select
            l.article_id,
            l.batch_id,
            l.counted_quantity as quantity,
            l.uom,
            coalesce(a.initial_average_price, s.average_price, 0) as average_price
        from inventory_count_line l
        join inventory_count ic
          on ic.id = l.inventory_count_id
        join article a
          on a.id = l.article_id
        left join stock s
          on s.location_id = 1
         and s.article_id = l.article_id
         and s.batch_id is not distinct from l.batch_id
        where ic.id = %s
          and l.resolution = 'OPENING_STOCK_SET'
        """,
        (opening_count.id,),
    )


def collect_opening_snapshot(cur: RealDictCursor) -> list[dict[str, Any]]:
    cur.execute(
        """
        select
            a.article_no,
            b.batch_code,
            quantity,
            uom,
            average_price
        from tmp_opening_stock t
        join article a on a.id = t.article_id
        left join batch b on b.id = t.batch_id
        order by a.article_no, b.batch_code nulls first
        """
    )
    return [dict(row) for row in cur.fetchall()]


def apply_reset(cur: RealDictCursor, opening_count: OpeningCount) -> dict[str, int]:
    deleted_rows: dict[str, int] = {}
    for table_name in RESET_TABLES:
        cur.execute(f"delete from {table_name}")
        deleted_rows[table_name] = cur.rowcount

    cur.execute(
        """
        update stock s
           set quantity = t.quantity,
               uom = t.uom,
               average_price = t.average_price,
               last_updated = %s
          from tmp_opening_stock t
         where s.location_id = 1
           and s.article_id = t.article_id
           and s.batch_id is not distinct from t.batch_id
        """,
        (opening_count.completed_at,),
    )
    updated_stock = cur.rowcount

    cur.execute(
        """
        insert into stock (location_id, article_id, batch_id, quantity, uom, average_price, last_updated)
        select
            1,
            t.article_id,
            t.batch_id,
            t.quantity,
            t.uom,
            t.average_price,
            %s
        from tmp_opening_stock t
        left join stock s
          on s.location_id = 1
         and s.article_id = t.article_id
         and s.batch_id is not distinct from t.batch_id
        where s.id is null
        """,
        (opening_count.completed_at,),
    )
    inserted_stock = cur.rowcount

    cur.execute(
        """
        delete from stock s
        where s.location_id = 1
          and not exists (
              select 1
              from tmp_opening_stock t
              where t.article_id = s.article_id
                and t.batch_id is not distinct from s.batch_id
          )
        """
    )
    deleted_stock = cur.rowcount

    return {
        "updated_stock_rows": updated_stock,
        "inserted_stock_rows": inserted_stock,
        "deleted_stock_rows": deleted_stock,
        "deleted_approval_action": deleted_rows["approval_action"],
        "deleted_approval_override": deleted_rows["approval_override"],
        "deleted_draft": deleted_rows["draft"],
        "deleted_draft_group": deleted_rows["draft_group"],
        "deleted_transaction": deleted_rows["transaction"],
        "deleted_personal_issuance": deleted_rows["personal_issuance"],
        "deleted_receiving": deleted_rows["receiving"],
        "deleted_order_line": deleted_rows["order_line"],
        "deleted_order": deleted_rows['"order"'],
        "deleted_surplus": deleted_rows["surplus"],
    }


def collect_post_reset_counts(cur: RealDictCursor) -> dict[str, int]:
    results: dict[str, int] = {}
    for table_name in RESET_TABLES + ["stock"]:
        cur.execute(f"select count(*) as cnt from {table_name}")
        results[table_name] = int(cur.fetchone()["cnt"])
    return results


def verify_reset(cur: RealDictCursor) -> dict[str, Any]:
    cur.execute(
        """
        select count(*) as mismatch_count
        from (
            select
                t.article_id,
                t.batch_id,
                t.quantity as expected_quantity,
                t.uom as expected_uom,
                s.quantity as actual_quantity,
                s.uom as actual_uom
            from tmp_opening_stock t
            full outer join stock s
              on s.location_id = 1
             and s.article_id = t.article_id
             and s.batch_id is not distinct from t.batch_id
            where t.article_id is null
               or s.article_id is null
               or t.quantity <> s.quantity
               or t.uom <> s.uom
        ) mismatches
        """
    )
    mismatch_count = int(cur.fetchone()["mismatch_count"])

    empty_tables: dict[str, bool] = {}
    for table_name in RESET_TABLES:
        cur.execute(f"select count(*) as cnt from {table_name}")
        empty_tables[table_name] = int(cur.fetchone()["cnt"]) == 0

    return {
        "stock_matches_opening_snapshot": mismatch_count == 0,
        "stock_mismatch_count": mismatch_count,
        "cleared_tables": empty_tables,
        "all_cleared_tables_empty": all(empty_tables.values()),
    }


def run_reset(
    *,
    database_url: str,
    opening_count_id: int | None,
    apply: bool,
) -> dict[str, Any]:
    conn = psycopg2.connect(database_url)
    try:
        conn.autocommit = False
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "select current_database() as db, current_user as db_user"
            )
            database_info = dict(cur.fetchone())
            opening_count = load_opening_count(cur, opening_count_id)
            pre_counts = collect_pre_reset_counts(cur)
            create_temp_opening_snapshot(cur, opening_count)
            opening_snapshot = collect_opening_snapshot(cur)
            mutation_summary = apply_reset(cur, opening_count)
            post_counts = collect_post_reset_counts(cur)
            verification = verify_reset(cur)

            if not verification["stock_matches_opening_snapshot"]:
                conn.rollback()
                raise RuntimeError(
                    f"Stock verification failed with {verification['stock_mismatch_count']} mismatches."
                )
            if not verification["all_cleared_tables_empty"]:
                conn.rollback()
                raise RuntimeError("One or more reset tables still contain rows after reset.")

            if apply:
                conn.commit()
            else:
                conn.rollback()

            return {
                "database": database_info,
                "mode": "apply" if apply else "dry_run",
                "opening_inventory_count": {
                    "id": opening_count.id,
                    "completed_at": opening_count.completed_at.isoformat(),
                },
                "counts_before": pre_counts,
                "counts_after": post_counts,
                "opening_snapshot": opening_snapshot,
                "mutation_summary": mutation_summary,
                "verification": verification,
                "committed": apply,
            }
    finally:
        conn.close()


def main() -> int:
    args = parse_args()
    database_url = load_database_url(args.database_url)
    report = run_reset(
        database_url=database_url,
        opening_count_id=args.opening_count_id,
        apply=args.apply,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    print(rendered)
    if args.json_out:
        Path(args.json_out).write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
