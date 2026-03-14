"""Barcode PDF generation for Phase 15."""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.article import Article
from app.models.batch import Batch
from app.services import settings_service

_PDF_MIMETYPE = "application/pdf"
_LABEL_PAGE_SIZE = (100 * mm, 60 * mm)
_ARTICLE_PREFIX = "20"
_BATCH_PREFIX = "30"
_ALLOWED_FORMATS = {"EAN-13", "Code128"}
_DIGITS_RE = re.compile(r"^\d+$")


class BarcodeServiceError(Exception):
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


@dataclass(frozen=True, slots=True)
class _LabelPage:
    title: str
    lines: tuple[str, ...]
    barcode_value: str
    barcode_format: str


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _trim_text(value: str, *, max_length: int = 56) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3]}..."


def _safe_filename_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "barcode"


def _get_article_or_404(article_id: int) -> Article:
    article = db.session.get(Article, article_id)
    if article is None:
        raise BarcodeServiceError(
            "ARTICLE_NOT_FOUND",
            "Article not found.",
            404,
            {"article_id": article_id},
        )
    return article


def _get_batch_or_404(batch_id: int) -> Batch:
    batch = (
        Batch.query.options(joinedload(Batch.article))
        .filter(Batch.id == batch_id)
        .first()
    )
    if batch is None:
        raise BarcodeServiceError(
            "BATCH_NOT_FOUND",
            "Batch not found.",
            404,
            {"batch_id": batch_id},
        )
    return batch


def _get_configured_barcode_format() -> str:
    barcode_format = settings_service.get_barcode_settings().get("barcode_format")
    normalized = _normalize_optional_text(barcode_format) or "Code128"
    if normalized not in _ALLOWED_FORMATS:
        raise BarcodeServiceError(
            "UNSUPPORTED_BARCODE_FORMAT",
            f"Configured barcode format '{normalized}' is not supported.",
            400,
            {"barcode_format": normalized},
        )
    return normalized


def _ean13_check_digit(base_digits: str) -> str:
    odd_total = sum(int(digit) for digit in base_digits[::2])
    even_total = sum(int(digit) for digit in base_digits[1::2])
    return str((10 - ((odd_total + (even_total * 3)) % 10)) % 10)


def _build_generated_barcode(prefix: str, entity_id: int) -> str:
    if entity_id <= 0:
        raise BarcodeServiceError(
            "INVALID_BARCODE_SOURCE",
            "Barcode source id must be positive.",
            400,
            {"entity_id": entity_id},
        )

    base_digits = f"{prefix}{entity_id:010d}"
    if len(base_digits) != 12:
        raise BarcodeServiceError(
            "INVALID_BARCODE_SOURCE",
            "Barcode source id exceeds the supported range.",
            400,
            {"entity_id": entity_id},
        )
    return f"{base_digits}{_ean13_check_digit(base_digits)}"


def _is_valid_ean13(value: str) -> bool:
    return len(value) == 13 and _DIGITS_RE.fullmatch(value) is not None and value[-1] == _ean13_check_digit(value[:12])


def _resolve_barcode_value(
    *,
    entity: Article | Batch,
    existing_value: str | None,
    generated_value: str,
    barcode_format: str,
    entity_type: str,
) -> tuple[str, bool]:
    normalized = _normalize_optional_text(existing_value)
    changed = False

    if normalized is None:
        normalized = generated_value
        entity.barcode = normalized
        changed = True

    if barcode_format != "EAN-13":
        return normalized, changed

    if _DIGITS_RE.fullmatch(normalized) is None:
        raise BarcodeServiceError(
            "INVALID_BARCODE_VALUE",
            f"{entity_type} barcode must contain 12 or 13 digits for EAN-13.",
            400,
            {"barcode": normalized, "barcode_format": barcode_format},
        )

    if len(normalized) == 12:
        normalized = f"{normalized}{_ean13_check_digit(normalized)}"
        entity.barcode = normalized
        changed = True
        return normalized, changed

    if len(normalized) != 13 or not _is_valid_ean13(normalized):
        raise BarcodeServiceError(
            "INVALID_BARCODE_VALUE",
            f"{entity_type} barcode is not a valid EAN-13 value.",
            400,
            {"barcode": normalized, "barcode_format": barcode_format},
        )

    return normalized, changed


