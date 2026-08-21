"""
B5 - Tag Data Model & article_tags Association Table
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 1 (Foundation)

Tags implement a Many-to-Many relationship with Articles via an explicit
association table (`article_tags`). Using `Table()` instead of a full ORM
model is the correct SQLAlchemy 2.0 pattern for pure join tables that carry
no extra columns.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# TYPE_CHECKING guard prevents circular import at runtime.
if TYPE_CHECKING:
    from app.models.article import Article


# ---------------------------------------------------------------------------
# Association Table  –  article_tags
# ---------------------------------------------------------------------------
# Declared at module level (outside any class) so it is registered with
# Base.metadata and picked up by Alembic / create_all automatically.
# Composite primary key (article_id + tag_id) enforces uniqueness and
# doubles as the index – no separate PK column needed.
# ---------------------------------------------------------------------------
article_tags = Table(
    "article_tags",
    Base.metadata,
    Column(
        "article_id",
        Integer,
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "tag_id",
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    # Audit column: when was this tag applied to this article?
    Column(
        "tagged_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
)


# ---------------------------------------------------------------------------
# Tag ORM Model
# ---------------------------------------------------------------------------
class Tag(Base):
    """
    Represents a keyword tag that can be applied to multiple Articles.

    Columns
    -------
    id         : Auto-incremented primary key.
    name       : Human-readable tag label. Globally unique (e.g., "Python").
    slug       : URL-safe identifier (e.g., "python"). Unique & indexed.
    created_at : Server-managed creation timestamp.

    Relationships
    -------------
    articles : Many-to-Many → Article (via `article_tags` join table).
               Cascade "all, delete-orphan" is NOT set here because the
               association table itself handles cascade via `ondelete="CASCADE"`.
    """

    __tablename__ = "tags"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
        doc="Auto-incremented primary key.",
    )

    name: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        index=True,
        nullable=False,
        doc="Unique human-readable tag name (max 80 chars).",
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        doc="URL-safe unique identifier for the tag (max 100 chars).",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp of tag creation (UTC, set by the database server).",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    articles: Mapped[List["Article"]] = relationship(
        "Article",
        secondary=article_tags,
        back_populates="tags",
        doc="All articles associated with this tag.",
    )

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<Tag id={self.id} slug={self.slug!r}>"
