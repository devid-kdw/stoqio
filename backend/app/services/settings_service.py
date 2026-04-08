"""Business logic for the Phase 14 Settings module."""

from __future__ import annotations

import ipaddress
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import joinedload
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.annual_quota import AnnualQuota
from app.models.article import Article
from app.models.category import Category
from app.models.enums import QuotaEnforcement, UserRole
from app.models.location import Location
from app.models.role_display_name import RoleDisplayName
from app.models.supplier import Supplier
from app.models.system_config import SystemConfig
from app.models.uom_catalog import UomCatalog
from app.models.user import User
from app.utils.validators import validate_note

_INITIAL_LOCATION_ID = 1
_DEFAULT_LANGUAGE = "hr"
_DEFAULT_BARCODE_FORMAT = "Code128"
_DEFAULT_BARCODE_PRINTER = ""
_DEFAULT_EXPORT_FORMAT = "generic"
_DEFAULT_LABEL_PRINTER_IP = ""
_DEFAULT_LABEL_PRINTER_PORT = "9100"
_DEFAULT_LABEL_PRINTER_MODEL = "zebra_zpl"
_ALLOWED_PRINTER_MODELS = {"zebra_zpl"}
_DEFAULT_SYSTEM_CONFIG = {
    "default_language": _DEFAULT_LANGUAGE,
    "barcode_format": _DEFAULT_BARCODE_FORMAT,
    "barcode_printer": _DEFAULT_BARCODE_PRINTER,
    "export_format": _DEFAULT_EXPORT_FORMAT,
    "label_printer_ip": _DEFAULT_LABEL_PRINTER_IP,
    "label_printer_port": _DEFAULT_LABEL_PRINTER_PORT,
    "label_printer_model": _DEFAULT_LABEL_PRINTER_MODEL,
}
_ROLE_ORDER = (
    UserRole.ADMIN,
    UserRole.MANAGER,
    UserRole.WAREHOUSE_STAFF,
    UserRole.VIEWER,
    UserRole.OPERATOR,
)
_ROLE_DEFAULTS = {
    UserRole.ADMIN: "Admin",
    UserRole.MANAGER: "Menadžment",
    UserRole.WAREHOUSE_STAFF: "Administracija",
    UserRole.VIEWER: "Kontrola",
    UserRole.OPERATOR: "Operater",
}
_ALLOWED_LANGUAGES = {"hr", "en", "de", "hu"}
_ALLOWED_BARCODE_FORMATS = {"EAN-13", "Code128"}
_ALLOWED_EXPORT_FORMATS = {"generic", "sap"}
# Ports permitted for label-printer raw socket connections.
# Extend this set if a future supported printer model requires a different port.
_ALLOWED_LABEL_PRINTER_PORTS: frozenset[int] = frozenset({9100})
_ALLOWED_LABEL_PRINTER_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)
_QUOTA_SCOPE_GLOBAL_ARTICLE = "GLOBAL_ARTICLE_OVERRIDE"
_QUOTA_SCOPE_JOB_TITLE_CATEGORY = "JOB_TITLE_CATEGORY_DEFAULT"


class SettingsServiceError(Exception):
    """Structured service error that maps directly to API responses."""

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


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(Decimal(str(value)))


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    text = value.strip()
    return text or None


def _require_text(
    value: Any,
    *,
    field_name: str,
    max_length: int | None = None,
    details: dict[str, Any] | None = None,
) -> str:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"{field_name} is required.",
            400,
            {**(details or {}), "_msg_key": "FIELD_REQUIRED", "field": field_name},
        )
    if max_length is not None and len(normalized) > max_length:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be {max_length} characters or fewer.",
            400,
            {**(details or {}), "_msg_key": "FIELD_TOO_LONG", "field": field_name, "max_length": max_length},
        )
    return normalized


def _validate_optional_text(
    value: Any,
    *,
    field_name: str,
    max_length: int | None = None,
) -> str | None:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    if max_length is not None and len(normalized) > max_length:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be {max_length} characters or fewer.",
            400,
        )
    return normalized


def _parse_bool(value: Any, *, field_name: str, default: bool | None = None) -> bool:
    if value is None:
        if default is None:
            raise SettingsServiceError(
                "VALIDATION_ERROR",
                f"{field_name} is required.",
                400,
            )
        return default

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False

    raise SettingsServiceError(
        "VALIDATION_ERROR",
        f"{field_name} must be 'true' or 'false'.",
        400,
    )


