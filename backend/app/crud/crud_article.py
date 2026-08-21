"""
B23 - Article Repository (CRUD)
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 2 (Data Access)

Implements all data-access operations for the `Article` entity using
SQLAlchemy 2.0 patterns:
  - `select()` query construction
  - `session.scalars()` / `session.execute()` for result fetching
  - `selectinload` for eager loading of related Category and Tags
    (prevents N+1 queries when serialising responses in Stage 3+)

Design principles
-----------------
* The session is NEVER committed here. Commit / rollback is the caller's
  responsibility (typically the FastAPI route or a service layer). This
  keeps the repository focused purely on data-access and makes it trivially
  testable with a rolled-back test session.
* Every public method has a clear return type annotation so IDEs and the
  Pydantic response serialiser can reason about the data without reflection.
* `get_with_relations` always eager-loads Category and Tags in a single
  additional SELECT (selectinload strategy) – safe for both small and large
  result sets.
"""

from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.article import Article, ArticleStatus
from app.models.category import Category
from app.models.tag import Tag


class ArticleRepository:
    """
    Stateless repository for Article CRUD operations.

    All methods accept an explicit `db: Session` argument so the repository
    works seamlessly with FastAPI's `Depends(get_db)` pattern and is fully
    unit-testable without a real database.
    """

    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def get(self, db: Session, article_id: int) -> Optional[Article]:
        """
        Fetch a single article by primary key WITHOUT eagerly loading
        relations.

        Use this when you only need scalar article fields (e.g., existence
        check, status toggle) and want to avoid the overhead of extra SELECTs.

        Returns None if no article with the given id exists.
        """
        stmt = select(Article).where(Article.id == article_id)
        return db.scalars(stmt).first()

    def get_with_relations(self, db: Session, article_id: int) -> Optional[Article]:
        """
        Fetch a single article by primary key WITH Category and Tags
        eagerly loaded via `selectinload`.

        SQLAlchemy will emit at most 2 additional SELECTs (one for category,
        one for tags) instead of potentially hundreds of lazy-load calls.

        Use this as the primary fetch method for GET /articles/{id} (B10)
        and PUT /articles/{id} (B12) responses.

        Returns None if no article with the given id exists.
        """
        stmt = (
            select(Article)
            .where(Article.id == article_id)
            .options(
                selectinload(Article.category),
                selectinload(Article.tags),
            )
        )
        return db.scalars(stmt).first()

    def get_by_slug(self, db: Session, slug: str) -> Optional[Article]:
        """
        Fetch a single article by its URL-safe slug WITH relations eagerly
        loaded.

        Slugs are unique (enforced at DB level), so at most one row is
        returned. Returns None if the slug does not exist.
        """
        stmt = (
            select(Article)
            .where(Article.slug == slug)
            .options(
                selectinload(Article.category),
                selectinload(Article.tags),
            )
        )
        return db.scalars(stmt).first()

    def get_all(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 20,
        status: Optional[ArticleStatus] = None,
        category_id: Optional[int] = None,
    ) -> Sequence[Article]:
        """
        Return a paginated list of articles with optional filters.

        Parameters
        ----------
        skip        : Number of rows to skip (OFFSET) – for pagination.
        limit       : Maximum rows to return (LIMIT) – capped at 100 for safety.
        status      : Filter by ArticleStatus (draft | published | archived).
        category_id : Filter by category FK – used by B15 (Stage 4).

        The WHERE clauses are added conditionally so unused filters do not
        affect query performance. Relations are eagerly loaded to avoid N+1
        issues when serialising list responses.
        """
        limit = min(limit, 100)  # Hard cap – protects against large result sets.

        stmt = select(Article).options(
            selectinload(Article.category),
            selectinload(Article.tags),
        )

        if status is not None:
            stmt = stmt.where(Article.status == status)

        if category_id is not None:
            stmt = stmt.where(Article.category_id == category_id)

        stmt = stmt.order_by(Article.created_at.desc()).offset(skip).limit(limit)

        return db.scalars(stmt).all()

    def count(
        self,
        db: Session,
        *,
        status: Optional[ArticleStatus] = None,
        category_id: Optional[int] = None,
    ) -> int:
        """
        Return the total number of articles matching the given filters.

        Used alongside `get_all` to compute pagination metadata
        (total pages, current page, etc.) without fetching full rows.
        """
        from sqlalchemy import func as sa_func

        stmt = select(sa_func.count(Article.id))

        if status is not None:
            stmt = stmt.where(Article.status == status)
        if category_id is not None:
            stmt = stmt.where(Article.category_id == category_id)

        result = db.execute(stmt).scalar_one()
        return result

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create(
        self,
        db: Session,
        *,
        title: str,
        slug: str,
        content: str,
        status: ArticleStatus = ArticleStatus.DRAFT,
        category_id: Optional[int] = None,
        tags: Optional[List[Tag]] = None,
    ) -> Article:
        """
        Persist a new Article to the database.

        Parameters
        ----------
        title       : Article headline.
        slug        : URL-safe unique identifier.
        content     : Full article body.
        status      : Initial lifecycle state (defaults to DRAFT).
        category_id : Optional FK to an existing Category.
        tags        : Optional list of Tag ORM instances to associate.

        The new Article is added to the session and flushed (so the DB
        assigns `id`, `created_at`, `updated_at`) but NOT committed.
        The caller must commit when ready.

        Returns the flushed Article instance (with `id` populated).
        """
        article = Article(
            title=title,
            slug=slug,
            content=content,
            status=status,
            category_id=category_id,
            tags=tags or [],
        )
        db.add(article)
        db.flush()          # Sends INSERT, populates article.id from DB sequence.
        db.refresh(article) # Re-reads server defaults (created_at, updated_at).
        return article

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(
        self,
        db: Session,
        *,
        article: Article,
        title: Optional[str] = None,
        slug: Optional[str] = None,
        content: Optional[str] = None,
        status: Optional[ArticleStatus] = None,
        category_id: Optional[int] = None,
        tags: Optional[List[Tag]] = None,
    ) -> Article:
        """
        Apply a partial update to an existing Article instance.

        Only fields that are explicitly passed (not None) are modified,
        implementing a clean PATCH-style update even for a PUT endpoint –
        the route handler controls which fields are present.

        The `article` argument must already be attached to `db` (i.e.,
        fetched in the same session). No second SELECT is performed here.

        Returns the updated Article instance (not yet committed).
        """
        if title is not None:
            article.title = title
        if slug is not None:
            article.slug = slug
        if content is not None:
            article.content = content
        if status is not None:
            article.status = status
        if category_id is not None:
            article.category_id = category_id
        if tags is not None:
            # Replacing the entire tags collection correctly updates the
            # article_tags join table via SQLAlchemy's relationship machinery.
            article.tags = tags

        db.flush()
        db.refresh(article)
        return article

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete(self, db: Session, *, article: Article) -> None:
        """
        Delete an Article and its join-table entries (article_tags).

        The join-table rows are removed automatically because both FK
        columns have `ondelete="CASCADE"` at the DB level. No manual
        cleanup of article_tags is needed.

        The `article` argument must already be attached to `db`.
        The deletion is flushed but NOT committed – the caller commits.
        """
        db.delete(article)
        db.flush()

    # ------------------------------------------------------------------
    # Existence helpers
    # ------------------------------------------------------------------

    def slug_exists(self, db: Session, slug: str, exclude_id: Optional[int] = None) -> bool:
        """
        Check whether a given slug is already taken by another article.

        `exclude_id` allows the current article's own slug to be excluded
        during a PUT update (so unchanged slugs don't falsely report a conflict).

        Returns True if the slug is taken, False otherwise.
        """
        stmt = select(Article.id).where(Article.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(Article.id != exclude_id)
        result = db.execute(stmt).first()
        return result is not None
