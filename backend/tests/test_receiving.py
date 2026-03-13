"""Integration tests for Phase 7 Receiving and dependent order lookups."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import uuid

import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db as _db
from app.models.article import Article
from app.models.batch import Batch
from app.models.category import Category
from app.models.enums import OrderLineStatus, OrderStatus, TxType, UserRole
from app.models.location import Location
from app.models.order import Order
from app.models.order_line import OrderLine
from app.models.receiving import Receiving
from app.models.stock import Stock
from app.models.supplier import Supplier
from app.models.transaction import Transaction
from app.models.uom_catalog import UomCatalog
from app.models.user import User


@pytest.fixture(scope="module")
def receiving_data(app):
    """Seed static receiving/order lookup dependencies once for the module."""
    with app.app_context():
        location = _db.session.get(Location, 1)
        if location is None:
            location = Location(id=1, name="Receiving Warehouse", timezone="UTC", is_active=True)
            _db.session.add(location)

        batch_uom = UomCatalog.query.filter_by(code="rkg").first()
        if batch_uom is None:
            batch_uom = UomCatalog(
                code="rkg",
                label_hr="receiving kilogram",
                label_en="receiving kilogram",
                decimal_display=True,
            )
            _db.session.add(batch_uom)

        plain_uom = UomCatalog.query.filter_by(code="rkom").first()
        if plain_uom is None:
            plain_uom = UomCatalog(
                code="rkom",
                label_hr="receiving komad",
                label_en="receiving piece",
                decimal_display=False,
            )
            _db.session.add(plain_uom)

        category = Category.query.filter_by(key="receiving_test_cat").first()
        if category is None:
            category = Category(
                key="receiving_test_cat",
                label_hr="Receiving test category",
                label_en="Receiving test category",
                is_active=True,
            )
            _db.session.add(category)

        _db.session.flush()

        supplier = Supplier.query.filter_by(internal_code="RCV-SUP").first()
        if supplier is None:
            supplier = Supplier(
                internal_code="RCV-SUP",
                name="Receiving Supplier",
                is_active=True,
            )
            _db.session.add(supplier)

        admin = User.query.filter_by(username="receiving_admin").first()
        if admin is None:
            admin = User(
                username="receiving_admin",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            _db.session.add(admin)

        manager = User.query.filter_by(username="receiving_manager").first()
        if manager is None:
            manager = User(
                username="receiving_manager",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.MANAGER,
                is_active=True,
            )
            _db.session.add(manager)

        batch_article = Article.query.filter_by(article_no="RCV-BATCH").first()
        if batch_article is None:
            batch_article = Article(
                article_no="RCV-BATCH",
                description="Receiving batch article",
                category_id=category.id,
                base_uom=batch_uom.id,
                has_batch=True,
                is_active=True,
            )
            _db.session.add(batch_article)

        plain_article = Article.query.filter_by(article_no="RCV-PLAIN").first()
        if plain_article is None:
            plain_article = Article(
                article_no="RCV-PLAIN",
                description="Receiving plain article",
                category_id=category.id,
                base_uom=plain_uom.id,
                has_batch=False,
                is_active=True,
            )
            _db.session.add(plain_article)

        inactive_article = Article.query.filter_by(article_no="RCV-INACTIVE").first()
        if inactive_article is None:
            inactive_article = Article(
                article_no="RCV-INACTIVE",
                description="Inactive receiving article",
                category_id=category.id,
                base_uom=plain_uom.id,
                has_batch=False,
                is_active=False,
            )
            _db.session.add(inactive_article)

        _db.session.commit()

        yield {
            "location_id": location.id,
            "supplier_id": supplier.id,
            "admin_id": admin.id,
            "admin_username": admin.username,
            "manager_username": manager.username,
            "batch_article_id": batch_article.id,
            "batch_article_no": batch_article.article_no,
            "plain_article_id": plain_article.id,
            "plain_article_no": plain_article.article_no,
            "inactive_article_id": inactive_article.id,
            "batch_uom": batch_uom.code,
            "plain_uom": plain_uom.code,
        }


@pytest.fixture(autouse=True)
def clean_receiving_state(app):
    """Remove dynamic receiving/order data before every test."""
    with app.app_context():
        _db.session.query(Transaction).delete()
        _db.session.query(Receiving).delete()
        _db.session.query(Stock).delete()
        _db.session.query(Batch).delete()
        _db.session.query(OrderLine).delete()
        _db.session.query(Order).delete()
        _db.session.commit()
        yield


_token_cache: dict[str, str] = {}


def _login(client, username: str) -> str:
    if username in _token_cache:
        return _token_cache[username]
    octet = (sum(ord(ch) for ch in username) % 200) + 20
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "pass"},
        environ_base={"REMOTE_ADDR": f"127.0.9.{octet}"},
    )
    body = response.get_json()
    assert response.status_code == 200, body
    token = body["access_token"]
    _token_cache[username] = token
    return token


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_order(
    app,
    *,
    supplier_id: int,
    created_by_id: int,
    lines: list[dict],
    status: OrderStatus = OrderStatus.OPEN,
) -> dict[str, object]:
    with app.app_context():
        order = Order(
            order_number=f"ORD-RCV-{uuid.uuid4().hex[:8].upper()}",
            supplier_id=supplier_id,
            status=status,
            created_by=created_by_id,
            note="Receiving test order",
        )
        _db.session.add(order)
        _db.session.flush()

        created_lines = []
        for line in lines:
            order_line = OrderLine(
                order_id=order.id,
                article_id=line["article_id"],
                ordered_qty=Decimal(str(line["ordered_qty"])),
                received_qty=Decimal(str(line.get("received_qty", 0))),
                uom=line["uom"],
                unit_price=(
                    Decimal(str(line["unit_price"]))
                    if line.get("unit_price") is not None
                    else None
                ),
                delivery_date=line.get("delivery_date"),
                status=line.get("status", OrderLineStatus.OPEN),
                note=line.get("note"),
            )
            _db.session.add(order_line)
            _db.session.flush()
            created_lines.append(
                {
                    "id": order_line.id,
                    "article_id": order_line.article_id,
                    "uom": order_line.uom,
                }
            )

        _db.session.commit()
        return {
            "id": order.id,
            "order_number": order.order_number,
            "lines": created_lines,
        }


def _insert_stock(
    app,
    *,
    location_id: int,
    article_id: int,
    uom: str,
    quantity: Decimal | float | int,
    average_price: Decimal | float | int,
    batch_id: int | None = None,
) -> None:
    with app.app_context():
        stock = Stock(
            location_id=location_id,
            article_id=article_id,
            batch_id=batch_id,
            quantity=Decimal(str(quantity)),
            uom=uom,
            average_price=Decimal(str(average_price)),
        )
        _db.session.add(stock)
        _db.session.commit()


class TestReceivingCreate:
    def test_linked_receipt_updates_stock_transactions_and_order_status(
        self, client, app, receiving_data
    ):
        order = _create_order(
            app,
            supplier_id=receiving_data["supplier_id"],
            created_by_id=receiving_data["admin_id"],
            lines=[
                {
                    "article_id": receiving_data["batch_article_id"],
                    "ordered_qty": 5,
                    "uom": receiving_data["batch_uom"],
                    "unit_price": Decimal("11.2500"),
                    "delivery_date": date(2026, 4, 10),
                },
                {
                    "article_id": receiving_data["plain_article_id"],
                    "ordered_qty": 3,
                    "uom": receiving_data["plain_uom"],
                    "unit_price": Decimal("2.5000"),
                    "delivery_date": date(2026, 4, 11),
                },
            ],
        )

        token = _login(client, receiving_data["admin_username"])
        response = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": "LS12606198",
                "note": None,
                "lines": [
                    {
                        "order_line_id": order["lines"][0]["id"],
                        "article_id": receiving_data["batch_article_id"],
                        "quantity": 5,
                        "uom": receiving_data["batch_uom"],
                        "batch_code": "24001",
                        "expiry_date": "2027-12-31",
                    },
                    {
                        "order_line_id": order["lines"][1]["id"],
                        "article_id": receiving_data["plain_article_id"],
                        "quantity": 4,
                        "uom": receiving_data["plain_uom"],
                        "batch_code": "99999",
                        "expiry_date": "2028-01-01",
                    },
                ],
            },
            headers=_auth_header(token),
        )

        assert response.status_code == 201
        body = response.get_json()
        assert len(body["receiving_ids"]) == 2
        assert body["stock_updated"] == [
            {
                "article_id": receiving_data["batch_article_id"],
                "article_no": receiving_data["batch_article_no"],
                "quantity_added": 5.0,
                "uom": receiving_data["batch_uom"],
            },
            {
                "article_id": receiving_data["plain_article_id"],
                "article_no": receiving_data["plain_article_no"],
                "quantity_added": 4.0,
                "uom": receiving_data["plain_uom"],
            },
        ]

        with app.app_context():
            batch = Batch.query.filter_by(
                article_id=receiving_data["batch_article_id"],
                batch_code="24001",
            ).first()
            assert batch is not None
            assert batch.expiry_date.isoformat() == "2027-12-31"

            batch_stock = Stock.query.filter_by(
                article_id=receiving_data["batch_article_id"],
                batch_id=batch.id,
            ).first()
            assert batch_stock is not None
            assert Decimal(str(batch_stock.quantity)) == Decimal("5.000")
            assert Decimal(str(batch_stock.average_price)) == Decimal("11.2500")

            plain_stock = Stock.query.filter_by(
                article_id=receiving_data["plain_article_id"],
                batch_id=None,
            ).first()
            assert plain_stock is not None
            assert Decimal(str(plain_stock.quantity)) == Decimal("4.000")
            assert Decimal(str(plain_stock.average_price)) == Decimal("2.5000")

            receivings = Receiving.query.order_by(Receiving.id.asc()).all()
            assert len(receivings) == 2
            assert receivings[0].batch_id == batch.id
            assert receivings[1].batch_id is None
            assert receivings[1].delivery_note_number == "LS12606198"

            transactions = Transaction.query.order_by(Transaction.id.asc()).all()
            assert len(transactions) == 2
            assert all(tx.tx_type == TxType.STOCK_RECEIPT for tx in transactions)
            assert [Decimal(str(tx.quantity)) for tx in transactions] == [
                Decimal("5.000"),
                Decimal("4.000"),
            ]
            assert all(tx.reference_type == "receiving" for tx in transactions)
            assert all(tx.delivery_note_number == "LS12606198" for tx in transactions)
            assert all(tx.order_number == order["order_number"] for tx in transactions)

            line_one = _db.session.get(OrderLine, order["lines"][0]["id"])
            line_two = _db.session.get(OrderLine, order["lines"][1]["id"])
            assert Decimal(str(line_one.received_qty)) == Decimal("5.000")
            assert Decimal(str(line_two.received_qty)) == Decimal("4.000")
            assert line_one.status == OrderLineStatus.CLOSED
            assert line_two.status == OrderLineStatus.CLOSED

            saved_order = _db.session.get(Order, order["id"])
            assert saved_order.status == OrderStatus.CLOSED

    def test_linked_receipt_uses_order_line_price_for_weighted_average(
        self, client, app, receiving_data
    ):
        _insert_stock(
            app,
            location_id=receiving_data["location_id"],
            article_id=receiving_data["plain_article_id"],
            uom=receiving_data["plain_uom"],
            quantity=10,
            average_price=5,
        )
        order = _create_order(
            app,
            supplier_id=receiving_data["supplier_id"],
            created_by_id=receiving_data["admin_id"],
            lines=[
                {
                    "article_id": receiving_data["plain_article_id"],
                    "ordered_qty": 5,
                    "uom": receiving_data["plain_uom"],
                    "unit_price": Decimal("9.0000"),
                }
            ],
        )

        token = _login(client, receiving_data["admin_username"])
        response = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": "LS12606199",
                "note": None,
                "lines": [
                    {
                        "order_line_id": order["lines"][0]["id"],
                        "article_id": receiving_data["plain_article_id"],
                        "quantity": 5,
                        "uom": receiving_data["plain_uom"],
                    }
                ],
            },
            headers=_auth_header(token),
        )

        assert response.status_code == 201
        with app.app_context():
            stock = Stock.query.filter_by(
                article_id=receiving_data["plain_article_id"],
                batch_id=None,
            ).first()
            assert stock is not None
            assert Decimal(str(stock.quantity)) == Decimal("15.000")
            assert Decimal(str(stock.average_price)) == Decimal("6.3333")

            receiving = Receiving.query.one()
            assert Decimal(str(receiving.unit_price)) == Decimal("9.0000")

    def test_adhoc_receipt_without_unit_price_preserves_existing_average(
        self, client, app, receiving_data
    ):
        _insert_stock(
            app,
            location_id=receiving_data["location_id"],
            article_id=receiving_data["plain_article_id"],
            uom=receiving_data["plain_uom"],
            quantity=10,
            average_price=4.2500,
        )

        token = _login(client, receiving_data["admin_username"])
        response = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": "LS12606200",
                "note": "Urgent ad-hoc delivery",
                "lines": [
                    {
                        "order_line_id": None,
                        "article_id": receiving_data["plain_article_id"],
                        "quantity": 2,
                        "uom": receiving_data["plain_uom"],
                    }
                ],
            },
            headers=_auth_header(token),
        )

        assert response.status_code == 201
        with app.app_context():
            stock = Stock.query.filter_by(
                article_id=receiving_data["plain_article_id"],
                batch_id=None,
            ).first()
            assert stock is not None
            assert Decimal(str(stock.quantity)) == Decimal("12.000")
            assert Decimal(str(stock.average_price)) == Decimal("4.2500")

            receiving = Receiving.query.one()
            transaction = Transaction.query.one()
            assert receiving.unit_price is None
            assert transaction.unit_price is None
            assert receiving.note == "Urgent ad-hoc delivery"

    def test_adhoc_receipt_without_unit_price_new_stock_defaults_average_to_zero(
        self, client, app, receiving_data
    ):
        token = _login(client, receiving_data["admin_username"])
        response = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": "LS12606201",
                "note": "First ad-hoc delivery",
                "lines": [
                    {
                        "order_line_id": None,
                        "article_id": receiving_data["plain_article_id"],
                        "quantity": 1,
                        "uom": receiving_data["plain_uom"],
                    }
                ],
            },
            headers=_auth_header(token),
        )

        assert response.status_code == 201
        with app.app_context():
            stock = Stock.query.filter_by(
                article_id=receiving_data["plain_article_id"],
                batch_id=None,
            ).first()
            assert stock is not None
            assert Decimal(str(stock.average_price)) == Decimal("0.0000")

    def test_batch_expiry_mismatch_returns_409_with_details(
        self, client, app, receiving_data
    ):
        with app.app_context():
            _db.session.add(
                Batch(
                    article_id=receiving_data["batch_article_id"],
                    batch_code="24001",
                    expiry_date=date(2027, 12, 31),
                )
            )
            _db.session.commit()

        token = _login(client, receiving_data["admin_username"])
        response = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": "LS12606202",
                "note": "Mismatch test",
                "lines": [
                    {
                        "order_line_id": None,
                        "article_id": receiving_data["batch_article_id"],
                        "quantity": 1,
                        "uom": receiving_data["batch_uom"],
                        "batch_code": "24001",
                        "expiry_date": "2028-01-31",
                    }
                ],
            },
            headers=_auth_header(token),
        )

        assert response.status_code == 409
        body = response.get_json()
        assert body["error"] == "BATCH_EXPIRY_MISMATCH"
        assert body["details"]["line_index"] == 0
        assert body["details"]["batch_code"] == "24001"

        with app.app_context():
            assert Receiving.query.count() == 0
            assert Transaction.query.count() == 0

    def test_receiving_rejects_all_skipped(self, client, receiving_data):
        token = _login(client, receiving_data["admin_username"])
        response = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": "LS12606203",
                "note": "Skipped lines",
                "lines": [
                    {"skip": True},
                    {"skip": True},
                ],
            },
            headers=_auth_header(token),
        )

        assert response.status_code == 400
        assert response.get_json()["message"] == "At least one line must be received."

    def test_adhoc_receipt_requires_note(self, client, receiving_data):
        token = _login(client, receiving_data["admin_username"])
        response = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": "LS12606204",
                "note": None,
                "lines": [
                    {
                        "order_line_id": None,
                        "article_id": receiving_data["plain_article_id"],
                        "quantity": 1,
                        "uom": receiving_data["plain_uom"],
                    }
                ],
            },
            headers=_auth_header(token),
        )

        assert response.status_code == 400
        assert response.get_json()["message"] == "A note is required for ad-hoc receipts."

    def test_receiving_rejects_removed_line_and_closed_order(
        self, client, app, receiving_data
    ):
        removed_order = _create_order(
            app,
            supplier_id=receiving_data["supplier_id"],
            created_by_id=receiving_data["admin_id"],
            lines=[
                {
                    "article_id": receiving_data["plain_article_id"],
                    "ordered_qty": 2,
                    "uom": receiving_data["plain_uom"],
                    "unit_price": Decimal("1.0000"),
                    "status": OrderLineStatus.REMOVED,
                }
            ],
        )
        closed_order = _create_order(
            app,
            supplier_id=receiving_data["supplier_id"],
            created_by_id=receiving_data["admin_id"],
            status=OrderStatus.CLOSED,
            lines=[
                {
                    "article_id": receiving_data["plain_article_id"],
                    "ordered_qty": 2,
                    "uom": receiving_data["plain_uom"],
                    "unit_price": Decimal("1.0000"),
                }
            ],
        )

        token = _login(client, receiving_data["admin_username"])

        removed_response = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": "LS12606205",
                "lines": [
                    {
                        "order_line_id": removed_order["lines"][0]["id"],
                        "article_id": receiving_data["plain_article_id"],
                        "quantity": 1,
                        "uom": receiving_data["plain_uom"],
                    }
                ],
            },
            headers=_auth_header(token),
        )
        assert removed_response.status_code == 409
        assert removed_response.get_json()["error"] == "ORDER_LINE_REMOVED"

        closed_response = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": "LS12606206",
                "lines": [
                    {
                        "order_line_id": closed_order["lines"][0]["id"],
                        "article_id": receiving_data["plain_article_id"],
                        "quantity": 1,
                        "uom": receiving_data["plain_uom"],
                    }
                ],
            },
            headers=_auth_header(token),
        )
        assert closed_response.status_code == 409
        assert closed_response.get_json()["error"] == "ORDER_CLOSED"

    def test_receiving_existing_batch_same_expiry_increases_stock(
        self, client, app, receiving_data
    ):
        with app.app_context():
            batch = Batch(
                article_id=receiving_data["batch_article_id"],
                batch_code="24001",
                expiry_date=date(2027, 12, 31),
            )
            _db.session.add(batch)
            _db.session.flush()
            _db.session.add(Stock(
                location_id=receiving_data["location_id"],
                article_id=receiving_data["batch_article_id"],
                batch_id=batch.id,
                quantity=Decimal("10.000"),
                uom=receiving_data["batch_uom"],
                average_price=Decimal("5.0000"),
            ))
            _db.session.commit()

        token = _login(client, receiving_data["admin_username"])
        response = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": "LS12606210",
                "note": "Same expiry test",
                "lines": [
                    {
                        "order_line_id": None,
                        "article_id": receiving_data["batch_article_id"],
                        "quantity": 5,
                        "uom": receiving_data["batch_uom"],
                        "batch_code": "24001",
                        "expiry_date": "2027-12-31",
                    }
                ],
            },
            headers=_auth_header(token),
        )

        assert response.status_code == 201
        with app.app_context():
            stock = Stock.query.filter_by(
                article_id=receiving_data["batch_article_id"],
            ).first()
            assert Decimal(str(stock.quantity)) == Decimal("15.000")

    def test_receiving_requires_delivery_note_number(self, client, receiving_data):
        token = _login(client, receiving_data["admin_username"])
        
        # Test None
        response1 = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": None,
                "note": "Missing note number",
                "lines": [
                    {
                        "order_line_id": None,
                        "article_id": receiving_data["plain_article_id"],
                        "quantity": 1,
                        "uom": receiving_data["plain_uom"],
                    }
                ],
            },
            headers=_auth_header(token),
        )
        assert response1.status_code == 400

        # Test missing key entirely
        response2 = client.post(
            "/api/v1/receiving",
            json={
                "note": "Missing note number",
                "lines": [
                    {
                        "order_line_id": None,
                        "article_id": receiving_data["plain_article_id"],
                        "quantity": 1,
                        "uom": receiving_data["plain_uom"],
                    }
                ],
            },
            headers=_auth_header(token),
        )
        assert response2.status_code == 400

        # Test empty string
        response3 = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": "   ",
                "note": "Empty note number",
                "lines": [
                    {
                        "order_line_id": None,
                        "article_id": receiving_data["plain_article_id"],
                        "quantity": 1,
                        "uom": receiving_data["plain_uom"],
                    }
                ],
            },
            headers=_auth_header(token),
        )
        assert response3.status_code == 400


class TestReceivingHistoryAndOrderLookup:
    def test_receiving_history_returns_newest_first_and_adhoc_label(
        self, client, app, receiving_data
    ):
        order = _create_order(
            app,
            supplier_id=receiving_data["supplier_id"],
            created_by_id=receiving_data["admin_id"],
            lines=[
                {
                    "article_id": receiving_data["plain_article_id"],
                    "ordered_qty": 2,
                    "uom": receiving_data["plain_uom"],
                    "unit_price": Decimal("3.0000"),
                }
            ],
        )

        token = _login(client, receiving_data["admin_username"])
        first = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": "LS12606207",
                "lines": [
                    {
                        "order_line_id": order["lines"][0]["id"],
                        "article_id": receiving_data["plain_article_id"],
                        "quantity": 1,
                        "uom": receiving_data["plain_uom"],
                    }
                ],
            },
            headers=_auth_header(token),
        )
        assert first.status_code == 201

        second = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": "LS12606208",
                "note": "Ad-hoc second receipt",
                "lines": [
                    {
                        "order_line_id": None,
                        "article_id": receiving_data["plain_article_id"],
                        "quantity": 2,
                        "uom": receiving_data["plain_uom"],
                    }
                ],
            },
            headers=_auth_header(token),
        )
        assert second.status_code == 201

        history = client.get(
            "/api/v1/receiving?page=1&per_page=50",
            headers=_auth_header(token),
        )
        assert history.status_code == 200
        data = history.get_json()
        assert data["total"] == 2
        assert data["items"][0]["delivery_note_number"] == "LS12606208"
        assert data["items"][0]["order_number"] == "Ad-hoc"
        assert data["items"][1]["order_number"] == order["order_number"]
        assert data["items"][1]["received_by"] == receiving_data["admin_username"]

    def test_order_lookup_and_detail_return_receiving_fields(
        self, client, app, receiving_data
    ):
        order = _create_order(
            app,
            supplier_id=receiving_data["supplier_id"],
            created_by_id=receiving_data["admin_id"],
            lines=[
                {
                    "article_id": receiving_data["batch_article_id"],
                    "ordered_qty": 10,
                    "received_qty": 4,
                    "uom": receiving_data["batch_uom"],
                    "unit_price": Decimal("7.2500"),
                    "delivery_date": date(2026, 5, 5),
                    "status": OrderLineStatus.OPEN,
                },
                {
                    "article_id": receiving_data["plain_article_id"],
                    "ordered_qty": 2,
                    "received_qty": 2,
                    "uom": receiving_data["plain_uom"],
                    "unit_price": Decimal("1.5000"),
                    "status": OrderLineStatus.CLOSED,
                },
                {
                    "article_id": receiving_data["plain_article_id"],
                    "ordered_qty": 3,
                    "received_qty": 0,
                    "uom": receiving_data["plain_uom"],
                    "unit_price": Decimal("1.7000"),
                    "status": OrderLineStatus.REMOVED,
                },
            ],
        )

        token = _login(client, receiving_data["admin_username"])
        lookup = client.get(
            f"/api/v1/orders?q={order['order_number']}",
            headers=_auth_header(token),
        )
        assert lookup.status_code == 200
        lookup_body = lookup.get_json()
        assert lookup_body["id"] == order["id"]
        assert lookup_body["order_number"] == order["order_number"]
        assert lookup_body["open_line_count"] == 1
        assert lookup_body["status"] == "OPEN"

        detail = client.get(
            f"/api/v1/orders/{order['id']}?view=receiving",
            headers=_auth_header(token),
        )
        assert detail.status_code == 200
        detail_body = detail.get_json()
        assert detail_body["id"] == order["id"]
        assert detail_body["supplier_name"] == "Receiving Supplier"
        assert len(detail_body["lines"]) == 1
        line = detail_body["lines"][0]
        assert line["article_id"] == receiving_data["batch_article_id"]
        assert line["article_no"] == receiving_data["batch_article_no"]
        assert line["description"] == "Receiving batch article"
        assert line["has_batch"] is True
        assert line["ordered_qty"] == 10.0
        assert line["received_qty"] == 4.0
        assert line["remaining_qty"] == 6.0
        assert line["is_open"] is True
        assert line["uom"] == receiving_data["batch_uom"]
        assert line["unit_price"] == 7.25
        assert line["delivery_date"] == "2026-05-05"

    def test_order_lookup_not_found_returns_404(self, client, receiving_data):
        token = _login(client, receiving_data["admin_username"])
        response = client.get(
            "/api/v1/orders?q=DOES-NOT-EXIST",
            headers=_auth_header(token),
        )
        assert response.status_code == 404
        assert response.get_json()["error"] == "ORDER_NOT_FOUND"


class TestReceivingRbac:
    def test_receiving_is_admin_only_but_orders_get_endpoints_allow_manager(
        self, client, app, receiving_data
    ):
        order = _create_order(
            app,
            supplier_id=receiving_data["supplier_id"],
            created_by_id=receiving_data["admin_id"],
            lines=[
                {
                    "article_id": receiving_data["plain_article_id"],
                    "ordered_qty": 2,
                    "uom": receiving_data["plain_uom"],
                    "unit_price": Decimal("1.0000"),
                    "status": OrderLineStatus.OPEN,
                }
            ],
        )
        manager_token = _login(client, receiving_data["manager_username"])

        receiving_history = client.get(
            "/api/v1/receiving",
            headers=_auth_header(manager_token),
        )
        assert receiving_history.status_code == 403

        order_lookup = client.get(
            f"/api/v1/orders?q={order['order_number']}",
            headers=_auth_header(manager_token),
        )
        assert order_lookup.status_code == 200

        order_detail = client.get(
            f"/api/v1/orders/{order['id']}?view=receiving",
            headers=_auth_header(manager_token),
        )
        assert order_detail.status_code == 200

        create_receipt = client.post(
            "/api/v1/receiving",
            json={
                "delivery_note_number": "LS12606209",
                "note": "Manager should not be allowed.",
                "lines": [
                    {
                        "order_line_id": None,
                        "article_id": receiving_data["plain_article_id"],
                        "quantity": 1,
                        "uom": receiving_data["plain_uom"],
                    }
                ],
            },
            headers=_auth_header(manager_token),
        )
        assert create_receipt.status_code == 403
