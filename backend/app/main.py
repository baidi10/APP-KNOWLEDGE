"""
B26 - FastAPI Application Entry Point with Full OpenAPI Metadata
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stages  : 3, 4 & 5 (Core APIs, Advanced Endpoints, Docs & Tests)

This module is the top-level application factory. It:
  1. Instantiates the FastAPI app with rich OpenAPI metadata (B26).
  2. Configures `openapi_tags` to group Swagger UI endpoints cleanly.
  3. Registers all centralized exception handlers (B20).
  4. Mounts the versioned API router under /api/v1.
  5. Exposes a health-check endpoint for infrastructure monitoring.

Run locally:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Interactive API docs:
    http://localhost:8000/docs          (Swagger UI)
    http://localhost:8000/redoc         (ReDoc)
    http://localhost:8000/openapi.json  (Raw OpenAPI schema)
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.router import api_router
from app.core.config import settings
from app.core.error_handlers import register_exception_handlers

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# B26 — OpenAPI tag definitions
# ---------------------------------------------------------------------------
# Each entry creates a named section in Swagger UI with a description tooltip.
# Tags must match the `tags=[...]` values used in the router decorators.
# ---------------------------------------------------------------------------
OPENAPI_TAGS: list[dict] = [
    {
        "name": "Articles",
        "description": (
            "Operations on **knowledge-base articles**. "
            "Articles are the core content unit of AdoptAI — they contain "
            "step-by-step guidance, FAQs, and how-to content for enterprise "
            "applications (SAP, ServiceNow, Apple, etc.). "
            "Each article belongs to one **Category** and may carry multiple **Tags**."
        ),
        "externalDocs": {
            "description": "Article data model reference",
            "url": "https://github.com/baidi10/APP-KNOWLEDGE#articles",
        },
    },
    {
        "name": "Health",
        "description": (
            "Infrastructure health and readiness probes. "
            "These endpoints are used by load balancers and monitoring systems "
            "to verify that the API process is running and reachable."
        ),
    },
]

# ---------------------------------------------------------------------------
# B26 — Professional Markdown description (rendered in Swagger UI & ReDoc)
# ---------------------------------------------------------------------------
API_DESCRIPTION: str = """
## AdoptAI App Knowledge Base API

A **centralized knowledge management system** built for AdoptAI to help
enterprise teams find, manage, and consume application guidance content.

### What this API provides

| Resource | Description |
|---|---|
| **Articles** | Core content units: guides, FAQs, how-tos for enterprise apps |
| **Categories** | Top-level taxonomy (SAP, ServiceNow, Apple, …) |
| **Tags** | Cross-cutting keyword labels for fine-grained filtering |

### Versioning

All production endpoints are versioned under `/api/v1`.
Breaking changes will be introduced under a new version prefix (`/api/v2`, etc.).

### Authentication

> ⚠️ Authentication is reserved for a future release.
> All endpoints are currently open for internal development and testing.

### Error format

Every error response follows a consistent JSON envelope:

```json
{
  "error": {
    "code":    "ARTICLE_NOT_FOUND",
    "message": "Article with id '42' was not found.",
    "status":  404
  }
}
```

### Project team

| Role | Name |
|---|---|
| Project supervisor | Khadija Boukhatem |
| Backend – Foundation & Core APIs | **Oussama** |
| Backend – Schemas & List Endpoints | Safouane |

### Source code

[github.com/baidi10/APP-KNOWLEDGE](https://github.com/baidi10/APP-KNOWLEDGE)
"""


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_application() -> FastAPI:
    """
    Build and configure the FastAPI application instance.

    Using a factory function (rather than module-level instantiation)
    makes the app testable: tests call `create_application()` with
    overridden dependencies instead of importing the global `app` directly.
    """
    application = FastAPI(
        # ------------------------------------------------------------------
        # B26 — Core OpenAPI metadata
        # ------------------------------------------------------------------
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=API_DESCRIPTION,
        # ------------------------------------------------------------------
        # B26 — Contact & license (rendered in ReDoc sidebar)
        # ------------------------------------------------------------------
        contact={
            "name": "Oussama Baidi — Backend Developer",
            "url": "https://github.com/baidi10/APP-KNOWLEDGE",
            "email": "oussamabaidi10@gmail.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        # ------------------------------------------------------------------
        # B26 — Tag definitions: creates labelled sections in Swagger UI
        # ------------------------------------------------------------------
        openapi_tags=OPENAPI_TAGS,
        # ------------------------------------------------------------------
        # B26 — Doc UI URLs (keep explicit for clarity)
        # ------------------------------------------------------------------
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        # ------------------------------------------------------------------
        # B26 — Swagger UI customisation: cleaner, professional look
        # ------------------------------------------------------------------
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 2,      # Expand schema models by default
            "defaultTagsExpandDepth": 1,        # Tags start expanded
            "operationsSorter": "method",       # Group by HTTP method (GET, PUT…)
            "filter": True,                     # Show the endpoint search filter box
            "syntaxHighlight.theme": "monokai", # Dark code highlighting
            "tryItOutEnabled": True,            # 'Try it out' open by default
        },
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
# Module-level app instance (used by uvicorn, pytest, and gunicorn)
# ---------------------------------------------------------------------------
app: FastAPI = create_application()


# ---------------------------------------------------------------------------
# B26 — Custom OpenAPI schema hook
# ---------------------------------------------------------------------------
# Overriding `app.openapi()` lets us inject additional metadata (servers,
# security schemes, x-logo, etc.) that FastAPI's default generator omits.
# ---------------------------------------------------------------------------

def custom_openapi() -> dict:
    """
    Generate and cache a customised OpenAPI schema.

    Called lazily on first access to /openapi.json. The result is stored in
    `app.openapi_schema` so subsequent requests are served from memory.
    """
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        contact=app.contact,           # type: ignore[arg-type]
        license_info=app.license_info, # type: ignore[arg-type]
        tags=OPENAPI_TAGS,
        routes=app.routes,
    )

    # ------------------------------------------------------------------
    # B26 — Servers block: documents environment URLs for Swagger UI
    # ------------------------------------------------------------------
    schema["info"]["x-logo"] = {
        "url": "https://avatars.githubusercontent.com/u/baidi10",
        "altText": "AdoptAI Logo",
    }
    schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Local development server",
        },
        {
            "url": "https://api.adoptai.example.com",
            "description": "Production server (placeholder)",
        },
    ]

    app.openapi_schema = schema
    return app.openapi_schema


# Attach the custom schema generator to the app instance.
app.openapi = custom_openapi  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# Health-check endpoint
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    tags=["Health"],
    summary="Liveness probe",
    description=(
        "Returns `200 OK` with basic application metadata. "
        "Used by load balancers and uptime monitors to verify the process is alive. "
        "Does **not** check the database connection."
    ),
    response_description="Application is running.",
    include_in_schema=True,
)
def health_check() -> dict:
    """
    **Liveness probe** — confirms the API process is running.

    This endpoint intentionally avoids any database call so it remains fast
    and reliable even when the database is temporarily unreachable.
    Use a separate **readiness** endpoint (future) to probe DB connectivity.
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
    }


logger.info("Application '%s' v%s initialized.", settings.APP_NAME, settings.APP_VERSION)
