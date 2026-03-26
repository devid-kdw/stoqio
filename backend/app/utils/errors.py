"""Centralized API error response builder.

All route modules import ``api_error`` as their ``_error`` helper so that
error messages are automatically localized via the i18n layer.

Usage in route files::

    from app.utils.errors import api_error as _error

    # inline call
    return _error("NOT_FOUND", "Draft group not found.", 404)

    # from service exception
    return _error(exc.error, exc.message, exc.status_code, exc.details)

The ``message`` argument acts only as an English fallback when the error code
has no catalog entry.  Details keys prefixed with ``_`` (e.g. ``_msg_key``)
are used internally for translation key selection and are stripped from the
response payload.
"""

from __future__ import annotations

from typing import Any

from flask import jsonify

from app.utils.i18n import localize_message


def api_error(
    error: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
) -> tuple:
    """Return a localized ``(Response, status_code)`` tuple.

    The ``error`` code and ``details`` shape are never changed.
    Only the human-readable ``message`` field is localized.
    Internal ``_``-prefixed keys in *details* are stripped before the
    response is serialized.
    """
    clean_details = {k: v for k, v in (details or {}).items() if not k.startswith("_")}
    localized = localize_message(error, details, fallback=message)
    return (
        jsonify(
            {
                "error": error,
                "message": localized,
                "details": clean_details,
            }
        ),
        status_code,
    )
