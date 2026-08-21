"""
B4 - Category Data Model
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 1 (Foundation)

Category is a top-level taxonomy entity.
Each Article belongs to exactly one Category (nullable FK,
so articles can be uncategorized if needed).
"""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# TYPE_CHECKING guard avoids circular imports at runtime while still
# providing full type information for IDEs and static analysers.
if TYPE_CHECKING:
    from app.models.article import Article


class Category(Base, TimestampMixin):
    """
    Represents an article category (e.g., "SAP", "ServiceNow", "Apple").

    Columns
    -------
    id          : Auto-incremented primary key.
    name        : Human-readable category label. Must be globally unique.
    slug        : URL-safe identifier (e.g., "service-now"). Unique & indexed
                  for fast slug-based lookups from the frontend router.
    description : Optional long-form description of the category.

    Relationships
    -------------
    articles : One-to-Many → Article.
               `back_populates` keeps both sides of the relationship in sync.
               `lazy="select"` (SQLAlchemy default) – articles are loaded on
               first access; override with `joined` or `subquery` per query.
    """

    __tablename__ = "categories"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
        doc="Auto-incremented primary key.",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        doc="Unique human-readable category name (max 100 chars).",
    )

    slug: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
        nullable=False,
        doc="URL-safe unique identifier for the category (max 120 chars).",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
        doc="Optional long-form description of this category.",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    articles: Mapped[List["Article"]] = relationship(
        "Article",
        back_populates="category",
        # When a Category is deleted, set article.category_id → NULL
        # rather than cascading the delete (preserves articles).
        passive_deletes=True,
        doc="All articles belonging to this category.",
    )

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"<Category id={self.id} slug={self.slug!r}>"
