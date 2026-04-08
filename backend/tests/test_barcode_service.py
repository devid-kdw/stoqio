"""Unit tests for barcode service (ZPL generation)."""

from __future__ import annotations

import pytest

from app.services.barcode_service import (
    BarcodeServiceError,
    _generate_zpl,
    generate_label,
)


def _zpl_hex(value: str) -> str:
    return "".join(f"\\{byte:02X}" for byte in value.encode("utf-8"))


def test_generate_zpl_includes_required_commands():
    result_bytes = _generate_zpl(
        article_no="ART-123",
        description="A simple article",
        barcode_value="123456789",
        batch_code=None,
    )
    result = result_bytes.decode("utf-8")

    assert "^XA" in result
    assert "^XZ" in result
    assert result.count("^FH\\^FD") == 3
    assert _zpl_hex("ART-123") in result
    assert _zpl_hex("A simple article") in result
    assert _zpl_hex("123456789") in result


def test_generate_zpl_truncates_long_description():
    long_desc = "This is a very long description that exceeds thirty characters"
    result_bytes = _generate_zpl(
        article_no="ART-456",
        description=long_desc,
        barcode_value="987654321",
        batch_code=None,
    )
    result = result_bytes.decode("utf-8")

    truncated = long_desc[:30]
    assert _zpl_hex(truncated) in result
    assert _zpl_hex(long_desc) not in result


def test_generate_zpl_includes_batch_line_when_present():
    result_bytes = _generate_zpl(
        article_no="ART-789",
        description="Batched article",
        barcode_value="111222333",
        batch_code="BATCH-99",
    )
    result = result_bytes.decode("utf-8")

    assert "Batch: " in result
    assert _zpl_hex("BATCH-99") in result


def test_generate_zpl_excludes_batch_line_when_absent():
    result_bytes = _generate_zpl(
        article_no="ART-789",
        description="Batched article",
        barcode_value="111222333",
        batch_code=None,
    )
    result = result_bytes.decode("utf-8")

    assert "Batch:" not in result
    assert result.count("^FH\\^FD") == 3


def test_generate_label_dispatches_to_zpl_generator():
    result_bytes = generate_label(
        "zebra_zpl",
        article_no="ART-000",
        description="Dispatch test",
        barcode_value="123",
        batch_code=None,
    )
    result = result_bytes.decode("utf-8")

    assert "^XA" in result
    assert result.count("^FH\\^FD") == 3
    assert _zpl_hex("ART-000") in result


def test_generate_label_raises_400_for_unknown_model():
    with pytest.raises(BarcodeServiceError) as exc_info:
        generate_label(
            "unknown_model",
            article_no="ART-000",
            description="Unknown model test",
            barcode_value="123",
            batch_code=None,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.error == "PRINTER_MODEL_UNKNOWN"
    assert exc_info.value.details == {"model": "unknown_model"}
