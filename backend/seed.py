"""Idempotent bootstrap seed script.

Run after ``alembic upgrade head`` to populate the initial reference data:
  - Admin user (admin / admin123)
  - UOM catalog (10 entries)
  - Article categories (12 entries)
  - SystemConfig defaults
  - RoleDisplayName defaults

This script is intentionally NOT called from create_app(). Run it explicitly:

    cd backend
    python seed.py

Or with an explicit environment:

    FLASK_ENV=development DATABASE_URL=postgresql://localhost/wms_dev python seed.py

Each seeder function is idempotent — re-running the script is safe.
"""

import os
import sys

# Allow ``python seed.py`` from the backend/ directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models.category import Category
from app.models.enums import UserRole
from app.models.role_display_name import RoleDisplayName
from app.models.system_config import SystemConfig
from app.models.uom_catalog import UomCatalog
from app.models.user import User

load_dotenv()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_admin() -> None:
    """Seed the default admin user if it does not already exist."""
    if User.query.filter_by(username="admin").first():
        print("  [skip] admin user already exists")
        return
    admin = User(
        username="admin",
        password_hash=generate_password_hash("admin123", method="pbkdf2:sha256"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.session.add(admin)
    print("  [seed] admin user created")


def _seed_uom_catalog() -> None:
    """Seed UOM catalog entries (idempotent by code)."""
    entries = [
        ("kg", "kilogram", "kilogram", True),
        ("l", "litra", "litre", True),
        ("kom", "komad", "piece", False),
        ("pak", "pakiranje", "package", False),
        ("m", "metar", "metre", True),
        ("m²", "četvorni metar", "square metre", True),
        ("pár", "par", "pair", False),
        ("g", "gram", "gram", True),
        ("ml", "mililitar", "millilitre", True),
        ("t", "tona", "tonne", True),
    ]
    created = 0
    for code, label_hr, label_en, decimal in entries:
        if UomCatalog.query.filter_by(code=code).first():
            continue
        db.session.add(
            UomCatalog(
                code=code,
                label_hr=label_hr,
                label_en=label_en,
                decimal_display=decimal,
            )
        )
        created += 1
    if created:
        print(f"  [seed] {created} UOM entries created")
    else:
        print("  [skip] UOM catalog already seeded")


def _seed_categories() -> None:
    """Seed article categories (idempotent by key)."""
    entries = [
        ("equipment_installations", "Oprema i instalacije", "Equipment & Installations", False),
        ("safety_equipment", "Zaštitna oprema", "Safety Equipment", True),
        ("operational_supplies", "Operativni potrošni materijal", "Operational Supplies", False),
        ("spare_parts_small_parts", "Rezervni dijelovi", "Spare Parts", False),
        ("auxiliary_operating_materials", "Pomoćna sredstva", "Auxiliary Materials", False),
        ("assembly_material", "Montažni materijal", "Assembly Material", False),
        ("raw_material", "Sirovine", "Raw Material", False),
        ("packaging_material", "Ambalažni materijal", "Packaging Material", False),
        ("goods_merchandise", "Roba za prodaju", "Goods & Merchandise", False),
        ("maintenance_material", "Materijal za održavanje", "Maintenance Material", False),
        ("tools_small_equipment", "Alati i sitna oprema", "Tools & Small Equipment", True),
        ("accessories_small_machines", "Pribor za strojeve", "Machine Accessories", False),
    ]
    created = 0
    for key, label_hr, label_en, is_personal in entries:
        if Category.query.filter_by(key=key).first():
            continue
        db.session.add(
            Category(
                key=key,
                label_hr=label_hr,
                label_en=label_en,
                label_de=None,
                label_hu=None,
                is_personal_issue=is_personal,
                is_active=True,
            )
        )
        created += 1
    if created:
        print(f"  [seed] {created} categories created")
    else:
        print("  [skip] categories already seeded")


def _seed_system_config() -> None:
    """Seed SystemConfig defaults (idempotent by key)."""
    defaults = [
        ("default_language", "hr"),
        ("barcode_format", "Code128"),
        ("barcode_printer", ""),
        ("export_format", "generic"),
    ]
    created = 0
    for key, value in defaults:
        if SystemConfig.query.filter_by(key=key).first():
            continue
        db.session.add(SystemConfig(key=key, value=value))
        created += 1
    if created:
        print(f"  [seed] {created} SystemConfig entries created")
    else:
        print("  [skip] SystemConfig already seeded")


def _seed_role_display_names() -> None:
    """Seed RoleDisplayName defaults (idempotent by role)."""
    defaults = [
        (UserRole.ADMIN, "Admin"),
        (UserRole.MANAGER, "Menadžment"),
        (UserRole.WAREHOUSE_STAFF, "Administracija"),
        (UserRole.VIEWER, "Kontrola"),
        (UserRole.OPERATOR, "Operater"),
    ]
    created = 0
    for role, display_name in defaults:
        if RoleDisplayName.query.filter_by(role=role).first():
            continue
        db.session.add(RoleDisplayName(role=role, display_name=display_name))
        created += 1
    if created:
        print(f"  [seed] {created} RoleDisplayName entries created")
    else:
        print("  [skip] RoleDisplayName already seeded")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_seed() -> None:
    app = create_app()
    with app.app_context():
        print("Running seed...")
        _seed_admin()
        _seed_uom_catalog()
        _seed_categories()
        _seed_system_config()
        _seed_role_display_names()
        db.session.commit()
        print("Seed complete.")


if __name__ == "__main__":
    run_seed()
