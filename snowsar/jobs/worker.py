"""Celery application instance.

Loaded only when execution_mode == 'celery'. The docker/docker-compose.yml
worker service runs ``celery -A snowsar.jobs.worker worker``.
"""

from __future__ import annotations

from celery import Celery

from snowsar.config import Settings

_settings = Settings()

celery_app = Celery(
    "snowsar",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
    include=["snowsar.jobs.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
