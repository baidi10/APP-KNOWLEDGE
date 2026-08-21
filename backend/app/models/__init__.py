"""
models/__init__.py
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 1 (Foundation)

Central import hub for all ORM models.

WHY THIS FILE EXISTS
--------------------
Alembic's `env.py` and any `Base.metadata.create_all(engine)` call need
`Base.metadata` to already contain every table definition at the time they
run. Importing each model here guarantees they are all registered with the
shared `Base` before metadata is accessed, regardless of which module
triggers the import first.

USAGE
-----
In alembic/env.py (or main.py for create_all):

    from app.models import Base          # metadata is fully populated
    from app.core.database import engine
    Base.metadata.create_all(engine)
"""

from app.models.base import Base, TimestampMixin        # noqa: F401
from app.models.category import Category                # noqa: F401 – registers `categories`
from app.models.tag import Tag, article_tags            # noqa: F401 – registers `tags` + `article_tags`
from app.models.article import Article, ArticleStatus   # noqa: F401 – registers `articles`

__all__ = [
    "Base",
    "TimestampMixin",
    "Category",
    "Tag",
    "article_tags",
    "Article",
    "ArticleStatus",
]
