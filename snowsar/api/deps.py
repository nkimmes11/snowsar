"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from snowsar.db.session import session_scope


def get_db_session() -> Iterator[Session]:
    """Yield a SQLAlchemy session scoped to the request.

    Only used by routes that opt into DB persistence. Default routes
    use snowsar.jobs.store (in-process) and don't depend on this.
    """
    with session_scope() as session:
        yield session
