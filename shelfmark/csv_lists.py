"""Local CSV-backed book list storage for Shelfmark.

Each CSV file represents one named list. Row order is preserved. The parser accepts
our compact exported CSVs (Title, Author, Status) as well as common Goodreads-style
headers and optional ISBN/rank columns.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shelfmark.config.env import CONFIG_DIR

CSV_LISTS_DIRNAME = "csv-lists"
CSV_LIST_MAX_BYTES = 10 * 1024 * 1024
_SAFE_ID_PATTERN = re.compile(r"[^a-zA-Z0-9._-]+")

_TITLE_ALIASES = ("title", "book title")
_AUTHOR_ALIASES = ("author", "authors", "author name")
_ISBN10_ALIASES = ("isbn", "isbn10", "isbn 10")
_ISBN13_ALIASES = ("isbn13", "isbn 13")
_RANK_ALIASES = ("rank", "position")


@dataclass(frozen=True)
class CsvListBook:
    """Normalized book row from a CSV list."""

    row_number: int
    title: str
    author: str
    isbn_10: str | None = None
    isbn_13: str | None = None
    rank: int | None = None


@dataclass(frozen=True)
class CsvListInfo:
    """Metadata describing one stored CSV list."""

    list_id: str
    name: str
    filename: str
    book_count: int


def csv_lists_dir() -> Path:
    """Return the persistent directory used for CSV list files."""
    return Path(CONFIG_DIR) / CSV_LISTS_DIRNAME


def _normalize_header(value: str) -> str:
    return " ".join(str(value or "").replace("_", " ").strip().casefold().split())


def _normalized_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        _normalize_header(key): str(value or "").strip()
        for key, value in row.items()
        if key is not None
    }


def _first_value(row: dict[str, str], aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        value = row.get(alias, "").strip()
        if value:
            return value
    return ""


def _normalize_isbn(value: str) -> str | None:
    normalized = re.sub(r"[^0-9Xx]", "", value or "")
    return normalized.upper() or None


def _parse_rank(value: str) -> int | None:
    if not value:
        return None
    try:
        return int(value.replace(",", "").strip())
    except ValueError:
        return None


def sanitize_list_id(value: str) -> str:
    """Create a safe stable identifier suitable for a filename stem."""
    normalized = _SAFE_ID_PATTERN.sub("-", str(value or "").strip()).strip("-._")
    normalized = re.sub(r"-+", "-", normalized)
    if not normalized:
        raise ValueError("CSV list name must contain at least one letter or number")
    return normalized[:120]


def _path_for_list(list_id: str) -> Path:
    safe_id = sanitize_list_id(list_id)
    return csv_lists_dir() / f"{safe_id}.csv"


def _display_name(list_id: str) -> str:
    return list_id.replace("_", " ").replace("-", " ").strip()


def parse_csv_bytes(payload: bytes) -> list[CsvListBook]:
    """Parse CSV bytes into normalized book rows."""
    if len(payload) > CSV_LIST_MAX_BYTES:
        raise ValueError(f"CSV file exceeds {CSV_LIST_MAX_BYTES // (1024 * 1024)} MB limit")

    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV is missing a header row")

    normalized_headers = {_normalize_header(field) for field in reader.fieldnames if field}
    if not any(alias in normalized_headers for alias in _TITLE_ALIASES):
        raise ValueError("CSV must include a Title column")

    books: list[CsvListBook] = []
    for row_number, raw_row in enumerate(reader, start=2):
        row = _normalized_row(raw_row)
        title = _first_value(row, _TITLE_ALIASES)
        if not title:
            continue

        author = _first_value(row, _AUTHOR_ALIASES)
        isbn_10 = _normalize_isbn(_first_value(row, _ISBN10_ALIASES))
        isbn_13 = _normalize_isbn(_first_value(row, _ISBN13_ALIASES))
        rank = _parse_rank(_first_value(row, _RANK_ALIASES))

        # Goodreads-style exports may place ISBN-13 in the generic ISBN column.
        if isbn_10 and len(isbn_10) == 13 and not isbn_13:
            isbn_13, isbn_10 = isbn_10, None
        elif isbn_10 and len(isbn_10) != 10:
            isbn_10 = None
        if isbn_13 and len(isbn_13) != 13:
            isbn_13 = None

        books.append(
            CsvListBook(
                row_number=row_number,
                title=title,
                author=author,
                isbn_10=isbn_10,
                isbn_13=isbn_13,
                rank=rank,
            )
        )

    if not books:
        raise ValueError("CSV contains no rows with a title")
    return books


def save_csv_list(payload: bytes, name: str) -> CsvListInfo:
    """Validate and persist a CSV list, replacing a same-named list."""
    list_id = sanitize_list_id(name)
    books = parse_csv_bytes(payload)
    target_dir = csv_lists_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = _path_for_list(list_id)
    path.write_bytes(payload)
    return CsvListInfo(
        list_id=list_id,
        name=_display_name(list_id),
        filename=path.name,
        book_count=len(books),
    )


def load_csv_list(list_id: str) -> list[CsvListBook]:
    """Load and parse one persisted CSV list."""
    path = _path_for_list(list_id)
    if not path.is_file():
        raise FileNotFoundError(f"CSV list not found: {list_id}")
    return parse_csv_bytes(path.read_bytes())


def delete_csv_list(list_id: str) -> bool:
    """Delete a stored CSV list. Returns True when a file was removed."""
    path = _path_for_list(list_id)
    if not path.exists():
        return False
    path.unlink()
    return True


def list_csv_lists() -> list[CsvListInfo]:
    """Return all persisted CSV lists sorted by display name."""
    directory = csv_lists_dir()
    if not directory.is_dir():
        return []

    lists: list[CsvListInfo] = []
    for path in sorted(directory.glob("*.csv"), key=lambda item: item.name.casefold()):
        try:
            books = parse_csv_bytes(path.read_bytes())
        except (OSError, ValueError):
            continue
        lists.append(
            CsvListInfo(
                list_id=path.stem,
                name=_display_name(path.stem),
                filename=path.name,
                book_count=len(books),
            )
        )
    return lists