def _parse_positive_decimal(value: Any, *, field_name: str) -> Decimal:
    if value in (None, ""):
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"{field_name} is required.",
            400,
        )
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be a valid number.",
            400,
        ) from None
    if parsed <= 0:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be greater than 0.",
            400,
        )
    return parsed


def _parse_optional_int(value: Any, *, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be a valid integer.",
            400,
        ) from None


def _parse_reset_month(value: Any) -> int:
    if value in (None, ""):
        return 1
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "reset_month must be a valid integer.",
            400,
        ) from None
    if parsed < 1 or parsed > 12:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "reset_month must be between 1 and 12.",
            400,
        )
    return parsed


def _parse_user_role(value: Any, *, field_name: str = "role") -> UserRole:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"{field_name} is required.",
            400,
        )
    try:
        return UserRole(normalized.upper())
    except ValueError:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"{field_name} must be one of: {', '.join(role.value for role in _ROLE_ORDER)}.",
            400,
        ) from None


def _parse_quota_enforcement(value: Any) -> QuotaEnforcement:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return QuotaEnforcement.WARN
    try:
        return QuotaEnforcement(normalized.upper())
    except ValueError:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "enforcement must be WARN or BLOCK.",
            400,
        ) from None


def _validate_allowed_fields(
    payload: dict[str, Any],
    *,
    allowed_fields: set[str],
) -> None:
    extra_fields = sorted(set(payload.keys()) - allowed_fields)
    if extra_fields:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"Unsupported fields: {', '.join(extra_fields)}.",
            400,
            {"fields": extra_fields},
        )


def _settings_location_or_404() -> Location:
    location = db.session.get(Location, _INITIAL_LOCATION_ID)
    if location is None:
        raise SettingsServiceError(
            "LOCATION_NOT_FOUND",
            "Location not found.",
            404,
            {"location_id": _INITIAL_LOCATION_ID},
        )
    return location


def _system_config_value(key: str) -> str:
    row = db.session.query(SystemConfig).filter_by(key=key).first()
    if row is None:
        return _DEFAULT_SYSTEM_CONFIG[key]
    return row.value


def _set_system_config_value(key: str, value: str) -> SystemConfig:
    row = db.session.query(SystemConfig).filter_by(key=key).first()
    if row is None:
        row = SystemConfig(key=key, value=value, updated_at=_now_utc())
        db.session.add(row)
    else:
        row.value = value
        row.updated_at = _now_utc()
    return row


def _role_display_name_map() -> dict[UserRole, str]:
    rows = db.session.query(RoleDisplayName).all()
    result = {row.role: row.display_name for row in rows}
    for role in _ROLE_ORDER:
        result.setdefault(role, _ROLE_DEFAULTS[role])
    return result


def _find_or_create_role_display_name(role: UserRole) -> RoleDisplayName:
    row = db.session.query(RoleDisplayName).filter_by(role=role).first()
    if row is None:
        row = RoleDisplayName(role=role, display_name=_ROLE_DEFAULTS[role])
        db.session.add(row)
    return row


def _serialize_role_row(role: UserRole, display_name: str) -> dict[str, Any]:
    return {"role": role.value, "display_name": display_name}


def _serialize_uom(uom: UomCatalog) -> dict[str, Any]:
    return {
        "id": uom.id,
        "code": uom.code,
        "label_hr": uom.label_hr,
        "label_en": uom.label_en,
        "decimal_display": uom.decimal_display,
    }


def _serialize_category(category: Category) -> dict[str, Any]:
    return {
        "id": category.id,
        "key": category.key,
        "label_hr": category.label_hr,
        "label_en": category.label_en,
        "is_personal_issue": category.is_personal_issue,
    }


def _serialize_quota_scope(quota: AnnualQuota) -> str:
    if quota.article_id is not None and quota.employee_id is None:
        return _QUOTA_SCOPE_GLOBAL_ARTICLE
    return _QUOTA_SCOPE_JOB_TITLE_CATEGORY


def _serialize_quota(quota: AnnualQuota) -> dict[str, Any]:
    article = quota.article
    category = quota.category or (article.category if article and article.category else None)
    return {
        "id": quota.id,
        "scope": _serialize_quota_scope(quota),
        "job_title": quota.job_title,
        "article_id": quota.article_id,
        "article_no": article.article_no if article else None,
        "article_description": article.description if article else None,
        "category_id": category.id if category else None,
        "category_key": category.key if category else None,
        "category_label_hr": category.label_hr if category else None,
        "category_label_en": category.label_en if category else None,
        "quantity": _to_float(quota.quantity),
        "uom": quota.uom,
        "enforcement": _enum_value(quota.enforcement),
        "reset_month": quota.reset_month,
    }


