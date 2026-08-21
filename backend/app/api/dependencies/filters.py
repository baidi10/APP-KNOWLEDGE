"""
B15 - Category Filtering Dependency
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 4 (Advanced Endpoints)

Provides a reusable FastAPI dependency (`CategoryFilterParams`) that
extracts, validates, and bundles category-related query parameters from
any incoming request.

WHY A DEPENDENCY INSTEAD OF INLINE QUERY PARAMS?
-------------------------------------------------
1. Reusability   – Any endpoint that supports category filtering (today:
                   Safouane's GET /articles; tomorrow: potentially GET /tags
                   or an admin list) injects this dependency without
                   duplicating the validation logic.
2. Testability   – The dependency is a plain dataclass; tests can construct
                   it directly without simulating an HTTP request.
3. Separation    – Filter logic is not tangled in the route handler, keeping
                   the handler focused on orchestration only.
4. OpenAPI docs  – FastAPI automatically documents the query parameters
                   extracted by a Depends() class with full descriptions and
                   type information in Swagger UI.

HOW SAFOUANE USES THIS IN GET /articles  (B9)
----------------------------------------------
In `app/api/endpoints/articles.py` (or his own endpoint file), Safouane
adds the dependency to any listing route:

    from fastapi import APIRouter, Depends
    from sqlalchemy.orm import Session

    from app.api.dependencies.filters import CategoryFilterParams
    from app.core.database import get_db
    from app.crud import article_repo

    router = APIRouter()

    @router.get("/", ...)
    def list_articles(
        filters: CategoryFilterParams = Depends(),
        db: Session = Depends(get_db),
    ):
        articles = article_repo.get_all(
            db,
            skip=filters.skip,
            limit=filters.limit,
            status=filters.status,
            category_id=filters.category_id,
        )
        total = article_repo.count(
            db,
            status=filters.status,
            category_id=filters.category_id,
        )
        return {"total": total, "items": articles}

Safouane should NOT modify this file. He only imports `CategoryFilterParams`
and injects it with `Depends()`.
"""

from dataclasses import dataclass
from typing import Optional

from fastapi import Query

from app.models.article import ArticleStatus


# ---------------------------------------------------------------------------
# Pagination constants (project-wide defaults, adjust per team agreement)
# ---------------------------------------------------------------------------
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100


@dataclass
class CategoryFilterParams:
    """
    FastAPI dependency that captures and validates category-related query
    parameters for list endpoints.

    Inject into any route with `Depends()`:
        filters: CategoryFilterParams = Depends()

    FastAPI will automatically:
      - Extract each field from the query string.
      - Validate types and constraints (ge/le).
      - Display each field as a documented query parameter in Swagger UI.

    Fields
    ------
    category_id : Filter articles to a specific category by its numeric id.
                  Omit (or pass `null`) to return articles from all categories.

    status      : Filter articles by lifecycle state.
                  Accepted values: "draft", "published", "archived".
                  Omit to return articles in all states.

    skip        : Pagination offset (number of records to skip). Min: 0.

    limit       : Pagination page size. Min: 1, Max: 100 (capped server-side).
    """

    # ------------------------------------------------------------------
    # Category filter  (B15 core)
    # ------------------------------------------------------------------
    category_id: Optional[int] = Query(
        default=None,
        ge=1,
        description=(
            "Numeric ID of the category to filter by. "
            "Returns only articles belonging to this category. "
            "Omit to include articles from all categories."
        ),
        example=3,
    )

    # ------------------------------------------------------------------
    # Status filter  (natural companion to category filter)
    # ------------------------------------------------------------------
    status: Optional[ArticleStatus] = Query(
        default=None,
        description=(
            "Filter by article lifecycle status. "
            "Accepted values: `draft`, `published`, `archived`. "
            "Omit to include articles in all states."
        ),
        example=ArticleStatus.PUBLISHED,
    )

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip (pagination offset). Must be ≥ 0.",
        example=0,
    )

    limit: int = Query(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=(
            f"Maximum number of records to return per page. "
            f"Must be between 1 and {MAX_PAGE_SIZE}. "
            f"Defaults to {DEFAULT_PAGE_SIZE}."
        ),
        example=DEFAULT_PAGE_SIZE,
    )

    # ------------------------------------------------------------------
    # Convenience helpers (used internally by the repository calls)
    # ------------------------------------------------------------------

    def has_category_filter(self) -> bool:
        """True if a category_id filter was provided."""
        return self.category_id is not None

    def has_status_filter(self) -> bool:
        """True if a status filter was provided."""
        return self.status is not None

    def as_repo_kwargs(self) -> dict:
        """
        Return a dict of keyword arguments ready to be unpacked into
        `article_repo.get_all(db, **filters.as_repo_kwargs())`.

        This shields the route handler from knowing the repository's exact
        parameter names — if the repo signature ever changes, only this
        method needs updating.
        """
        return {
            "skip": self.skip,
            "limit": self.limit,
            "status": self.status,
            "category_id": self.category_id,
        }
