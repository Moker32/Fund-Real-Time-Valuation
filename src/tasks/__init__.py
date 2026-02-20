"""Celery tasks package."""

from celery import Celery

from .config import (
    broker_url,
    result_backend,
    task_serializer,
    result_serializer,
    accept_content,
    timezone,
    enable_utc,
)

celery_app = Celery("fund_valuation")

celery_app.config_from_object(
    "src.tasks.config",
    namespace="CELERY",
)

__all__ = ["celery_app"]
