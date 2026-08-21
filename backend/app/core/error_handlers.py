"""
B20 - Centralized Exception Handlers (FastAPI registration)
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 3 (Core APIs & Errors)

This module contains the actual FastAPI handler functions and a single
`register_exception_handlers(app)` helper that is called once in `main.py`.

Keeping handler registration separate from the exception class definitions
(exceptions.py) means:
  - `exceptions.py` has zero FastAPI dependency → pure Python, 100% testable.
  - This file owns the "wire-up" concern and can be modified without touching
    domain exception classes.

All handlers return the same JSON shape:
    {
        "error": {
            "code":    "ARTICLE_NOT_FOUND",
            "message": "Article with id 42 was not found.",
            "status":  404
        }
    }
This consistency lets the frontend (Safouane's team) handle all errors with
a single response interceptor.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppBaseException

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Handler: all custom AppBaseException subclasses  (B19 + B20 core)
# ---------------------------------------------------------------------------

async def app_exception_handler(
    request: Request,
    exc: AppBaseException,
) -> JSONResponse:
    """
    Catches every custom domain exception (ArticleNotFoundException,
    ConflictException, etc.) and converts it to the standard error JSON body.

    The `exc.to_dict()` call produces the structured payload defined in
    exceptions.py so no formatting logic lives here.
    """
    logger.warning(
        "Domain exception [%s] on %s %s: %s",
        exc.error_code,
        request.method,
        request.url.path,
        exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


# ---------------------------------------------------------------------------
# Handler: FastAPI / Starlette native HTTPException
# ---------------------------------------------------------------------------

async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """
    Wraps Starlette's built-in HTTPException (e.g., 405 Method Not Allowed,
    404 from Starlette's routing) into the same standard error envelope so
    clients always receive a uniform JSON structure regardless of error source.
    """
    logger.warning(
        "HTTP exception [%s] on %s %s: %s",
        exc.status_code,
        request.method,
        request.url.path,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": _status_to_code(exc.status_code),
                "message": str(exc.detail),
                "status": exc.status_code,
            }
        },
    )


# ---------------------------------------------------------------------------
# Handler: Pydantic v2 RequestValidationError (422)
# ---------------------------------------------------------------------------

async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Intercepts Pydantic v2 validation errors raised by FastAPI's request
    parsing (wrong types, missing required fields, etc.) and converts them
    into the standard error envelope with a `details` sub-key listing each
    field-level failure.

    The `details` array gives the frontend enough context to highlight the
    specific form fields that failed validation.
    """
    details = [
        {
            "field": " → ".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]
    logger.warning(
        "Request validation error on %s %s: %s",
        request.method,
        request.url.path,
        details,
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "REQUEST_VALIDATION_ERROR",
                "message": "One or more request fields failed validation.",
                "status": 422,
                "details": details,
            }
        },
    )


# ---------------------------------------------------------------------------
# Handler: catch-all for unexpected exceptions (500)
# ---------------------------------------------------------------------------

async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Safety net for any exception not caught by the handlers above.

    Logs the full traceback (with exc_info=True) for debugging while
    returning a sanitized 500 response to the client – never leaks
    internal stack traces to the outside world.
    """
    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal error occurred. Please try again later.",
                "status": 500,
            }
        },
    )


# ---------------------------------------------------------------------------
# Registration helper – called once in main.py
# ---------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """
    Attach all exception handlers to the FastAPI application instance.

    Call this function once during application startup, before any routes
    are processed. Handler registration order matters:
    1. Most specific first (domain exceptions > HTTP > Pydantic > catch-all).
    2. The catch-all `Exception` handler must be LAST.

    Usage in main.py:
        from app.core.error_handlers import register_exception_handlers
        register_exception_handlers(app)
    """
    app.add_exception_handler(AppBaseException, app_exception_handler)          # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)   # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)           # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Private helper
# ---------------------------------------------------------------------------

def _status_to_code(status: int) -> str:
    """
    Convert an integer HTTP status code to a screaming-snake-case error code.
    Falls back to "HTTP_{status}" for non-standard status codes.
    """
    from http import HTTPStatus
    try:
        return HTTPStatus(status).name  # e.g. 404 → "NOT_FOUND"
    except ValueError:
        return f"HTTP_{status}"
