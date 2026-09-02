"""Cached Grimmory library lookup and conservative book identity matching."""

from __future__ import annotations

import re
import threading
import time
import unicodedata
from dataclasses import dataclass
from typing import Any

from shelfmark.core.config import config
from shelfmark.core.logger import setup_logger

logger = setup_logger(__name__)

ALREADY_IN_LIBRARY_ERROR = "Already in Grimmory library"
_CACHE_TTL_SECONDS = 300
_cache_lock = threading.Lock()
_cache: dict[tuple[str, str, int | None], tuple[float, GrimmoryLibraryIndex]] = {}
_BRACKETED = re.compile(r"\s*\[[^\]]*\]\s*$")


@dataclass(frozen=True)
class GrimmoryMatch:
    """A high-confidence match to a book already stored in Grimmory."""

    book_id: int
    title: str
    matched_by: str


@dataclass(frozen=True)
class _IndexedBook:
    book_id: int
    title: str
    title_key: str
    author_keys: frozenset[frozenset[str]]
    isbns: frozenset[str]


@dataclass(frozen=True)
class GrimmoryLibraryIndex:
    """Normalized, immutable view of the Grimmory library."""

    books: tuple[_IndexedBook, ...]
    by_isbn: dict[str, _IndexedBook]
    by_title: dict[str, tuple[_IndexedBook, ...]]


def _normalize_text(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "")).casefold()
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join("".join(char if char.isalnum() else " " for char in without_marks).split())


def _normalize_isbn(value: object) -> str:
    return re.sub(r"[^0-9Xx]", "", str(value or "")).upper()


def _author_key(value: object) -> frozenset[str]:
    text = _BRACKETED.sub("", str(value or "")).strip()
    if not text or ".com" in text.casefold():
        return frozenset()
    return frozenset(_normalize_text(text).split())


def _metadata_for(record: dict[str, Any]) -> dict[str, Any]:
    metadata = record.get("metadata")
    return metadata if isinstance(metadata, dict) else record


def _build_index(records: list[dict[str, Any]]) -> GrimmoryLibraryIndex:
    books: list[_IndexedBook] = []
    by_isbn: dict[str, _IndexedBook] = {}
    by_title_lists: dict[str, list[_IndexedBook]] = {}

    for record in records:
        metadata = _metadata_for(record)
        title = str(metadata.get("title") or record.get("title") or "").strip()
        title_key = _normalize_text(title)
        raw_id = record.get("id") or metadata.get("bookId")
        if not title_key or not isinstance(raw_id, int):
            continue

        raw_authors = metadata.get("authors") or record.get("authors") or []
        if isinstance(raw_authors, str):
            raw_authors = [raw_authors]
        author_keys = frozenset(key for author in raw_authors if (key := _author_key(author)))
        isbns = frozenset(
            isbn
            for field in ("isbn13", "isbn10", "isbn_13", "isbn_10", "isbn")
            if (isbn := _normalize_isbn(metadata.get(field) or record.get(field)))
        )
        book = _IndexedBook(
            book_id=raw_id,
            title=title,
            title_key=title_key,
            author_keys=author_keys,
            isbns=isbns,
        )
        books.append(book)
        by_title_lists.setdefault(title_key, []).append(book)
        for isbn in isbns:
            by_isbn.setdefault(isbn, book)

    return GrimmoryLibraryIndex(
        books=tuple(books),
        by_isbn=by_isbn,
        by_title={key: tuple(value) for key, value in by_title_lists.items()},
    )


def _effective_booklore_settings(user_id: int | None) -> dict[str, Any]:
    keys = (
        "BOOKLORE_HOST",
        "BOOKLORE_USERNAME",
        "BOOKLORE_PASSWORD",
        "BOOKLORE_DESTINATION",
        "BOOKLORE_LIBRARY_ID",
        "BOOKLORE_PATH_ID",
    )
    return {key: config.get(key, None, user_id=user_id) for key in keys}


def _load_index(user_id: int | None) -> GrimmoryLibraryIndex:
    from shelfmark.download.outputs.booklore import (
        booklore_list_books,
        booklore_login,
        build_booklore_config,
    )

    booklore_config = build_booklore_config(_effective_booklore_settings(user_id), user_id=user_id)
    cache_key = (booklore_config.base_url, booklore_config.username, user_id)
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]

    token = booklore_login(booklore_config)
    index = _build_index(booklore_list_books(booklore_config, token))
    with _cache_lock:
        _cache[cache_key] = (now, index)
    return index


def invalidate_grimmory_library_cache() -> None:
    """Clear cached library identities after Shelfmark uploads a new book."""
    with _cache_lock:
        _cache.clear()


def find_grimmory_match(
    *,
    title: str,
    authors: list[str] | tuple[str, ...] | None = None,
    isbn_10: str | None = None,
    isbn_13: str | None = None,
    user_id: int | None = None,
) -> GrimmoryMatch | None:
    """Find an ISBN match or an exact normalized title-and-author match.

    Integration errors fail open so a temporary Grimmory outage does not block downloads.
    """
    try:
        index = _load_index(user_id)
    except Exception as exc:  # noqa: BLE001 - availability check must fail open
        logger.warning("Could not check Grimmory library: %s", exc)
        return None

    for candidate in (isbn_13, isbn_10):
        isbn = _normalize_isbn(candidate)
        if isbn and isbn in index.by_isbn:
            book = index.by_isbn[isbn]
            return GrimmoryMatch(book_id=book.book_id, title=book.title, matched_by="isbn")

    title_key = _normalize_text(title)
    author_keys = {_author_key(author) for author in authors or []}
    author_keys.discard(frozenset())
    if not title_key or not author_keys:
        return None

    for book in index.by_title.get(title_key, ()):
        if author_keys.intersection(book.author_keys):
            return GrimmoryMatch(book_id=book.book_id, title=book.title, matched_by="title_author")
    return None


def annotate_books_with_grimmory_status(
    books: list[dict[str, Any]], *, user_id: int | None
) -> None:
    """Add library-presence fields to serialized metadata search results in place."""
    for book in books:
        raw_authors = book.get("authors") or []
        authors = [raw_authors] if isinstance(raw_authors, str) else list(raw_authors)
        match = find_grimmory_match(
            title=str(book.get("title") or ""),
            authors=authors,
            isbn_10=book.get("isbn_10"),
            isbn_13=book.get("isbn_13"),
            user_id=user_id,
        )
        book["in_library"] = match is not None
        if match is not None:
            book["library_book_id"] = match.book_id
