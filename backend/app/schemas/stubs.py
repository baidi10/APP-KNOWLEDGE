"""
Temporary Placeholder Schemas — Article
Project : AdoptAI App Knowledge Base
Author  : Oussama  (temporary stubs only)
Stage   : 3 (Core APIs & Errors)

╔══════════════════════════════════════════════════════════════════════════╗
║  ⚠  INTEGRATION BOUNDARY — FOR SAFOUANE (Task B7)                      ║
║                                                                          ║
║  The schemas in this file are TEMPORARY STUBS created solely to allow   ║
║  Oussama's B10 endpoint to run and be tested while Safouane's full      ║
║  Pydantic schema set (B7) is in progress.                               ║
║                                                                          ║
║  REPLACEMENT INSTRUCTIONS FOR SAFOUANE:                                 ║
║  1. Create your canonical schemas in `app/schemas/article.py`           ║
║     (or whatever path fits your schema package structure).              ║
║  2. In `app/api/endpoints/articles.py`, replace the import:            ║
║         from app.schemas.stubs import ArticleResponseStub               ║
║     with:                                                                ║
║         from app.schemas.article import ArticleResponse                 ║
║  3. In the route decorator, change `response_model=ArticleResponseStub` ║
║     to `response_model=ArticleResponse`.                                ║
║  4. Delete this file once the swap is complete.                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Nested stubs  (mirror the ORM relationships just enough for serialisation)
# ---------------------------------------------------------------------------

class CategoryStub(BaseModel):
    """Minimal Category representation — replace with Safouane's CategoryResponse."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class TagStub(BaseModel):
    """Minimal Tag representation — replace with Safouane's TagResponse."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


# ---------------------------------------------------------------------------
# ArticleResponseStub  (the placeholder used by B10)
# ---------------------------------------------------------------------------

class ArticleResponseStub(BaseModel):
    """
    Temporary response schema for Article endpoints.

    Includes all scalar columns and the two relationships (category, tags)
    so the B10 endpoint returns a usable, self-consistent payload while
    Safouane's full schema (with validators, computed fields, etc.) is built.

    `from_attributes=True` enables direct construction from a SQLAlchemy ORM
    instance (replaces the deprecated `orm_mode = True` of Pydantic v1).
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    content: str
    status: str                         # ArticleStatus.value → plain string
    category_id: Optional[int] = None
    category: Optional[CategoryStub] = None
    tags: List[TagStub] = []
    created_at: datetime
    updated_at: datetime
