"""Shared IZL-#### DraftGroup sequence helper.

Both the Draft Entry routes (DAILY_OUTBOUND) and the Inventory Count service
(INVENTORY_SHORTAGE) must share one visible numbering sequence for DraftGroup
numbers.  This module is the single source of that logic.

Accepted semantics (DEC-BE-004, DEC-INV-001):
  - Scan all DraftGroup.group_number values.
  - Ignore entries that do not match IZL-#### (e.g. IZL-LEGACY-*).
  - Use the maximum matching numeric suffix; if none exist start at IZL-0001.
  - DAILY_OUTBOUND and INVENTORY_SHORTAGE groups share the same sequence.
  - Visible number must not be derived from DraftGroup.id.
"""

import re

from app.extensions import db
from app.models.draft_group import DraftGroup

_IZL_NUMBER_RE = re.compile(r"^IZL-(\d+)$")


def next_izl_group_number() -> str:
    """Return the next IZL-#### group number based on the max existing matching suffix."""
    max_suffix = 0
    rows = db.session.query(DraftGroup.group_number).all()
    for (group_number,) in rows:
        if not group_number:
            continue
        match = _IZL_NUMBER_RE.match(group_number)
        if match:
            max_suffix = max(max_suffix, int(match.group(1)))
    return f"IZL-{max_suffix + 1:04d}"
