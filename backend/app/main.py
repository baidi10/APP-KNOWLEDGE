"""
FastAPI Application Entry Point
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 3 (Core APIs & Errors)

This is the top-level application factory. It:
  1. Instantiates the FastAPI app with project metadata (B26 prep).
  2. Registers all centralized exception handlers (B20).
  3. Mounts the versioned API router (includes B10 and future endpoints).
  4. Exposes a minimal health-check endpoint for infrastructure monitoring.

Run locally with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Interactive API docs available at:
    http://localhost:8000/docs      (Swagger UI)
    http://localhost:8000/redoc     (ReDoc)
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.error_handlers import register_exception_handlers

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_application() -> FastAPI:
    """
    Build and configure the FastAPI application instance.

    Using a factory function (rather than module-level instantiation)
    makes the app easy to reconfigure in tests (e.g., override dependencies,
    swap the database URL) without global state side-effects.
    """
    application = FastAPI(
        # -------------------------------------------------------------------
        # B26 (OpenAPI metadata) — preliminary values; Oussama will expand
        # these with full tag descriptions and external docs in Stage 5.
        # -------------------------------------------------------------------
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ------------------------------------------------------------------
    # CORS Middleware
    # ------------------------------------------------------------------
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Exception Handlers  (B20)
    # ------------------------------------------------------------------
    register_exception_handlers(application)

    # ------------------------------------------------------------------
    # API Routes  (versioned under /api/v1)
    # ------------------------------------------------------------------
    application.include_router(api_router, prefix="/api/v1")

    return application


# ---------------------------------------------------------------------------
# Module-level app instance (used by uvicorn and pytest)
# ---------------------------------------------------------------------------
app: FastAPI = create_application()


# ---------------------------------------------------------------------------
# Health-check endpoint
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    tags=["Health"],
    summary="Application health check",
    description="Returns the application status and version. Used by load balancers and monitoring systems.",
    include_in_schema=True,
)
def health_check() -> dict:
    """
    Lightweight health-check — verifies the app process is reachable.
    Does NOT check the database (use a dedicated readiness probe for that).
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
    }


logger.info("Application '%s' v%s initialized.", settings.APP_NAME, settings.APP_VERSION)
