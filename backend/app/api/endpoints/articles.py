"""
B10 - GET /articles/{id} Endpoint
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 3 (Core APIs & Errors)

This module defines the articles API router and implements the first
endpoint: GET /articles/{id}.

Architecture notes
------------------
* The router is mounted at `/articles` in `app/api/router.py` — the prefix
  is set there, NOT here, which keeps this file portable and testable.
* The `get_db` dependency injects a SQLAlchemy Session scoped to the request.
* `article_repo` is the singleton from Stage 2 (crud/__init__.py).
* `ArticleNotFoundException` (B19) is raised here, caught by the centralised
  handler registered in `main.py`, and converted to a structured 404 JSON
  response automatically.
* `response_model=ArticleResponseStub` is the TEMPORARY placeholder.
  Safouane replaces it with `ArticleResponse` from his B7 schema work.
  See `app/schemas/stubs.py` for the full replacement guide.
"""

import logging

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ArticleNotFoundException
from app.crud import article_repo
from app.schemas.stubs import ArticleResponseStub

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
# tags=["Articles"] groups all endpoints in this module under a single section
# in the auto-generated OpenAPI / Swagger UI documentation.
# ---------------------------------------------------------------------------
router = APIRouter(tags=["Articles"])


# ---------------------------------------------------------------------------
# GET /articles/{id}  — B10
# ---------------------------------------------------------------------------

@router.get(
    "/{article_id}",
    response_model=ArticleResponseStub,   # TODO(Safouane/B7): replace with ArticleResponse
    status_code=status.HTTP_200_OK,
    summary="Retrieve an article by ID",
    description=(
        "Fetches a single knowledge-base article by its numeric primary key. "
        "The response includes the article's full content, its parent category, "
        "and all associated tags. Returns **404** if the article does not exist."
    ),
    responses={
        200: {"description": "Article found and returned successfully."},
        404: {
            "description": "No article exists with the given id.",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "ARTICLE_NOT_FOUND",
                            "message": "Article with id '42' was not found.",
                            "status": 404,
                        }
                    }
                }
            },
        },
    },
)
def get_article_by_id(
    article_id: int = Path(
        ...,
        ge=1,                           # Must be a positive integer ≥ 1.
        description="The numeric primary key of the article to retrieve.",
        example=1,
    ),
    db: Session = Depends(get_db),
) -> ArticleResponseStub:
    """
    **GET /articles/{article_id}**

    Retrieves a knowledge-base article by its numeric primary key.

    - **article_id**: Must be a positive integer (`>= 1`). Non-integer or
      zero/negative values are rejected by FastAPI's path validation with a
      422 error before this function is even called.

    - On success, returns a full article object including its parent
      `category` and associated `tags` (both eagerly loaded — no N+1 queries).

    - Raises `ArticleNotFoundException` (→ 404) if no article with the given
      id exists. The exception is caught by the centralised handler registered
      in `main.py` and converted to the standard error JSON envelope.
    """
    logger.info("GET /articles/%s — fetching article", article_id)

    article = article_repo.get_with_relations(db, article_id)

    if article is None:
        logger.warning("GET /articles/%s — article not found", article_id)
        raise ArticleNotFoundException(article_id)   # B19 – 404 handling

    logger.info("GET /articles/%s — found article slug=%r", article_id, article.slug)
    return article  # type: ignore[return-value]  # Pydantic's from_attributes handles ORM → schema
