"""Tests for conservative Grimmory library identity matching."""

from shelfmark.core import grimmory_library


def _index():
    return grimmory_library._build_index(
        [
            {
                "id": 42,
                "metadata": {
                    "title": "The Body in the Library",
                    "authors": ["Agatha Christie [Christie, Agatha]", "chenjin5.com"],
                    "isbn13": "978-0-06-207361-7",
                },
            },
            {
                "id": 77,
                "metadata": {
                    "title": "Dune",
                    "authors": ["Frank Herbert"],
                },
            },
        ]
    )


def test_matches_exact_isbn(monkeypatch):
    monkeypatch.setattr(grimmory_library, "_load_index", lambda _user_id: _index())

    match = grimmory_library.find_grimmory_match(
        title="Different edition title",
        authors=["Someone Else"],
        isbn_13="9780062073617",
    )

    assert match is not None
    assert match.book_id == 42
    assert match.matched_by == "isbn"


def test_matches_normalized_title_and_author(monkeypatch):
    monkeypatch.setattr(grimmory_library, "_load_index", lambda _user_id: _index())

    match = grimmory_library.find_grimmory_match(
        title="THE BODY IN THE LIBRARY!",
        authors=["Agatha Christie"],
    )

    assert match is not None
    assert match.book_id == 42
    assert match.matched_by == "title_author"


def test_does_not_match_title_without_same_author(monkeypatch):
    monkeypatch.setattr(grimmory_library, "_load_index", lambda _user_id: _index())

    assert grimmory_library.find_grimmory_match(title="Dune", authors=["Brian Herbert"]) is None


def test_lookup_failure_fails_open(monkeypatch):
    def fail(_user_id):
        raise RuntimeError("offline")

    monkeypatch.setattr(grimmory_library, "_load_index", fail)

    assert grimmory_library.find_grimmory_match(title="Dune", authors=["Frank Herbert"]) is None
