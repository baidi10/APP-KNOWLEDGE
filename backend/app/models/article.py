"""
B3 - Article Data Model
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 1 (Foundation)

Article is the central entity of the knowledge base. It belongs to one
Category (nullable) and can have many Tags (Many-to-Many via article_tags).
"""

import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.tag import Tag, article_tags

# TYPE_CHECKING guard prevents circular imports at runtime.
if TYPE_CHECKING:
    from app.models.category import Category


# ---------------------------------------------------------------------------
# Article Status Enum
# ---------------------------------------------------------------------------
class ArticleStatus(str, enum.Enum):
    """
    Lifecycle state of an article.

    Using `str` as a mixin makes the enum JSON-serialisable by default
    (FastAPI / Pydantic will see plain strings), while still providing
    the safety of an enum type in Python and the database.

    draft     – Work-in-progress; not visible to end users.
    published – Approved and live in the knowledge base.
    archived  – Removed from active listings but preserved for history.
    """
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# ---------------------------------------------------------------------------
# Article ORM Model
# ---------------------------------------------------------------------------
class Article(Base, TimestampMixin):
    """
    Represents a knowledge-base article authored within AdoptAI.

    Columns
    -------
    id          : Auto-incremented primary key.
    title       : Article headline. Indexed for fast search/ordering.
    slug        : URL-safe unique identifier (e.g., "how-to-reset-sap-password").
    content     : Full article body (plain text or Markdown).
    status      : Lifecycle state – one of ArticleStatus (draft/published/archived).
    category_id : FK → categories.id (nullable; article can be uncategorised).

    Relationships
    -------------
    category : Many-to-One → Category  (nullable)
    tags     : Many-to-Many → Tag  (via article_tags association table)

    Indexes
    -------
    A composite index on (status, category_id) is added to accelerate the
    most common query pattern: filtered listing by status and/or category
    (used by B15 – category filtering, Stage 4).
    """

    __tablename__ = "articles"

    # Composite index for frequent filter queries (status + category_id).
    # Declared via __table_args__ so SQLAlchemy registers it with the table
    # rather than as a column-level index.
    __table_args__ = (
        Index("ix_articles_status_category", "status", "category_id"),
    )

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        doc="Auto-incremented primary key.",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
        doc="Article headline (max 255 chars).",
    )

    slug: Mapped[str] = mapped_column(
        String(300),
        unique=True,
        index=True,
        nullable=False,
        doc="URL-safe unique identifier for the article (max 300 chars).",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Full article body (plain text or Markdown).",
    )

    status: Mapped[ArticleStatus] = mapped_column(
        # SAEnum stores the string value in the DB (e.g., "draft"),
        # not the Python enum name – keeps the DB column human-readable.
        SAEnum(ArticleStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ArticleStatus.DRAFT,
        server_default=ArticleStatus.DRAFT.value,
        index=True,
        doc="Article lifecycle state (draft | published | archived).",
    )

    category_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        doc="FK to the owning Category. NULL means the article is uncategorised.",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    category: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="articles",
        # Load category in the same SELECT as the article when explicitly
        # requested (lazy="select" keeps behaviour predictable by default).
        lazy="select",
        doc="The category this article belongs to (nullable).",
    )

    tags: Mapped[List[Tag]] = relationship(
        Tag,
        secondary=article_tags,
        back_populates="articles",
        lazy="select",
        doc="Tags associated with this article (Many-to-Many).",
    )

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<Article id={self.id} slug={self.slug!r} status={self.status.value!r}>"
        )
