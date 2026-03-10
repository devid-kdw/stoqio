"""Shared enum definitions for WMS models."""

import enum


class DraftStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DraftType(str, enum.Enum):
    OUTBOUND = "OUTBOUND"
    INVENTORY_SHORTAGE = "INVENTORY_SHORTAGE"


class DraftSource(str, enum.Enum):
    scale = "scale"
    manual = "manual"


class DraftGroupStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ApprovalActionType(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class OrderStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class OrderLineStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    REMOVED = "REMOVED"


class TxType(str, enum.Enum):
    STOCK_RECEIPT = "STOCK_RECEIPT"
    OUTBOUND = "OUTBOUND"
    SURPLUS_CONSUMED = "SURPLUS_CONSUMED"
    STOCK_CONSUMED = "STOCK_CONSUMED"
    INVENTORY_ADJUSTMENT = "INVENTORY_ADJUSTMENT"
    WRITEOFF = "WRITEOFF"
    PERSONAL_ISSUE = "PERSONAL_ISSUE"


class InventoryCountStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class InventoryCountLineResolution(str, enum.Enum):
    SURPLUS_ADDED = "SURPLUS_ADDED"
    SHORTAGE_DRAFT_CREATED = "SHORTAGE_DRAFT_CREATED"
    NO_CHANGE = "NO_CHANGE"


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    WAREHOUSE_STAFF = "WAREHOUSE_STAFF"
    VIEWER = "VIEWER"
    OPERATOR = "OPERATOR"


class MissingArticleReportStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class QuotaEnforcement(str, enum.Enum):
    WARN = "WARN"
    BLOCK = "BLOCK"