def _serialize_supplier(supplier: Supplier) -> dict[str, Any]:
    return {
        "id": supplier.id,
        "internal_code": supplier.internal_code,
        "name": supplier.name,
        "contact_person": supplier.contact_person,
        "phone": supplier.phone,
        "email": supplier.email,
        "address": supplier.address,
        "iban": supplier.iban,
        "note": supplier.note,
        "is_active": supplier.is_active,
        "created_at": supplier.created_at.isoformat() if supplier.created_at else None,
    }


def _serialize_user(user: User, *, role_names: dict[UserRole, str]) -> dict[str, Any]:
    role = user.role if isinstance(user.role, UserRole) else UserRole(str(user.role))
    return {
        "id": user.id,
        "username": user.username,
        "role": role.value,
        "role_display_name": role_names.get(role, _ROLE_DEFAULTS[role]),
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _supplier_or_404(supplier_id: int) -> Supplier:
    supplier = db.session.get(Supplier, supplier_id)
    if supplier is None:
        raise SettingsServiceError("SUPPLIER_NOT_FOUND", "Supplier not found.", 404)
    return supplier


def _user_or_404(user_id: int) -> User:
    user = db.session.get(User, user_id)
    if user is None:
        raise SettingsServiceError("USER_NOT_FOUND", "User not found.", 404)
    return user


def _settings_quota_or_404(quota_id: int) -> AnnualQuota:
    quota = (
        db.session.query(AnnualQuota)
        .options(
            joinedload(AnnualQuota.article).joinedload(Article.category),
            joinedload(AnnualQuota.category),
        )
        .filter(AnnualQuota.id == quota_id, AnnualQuota.employee_id.is_(None))
        .first()
    )
    if quota is None:
        raise SettingsServiceError("QUOTA_NOT_FOUND", "Quota not found.", 404)
    if quota.article_id is None and (quota.job_title is None or quota.category_id is None):
        raise SettingsServiceError("QUOTA_NOT_FOUND", "Quota not found.", 404)
    return quota


def _parse_roles_payload(payload: Any) -> dict[UserRole, str]:
    raw_items: Any
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        if "roles" in payload:
            raw_items = payload["roles"]
        elif "items" in payload:
            raw_items = payload["items"]
        else:
            raw_items = [
                {"role": role_name, "display_name": display_name}
                for role_name, display_name in payload.items()
            ]
    else:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "Role payload must be a list or object.",
            400,
        )

    if not isinstance(raw_items, list):
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "Role payload must be a list.",
            400,
        )

    parsed: dict[UserRole, str] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            raise SettingsServiceError(
                "VALIDATION_ERROR",
                "Each role entry must be an object.",
                400,
            )
        role = _parse_user_role(item.get("role"))
        display_name = _require_text(
            item.get("display_name"),
            field_name="display_name",
            max_length=50,
            details={"role": role.value},
        )
        if role in parsed:
            raise SettingsServiceError(
                "VALIDATION_ERROR",
                f"Duplicate role entry for {role.value}.",
                400,
            )
        parsed[role] = display_name

    missing_roles = [role.value for role in _ROLE_ORDER if role not in parsed]
    if missing_roles:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "All five system roles must be provided.",
            400,
            {"missing_roles": missing_roles},
        )

    return parsed


def _parse_quota_scope(value: Any) -> str | None:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None

    aliases = {
        "ARTICLE": _QUOTA_SCOPE_GLOBAL_ARTICLE,
        "GLOBAL_ARTICLE_OVERRIDE": _QUOTA_SCOPE_GLOBAL_ARTICLE,
        "CATEGORY": _QUOTA_SCOPE_JOB_TITLE_CATEGORY,
        "JOB_TITLE_CATEGORY": _QUOTA_SCOPE_JOB_TITLE_CATEGORY,
        "JOB_TITLE_CATEGORY_DEFAULT": _QUOTA_SCOPE_JOB_TITLE_CATEGORY,
    }
    canonical = aliases.get(normalized.upper())
    if canonical is None:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "scope must be GLOBAL_ARTICLE_OVERRIDE or JOB_TITLE_CATEGORY_DEFAULT.",
            400,
        )
    return canonical


