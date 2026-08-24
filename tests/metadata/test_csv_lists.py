"""Tests for local CSV list ingestion and browsing."""

from pathlib import Path

import pytest

from shelfmark import csv_lists
from shelfmark.metadata_providers import MetadataSearchOptions
from shelfmark.metadata_providers.csvlists import CsvListsProvider


@pytest.fixture
def csv_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(csv_lists, "CONFIG_DIR", str(tmp_path))
    return tmp_path / csv_lists.CSV_LISTS_DIRNAME


def test_parse_compact_export_csv() -> None:
    payload = (
        b"Title,Author,Status\n"
        b"Project Hail Mary,Andy Weir,Want to Read\n"
        b"Piranesi,Susanna Clarke,Want to Read\n"
    )

    books = csv_lists.parse_csv_bytes(payload)

    assert [(book.title, book.author) for book in books] == [
        ("Project Hail Mary", "Andy Weir"),
        ("Piranesi", "Susanna Clarke"),
    ]
    assert [book.row_number for book in books] == [2, 3]


def test_parse_goodreads_style_columns_and_isbn() -> None:
    payload = (
        b"Book Title,Authors,ISBN,ISBN13,Rank\n"
        b"Dune,Frank Herbert,0441172717,9780441172719,42\n"
    )

    books = csv_lists.parse_csv_bytes(payload)

    assert len(books) == 1
    assert books[0].title == "Dune"
    assert books[0].author == "Frank Herbert"
    assert books[0].isbn_10 == "0441172717"
    assert books[0].isbn_13 == "9780441172719"
    assert books[0].rank == 42


def test_parser_accepts_utf8_bom_and_skips_blank_titles() -> None:
    payload = "\ufeffTitle,Author\n,Unknown\nRecursion,Blake Crouch\n".encode("utf-8")

    books = csv_lists.parse_csv_bytes(payload)

    assert len(books) == 1
    assert books[0].title == "Recursion"


def test_parser_requires_title_column() -> None:
    with pytest.raises(ValueError, match="Title"):
        csv_lists.parse_csv_bytes(b"Author,Status\nAndy Weir,Want to Read\n")


def test_save_list_sanitizes_name_and_can_be_reloaded(csv_dir: Path) -> None:
    payload = b"Title,Author\nDark Matter,Blake Crouch\n"

    info = csv_lists.save_csv_list(payload, "Goodreads 2020s / Part 01")

    assert info.list_id == "Goodreads-2020s-Part-01"
    assert info.book_count == 1
    assert (csv_dir / "Goodreads-2020s-Part-01.csv").is_file()
    assert csv_lists.load_csv_list(info.list_id)[0].title == "Dark Matter"


def test_list_csv_lists_reports_counts(csv_dir: Path) -> None:
    csv_lists.save_csv_list(b"Title,Author\nOne,A\nTwo,B\n", "Batch 2")
    csv_lists.save_csv_list(b"Title,Author\nThree,C\n", "Batch 1")

    lists = csv_lists.list_csv_lists()

    assert [(item.list_id, item.book_count) for item in lists] == [
        ("Batch-1", 1),
        ("Batch-2", 2),
    ]


def test_provider_exposes_lists_and_preserves_pagination(csv_dir: Path) -> None:
    csv_lists.save_csv_list(
        b"Title,Author,Rank\nOne,Author A,1\nTwo,Author B,2\nThree,Author C,3\n",
        "Reading Batch",
    )
    provider = CsvListsProvider()

    options = provider.get_search_field_options("csv_list")
    result = provider.search_paginated(
        MetadataSearchOptions(
            query="",
            limit=2,
            page=1,
            fields={"csv_list": "Reading-Batch"},
        )
    )

    assert options == [
        {
            "value": "Reading-Batch",
            "label": "Reading Batch",
            "description": "3 books",
        }
    ]
    assert [book.title for book in result.books] == ["One", "Two"]
    assert result.total_found == 3
    assert result.has_more is True
    assert result.source_title == "Reading Batch"


def test_provider_get_book_uses_stable_row_id(csv_dir: Path) -> None:
    csv_lists.save_csv_list(b"Title,Author\nFour,Author D\n", "Batch")
    provider = CsvListsProvider()

    book = provider.get_book("Batch:2")

    assert book is not None
    assert book.title == "Four"
    assert book.authors == ["Author D"]
    assert book.provider_id == "Batch:2"
