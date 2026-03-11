"""Article lookup routes for Draft Entry.

Provides:
  GET /api/v1/articles?q={query}  — search by article_no or barcode
"""

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models.article import Article
from app.models.batch import Batch
from app.models.uom_catalog import UomCatalog
from app.utils.auth import require_role

articles_bp = Blueprint("articles", __name__)


def _serialize_article(article: Article) -> dict:
    """Build the article response dict with UOM code and optional batches."""
    uom = db.session.get(UomCatalog, article.base_uom)
    uom_code = uom.code if uom else str(article.base_uom)

    data: dict = {
        "id": article.id,
        "article_no": article.article_no,
        "description": article.description,
        "base_uom": uom_code,
        "has_batch": article.has_batch,
    }

    if article.has_batch:
        batches = (
            Batch.query
            .filter_by(article_id=article.id)
            .order_by(Batch.expiry_date.asc())
            .all()
        )
        data["batches"] = [
            {
                "id": b.id,
                "batch_code": b.batch_code,
                "expiry_date": b.expiry_date.isoformat(),
            }
            for b in batches
        ]

    return data


@articles_bp.route("/articles", methods=["GET"])
@require_role("OPERATOR", "ADMIN")
def search_articles():
    """Lookup article by article_no or barcode.

    Query param ``q`` is matched case-insensitively against article_no
    (stored uppercase) and barcode.  Returns a list (typically 0 or 1
    match) so the frontend can handle no-match gracefully.
    """
    q = (request.args.get("q") or "").strip()

    if not q:
        return (
            jsonify(
                {
                    "error": "VALIDATION_ERROR",
                    "message": "Query parameter 'q' is required.",
                    "details": {},
                }
            ),
            400,
        )

    normalized = q.upper()

    # Search by exact article_no (normalized uppercase) or barcode
    article = (
        Article.query
        .filter(
            db.or_(
                Article.article_no == normalized,
                Article.barcode == q,
            )
        )
        .filter(Article.is_active.is_(True))
        .first()
    )

    if article is None:
        return (
            jsonify(
                {
                    "error": "ARTICLE_NOT_FOUND",
                    "message": "Article not found.",
                    "details": {},
                }
            ),
            404,
        )

    return jsonify(_serialize_article(article)), 200
