"""Core module - shared models, queue, and utilities."""

from __future__ import annotations

from shelfmark.core.logger import setup_logger
from shelfmark.core.models import QueueItem, QueueStatus, SearchFilters
from shelfmark.core.queue import BookQueue, book_queue

__all__ = [
    "BookQueue",
    "QueueItem",
    "QueueStatus",
    "SearchFilters",
    "book_queue",
    "setup_logger",
]
