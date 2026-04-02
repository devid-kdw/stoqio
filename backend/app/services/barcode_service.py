"""Barcode PDF generation and direct label-printer support for Phase 15 / Wave 2 Phase 8."""

from __future__ import annotations

import re
import socket
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


def _resolve_direct_print_barcode_value(
    *,
    entity: Article | Batch,
    existing_value: str | None,
    generated_value: str,
) -> tuple[str, bool]:
    """Return a direct-print barcode value without PDF-format coupling.

    The direct printer path always emits Code128 in ZPL, so it must not inherit
    the stricter PDF/EAN-13 validation rules from the PDF download flow. The
    stored barcode value is reused as-is when present; otherwise the generated
    fallback is persisted and returned.
    """
    normalized = _normalize_optional_text(existing_value)
    if normalized is not None:
        return normalized, False

    entity.barcode = generated_value
    return generated_value, True


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


# ---------------------------------------------------------------------------
# Direct label-printer support (Wave 2 Phase 8)
# ---------------------------------------------------------------------------

_ZPL_DESCRIPTION_MAX = 30
_PRINTER_SOCKET_TIMEOUT = 5


def _generate_zpl(
    *,
    article_no: str,
    description: str,
    barcode_value: str,
    batch_code: str | None,
) -> bytes:
    """Build a ZPL II label for a Zebra printer.

    Layout:
    - Code128 barcode at top
    - Description (truncated to 30 chars)
    - Article number
    - Batch line only when batch_code is present
    """
    desc_line = description[:_ZPL_DESCRIPTION_MAX]
    lines = [
        "^XA",
        f"^FO50,30^BY2^BCN,100,Y,N,N^FD{barcode_value}^FS",
        f"^FO50,150^A0N,25,25^FD{desc_line}^FS",
        f"^FO50,185^A0N,20,20^FD{article_no}^FS",
    ]
    if batch_code:
        lines.append(f"^FO50,215^A0N,20,20^FDBatch: {batch_code}^FS")
    lines.append("^XZ")
    return "\n".join(lines).encode("utf-8")


# Dispatch map: model key → generator callable.
# Add new models here; no changes to the API layer required.
_LABEL_GENERATORS: dict[str, Any] = {
    "zebra_zpl": _generate_zpl,
}


def generate_label(
    model: str,
    *,
    article_no: str,
    description: str,
    barcode_value: str,
    batch_code: str | None,
) -> bytes:
    """Return raw label bytes for the given printer model.

    Raises ``BarcodeServiceError`` with ``PRINTER_MODEL_UNKNOWN`` (400)
    when the model is not in the supported dispatch map.
    """
    generator = _LABEL_GENERATORS.get(model)
    if generator is None:
        raise BarcodeServiceError(
            "PRINTER_MODEL_UNKNOWN",
            f"Unknown printer model: {model}.",
            400,
            {"model": model},
        )
    return generator(
        article_no=article_no,
        description=description,
        barcode_value=barcode_value,
        batch_code=batch_code,
    )


def _send_to_printer(ip: str, port: int, data: bytes) -> None:
    """Open a TCP socket to ``ip:port`` and send *data*.

    Raises ``BarcodeServiceError`` with ``PRINTER_UNREACHABLE`` (502)
    on any socket or OS-level failure.
    """
    try:
        with socket.create_connection((ip, port), timeout=_PRINTER_SOCKET_TIMEOUT) as sock:
            sock.sendall(data)
    except OSError as exc:
        raise BarcodeServiceError(
            "PRINTER_UNREACHABLE",
            f"Printer is not reachable at {ip}.",
            502,
            {"printer_ip": ip},
        ) from exc


def _get_validated_printer_config() -> tuple[str, int, str]:
    """Load and validate printer settings.

    Returns ``(ip, port, model)`` on success.

    Raises ``BarcodeServiceError`` for:
    - ``PRINTER_NOT_CONFIGURED`` (400) — IP is blank
    - ``PRINTER_MODEL_UNKNOWN`` (400) — stored model not in supported set
    """
    cfg = settings_service.get_barcode_settings()
    ip: str = (cfg.get("label_printer_ip") or "").strip()
    port: int = cfg.get("label_printer_port") or 9100
    model: str = (cfg.get("label_printer_model") or "").strip()

    if not ip:
        raise BarcodeServiceError(
            "PRINTER_NOT_CONFIGURED",
            "Printer is not configured. Set the printer IP address in settings.",
            400,
        )

    if model not in _LABEL_GENERATORS:
        raise BarcodeServiceError(
            "PRINTER_MODEL_UNKNOWN",
            f"Unknown printer model: {model}.",
            400,
            {"model": model},
        )

    return ip, int(port), model


def print_article_label(article_id: int) -> dict[str, Any]:
    """Resolve article barcode and send a ZPL label to the configured printer.

    Returns ``{"status": "sent", "printer_ip": ..., "model": ...}`` on success.
    """
    ip, port, model = _get_validated_printer_config()
    article = _get_article_or_404(article_id)
    barcode_value, changed = _resolve_direct_print_barcode_value(
        entity=article,
        existing_value=article.barcode,
        generated_value=_build_generated_barcode(_ARTICLE_PREFIX, article.id),
    )
    if changed:
        db.session.commit()

    label = generate_label(
        model,
        article_no=article.article_no,
        description=article.description,
        barcode_value=barcode_value,
        batch_code=None,
    )
    _send_to_printer(ip, port, label)
    return {"status": "sent", "printer_ip": ip, "model": model}


def print_batch_label(batch_id: int) -> dict[str, Any]:
    """Resolve batch barcode and send a ZPL label to the configured printer.

    Returns ``{"status": "sent", "printer_ip": ..., "model": ...}`` on success.
    """
    ip, port, model = _get_validated_printer_config()
    batch = _get_batch_or_404(batch_id)
    barcode_value, changed = _resolve_direct_print_barcode_value(
        entity=batch,
        existing_value=batch.barcode,
        generated_value=_build_generated_barcode(_BATCH_PREFIX, batch.id),
    )
    if changed:
        db.session.commit()

    article = batch.article
    article_no = article.article_no if article is not None else f"article-{batch.article_id}"
    description = article.description if article is not None else "Unknown article"

    label = generate_label(
        model,
        article_no=article_no,
        description=description,
        barcode_value=barcode_value,
        batch_code=batch.batch_code,
    )
    _send_to_printer(ip, port, label)
    return {"status": "sent", "printer_ip": ip, "model": model}
