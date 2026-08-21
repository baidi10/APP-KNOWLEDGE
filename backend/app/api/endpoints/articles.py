"""
B10 / B12 / B13 - Article Endpoints (GET, PUT, DELETE)
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stages  : 3 & 4 (Core APIs & Advanced Endpoints)

This module defines the articles API router and implements:
  - GET    /articles/{id}  — B10  (Stage 3)
  - PUT    /articles/{id}  — B12  (Stage 4)
  - DELETE /articles/{id}  — B13  (Stage 4)

Architecture notes
------------------
* Router prefix `/articles` is applied in `app/api/router.py`.
* `get_db` injects a per-request SQLAlchemy Session (Stage 1, database.py).
* `article_repo` / `tag_repo` are Stage-2 singletons (crud/__init__.py).
* All 404 paths raise `ArticleNotFoundException` (B19), caught and serialised
  by the centralised handler registered in `main.py` (B20).
* Schema stubs (`ArticleResponseStub`, `ArticleUpdateStub`) are temporary.
  See `app/schemas/stubs.py` for Safouane's (B7/B8) replacement guide.
"""

import logging

from fastapi import APIRouter, Body, Depends, Path, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ArticleNotFoundException, ArticleSlugConflictException
from app.crud import article_repo, tag_repo
from app.models.article import ArticleStatus
from app.schemas.stubs import ArticleResponseStub, ArticleUpdateStub

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


# ---------------------------------------------------------------------------
# PUT /articles/{id}  — B12
# ---------------------------------------------------------------------------

@router.put(
    "/{article_id}",
    response_model=ArticleResponseStub,   # TODO(Safouane/B7): replace with ArticleResponse
    status_code=status.HTTP_200_OK,
    summary="Update an article by ID",
    description=(
        "Performs a partial update on a knowledge-base article. "
        "Only the fields included in the request body are modified; "
        "omitted fields retain their current values. "
        "Returns the full updated article on success. "
        "Returns **404** if the article does not exist, "
        "**409** if the new slug is already taken by another article."
    ),
    responses={
        200: {"description": "Article updated and returned successfully."},
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
        409: {
            "description": "The requested slug is already taken by another article.",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "ARTICLE_SLUG_CONFLICT",
                            "message": "An article with slug 'my-slug' already exists.",
                            "status": 409,
                        }
                    }
                }
            },
        },
    },
)
def update_article(
    article_id: int = Path(
        ...,
        ge=1,
        description="The numeric primary key of the article to update.",
        example=1,
    ),
    body: ArticleUpdateStub = Body(   # TODO(Safouane/B8): replace with ArticleUpdate
        ...,
        description="Fields to update. All fields are optional; omit any field to keep its current value.",
    ),
    db: Session = Depends(get_db),
) -> ArticleResponseStub:
    """
    **PUT /articles/{article_id}**

    Partially updates a knowledge-base article.

    - **article_id**: Positive integer primary key of the article to update.
    - **body**: JSON object with one or more updatable fields (`title`, `slug`,
      `content`, `status`, `category_id`, `tag_ids`). Any omitted field is
      left unchanged.

    **Validation flow**:
    1. Fetch the article → 404 if not found.
    2. If a new `slug` is supplied, verify it is not already used by a
       *different* article → 409 if conflict.
    3. If `tag_ids` are supplied, resolve them to Tag ORM instances.
    4. Call `article_repo.update()`, flush, commit.
    5. Re-fetch with relations eagerly loaded and return.
    """
    logger.info("PUT /articles/%s — updating article", article_id)

    # Step 1: Confirm article exists.
    article = article_repo.get(db, article_id)
    if article is None:
        logger.warning("PUT /articles/%s — article not found", article_id)
        raise ArticleNotFoundException(article_id)

    # Step 2: Slug uniqueness check (only when a new slug is supplied).
    if body.slug is not None and body.slug != article.slug:
        if article_repo.slug_exists(db, body.slug, exclude_id=article_id):
            logger.warning(
                "PUT /articles/%s — slug conflict: %r", article_id, body.slug
            )
            raise ArticleSlugConflictException(body.slug)

    # Step 3: Resolve tag_ids → Tag ORM instances (if provided).
    resolved_tags = None
    if body.tag_ids is not None:
        resolved_tags = list(tag_repo.get_by_ids(db, body.tag_ids))

    # Step 4: Apply the partial update.
    # Convert status string → ArticleStatus enum if provided.
    new_status = None
    if body.status is not None:
        new_status = ArticleStatus(body.status)

    article_repo.update(
        db,
        article=article,
        title=body.title,
        slug=body.slug,
        content=body.content,
        status=new_status,
        category_id=body.category_id,
        tags=resolved_tags,
    )

    # Commit after successful update.
    db.commit()

    # Step 5: Re-fetch with relations for the full response payload.
    updated = article_repo.get_with_relations(db, article_id)
    logger.info("PUT /articles/%s — updated successfully", article_id)
    return updated  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# DELETE /articles/{id}  — B13
# ---------------------------------------------------------------------------

@router.delete(
    "/{article_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an article by ID",
    description=(
        "Permanently deletes a knowledge-base article and all its tag associations. "
        "Returns **204 No Content** on success (no response body). "
        "Returns **404** if the article does not exist."
    ),
    responses={
        204: {"description": "Article deleted successfully. No content is returned."},
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
def delete_article(
    article_id: int = Path(
        ...,
        ge=1,
        description="The numeric primary key of the article to delete.",
        example=1,
    ),
    db: Session = Depends(get_db),
) -> Response:
    """
    **DELETE /articles/{article_id}**

    Permanently removes a knowledge-base article from the database.

    - **article_id**: Positive integer primary key of the article to delete.
    - The `article_tags` join-table rows are removed automatically by the
      PostgreSQL `ON DELETE CASCADE` constraint — no manual cleanup needed.
    - Returns HTTP **204 No Content** with an empty body on success.
      (RFC 9110 §15.3.5 — clients must not expect a body on 204.)
    - Raises `ArticleNotFoundException` (→ 404) if no article with the
      given id exists.
    """
    logger.info("DELETE /articles/%s — deleting article", article_id)

    # Step 1: Confirm the article exists before attempting deletion.
    article = article_repo.get(db, article_id)
    if article is None:
        logger.warning("DELETE /articles/%s — article not found", article_id)
        raise ArticleNotFoundException(article_id)

    # Step 2: Delete + commit.
    article_repo.delete(db, article=article)
    db.commit()

    logger.info("DELETE /articles/%s — deleted successfully", article_id)

    # Return an explicit empty Response with 204 so FastAPI does not attempt
    # to serialise the None return value (which would cause a runtime error
    # since response_model is absent on this route).
    return Response(status_code=status.HTTP_204_NO_CONTENT)
