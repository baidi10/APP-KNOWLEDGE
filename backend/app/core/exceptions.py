"""
B20 & B19 - Centralized Exception Hierarchy
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 3 (Core APIs & Errors)

This module defines the project-wide custom exception classes.
Every domain exception inherits from `AppBaseException`, which carries a
structured payload (HTTP status, error code, message) that the centralized
exception handlers in `error_handlers.py` convert into a consistent JSON
error response.

Error response contract (returned to the client on every error):
    {
        "error": {
            "code":    "ARTICLE_NOT_FOUND",      ← machine-readable slug
            "message": "Article with id 42 ...", ← human-readable description
            "status":  404                        ← mirrors the HTTP status code
        }
    }

Why a custom hierarchy instead of raising HTTPException directly?
-----------------------------------------------------------------
1. Domain clarity  – route code reads `raise ArticleNotFoundException(42)`
   instead of inline `raise HTTPException(status_code=404, detail="...")`.
2. Testability     – unit tests can assert on exception TYPE, not on HTTP
   detail strings that may be refactored.
3. Single source of truth – all error codes and messages are defined here,
   not scattered across endpoint files.
4. Extensibility   – adding a new domain error requires a single class;
   the handler registration in `error_handlers.py` picks it up automatically.
"""

from http import HTTPStatus


# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------

class AppBaseException(Exception):
    """
    Root of the AdoptAI exception hierarchy.

    All custom application exceptions must inherit from this class so the
    centralized exception handler can catch them with a single `except` clause.

    Attributes
    ----------
    status_code : HTTP status code to return (integer, e.g. 404).
    error_code  : Machine-readable ALL_CAPS_SNAKE_CASE code (e.g. "NOT_FOUND").
    message     : Human-readable description suitable for display in API docs
                  and client error messages.
    """

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        # Allow per-instance overrides while keeping class-level defaults.
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """
        Serialise the exception into the standard error response body.

        Used by the FastAPI exception handler to build the JSON response.
        """
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "status": self.status_code,
            }
        }


# ---------------------------------------------------------------------------
# 404 Not Found exceptions
# ---------------------------------------------------------------------------

class NotFoundException(AppBaseException):
    """
    Generic 404 – raised when a requested resource does not exist.
    Subclassed by entity-specific variants below.
    """
    status_code = 404
    error_code = "NOT_FOUND"
    message = "The requested resource was not found."


class ArticleNotFoundException(NotFoundException):
    """
    B19 – Raised when GET /articles/{id} (or any other operation) targets an
    Article that does not exist in the database.

    Usage in route handlers:
        article = article_repo.get_with_relations(db, article_id)
        if article is None:
            raise ArticleNotFoundException(article_id)
    """
    error_code = "ARTICLE_NOT_FOUND"

    def __init__(self, article_id: int | str) -> None:
        super().__init__(
            message=f"Article with id '{article_id}' was not found.",
        )


class CategoryNotFoundException(NotFoundException):
    """Raised when a referenced Category id does not exist."""
    error_code = "CATEGORY_NOT_FOUND"

    def __init__(self, category_id: int | str) -> None:
        super().__init__(
            message=f"Category with id '{category_id}' was not found.",
        )


class TagNotFoundException(NotFoundException):
    """Raised when a referenced Tag id does not exist."""
    error_code = "TAG_NOT_FOUND"

    def __init__(self, tag_id: int | str) -> None:
        super().__init__(
            message=f"Tag with id '{tag_id}' was not found.",
        )


# ---------------------------------------------------------------------------
# 409 Conflict exceptions
# ---------------------------------------------------------------------------

class ConflictException(AppBaseException):
    """
    Generic 409 – raised when an operation would violate a uniqueness
    constraint (e.g., duplicate slug).
    """
    status_code = 409
    error_code = "CONFLICT"
    message = "A resource with the same unique identifier already exists."


class ArticleSlugConflictException(ConflictException):
    """Raised when creating/updating an article would produce a duplicate slug."""
    error_code = "ARTICLE_SLUG_CONFLICT"

    def __init__(self, slug: str) -> None:
        super().__init__(
            message=f"An article with slug '{slug}' already exists.",
        )


class TagNameConflictException(ConflictException):
    """Raised when creating a tag whose name is already taken."""
    error_code = "TAG_NAME_CONFLICT"

    def __init__(self, name: str) -> None:
        super().__init__(
            message=f"A tag with name '{name}' already exists.",
        )


# ---------------------------------------------------------------------------
# 422 Unprocessable Entity  (business-rule validation, distinct from Pydantic)
# ---------------------------------------------------------------------------

class ValidationException(AppBaseException):
    """
    422 – Raised for business-rule violations that Pydantic cannot catch
    (e.g., referencing a non-existent category_id in an article create).
    """
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "The submitted data failed business validation."


# ---------------------------------------------------------------------------
# 403 Forbidden
# ---------------------------------------------------------------------------

class ForbiddenException(AppBaseException):
    """403 – Reserved for future authorization stages."""
    status_code = 403
    error_code = "FORBIDDEN"
    message = "You do not have permission to perform this action."
