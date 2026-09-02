# This exposes the Celery app so every Django process gets it on startup.
from .celery import app as celery_app  # noqa: F401

__all__ = ('celery_app',)
