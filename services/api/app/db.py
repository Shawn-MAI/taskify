"""SQLite engine and session management for the API service.

Only the API service opens the database (constitution Principle III). The engine
runs in WAL mode so readers are not blocked by the single writer, and enforces
foreign keys.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def default_db_path() -> str:
    """Return the database file path from ``TASKIFY_DB_PATH`` or a local default."""
    return os.environ.get("TASKIFY_DB_PATH", "taskify.db")


def init_engine(path: str | None = None) -> Engine:
    """Create (or replace) the global engine for ``path``.

    Args:
        path: SQLite file path; defaults to :func:`default_db_path`.

    Returns:
        The configured SQLAlchemy engine.
    """
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    engine = create_engine(
        f"sqlite:///{path or default_db_path()}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()

    _engine = engine
    _session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return engine


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a session; uncommitted work is rolled back on close."""
    if _session_factory is None:
        raise RuntimeError("Database engine is not initialised")
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()


def new_session() -> Session:
    """Return a standalone session (used by seeding and tests). Caller must close it."""
    if _session_factory is None:
        raise RuntimeError("Database engine is not initialised")
    return _session_factory()
