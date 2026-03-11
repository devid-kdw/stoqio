"""Reusable validation helpers.

Provides batch-code regex, quantity, and note validators used by
multiple API modules (drafts, receiving, etc.).
"""

import re
from decimal import Decimal, InvalidOperation

_BATCH_CODE_RE = re.compile(r"^\d{4,5}$|^\d{9,12}$")


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