def _prepare_quota_payload(payload: dict[str, Any]) -> dict[str, Any]:
    _validate_allowed_fields(
        payload,
        allowed_fields={
            "scope",
            "job_title",
            "category_id",
            "article_id",
            "employee_id",
            "quantity",
            "uom",
            "reset_month",
            "enforcement",
        },
    )

    requested_scope = _parse_quota_scope(payload.get("scope"))
    job_title = _normalize_optional_text(payload.get("job_title"))
    category_id = _parse_optional_int(payload.get("category_id"), field_name="category_id")
    article_id = _parse_optional_int(payload.get("article_id"), field_name="article_id")
    employee_id = _parse_optional_int(payload.get("employee_id"), field_name="employee_id")
    quantity = _parse_positive_decimal(payload.get("quantity"), field_name="quantity")
    uom = _require_text(payload.get("uom"), field_name="uom")
    reset_month = _parse_reset_month(payload.get("reset_month"))
    enforcement = _parse_quota_enforcement(payload.get("enforcement"))

    if employee_id is not None:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "Settings quotas cannot target employee-specific overrides.",
            400,
        )

    if UomCatalog.query.filter_by(code=uom).first() is None:
        raise SettingsServiceError("UOM_NOT_FOUND", "UOM not found.", 400, {"uom": uom})

    scope: str
    if article_id is not None and job_title is None and category_id is None:
        article = db.session.get(Article, article_id)
        if article is None:
            raise SettingsServiceError("ARTICLE_NOT_FOUND", "Article not found.", 400)
        scope = _QUOTA_SCOPE_GLOBAL_ARTICLE
        category = None
    elif article_id is None and job_title is not None and category_id is not None:
        category = db.session.get(Category, category_id)
        if category is None:
            raise SettingsServiceError("CATEGORY_NOT_FOUND", "Category not found.", 400)
        scope = _QUOTA_SCOPE_JOB_TITLE_CATEGORY
        article = None
    else:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "Quota must be either a global article override or a job_title + category default.",
            400,
        )

    if requested_scope is not None and requested_scope != scope:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "scope does not match the provided quota fields.",
            400,
        )

    return {
        "scope": scope,
        "job_title": job_title,
        "category_id": category.id if category else None,
        "article_id": article.id if article else None,
        "employee_id": None,
        "quantity": quantity,
        "uom": uom,
        "reset_month": reset_month,
        "enforcement": enforcement,
    }


def get_shell_settings() -> dict[str, Any]:
    """Return the minimal installation-wide shell branding payload.

    Accessible to all authenticated roles (ADMIN, MANAGER, WAREHOUSE_STAFF,
    VIEWER, OPERATOR).  Exposes only the fields consumed by AppShell/Sidebar:
    location_name, default_language, and role_display_names.
    """
    location = _settings_location_or_404()
    role_names = _role_display_name_map()
    return {
        "location_name": location.name,
        "default_language": _system_config_value("default_language"),
        "role_display_names": [
            _serialize_role_row(role, role_names[role]) for role in _ROLE_ORDER
        ],
    }


def get_general_settings() -> dict[str, Any]:
    location = _settings_location_or_404()
    return {
        "location_name": location.name,
        "timezone": location.timezone,
        "default_language": _system_config_value("default_language"),
    }


def update_general_settings(payload: dict[str, Any]) -> dict[str, Any]:
    _validate_allowed_fields(
        payload,
        allowed_fields={"location_name", "timezone", "default_language"},
    )
    location = _settings_location_or_404()
    location_name = _require_text(
        payload.get("location_name"),
        field_name="location_name",
        max_length=100,
    )
    timezone_name = _require_text(payload.get("timezone"), field_name="timezone")
    default_language = _require_text(
        payload.get("default_language"),
        field_name="default_language",
    ).lower()
    if default_language not in _ALLOWED_LANGUAGES:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "default_language must be one of: hr, en, de, hu.",
            400,
        )

    location.name = location_name
    location.timezone = timezone_name
    _set_system_config_value("default_language", default_language)
    db.session.commit()
    return get_general_settings()


def list_role_display_names() -> list[dict[str, Any]]:
    role_names = _role_display_name_map()
    return [_serialize_role_row(role, role_names[role]) for role in _ROLE_ORDER]


