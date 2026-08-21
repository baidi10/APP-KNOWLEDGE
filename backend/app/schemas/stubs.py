"""
Temporary Placeholder Schemas — Article
Project : AdoptAI App Knowledge Base
Author  : Oussama  (temporary stubs only)
Stages  : 3 & 4 (Core APIs & Advanced Endpoints)

╔══════════════════════════════════════════════════════════════════════════╗
║  ⚠  INTEGRATION BOUNDARY — FOR SAFOUANE (Tasks B7 & B8)               ║
║                                                                          ║
║  This file contains TEMPORARY STUBS that let Oussama's endpoints        ║
║  (B10 GET, B12 PUT, B13 DELETE) run while Safouane builds the full      ║
║  Pydantic schema set (B7 ArticleResponse, B8 ArticleUpdate).            ║
║                                                                          ║
║  REPLACEMENT INSTRUCTIONS FOR SAFOUANE:                                 ║
║                                                                          ║
║  ── Response schema (B7) ────────────────────────────────────────────── ║
║  1. Create `app/schemas/article.py` with `ArticleResponse`.             ║
║  2. In `articles.py`, swap:                                             ║
║       from app.schemas.stubs import ArticleResponseStub                 ║
║     → from app.schemas.article import ArticleResponse                   ║
║  3. Change `response_model=ArticleResponseStub`                         ║
║     → `response_model=ArticleResponse`  (on GET and PUT routes).       ║
║                                                                          ║
║  ── Update schema (B8) ──────────────────────────────────────────────── ║
║  4. Add `ArticleUpdate` to `app/schemas/article.py`.                    ║
║  5. In `articles.py`, swap:                                             ║
║       from app.schemas.stubs import ArticleUpdateStub                   ║
║     → from app.schemas.article import ArticleUpdate                     ║
║  6. Change the PUT function signature body type annotation accordingly. ║
║                                                                          ║
║  7. Delete this file once ALL swaps are complete.                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime
from typing import Annotated
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


# ---------------------------------------------------------------------------
# ArticleUpdateStub  (the placeholder used by B12 PUT)
# ---------------------------------------------------------------------------

class ArticleUpdateStub(BaseModel):
    """
    Temporary request body schema for PUT /articles/{id}.

    All fields are Optional so the endpoint supports partial updates
    (only supplied fields are forwarded to the repository's update() method).
    Safouane should replace this with a fully validated `ArticleUpdate`
    schema (B8) that adds field-level validators, min/max lengths, slug
    format checks, etc.

    ── Replacement guide (see banner at top of this file) ──────────────────
    Import:  from app.schemas.article import ArticleUpdate
    Swap:    body: ArticleUpdate  (in the PUT route function signature)
    Delete:  this class + import in articles.py
    """
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    # Accepts the string values of ArticleStatus: "draft", "published", "archived"
    status: Optional[str] = None
    category_id: Optional[int] = None
    # List of tag ids to associate with the article.
    # Safouane's ArticleUpdate may prefer tag names or nested objects.
    tag_ids: Optional[List[int]] = None
