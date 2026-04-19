"""SQLAlchemy ORM models.

Only imported when a DATABASE_URL is configured. The in-process
job_store remains the default for tests and single-node dev.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""


class Job(Base):
    """Persistent record of a retrieval job."""

    __tablename__ = "jobs"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    backend: Mapped[str] = mapped_column(String(16), nullable=False)
    algorithms: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    bbox: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    start_date: Mapped[str] = mapped_column(String(10), nullable=False)
    end_date: Mapped[str] = mapped_column(String(10), nullable=False)
    resolution_m: Mapped[int] = mapped_column(nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
