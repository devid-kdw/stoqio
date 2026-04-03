"""Integration tests for the Phase 8 Orders backend."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db as _db
from app.models.article import Article
from app.models.article_supplier import ArticleSupplier
from app.models.batch import Batch
from app.models.category import Category
from app.models.enums import OrderLineStatus, OrderStatus, TxType, UserRole
from app.models.order import Order
from app.models.order_line import OrderLine
from app.models.receiving import Receiving
from app.models.stock import Stock
from app.models.supplier import Supplier
from app.models.system_config import SystemConfig
from app.models.transaction import Transaction
from app.models.uom_catalog import UomCatalog
from app.models.user import User


@pytest.fixture(scope="module")
def orders_data(app):
    """Seed static supplier/article/user data for orders tests."""
    with app.app_context():
        qty_uom = UomCatalog.query.filter_by(code="okg").first()
        if qty_uom is None:
            qty_uom = UomCatalog(
                code="okg",
                label_hr="orders kilogram",
                label_en="orders kilogram",
                decimal_display=True,
            )
            _db.session.add(qty_uom)

        piece_uom = UomCatalog.query.filter_by(code="okom").first()
        if piece_uom is None:
            piece_uom = UomCatalog(
                code="okom",
                label_hr="orders piece",
                label_en="orders piece",
                decimal_display=False,
            )
            _db.session.add(piece_uom)

        category = Category.query.filter_by(key="orders_test_cat").first()
        if category is None:
            category = Category(
                key="orders_test_cat",
                label_hr="Orders test category",
                label_en="Orders test category",
                is_active=True,
            )
            _db.session.add(category)

        _db.session.flush()

        supplier = Supplier.query.filter_by(internal_code="ORD-SUP").first()
        if supplier is None:
            supplier = Supplier(
                internal_code="ORD-SUP",
                name="Orders Supplier",
                address="Order Street 1",
                is_active=True,
            )
            _db.session.add(supplier)

        second_supplier = Supplier.query.filter_by(internal_code="ORD-ALT").first()
        if second_supplier is None:
            second_supplier = Supplier(
                internal_code="ORD-ALT",
                name="Alternative Orders Supplier",
                address="Alternate Street 7",
                is_active=True,
            )
            _db.session.add(second_supplier)

        inactive_supplier = Supplier.query.filter_by(internal_code="ORD-INACTIVE").first()
        if inactive_supplier is None:
            inactive_supplier = Supplier(
                internal_code="ORD-INACTIVE",
                name="Inactive Orders Supplier",
                is_active=False,
            )
            _db.session.add(inactive_supplier)

        admin = User.query.filter_by(username="orders_admin").first()
        if admin is None:
            admin = User(
                username="orders_admin",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            _db.session.add(admin)

        manager = User.query.filter_by(username="orders_manager").first()
        if manager is None:
            manager = User(
                username="orders_manager",
                password_hash=generate_password_hash("pass", method="pbkdf2:sha256"),
                role=UserRole.MANAGER,
                is_active=True,
            )
            _db.session.add(manager)

        linked_article = Article.query.filter_by(article_no="ORD-LINKED").first()
        if linked_article is None:
            linked_article = Article(
                article_no="ORD-LINKED",
                description="Linked order article",
                category_id=category.id,
                base_uom=qty_uom.id,
                has_batch=False,
                is_active=True,
            )
            _db.session.add(linked_article)

        plain_article = Article.query.filter_by(article_no="ORD-PLAIN").first()
        if plain_article is None:
            plain_article = Article(
                article_no="ORD-PLAIN",
                description="Plain order article",
                category_id=category.id,
                base_uom=piece_uom.id,
                has_batch=False,
                is_active=True,
            )
            _db.session.add(plain_article)

        inactive_article = Article.query.filter_by(article_no="ORD-INACTIVE").first()
        if inactive_article is None:
            inactive_article = Article(
                article_no="ORD-INACTIVE",
                description="Inactive order article",
                category_id=category.id,
                base_uom=piece_uom.id,
                has_batch=False,
                is_active=False,
            )
            _db.session.add(inactive_article)

        _db.session.flush()

        link = (
            ArticleSupplier.query
            .filter_by(article_id=linked_article.id, supplier_id=supplier.id)
            .first()
        )
        if link is None:
            link = ArticleSupplier(
                article_id=linked_article.id,
                supplier_id=supplier.id,
                supplier_article_code="SUP-LINK-001",
                last_price=Decimal("12.3400"),
                is_preferred=True,
            )
            _db.session.add(link)

        _db.session.commit()
        yield {
            "admin_username": admin.username,
            "admin_id": admin.id,
            "manager_username": manager.username,
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "second_supplier_id": second_supplier.id,
            "inactive_supplier_id": inactive_supplier.id,
            "linked_article_id": linked_article.id,
            "linked_article_no": linked_article.article_no,
            "plain_article_id": plain_article.id,
            "plain_article_no": plain_article.article_no,
            "inactive_article_id": inactive_article.id,
            "qty_uom": qty_uom.code,
            "piece_uom": piece_uom.code,
        }


@pytest.fixture(autouse=True)
def clean_orders_state(app):
    """Reset dynamic order-related tables before every test."""
    with app.app_context():
        _db.session.query(Transaction).delete()
        _db.session.query(Receiving).delete()
        _db.session.query(Stock).delete()
        _db.session.query(Batch).delete()
        _db.session.query(OrderLine).delete()
        _db.session.query(Order).delete()
        _db.session.query(SystemConfig).filter_by(key="order_number_next").delete()
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
        environ_base={"REMOTE_ADDR": f"127.0.10.{octet}"},
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
    lines: list[dict[str, object]],
    order_number: str = "ORD-SEEDED",
    status: OrderStatus = OrderStatus.OPEN,
    created_at: datetime | None = None,
) -> dict[str, object]:
    with app.app_context():
        order = Order(
            order_number=order_number,
            supplier_id=supplier_id,
            supplier_confirmation_number=None,
            status=status,
            note="Seeded order note",
            created_by=created_by_id,
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=created_at or datetime.now(timezone.utc),
        )
        _db.session.add(order)
        _db.session.flush()

        created_lines = []
        for line in lines:
            order_line = OrderLine(
                order_id=order.id,
                article_id=int(line["article_id"]),
                supplier_article_code=line.get("supplier_article_code"),
                ordered_qty=Decimal(str(line["ordered_qty"])),
                received_qty=Decimal(str(line.get("received_qty", 0))),
                uom=str(line["uom"]),
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
            created_lines.append({"id": order_line.id, "status": order_line.status.value})

        _db.session.commit()
        return {
            "id": order.id,
            "order_number": order.order_number,
            "lines": created_lines,
        }


class TestOrdersContracts:
    def test_list_detail_receiving_view_and_lookup_follow_phase8_contract(
        self, client, app, orders_data
    ):
        open_order = _create_order(
            app,
            supplier_id=orders_data["supplier_id"],
            created_by_id=orders_data["admin_id"],
            order_number="ORD-OPEN-1",
            status=OrderStatus.OPEN,
            lines=[
                {
                    "article_id": orders_data["linked_article_id"],
                    "ordered_qty": 10,
                    "received_qty": 4,
                    "uom": orders_data["qty_uom"],
                    "unit_price": Decimal("7.2500"),
                    "delivery_date": date(2026, 5, 5),
                    "status": OrderLineStatus.OPEN,
                    "supplier_article_code": "SUP-LINK-001",
                },
                {
                    "article_id": orders_data["plain_article_id"],
                    "ordered_qty": 2,
                    "received_qty": 2,
                    "uom": orders_data["piece_uom"],
                    "unit_price": Decimal("1.5000"),
                    "status": OrderLineStatus.CLOSED,
                },
                {
                    "article_id": orders_data["plain_article_id"],
                    "ordered_qty": 3,
                    "received_qty": 0,
                    "uom": orders_data["piece_uom"],
                    "unit_price": Decimal("1.7000"),
                    "status": OrderLineStatus.REMOVED,
                    "note": "Removed from active scope",
                },
            ],
        )
        closed_order = _create_order(
            app,
            supplier_id=orders_data["second_supplier_id"],
            created_by_id=orders_data["admin_id"],
            order_number="ORD-CLOSED-1",
            status=OrderStatus.CLOSED,
            lines=[
                {
                    "article_id": orders_data["plain_article_id"],
                    "ordered_qty": 1,
                    "received_qty": 1,
                    "uom": orders_data["piece_uom"],
                    "unit_price": Decimal("4.5000"),
                    "status": OrderLineStatus.CLOSED,
                }
            ],
        )

        manager_token = _login(client, orders_data["manager_username"])

        list_response = client.get(
            "/api/v1/orders?page=1&per_page=50",
            headers=_auth_header(manager_token),
        )
        assert list_response.status_code == 200
        list_body = list_response.get_json()
        assert list_body["total"] == 2
        assert [item["id"] for item in list_body["items"]] == [
            open_order["id"],
            closed_order["id"],
        ]
        assert list_body["items"][0]["order_number"] == "ORD-OPEN-1"
        assert list_body["items"][0]["line_count"] == 3
        assert list_body["items"][0]["total_value"] == 75.5
        assert list_body["items"][1]["status"] == "CLOSED"

        lookup_response = client.get(
            "/api/v1/orders?q=ord-open-1",
            headers=_auth_header(manager_token),
        )
        assert lookup_response.status_code == 200
        lookup_body = lookup_response.get_json()
        assert lookup_body == {
            "id": open_order["id"],
            "order_number": "ORD-OPEN-1",
            "status": "OPEN",
            "supplier_id": orders_data["supplier_id"],
            "supplier_name": orders_data["supplier_name"],
            "open_line_count": 1,
            "created_at": lookup_body["created_at"],
        }

        detail_response = client.get(
            f"/api/v1/orders/{open_order['id']}",
            headers=_auth_header(manager_token),
        )
        assert detail_response.status_code == 200
        detail_body = detail_response.get_json()
        assert detail_body["supplier_address"] == "Order Street 1"
        assert detail_body["total_value"] == 75.5
        assert [line["status"] for line in detail_body["lines"]] == [
            "OPEN",
            "CLOSED",
            "REMOVED",
        ]
        assert [line["position"] for line in detail_body["lines"]] == [1, 2, 3]
        assert detail_body["lines"][2]["total_price"] == 5.1

        receiving_detail = client.get(
            f"/api/v1/orders/{open_order['id']}?view=receiving",
            headers=_auth_header(manager_token),
        )
        assert receiving_detail.status_code == 200
        receiving_body = receiving_detail.get_json()
        assert len(receiving_body["lines"]) == 1
        assert receiving_body["lines"][0]["article_no"] == orders_data["linked_article_no"]
        assert receiving_body["lines"][0]["remaining_qty"] == 6.0

    def test_q_mode_exact_match_and_list_mode_remain_separate_contracts(
        self, client, app, orders_data
    ):
        _create_order(
            app,
            supplier_id=orders_data["supplier_id"],
            created_by_id=orders_data["admin_id"],
            order_number="ORD-CODIFY-1",
            status=OrderStatus.OPEN,
            lines=[
                {
                    "article_id": orders_data["plain_article_id"],
                    "ordered_qty": 1,
                    "uom": orders_data["piece_uom"],
                    "unit_price": 1,
                }
            ],
        )
        _create_order(
            app,
            supplier_id=orders_data["second_supplier_id"],
            created_by_id=orders_data["admin_id"],
            order_number="ORD-CODIFY-2",
            status=OrderStatus.CLOSED,
            lines=[
                {
                    "article_id": orders_data["plain_article_id"],
                    "ordered_qty": 1,
                    "uom": orders_data["piece_uom"],
                    "unit_price": 1,
                    "status": OrderLineStatus.CLOSED,
                }
            ],
        )

        token = _login(client, orders_data["manager_username"])

        exact_match = client.get(
            "/api/v1/orders?q=ORD-CODIFY-1&page=9&per_page=3&status=CLOSED",
            headers=_auth_header(token),
        )
        assert exact_match.status_code == 200
        exact_body = exact_match.get_json()
        assert exact_body["order_number"] == "ORD-CODIFY-1"
        assert "items" not in exact_body

        list_mode = client.get(
            "/api/v1/orders?page=1&per_page=50&status=OPEN",
            headers=_auth_header(token),
        )
        assert list_mode.status_code == 200
        list_body = list_mode.get_json()
        assert list_body["page"] == 1
        assert list_body["per_page"] == 50
        assert isinstance(list_body["items"], list)
        assert list_body["items"]
        assert all(item["status"] == "OPEN" for item in list_body["items"])

    def test_lookup_not_found_and_invalid_view_are_reported(
        self, client, app, orders_data
    ):
        order = _create_order(
            app,
            supplier_id=orders_data["supplier_id"],
            created_by_id=orders_data["admin_id"],
            order_number="ORD-VALIDATE",
            lines=[
                {
                    "article_id": orders_data["plain_article_id"],
                    "ordered_qty": 1,
                    "uom": orders_data["piece_uom"],
                    "unit_price": Decimal("1.0000"),
                }
            ],
        )

        token = _login(client, orders_data["admin_username"])
        missing = client.get(
            "/api/v1/orders?q=DOES-NOT-EXIST",
            headers=_auth_header(token),
        )
        assert missing.status_code == 404
        assert missing.get_json()["error"] == "ORDER_NOT_FOUND"

        invalid_view = client.get(
            f"/api/v1/orders/{order['id']}?view=history",
            headers={**_auth_header(token), "Accept-Language": "en"},
        )
        assert invalid_view.status_code == 400
        assert invalid_view.get_json()["message"] == "view must be 'receiving' when provided."


class TestOrdersMutations:
    def test_create_order_auto_generates_number_and_snapshots_line_values(
        self, client, app, orders_data
    ):
        token = _login(client, orders_data["admin_username"])
        response = client.post(
            "/api/v1/orders",
            json={
                "order_number": "   ",
                "supplier_id": orders_data["supplier_id"],
                "supplier_confirmation_number": None,
                "note": "Created from API",
                "lines": [
                    {
                        "article_id": orders_data["linked_article_id"],
                        "supplier_article_code": "   ",
                        "ordered_qty": 5,
                        "uom": orders_data["qty_uom"],
                        "unit_price": 12.5,
                        "delivery_date": "2026-04-10",
                        "note": "First line",
                    }
                ],
            },
            headers=_auth_header(token),
        )

        assert response.status_code == 201
        body = response.get_json()
        assert body["order_number"] == "ORD-0001"
        assert body["supplier_name"] == orders_data["supplier_name"]
        assert body["total_value"] == 62.5

        with app.app_context():
            saved_order = Order.query.filter_by(order_number="ORD-0001").first()
            assert saved_order is not None
            saved_line = OrderLine.query.filter_by(order_id=saved_order.id).one()
            assert saved_line.supplier_article_code == "SUP-LINK-001"
            assert Decimal(str(saved_line.unit_price)) == Decimal("12.5000")
            assert saved_line.delivery_date.isoformat() == "2026-04-10"
            assert saved_line.note == "First line"

    def test_create_order_manual_number_returns_201(
        self, client, orders_data
    ):
        token = _login(client, orders_data["admin_username"])
        response = client.post(
            "/api/v1/orders",
            json={
                "order_number": "MANUAL-201-XYZ",
                "supplier_id": orders_data["supplier_id"],
                "lines": [
                    {
                        "article_id": orders_data["linked_article_id"],
                        "ordered_qty": 5,
                        "uom": orders_data["qty_uom"],
                        "unit_price": 12.5,
                    }
                ],
            },
            headers=_auth_header(token),
        )

        assert response.status_code == 201
        body = response.get_json()
        assert body["order_number"] == "MANUAL-201-XYZ"

    def test_auto_number_sequence_tracks_manual_ord_numbers_but_not_non_ord_manuals(
        self, client, app, orders_data
    ):
        token = _login(client, orders_data["admin_username"])

        manual_ord = client.post(
            "/api/v1/orders",
            json={
                "order_number": "ORD-0042",
                "supplier_id": orders_data["supplier_id"],
                "lines": [
                    {
                        "article_id": orders_data["linked_article_id"],
                        "ordered_qty": 1,
                        "uom": orders_data["qty_uom"],
                        "unit_price": 10,
                    }
                ],
            },
            headers=_auth_header(token),
        )
        assert manual_ord.status_code == 201
        assert manual_ord.get_json()["order_number"] == "ORD-0042"

        generated_after_ord = client.post(
            "/api/v1/orders",
            json={
                "supplier_id": orders_data["supplier_id"],
                "lines": [
                    {
                        "article_id": orders_data["linked_article_id"],
                        "ordered_qty": 1,
                        "uom": orders_data["qty_uom"],
                        "unit_price": 11,
                    }
                ],
            },
            headers=_auth_header(token),
        )
        assert generated_after_ord.status_code == 201
        assert generated_after_ord.get_json()["order_number"] == "ORD-0043"

        with app.app_context():
            counter = SystemConfig.query.filter_by(key="order_number_next").one()
            assert counter.value == "44"

    def test_auto_number_sequence_starts_at_ord_0001_after_non_ord_manual_number(
        self, client, app, orders_data
    ):
        token = _login(client, orders_data["admin_username"])

        manual_non_ord = client.post(
            "/api/v1/orders",
            json={
                "order_number": "260100",
                "supplier_id": orders_data["supplier_id"],
                "lines": [
                    {
                        "article_id": orders_data["linked_article_id"],
                        "ordered_qty": 1,
                        "uom": orders_data["qty_uom"],
                        "unit_price": 10,
                    }
                ],
            },
            headers=_auth_header(token),
        )
        assert manual_non_ord.status_code == 201
        assert manual_non_ord.get_json()["order_number"] == "260100"

        generated = client.post(
            "/api/v1/orders",
            json={
                "supplier_id": orders_data["supplier_id"],
                "lines": [
                    {
                        "article_id": orders_data["linked_article_id"],
                        "ordered_qty": 1,
                        "uom": orders_data["qty_uom"],
                        "unit_price": 11,
                    }
                ],
            },
            headers=_auth_header(token),
        )
        assert generated.status_code == 201
        assert generated.get_json()["order_number"] == "ORD-0001"

        with app.app_context():
            counter = SystemConfig.query.filter_by(key="order_number_next").one()
            assert counter.value == "2"

    def test_create_order_validates_duplicate_number_supplier_and_uom(
        self, client, app, orders_data
    ):
        _create_order(
            app,
            supplier_id=orders_data["supplier_id"],
            created_by_id=orders_data["admin_id"],
            order_number="MANUAL-42",
            lines=[
                {
                    "article_id": orders_data["plain_article_id"],
                    "ordered_qty": 1,
                    "uom": orders_data["piece_uom"],
                    "unit_price": 1,
                }
            ],
        )
        token = _login(client, orders_data["admin_username"])

        duplicate = client.post(
            "/api/v1/orders",
            json={
                "order_number": "manual-42",
                "supplier_id": orders_data["supplier_id"],
                "lines": [
                    {
                        "article_id": orders_data["plain_article_id"],
                        "ordered_qty": 1,
                        "uom": orders_data["piece_uom"],
                        "unit_price": 1,
                    }
                ],
            },
            headers=_auth_header(token),
        )
        assert duplicate.status_code == 409
        assert duplicate.get_json()["error"] == "ORDER_NUMBER_EXISTS"

        inactive_supplier = client.post(
            "/api/v1/orders",
            json={
                "supplier_id": orders_data["inactive_supplier_id"],
                "lines": [
                    {
                        "article_id": orders_data["plain_article_id"],
                        "ordered_qty": 1,
                        "uom": orders_data["piece_uom"],
                        "unit_price": 1,
                    }
                ],
            },
            headers=_auth_header(token),
        )
        assert inactive_supplier.status_code == 404
        assert inactive_supplier.get_json()["error"] == "SUPPLIER_NOT_FOUND"

        uom_mismatch = client.post(
            "/api/v1/orders",
            json={
                "supplier_id": orders_data["supplier_id"],
                "lines": [
                    {
                        "article_id": orders_data["plain_article_id"],
                        "ordered_qty": 1,
                        "uom": orders_data["qty_uom"],
                        "unit_price": 1,
                    }
                ],
            },
            headers=_auth_header(token),
        )
        assert uom_mismatch.status_code == 400
        assert uom_mismatch.get_json()["error"] == "UOM_MISMATCH"

    def test_header_and_line_mutations_recalculate_status_and_close_order(
        self, client, app, orders_data
    ):
        order = _create_order(
            app,
            supplier_id=orders_data["supplier_id"],
            created_by_id=orders_data["admin_id"],
            order_number="ORD-MUTATE",
            lines=[
                {
                    "article_id": orders_data["linked_article_id"],
                    "ordered_qty": 5,
                    "received_qty": 4,
                    "uom": orders_data["qty_uom"],
                    "unit_price": 7.25,
                    "status": OrderLineStatus.OPEN,
                },
                {
                    "article_id": orders_data["plain_article_id"],
                    "ordered_qty": 2,
                    "received_qty": 0,
                    "uom": orders_data["piece_uom"],
                    "unit_price": 3,
                    "status": OrderLineStatus.OPEN,
                },
            ],
        )
        token = _login(client, orders_data["admin_username"])

        header_response = client.patch(
            f"/api/v1/orders/{order['id']}",
            json={
                "supplier_confirmation_number": "SUP-7781",
                "note": "Deliver in two batches.",
            },
            headers=_auth_header(token),
        )
        assert header_response.status_code == 200
        assert header_response.get_json()["supplier_confirmation_number"] == "SUP-7781"

        add_line_response = client.post(
            f"/api/v1/orders/{order['id']}/lines",
            json={
                "article_id": orders_data["plain_article_id"],
                "ordered_qty": 1,
                "uom": orders_data["piece_uom"],
                "unit_price": 4.2,
            },
            headers=_auth_header(token),
        )
        assert add_line_response.status_code == 200
        added_line = add_line_response.get_json()["lines"][2]

        line_update_response = client.patch(
            f"/api/v1/orders/{order['id']}/lines/{order['lines'][0]['id']}",
            json={
                "ordered_qty": 4,
                "unit_price": 8.0,
                "note": "Supplier confirmed exact quantity.",
            },
            headers=_auth_header(token),
        )
        assert line_update_response.status_code == 200
        updated_line = line_update_response.get_json()["lines"][0]
        assert updated_line["status"] == "CLOSED"
        assert updated_line["total_price"] == 32.0

        remove_second = client.delete(
            f"/api/v1/orders/{order['id']}/lines/{order['lines'][1]['id']}",
            headers=_auth_header(token),
        )
        assert remove_second.status_code == 200
        assert remove_second.get_json()["lines"][1]["status"] == "REMOVED"

        remove_third = client.delete(
            f"/api/v1/orders/{order['id']}/lines/{added_line['id']}",
            headers=_auth_header(token),
        )
        assert remove_third.status_code == 200
        final_body = remove_third.get_json()
        assert final_body["status"] == "CLOSED"

        with app.app_context():
            saved_order = _db.session.get(Order, order["id"])
            assert saved_order.status == OrderStatus.CLOSED

        closed_edit = client.patch(
            f"/api/v1/orders/{order['id']}",
            json={"note": "Should fail"},
            headers=_auth_header(token),
        )
        assert closed_edit.status_code == 400
        assert closed_edit.get_json()["error"] == "ORDER_CLOSED"


class TestOrdersLookupsAndPdf:
    def test_supplier_and_article_lookups_filter_active_records_and_return_defaults(
        self, client, orders_data
    ):
        manager_token = _login(client, orders_data["manager_username"])

        suppliers = client.get(
            "/api/v1/orders/lookups/suppliers?q=ord",
            headers=_auth_header(manager_token),
        )
        assert suppliers.status_code == 200
        supplier_codes = [item["internal_code"] for item in suppliers.get_json()["items"]]
        assert "ORD-SUP" in supplier_codes
        assert "ORD-ALT" in supplier_codes
        assert "ORD-INACTIVE" not in supplier_codes

        articles = client.get(
            f"/api/v1/orders/lookups/articles?q=order&supplier_id={orders_data['supplier_id']}",
            headers=_auth_header(manager_token),
        )
        assert articles.status_code == 200
        article_items = {item["article_no"]: item for item in articles.get_json()["items"]}
        assert "ORD-LINKED" in article_items
        assert article_items["ORD-LINKED"]["supplier_article_code"] == "SUP-LINK-001"
        assert article_items["ORD-LINKED"]["last_price"] == 12.34
        assert "ORD-INACTIVE" not in article_items

    def test_pdf_endpoint_returns_pdf_and_manager_is_read_only_for_mutations(
        self, client, app, orders_data
    ):
        order = _create_order(
            app,
            supplier_id=orders_data["supplier_id"],
            created_by_id=orders_data["admin_id"],
            order_number="ORD-PDF",
            lines=[
                {
                    "article_id": orders_data["linked_article_id"],
                    "ordered_qty": 2,
                    "uom": orders_data["qty_uom"],
                    "unit_price": 9.99,
                    "status": OrderLineStatus.OPEN,
                    "supplier_article_code": "SUP-LINK-001",
                }
            ],
        )

        manager_token = _login(client, orders_data["manager_username"])
        pdf = client.get(
            f"/api/v1/orders/{order['id']}/pdf",
            headers=_auth_header(manager_token),
        )
        assert pdf.status_code == 200
        assert pdf.mimetype == "application/pdf"
        assert pdf.data.startswith(b"%PDF")

        manager_create = client.post(
            "/api/v1/orders",
            json={
                "supplier_id": orders_data["supplier_id"],
                "lines": [
                    {
                        "article_id": orders_data["plain_article_id"],
                        "ordered_qty": 1,
                        "uom": orders_data["piece_uom"],
                        "unit_price": 1,
                    }
                ],
            },
            headers=_auth_header(manager_token),
        )
        assert manager_create.status_code == 403

        manager_patch = client.patch(
            f"/api/v1/orders/{order['id']}",
            json={"note": "Nope"},
            headers=_auth_header(manager_token),
        )
        assert manager_patch.status_code == 403

        manager_delete = client.delete(
            f"/api/v1/orders/{order['id']}/lines/{order['lines'][0]['id']}",
            headers=_auth_header(manager_token),
        )
        assert manager_delete.status_code == 403


class TestOrdersStatusFilter:
    def test_status_open_returns_only_open_orders(self, client, app, orders_data):
        _create_order(
            app,
            supplier_id=orders_data["supplier_id"],
            created_by_id=orders_data["admin_id"],
            order_number="ORD-STAT-OPEN",
            status=OrderStatus.OPEN,
            lines=[
                {
                    "article_id": orders_data["plain_article_id"],
                    "ordered_qty": 1,
                    "uom": orders_data["piece_uom"],
                    "unit_price": 1,
                }
            ],
        )
        _create_order(
            app,
            supplier_id=orders_data["supplier_id"],
            created_by_id=orders_data["admin_id"],
            order_number="ORD-STAT-CLOSED",
            status=OrderStatus.CLOSED,
            lines=[
                {
                    "article_id": orders_data["plain_article_id"],
                    "ordered_qty": 1,
                    "uom": orders_data["piece_uom"],
                    "unit_price": 1,
                    "status": OrderLineStatus.CLOSED,
                }
            ],
        )
        token = _login(client, orders_data["admin_username"])
        response = client.get(
            "/api/v1/orders?status=OPEN&per_page=200",
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        body = response.get_json()
        statuses = {item["status"] for item in body["items"]}
        assert statuses == {"OPEN"}
        assert body["total"] >= 1

    def test_status_closed_returns_only_closed_orders(self, client, app, orders_data):
        _create_order(
            app,
            supplier_id=orders_data["supplier_id"],
            created_by_id=orders_data["admin_id"],
            order_number="ORD-FC-OPEN",
            status=OrderStatus.OPEN,
            lines=[
                {
                    "article_id": orders_data["plain_article_id"],
                    "ordered_qty": 1,
                    "uom": orders_data["piece_uom"],
                    "unit_price": 1,
                }
            ],
        )
        _create_order(
            app,
            supplier_id=orders_data["supplier_id"],
            created_by_id=orders_data["admin_id"],
            order_number="ORD-FC-CLOSED",
            status=OrderStatus.CLOSED,
            lines=[
                {
                    "article_id": orders_data["plain_article_id"],
                    "ordered_qty": 1,
                    "uom": orders_data["piece_uom"],
                    "unit_price": 1,
                    "status": OrderLineStatus.CLOSED,
                }
            ],
        )
        token = _login(client, orders_data["admin_username"])
        response = client.get(
            "/api/v1/orders?status=CLOSED&per_page=200",
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        body = response.get_json()
        statuses = {item["status"] for item in body["items"]}
        assert statuses == {"CLOSED"}
        assert body["total"] >= 1

    def test_invalid_status_returns_400(self, client, orders_data):
        token = _login(client, orders_data["admin_username"])
        response = client.get(
            "/api/v1/orders?status=PENDING",
            headers=_auth_header(token),
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "VALIDATION_ERROR"

    def test_q_param_ignores_status_and_returns_exact_match(
        self, client, app, orders_data
    ):
        _create_order(
            app,
            supplier_id=orders_data["supplier_id"],
            created_by_id=orders_data["admin_id"],
            order_number="ORD-Q-COMPAT",
            status=OrderStatus.OPEN,
            lines=[
                {
                    "article_id": orders_data["plain_article_id"],
                    "ordered_qty": 1,
                    "uom": orders_data["piece_uom"],
                    "unit_price": 1,
                }
            ],
        )
        token = _login(client, orders_data["admin_username"])
        response = client.get(
            "/api/v1/orders?q=ORD-Q-COMPAT",
            headers=_auth_header(token),
        )
        assert response.status_code == 200
        body = response.get_json()
        # Exact-match mode returns single object, not paginated list
        assert body["order_number"] == "ORD-Q-COMPAT"
        assert "items" not in body