def update_role_display_names(payload: Any) -> list[dict[str, Any]]:
    parsed = _parse_roles_payload(payload)
    for role in _ROLE_ORDER:
        row = _find_or_create_role_display_name(role)
        row.display_name = parsed[role]
    db.session.commit()
    return list_role_display_names()


def list_uom_catalog() -> list[dict[str, Any]]:
    rows = db.session.query(UomCatalog).order_by(UomCatalog.code.asc(), UomCatalog.id.asc()).all()
    return [_serialize_uom(row) for row in rows]


def create_uom(payload: dict[str, Any]) -> dict[str, Any]:
    _validate_allowed_fields(
        payload,
        allowed_fields={"code", "label_hr", "label_en", "decimal_display"},
    )
    code = _require_text(payload.get("code"), field_name="code")
    label_hr = _require_text(payload.get("label_hr"), field_name="label_hr")
    label_en = _validate_optional_text(payload.get("label_en"), field_name="label_en")
    decimal_display = _parse_bool(
        payload.get("decimal_display"),
        field_name="decimal_display",
        default=False,
    )

    if UomCatalog.query.filter_by(code=code).first() is not None:
        raise SettingsServiceError(
            "UOM_CODE_EXISTS",
            "Unit code already exists.",
            409,
            {"code": code},
        )

    row = UomCatalog(
        code=code,
        label_hr=label_hr,
        label_en=label_en,
        decimal_display=decimal_display,
    )
    db.session.add(row)
    db.session.commit()
    return _serialize_uom(row)


def list_categories() -> list[dict[str, Any]]:
    rows = db.session.query(Category).order_by(Category.key.asc(), Category.id.asc()).all()
    return [_serialize_category(row) for row in rows]


def update_category(category_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _validate_allowed_fields(
        payload,
        allowed_fields={"label_hr", "label_en", "is_personal_issue"},
    )
    if not payload:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "At least one category field must be provided.",
            400,
        )

    category = db.session.get(Category, category_id)
    if category is None:
        raise SettingsServiceError("CATEGORY_NOT_FOUND", "Category not found.", 404)

    if "label_hr" in payload:
        category.label_hr = _require_text(
            payload.get("label_hr"),
            field_name="label_hr",
        )
    if "label_en" in payload:
        category.label_en = _validate_optional_text(
            payload.get("label_en"),
            field_name="label_en",
        )
    if "is_personal_issue" in payload:
        category.is_personal_issue = _parse_bool(
            payload.get("is_personal_issue"),
            field_name="is_personal_issue",
        )

    db.session.commit()
    return _serialize_category(category)


def list_settings_quotas() -> list[dict[str, Any]]:
    rows = (
        db.session.query(AnnualQuota)
        .options(
            joinedload(AnnualQuota.article).joinedload(Article.category),
            joinedload(AnnualQuota.category),
        )
        .filter(AnnualQuota.employee_id.is_(None))
        .filter(
            or_(
                AnnualQuota.article_id.isnot(None),
                and_(
                    AnnualQuota.article_id.is_(None),
                    AnnualQuota.job_title.isnot(None),
                    AnnualQuota.category_id.isnot(None),
                ),
            )
        )
        .all()
    )

    serialized = [_serialize_quota(row) for row in rows]
    serialized.sort(
        key=lambda item: (
            0 if item["scope"] == _QUOTA_SCOPE_GLOBAL_ARTICLE else 1,
            (item["job_title"] or "").lower(),
            (item["article_no"] or "").lower(),
            (item["category_key"] or "").lower(),
            item["id"],
        )
    )
    return serialized


def create_quota(payload: dict[str, Any]) -> dict[str, Any]:
    prepared = _prepare_quota_payload(payload)
    row = AnnualQuota(
        job_title=prepared["job_title"],
        category_id=prepared["category_id"],
        article_id=prepared["article_id"],
        employee_id=None,
        quantity=prepared["quantity"],
        uom=prepared["uom"],
        reset_month=prepared["reset_month"],
        enforcement=prepared["enforcement"],
    )
    db.session.add(row)
    db.session.commit()
    row = _settings_quota_or_404(row.id)
    return _serialize_quota(row)