def _build_barcode_drawing(barcode_format: str, barcode_value: str):
    drawing_name = "EAN13" if barcode_format == "EAN-13" else "Code128"
    try:
        return createBarcodeDrawing(
            drawing_name,
            value=barcode_value,
            humanReadable=True,
            barHeight=18 * mm,
        )
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise BarcodeServiceError(
            "INVALID_BARCODE_VALUE",
            "Barcode value is incompatible with the configured format.",
            400,
            {"barcode": barcode_value, "barcode_format": barcode_format},
        ) from exc


def _draw_label_page(pdf: canvas.Canvas, page: _LabelPage) -> None:
    width, height = _LABEL_PAGE_SIZE
    barcode_drawing = _build_barcode_drawing(page.barcode_format, page.barcode_value)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(8 * mm, height - (9 * mm), page.title)
    pdf.setFont("Helvetica", 8)
    pdf.drawRightString(width - (8 * mm), height - (9 * mm), page.barcode_format)

    line_y = height - (15 * mm)
    for line in page.lines:
        pdf.drawString(8 * mm, line_y, _trim_text(line))
        line_y -= 4.5 * mm

    renderPDF.draw(barcode_drawing, pdf, 8 * mm, 8 * mm)


def _build_pdf(pages: list[_LabelPage], *, title: str) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(
        buffer,
        pagesize=_LABEL_PAGE_SIZE,
        pageCompression=0,
    )
    pdf.setTitle(title)

    for index, page in enumerate(pages):
        _draw_label_page(pdf, page)
        if index < len(pages) - 1:
            pdf.showPage()

    pdf.save()
    return buffer.getvalue()


def generate_article_barcode_pdf(article_id: int) -> tuple[bytes, str, str]:
    article = _get_article_or_404(article_id)
    barcode_format = _get_configured_barcode_format()
    barcode_value, changed = _resolve_barcode_value(
        entity=article,
        existing_value=article.barcode,
        generated_value=_build_generated_barcode(_ARTICLE_PREFIX, article.id),
        barcode_format=barcode_format,
        entity_type="Article",
    )

    lines = (
        f"Article No.: {article.article_no}",
        f"Description: {_trim_text(article.description, max_length=42)}",
    )
    content = _build_pdf(
        [
            _LabelPage(
                title="Article Barcode",
                lines=lines,
                barcode_value=barcode_value,
                barcode_format=barcode_format,
            )
        ],
        title=f"Article Barcode {article.article_no}",
    )
    if changed:
        db.session.commit()

    filename = f"wms_article_{_safe_filename_part(article.article_no)}_barcode.pdf"
    return content, filename, _PDF_MIMETYPE


def generate_batch_barcode_pdf(batch_id: int) -> tuple[bytes, str, str]:
    batch = _get_batch_or_404(batch_id)
    barcode_format = _get_configured_barcode_format()
    barcode_value, changed = _resolve_barcode_value(
        entity=batch,
        existing_value=batch.barcode,
        generated_value=_build_generated_barcode(_BATCH_PREFIX, batch.id),
        barcode_format=barcode_format,
        entity_type="Batch",
    )

    article = batch.article
    article_no = article.article_no if article is not None else f"article-{batch.article_id}"
    description = article.description if article is not None else "Unknown article"
    expiry = batch.expiry_date.isoformat() if batch.expiry_date else "-"
    content = _build_pdf(
        [
            _LabelPage(
                title="Batch Barcode",
                lines=(
                    f"Article No.: {article_no}",
                    f"Description: {_trim_text(description, max_length=42)}",
                    f"Batch: {batch.batch_code}",
                    f"Expiry: {expiry}",
                ),
                barcode_value=barcode_value,
                barcode_format=barcode_format,
            )
        ],
        title=f"Batch Barcode {article_no} {batch.batch_code}",
    )
    if changed:
        db.session.commit()

    filename = (
        f"wms_batch_{_safe_filename_part(article_no)}_"
        f"{_safe_filename_part(batch.batch_code)}_barcode.pdf"
    )
    return content, filename, _PDF_MIMETYPE
