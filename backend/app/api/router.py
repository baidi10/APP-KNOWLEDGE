"""
API Router – aggregates all endpoint sub-routers
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 3 (Core APIs & Errors)

All versioned API routers are registered here and mounted with their
respective URL prefixes. `main.py` imports `api_router` and includes it
once under the global `/api/v1` prefix.

Adding a new endpoint module (e.g., categories.py for B15) requires only:
    1. Create `app/api/endpoints/categories.py` with its own `router`.
    2. Add the two lines below:
           from app.api.endpoints.categories import router as categories_router
           api_router.include_router(categories_router, prefix="/categories")
"""

from fastapi import APIRouter

from app.api.endpoints.articles import router as articles_router

api_router = APIRouter()

# Mount articles router — all routes in articles.py become /articles/{...}
api_router.include_router(articles_router, prefix="/articles")