def update_quota(quota_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    row = _settings_quota_or_404(quota_id)
    prepared = _prepare_quota_payload(payload)
    row.job_title = prepared["job_title"]
    row.category_id = prepared["category_id"]
    row.article_id = prepared["article_id"]
    row.employee_id = None
    row.quantity = prepared["quantity"]
    row.uom = prepared["uom"]
    row.reset_month = prepared["reset_month"]
    row.enforcement = prepared["enforcement"]
    db.session.commit()
    row = _settings_quota_or_404(row.id)
    return _serialize_quota(row)


def delete_quota(quota_id: int) -> dict[str, Any]:
    row = _settings_quota_or_404(quota_id)
    deleted_id = row.id
    db.session.delete(row)
    db.session.commit()
    return {"id": deleted_id, "deleted": True}


def get_barcode_settings() -> dict[str, Any]:
    raw_port = _system_config_value("label_printer_port")
    try:
        port_int = int(raw_port)
    except (TypeError, ValueError):
        port_int = int(_DEFAULT_LABEL_PRINTER_PORT)
    return {
        "barcode_format": _system_config_value("barcode_format"),
        "barcode_printer": _system_config_value("barcode_printer"),
        "label_printer_ip": _system_config_value("label_printer_ip"),
        "label_printer_port": port_int,
        "label_printer_model": _system_config_value("label_printer_model"),
    }


def get_validated_label_printer_config() -> tuple[str, int, str]:
    """Return persisted label-printer settings after revalidating use-time inputs.

    Settings writes already enforce the allowed IP and port rules, but direct
    printer use must still recheck stored values so legacy or manually edited
    configuration cannot bypass the network guardrails.
    """
    cfg = get_barcode_settings()
    label_printer_ip = _normalize_optional_text(cfg.get("label_printer_ip")) or ""
    _validate_label_printer_ip(label_printer_ip)
    label_printer_port = _parse_label_printer_port(cfg.get("label_printer_port"))
    label_printer_model = (
        _normalize_optional_text(cfg.get("label_printer_model")) or _DEFAULT_LABEL_PRINTER_MODEL
    )
    return label_printer_ip, label_printer_port, label_printer_model


def _parse_label_printer_port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "label_printer_port must be a valid integer.",
            400,
        )
    allowed = sorted(_ALLOWED_LABEL_PRINTER_PORTS)
    if port not in _ALLOWED_LABEL_PRINTER_PORTS:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"label_printer_port must be one of: {', '.join(str(p) for p in allowed)}.",
            400,
        )
    return port


def _validate_label_printer_ip(ip: str) -> None:
    """Raise SettingsServiceError if *ip* is not a literal RFC 1918 IPv4 address.

    A blank *ip* string is accepted as "not configured" and passes validation.
    Rejects hostnames, public IPs, IPv6 values, CIDR notation, and any
    input outside the explicitly supported RFC 1918 ranges.
    """
    if not ip:
        return
    try:
        addr = ipaddress.IPv4Address(ip)
    except ValueError:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "label_printer_ip must be a valid private IPv4 address (RFC 1918).",
            400,
        )
    if not any(addr in network for network in _ALLOWED_LABEL_PRINTER_NETWORKS):
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "label_printer_ip must be a private IPv4 address (10.x.x.x, 172.16–31.x.x, or 192.168.x.x).",
            400,
        )


def update_barcode_settings(payload: dict[str, Any]) -> dict[str, Any]:
    _validate_allowed_fields(
        payload,
        allowed_fields={
            "barcode_format",
            "barcode_printer",
            "label_printer_ip",
            "label_printer_port",
            "label_printer_model",
        },
    )
    barcode_format = _require_text(
        payload.get("barcode_format"),
        field_name="barcode_format",
    )
    if barcode_format not in _ALLOWED_BARCODE_FORMATS:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "barcode_format must be EAN-13 or Code128.",
            400,
        )

    barcode_printer = _normalize_optional_text(payload.get("barcode_printer")) or ""
    label_printer_ip = _normalize_optional_text(payload.get("label_printer_ip")) or ""
    _validate_label_printer_ip(label_printer_ip)

    raw_port = payload.get("label_printer_port")
    if raw_port is None:
        label_printer_port = int(_DEFAULT_LABEL_PRINTER_PORT)
    else:
        label_printer_port = _parse_label_printer_port(raw_port)

    label_printer_model = (
        _normalize_optional_text(payload.get("label_printer_model")) or _DEFAULT_LABEL_PRINTER_MODEL
    )
    if label_printer_model not in _ALLOWED_PRINTER_MODELS:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"label_printer_model must be one of: {', '.join(sorted(_ALLOWED_PRINTER_MODELS))}.",
            400,
        )

    _set_system_config_value("barcode_format", barcode_format)
    _set_system_config_value("barcode_printer", barcode_printer)
    _set_system_config_value("label_printer_ip", label_printer_ip)
    _set_system_config_value("label_printer_port", str(label_printer_port))
    _set_system_config_value("label_printer_model", label_printer_model)
    db.session.commit()
    return get_barcode_settings()


