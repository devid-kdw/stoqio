"""Wave 5 backend security regression tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from werkzeug.security import generate_password_hash

from app.extensions import db as _db
from app.models.article import Article
from app.models.category import Category
from app.models.enums import UserRole
from app.models.order import Order
from app.models.order_line import OrderLine
from app.models.supplier import Supplier
from app.models.system_config import SystemConfig
from app.models.uom_catalog import UomCatalog
from app.models.user import User
from app.services import barcode_service, order_service, settings_service
from app.services.barcode_service import BarcodeServiceError, generate_label
from app.services.settings_service import SettingsServiceError

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"


def _zpl_hex(value: str) -> str:
    return "".join(f"\\{byte:02X}" for byte in value.encode("utf-8"))


def _ensure_catalog_rows() -> tuple[Category, UomCatalog]:
    category = Category.query.filter_by(key="wave5-security").first()
    if category is None:
        category = Category(
            key="wave5-security",
            label_hr="Wave 5 Security",
            label_en="Wave 5 Security",
            label_de="Wave 5 Security",
            label_hu="Wave 5 Security",
            is_personal_issue=False,
            is_active=True,
        )
        _db.session.add(category)

    uom = UomCatalog.query.filter_by(code="W5PCS").first()
    if uom is None:
        uom = UomCatalog(
            code="W5PCS",
            label_hr="Komad",
            label_en="Piece",
            decimal_display=False,
        )
        _db.session.add(uom)

    _db.session.commit()
    return category, uom


def _make_article(*, article_no: str, description: str) -> Article:
    category, uom = _ensure_catalog_rows()
    article = Article(
        article_no=article_no,
        description=description,
        category_id=category.id,
        base_uom=uom.id,
        has_batch=False,
        is_active=True,
    )
    _db.session.add(article)
    _db.session.commit()
    return article


def _make_admin_user(username: str) -> User:
    user = User(
        username=username,
        password_hash=generate_password_hash("Admin!Pass123", method="pbkdf2:sha256"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    _db.session.add(user)
    _db.session.commit()
    return user


def _make_managed_user(username: str, role: UserRole = UserRole.MANAGER) -> User:
    user = User(
        username=username,
        password_hash=generate_password_hash("Manager!Pass123", method="pbkdf2:sha256"),
        role=role,
        is_active=True,
    )
    _db.session.add(user)
    _db.session.commit()
    return user


def _make_supplier(*, internal_code: str, name: str, address: str) -> Supplier:
    supplier = Supplier(
        internal_code=internal_code,
        name=name,
        address=address,
        is_active=True,
    )
    _db.session.add(supplier)
    _db.session.commit()
    return supplier


def _make_order(
    *,
    order_number: str,
    supplier: Supplier,
    created_by: User,
    article: Article,
) -> Order:
    order = Order(
        order_number=order_number,
        supplier_id=supplier.id,
        supplier_confirmation_number='CONF<123>&"W5"',
        note="Need <b>two</b> lines & one sample.\nPlease confirm.",
        created_by=created_by.id,
    )
    _db.session.add(order)
    _db.session.flush()
    line = OrderLine(
        order_id=order.id,
        article_id=article.id,
        supplier_article_code='SUP<42>&"A"',
        ordered_qty=Decimal("4.000"),
        received_qty=Decimal("0.000"),
        uom="W5PCS",
        unit_price=Decimal("12.3400"),
        delivery_date=date(2026, 4, 8),
        note="Line <note> & more",
    )
    _db.session.add(line)
    _db.session.commit()
    return order


def test_alembic_has_single_head():
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    script = ScriptDirectory.from_config(config)

    heads = script.get_heads()

    assert len(heads) == 1


def test_admin_promotion_requires_password_reset_when_missing():
    actor = _make_admin_user("w5_admin_promote_actor")
    target = _make_managed_user("w5_admin_promote_target")

    with pytest.raises(SettingsServiceError) as exc_info:
        settings_service.update_user(
            target.id,
            {"role": "ADMIN"},
            acting_user_id=actor.id,
        )

    assert exc_info.value.error == "VALIDATION_ERROR"
    assert "password reset" in exc_info.value.message.lower()
    assert "admin" in exc_info.value.message.lower()


def test_admin_promotion_short_password_does_not_dirty_user_role():
    actor = _make_admin_user("w5_admin_promote_actor_short")
    target = _make_managed_user("w5_admin_promote_target_short")

    with pytest.raises(SettingsServiceError):
        settings_service.update_user(
            target.id,
            {"role": "ADMIN", "password": "too-short"},
            acting_user_id=actor.id,
        )

    assert target.role == UserRole.MANAGER
    assert not _db.session.is_modified(target, include_collections=False)


def test_admin_promotion_succeeds_with_admin_minimum_password():
    actor = _make_admin_user("w5_admin_promote_actor_ok")
    target = _make_managed_user("w5_admin_promote_target_ok")

    result = settings_service.update_user(
        target.id,
        {"role": "ADMIN", "password": "Adm1nPass!23"},
        acting_user_id=actor.id,
    )

    assert result["role"] == "ADMIN"
    assert result["username"] == "w5_admin_promote_target_ok"


@pytest.mark.parametrize(
    ("setting_key", "legacy_value"),
    [
        ("label_printer_ip", "8.8.8.8"),
        ("label_printer_port", "80"),
    ],
)
def test_direct_print_revalidates_persisted_printer_settings(
    setting_key: str,
    legacy_value: str,
):
    article = _make_article(
        article_no=f"W5-ART-PRN-{setting_key}",
        description="Printer validation article",
    )
    settings_service.update_barcode_settings(
        {
            "barcode_format": "Code128",
            "barcode_printer": "",
            "label_printer_ip": "192.168.10.50",
            "label_printer_port": 9100,
            "label_printer_model": "zebra_zpl",
        }
    )
    row = SystemConfig.query.filter_by(key=setting_key).one()
    row.value = legacy_value
    _db.session.commit()

    with patch("app.services.barcode_service._send_to_printer") as mock_send:
        with pytest.raises(BarcodeServiceError) as exc_info:
            barcode_service.print_article_label(article.id)

    assert exc_info.value.error == "VALIDATION_ERROR"
    mock_send.assert_not_called()


def test_generate_label_escapes_user_controlled_fields():
    result = generate_label(
        "zebra_zpl",
        article_no="ART^01\nW5",
        description="Desc~\r\n<danger>",
        barcode_value="123^456~789",
        batch_code="BATCH\r\n1",
    ).decode("utf-8")

    assert "^FH\\^FD" in result
    assert "ART^01" not in result
    assert "Desc~" not in result
    assert "123^456" not in result
    assert "BATCH\r\n1" not in result
    assert "\\5E" in result
    assert "\\7E" in result
    assert "\\0D" in result
    assert "\\0A" in result


def test_order_pdf_escapes_markup_like_text():
    creator = _make_admin_user("w5_order_pdf_creator")
    supplier = _make_supplier(
        internal_code="W5-SUP-001",
        name='Acme <Supply> & Co.',
        address="Line 1 & Line 2\nSuite <12>",
    )
    article = _make_article(
        article_no="W5-ORD-ART-001",
        description='Order <article> & "description"',
    )
    order = _make_order(
        order_number="ORD-W5-001",
        supplier=supplier,
        created_by=creator,
        article=article,
    )

    paragraph_texts: list[str] = []
    real_paragraph = order_service.Paragraph

    def recording_paragraph(text, style, *args, **kwargs):
        paragraph_texts.append(text)
        return real_paragraph(text, style, *args, **kwargs)

    with patch("app.services.order_service.Paragraph", side_effect=recording_paragraph):
        pdf_bytes, order_number = order_service.generate_order_pdf(order.id)

    assert order_number == "ORD-W5-001"
    assert pdf_bytes
    assert "Acme &lt;Supply&gt; &amp; Co." in paragraph_texts
    assert "Supplier confirmation number: CONF&lt;123&gt;&amp;\"W5\"" in paragraph_texts
    assert "Need &lt;b&gt;two&lt;/b&gt; lines &amp; one sample.\nPlease confirm." in paragraph_texts
