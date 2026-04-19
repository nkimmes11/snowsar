"""SQLAlchemy session factory.

The engine is created lazily on first use and only when
SNOWSAR_DATABASE_URL is configured. Tests that don't set the env var
never touch this module.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from snowsar.config import Settings
from snowsar.exceptions import SnowSARError

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _init() -> None:
    global _engine, _SessionLocal
    settings = Settings()
    if settings.database_url is None:
        msg = "SNOWSAR_DATABASE_URL is not configured"
        raise SnowSARError(msg)
    _engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context-managed SQLAlchemy session with commit/rollback."""
    if _SessionLocal is None:
        _init()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
