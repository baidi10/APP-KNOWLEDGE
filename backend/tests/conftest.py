"""
Test Fixtures – conftest.py
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 5 (Testing & Docs)  [B28, B30]

This file is automatically loaded by pytest before any test module runs.
It provides shared fixtures used by both B28 (GET tests) and B30 (DELETE tests).

DATABASE STRATEGY
-----------------
Tests use an **in-memory SQLite** database rather than the real PostgreSQL
instance for three reasons:
  1. Speed    – SQLite creates/drops in microseconds; no Docker required.
  2. Isolation – Each test function gets a fresh, empty database that is
                 rolled back or dropped after the test completes.
  3. CI-ready  – No external services needed in CI/CD pipelines.

SQLite vs PostgreSQL parity
---------------------------
The only behavioural difference relevant to our models is that SQLite does
not support PostgreSQL-native ENUMs. Our `ArticleStatus` column was declared
with `values_callable` which makes SQLAlchemy emit a VARCHAR + CHECK
constraint on SQLite — identical runtime behaviour for our test assertions.

DEPENDENCY OVERRIDE PATTERN
----------------------------
FastAPI's `app.dependency_overrides` dict lets us swap `get_db` (which
normally opens a PostgreSQL session) for `override_get_db` (which yields
an SQLite session). This means the actual endpoint code is tested without
modification — we are not mocking the repository, we are replacing only the
session factory at the infrastructure boundary.

FIXTURE SCOPE
-------------
`db_engine`   : session-scoped → one SQLite engine per test *module*
`db_session`  : function-scoped → one clean session per test *function*
                (transaction is rolled back after each test)
`client`      : function-scoped → inherits `db_session`'s override

ARTICLE FACTORIES
-----------------
`make_article` is a factory fixture that returns a callable.
Each test can call `make_article(title="...", ...)` multiple times to
create articles with custom attributes while relying on safe defaults
for fields that don't matter to the specific test.
"""

from collections.abc import Generator
from typing import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# App & model imports
# ---------------------------------------------------------------------------
# Import all models through the package __init__ so Base.metadata is fully
# populated before create_all() is called. Skipping this would cause some
# tables (e.g., article_tags) to be missing from the test schema.
from app.core.database import get_db
from app.main import app
from app.models import Base                        # noqa: F401 – populates metadata
from app.models.article import Article, ArticleStatus


# ---------------------------------------------------------------------------
# SQLite test engine  (session-scoped – shared by all tests in a module)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_engine():
    """
    Create a single in-memory SQLite engine for the entire test session.

    `StaticPool` with `connect_args={"check_same_thread": False}` is the
    correct pool configuration for SQLite + multi-threaded test clients.
    It ensures all connections share the same underlying SQLite database
    object, which is required for in-memory databases (otherwise each new
    connection would see an empty DB).

    `create_all` and `drop_all` wrap the engine lifecycle so the schema
    exists for every test and is cleaned up afterward.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,  # Set True to debug SQL in tests
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# Per-test database session  (function-scoped – rolled back after each test)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Yield a SQLAlchemy Session that is rolled back after each test.

    The rollback ensures complete isolation: data created in test_A cannot
    be seen by test_B, even within the same test module run.

    The session is bound to a *connection* (not the engine directly) so we
    can begin a SAVEPOINT and roll back to it without tearing down the schema.
    """
    connection = db_engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = TestingSessionLocal()

    yield session

    # Teardown: roll back everything written during this test.
    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# FastAPI TestClient with DB dependency override
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Yield a synchronous `TestClient` that routes database calls to the
    in-memory SQLite session instead of the real PostgreSQL database.

    FastAPI's `dependency_overrides` is the official mechanism for this.
    After the test completes, the override is cleared so it cannot leak
    into other test modules that import the same `app` object.
    """
    def override_get_db() -> Generator[Session, None, None]:
        """Replace the real get_db dependency with the test session."""
        try:
            yield db_session
        finally:
            pass  # Teardown is handled by the db_session fixture's rollback.

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client

    # Always clear overrides after the test — prevents cross-test contamination.
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Article factory fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def make_article(db_session: Session) -> Callable[..., Article]:
    """
    Factory fixture that creates and persists Article instances.

    Returns a callable so each test can create one or more articles with
    custom attributes while relying on sensible defaults for everything else.

    Usage in a test:
        def test_something(make_article):
            article = make_article(title="My Article", slug="my-article")
            another  = make_article(status=ArticleStatus.PUBLISHED)

    The articles are committed to the session so they are visible to the
    TestClient (which uses the same session via the dependency override).
    """

    def _factory(
        title: str = "Test Article",
        slug: str = "test-article",
        content: str = "This is test article content for the AdoptAI knowledge base.",
        status: ArticleStatus = ArticleStatus.PUBLISHED,
        category_id: int | None = None,
    ) -> Article:
        article = Article(
            title=title,
            slug=slug,
            content=content,
            status=status,
            category_id=category_id,
            tags=[],
        )
        db_session.add(article)
        db_session.commit()
        db_session.refresh(article)
        return article

    return _factory
