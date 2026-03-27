"""Reusable validation helpers.

Provides shared query, batch-code, quantity, and note validators used by
multiple API modules.
"""

import re
from decimal import Decimal, InvalidOperation

_BATCH_CODE_RE = re.compile(r"^\d{4,5}$|^\d{9,12}$")


class QueryValidationError(Exception):
    """Shared structured error for route-level query parsing failures."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.error = "VALIDATION_ERROR"
        self.message = message
        self.status_code = 400
        self.details: dict[str, str] = {}


def parse_positive_int(value, *, field_name: str, default: int) -> int:
    """Parse a positive integer query parameter using canonical error text."""
    raw_value = default if value is None else value
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        raise QueryValidationError(
            f"{field_name} must be a valid integer."
        ) from None
    if parsed <= 0:
        raise QueryValidationError(f"{field_name} must be greater than zero.")
    return parsed


def parse_bool_query(value, *, field_name: str, default: bool) -> bool:
    """Parse a boolean query parameter using canonical error text."""
    if value is None:
        return default

    normalized = str(value).strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise QueryValidationError(f"{field_name} must be 'true' or 'false'.")


def validate_batch_code(code: str) -> bool:
    """Return True if *code* matches the documented batch-code pattern.

    Valid patterns (08_SETUP_AND_GLOBALS §3.5):
      - 4–5 digits  (e.g. 1234, 12345)
      - 9–12 digits (e.g. 123456789, 123456789012)
    """
    if not isinstance(code, str):
        return False
    return _BATCH_CODE_RE.match(code) is not None


def validate_quantity(value) -> tuple[bool, Decimal | None, str | None]:
    """Validate a quantity value.

    Returns (ok, decimal_value, error_message).
    Rules (08_SETUP_AND_GLOBALS §3.3):
      - Must be a number
      - Must be > 0 (zero is rejected)
    """
    if value is None:
        return False, None, "Quantity is required."
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return False, None, "Quantity must be a valid number."
    if d <= 0:
        return False, None, "Quantity must be greater than zero."
    return True, d, None


def validate_note(text: str | None, max_length: int = 1000) -> tuple[bool, str | None]:
    """Validate an optional note field.

    Returns (ok, error_message).  None / empty is valid (field is optional).
    """
    if text is None or text == "":
        return True, None
    if not isinstance(text, str):
        return False, "Note must be a valid string."
    if len(text) > max_length:
        return False, f"Note must be {max_length} characters or fewer."
    return True, None
