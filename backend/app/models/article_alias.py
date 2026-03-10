"""ArticleAlias model — alternative names/codes for article search."""

from app.extensions import db


class ArticleAlias(db.Model):
    __tablename__ = "article_alias"

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(
        db.Integer, db.ForeignKey("article.id"), nullable=False
    )
    alias = db.Column(db.String, nullable=False)
    normalized = db.Column(db.String, nullable=False)
