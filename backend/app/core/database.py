"""
B2 - SQLAlchemy 2.0 Engine & Session Factory
Project : AdoptAI App Knowledge Base
Author  : Oussama
Stage   : 1 (Foundation)
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# `pool_pre_ping=True` ensures stale connections are detected and recycled
# before being handed to application code – critical for long-running servers.
# `echo=settings.DEBUG` logs all SQL statements when DEBUG mode is active,
# which is helpful during development but should be False in production.
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    # Connection pool settings – sensible defaults for a small-to-medium API.
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)


# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------
# `autocommit=False` – we manage transactions explicitly (best practice).
# `autoflush=False`  – prevents unintended flushes before queries; gives
#                      callers full control over when state is sent to DB.
# ---------------------------------------------------------------------------
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Avoids lazy-load errors after commit in APIs
)


# ---------------------------------------------------------------------------
# FastAPI Dependency – Database Session
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a transactional database session.

    Guarantees the session is always closed after the request completes,
    even if an exception is raised. Commit / rollback decisions are left
    to the service / repository layer.

    Usage in a route:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Health-check helper (used by Stage 3+ startup events / health endpoint)
# ---------------------------------------------------------------------------
def check_database_connection() -> bool:
    """
    Attempts a lightweight round-trip to the database.
    Returns True if the connection is healthy, False otherwise.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
