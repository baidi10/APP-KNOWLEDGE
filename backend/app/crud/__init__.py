"""
CRUD package – Data Access Layer
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 2 (Data Access)

This package exposes the two repository singletons used throughout the app:

    from app.crud import article_repo, tag_repo

Each repository is a stateless object (no instance state) – it is safe to
share a single instance across all requests. The SQLAlchemy `Session` is
always passed in per-call, keeping the repositories fully compatible with
FastAPI's `Depends(get_db)` dependency injection.
"""

from app.crud.crud_article import ArticleRepository
from app.crud.crud_tag import TagRepository

# ---------------------------------------------------------------------------
# Module-level singletons – import these instead of instantiating directly.
# ---------------------------------------------------------------------------
article_repo: ArticleRepository = ArticleRepository()
tag_repo: TagRepository = TagRepository()

__all__ = [
    "ArticleRepository",
    "TagRepository",
    "article_repo",
    "tag_repo",
]
