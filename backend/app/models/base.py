"""
DeclarativeBase & Shared Mixins
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 1 (Foundation)

All SQLAlchemy models inherit from `Base` (DeclarativeBase).
The `TimestampMixin` provides `created_at` and `updated_at` columns
that are managed automatically at the database level, making them
reliable regardless of the application layer.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Project-wide SQLAlchemy declarative base.

    Every ORM model must inherit from this class so that Alembic
    (or `Base.metadata.create_all`) can discover all tables in one place.
    """
    pass


class TimestampMixin:
    """
    Reusable mixin that adds `created_at` and `updated_at` columns.

    - `created_at` : set once by the DB server on INSERT; never changes.
    - `updated_at` : set on INSERT and refreshed on every UPDATE by the DB
                     server via `onupdate`. Using server defaults keeps the
                     value accurate even when rows are modified outside the app.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp of record creation (UTC, set by the database server).",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp of last record update (UTC, managed by the database server).",
    )