def get_export_settings() -> dict[str, Any]:
    return {"export_format": _system_config_value("export_format")}


def update_export_settings(payload: dict[str, Any]) -> dict[str, Any]:
    _validate_allowed_fields(payload, allowed_fields={"export_format"})
    export_format = _require_text(
        payload.get("export_format"),
        field_name="export_format",
    ).lower()
    if export_format not in _ALLOWED_EXPORT_FORMATS:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "export_format must be generic or sap.",
            400,
        )

    _set_system_config_value("export_format", export_format)
    db.session.commit()
    return get_export_settings()


def list_suppliers(
    *,
    page: int,
    per_page: int,
    q: str | None,
    include_inactive: bool,
) -> dict[str, Any]:
    # V-3 / Wave 6 Phase 1: cap per_page to prevent DoS via large result sets
    per_page = min(per_page, 200)
    query = db.session.query(Supplier)
    if not include_inactive:
        query = query.filter(Supplier.is_active.is_(True))
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Supplier.internal_code.ilike(pattern),
                Supplier.name.ilike(pattern),
            )
        )

    total = query.count()
    rows = (
        query.order_by(
            func.lower(Supplier.name).asc(),
            func.lower(Supplier.internal_code).asc(),
            Supplier.id.asc(),
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [_serialize_supplier(row) for row in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def create_supplier(payload: dict[str, Any]) -> dict[str, Any]:
    _validate_allowed_fields(
        payload,
        allowed_fields={
            "internal_code",
            "name",
            "contact_person",
            "phone",
            "email",
            "address",
            "iban",
            "note",
        },
    )
    internal_code = _require_text(payload.get("internal_code"), field_name="internal_code")
    name = _require_text(payload.get("name"), field_name="name", max_length=200)
    contact_person = _validate_optional_text(
        payload.get("contact_person"),
        field_name="contact_person",
    )
    phone = _validate_optional_text(payload.get("phone"), field_name="phone")
    email = _validate_optional_text(payload.get("email"), field_name="email")
    address = _validate_optional_text(payload.get("address"), field_name="address")
    iban = _validate_optional_text(payload.get("iban"), field_name="iban")
    note = _validate_optional_text(payload.get("note"), field_name="note", max_length=1000)
    note_ok, note_error = validate_note(note)
    if not note_ok:
        raise SettingsServiceError("VALIDATION_ERROR", note_error or "Invalid note.", 400)

    if Supplier.query.filter_by(internal_code=internal_code).first() is not None:
        raise SettingsServiceError(
            "SUPPLIER_CODE_EXISTS",
            "Supplier code already exists.",
            409,
            {"internal_code": internal_code},
        )

    supplier = Supplier(
        internal_code=internal_code,
        name=name,
        contact_person=contact_person,
        phone=phone,
        email=email,
        address=address,
        iban=iban,
        note=note,
        is_active=True,
    )
    db.session.add(supplier)
    db.session.commit()
    return _serialize_supplier(supplier)


def update_supplier(supplier_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    supplier = _supplier_or_404(supplier_id)
    if "internal_code" in payload:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "internal_code cannot be changed.",
            400,
        )

    _validate_allowed_fields(
        payload,
        allowed_fields={"name", "contact_person", "phone", "email", "address", "iban", "note"},
    )
    if not payload:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "At least one supplier field must be provided.",
            400,
        )

    if "name" in payload:
        supplier.name = _require_text(payload.get("name"), field_name="name", max_length=200)
    if "contact_person" in payload:
        supplier.contact_person = _validate_optional_text(
            payload.get("contact_person"),
            field_name="contact_person",
        )
    if "phone" in payload:
        supplier.phone = _validate_optional_text(payload.get("phone"), field_name="phone")
    if "email" in payload:
        supplier.email = _validate_optional_text(payload.get("email"), field_name="email")
    if "address" in payload:
        supplier.address = _validate_optional_text(payload.get("address"), field_name="address")
    if "iban" in payload:
        supplier.iban = _validate_optional_text(payload.get("iban"), field_name="iban")
    if "note" in payload:
        note = _validate_optional_text(payload.get("note"), field_name="note", max_length=1000)
        note_ok, note_error = validate_note(note)
        if not note_ok:
            raise SettingsServiceError(
                "VALIDATION_ERROR",
                note_error or "Invalid note.",
                400,
            )
        supplier.note = note

    db.session.commit()
    return _serialize_supplier(supplier)


def deactivate_supplier(supplier_id: int) -> dict[str, Any]:
    supplier = _supplier_or_404(supplier_id)
    supplier.is_active = False
    db.session.commit()
    return _serialize_supplier(supplier)


def list_users() -> list[dict[str, Any]]:
    role_names = _role_display_name_map()
    rows = db.session.query(User).order_by(func.lower(User.username).asc(), User.id.asc()).all()
    return [_serialize_user(row, role_names=role_names) for row in rows]


def _min_password_length(role: UserRole) -> int:
    """Return the minimum acceptable password length for the given role.

    ADMIN accounts require 12 characters; all other roles require 8.
    Centralised here so create and update paths share the same thresholds.
    """
    return 12 if role == UserRole.ADMIN else 8


def _validate_password_length(password: Any, role: UserRole) -> None:
    """Raise SettingsServiceError when the password is too short for the role."""
    min_len = _min_password_length(role)
    if not isinstance(password, str) or len(password) < min_len:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            f"password must be at least {min_len} characters long for role {role.value}.",
            400,
        )


def create_user(payload: dict[str, Any]) -> dict[str, Any]:
    _validate_allowed_fields(
        payload,
        allowed_fields={"username", "password", "role", "is_active"},
    )
    username = _require_text(payload.get("username"), field_name="username", max_length=50)
    password = payload.get("password")
    role = _parse_user_role(payload.get("role"))
    is_active = _parse_bool(payload.get("is_active"), field_name="is_active", default=True)

    _validate_password_length(password, role)

    if User.query.filter_by(username=username).first() is not None:
        raise SettingsServiceError(
            "USERNAME_EXISTS",
            "Username already exists.",
            409,
            {"username": username},
        )

    user = User(
        username=username,
        password_hash=generate_password_hash(password, method="scrypt"),
        role=role,
        is_active=is_active,
    )
    db.session.add(user)
    db.session.commit()
    return _serialize_user(user, role_names=_role_display_name_map())


def update_user(user_id: int, payload: dict[str, Any], *, acting_user_id: int) -> dict[str, Any]:
    user = _user_or_404(user_id)
    if "username" in payload:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "username cannot be changed.",
            400,
        )

    _validate_allowed_fields(
        payload,
        allowed_fields={"role", "is_active", "password"},
    )
    if not payload:
        raise SettingsServiceError(
            "VALIDATION_ERROR",
            "At least one user field must be provided.",
            400,
        )

    next_is_active = user.is_active
    if "is_active" in payload:
        next_is_active = _parse_bool(payload.get("is_active"), field_name="is_active")
        if not next_is_active and user.id == acting_user_id:
            raise SettingsServiceError(
                "SELF_DEACTIVATION_FORBIDDEN",
                "You cannot deactivate your own account.",
                400,
            )

    next_role = user.role
    if "role" in payload:
        next_role = _parse_user_role(payload.get("role"))
        if (
            next_role == UserRole.ADMIN
            and user.role != UserRole.ADMIN
            and "password" not in payload
        ):
            raise SettingsServiceError(
                "VALIDATION_ERROR",
                "Promoting a user to ADMIN requires a password reset that meets the ADMIN minimum.",
                400,
            )

    if "password" in payload:
        _validate_password_length(payload.get("password"), next_role)

    user.is_active = next_is_active
    user.role = next_role

    if "password" in payload:
        password = payload.get("password")
        user.password_hash = generate_password_hash(password, method="scrypt")
        user.password_changed_at = datetime.now(timezone.utc)

    db.session.commit()
    return _serialize_user(user, role_names=_role_display_name_map())


def deactivate_user(user_id: int, *, acting_user_id: int) -> dict[str, Any]:
    user = _user_or_404(user_id)
    if user.id == acting_user_id:
        raise SettingsServiceError(
            "SELF_DEACTIVATION_FORBIDDEN",
            "You cannot deactivate your own account.",
            400,
        )

    user.is_active = False
    db.session.commit()
    return _serialize_user(user, role_names=_role_display_name_map())
