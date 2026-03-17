"""Model package — imports every model so Alembic sees all metadata."""

# ruff: noqa: F401  (unused imports are intentional for metadata registration)

from app.models.location import Location
from app.models.supplier import Supplier
from app.models.category import Category
from app.models.uom_catalog import UomCatalog
from app.models.article import Article
from app.models.article_supplier import ArticleSupplier
from app.models.article_alias import ArticleAlias
from app.models.batch import Batch
from app.models.stock import Stock
from app.models.surplus import Surplus
from app.models.employee import Employee
from app.models.user import User
from app.models.revoked_token import RevokedToken
from app.models.draft_group import DraftGroup
from app.models.draft import Draft
from app.models.approval_action import ApprovalAction
from app.models.order import Order
from app.models.order_line import OrderLine
from app.models.receiving import Receiving
from app.models.transaction import Transaction
from app.models.inventory_count import InventoryCount, InventoryCountLine
from app.models.personal_issuance import PersonalIssuance
from app.models.annual_quota import AnnualQuota
from app.models.missing_article_report import MissingArticleReport
from app.models.system_config import SystemConfig
from app.models.role_display_name import RoleDisplayName
from app.models.approval_override import ApprovalOverride
