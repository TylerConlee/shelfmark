"""Local CSV Lists metadata provider.

This provider turns CSV files stored under CONFIG_DIR/csv-lists into browsable,
paginated Shelfmark book lists. It is intentionally metadata-only: selecting a
book continues through Shelfmark's existing release-search/request workflow.
"""

from __future__ import annotations

from typing import ClassVar

from shelfmark.core.settings_registry import (
    CheckboxField,
    CustomComponentField,
    HeadingField,
    SettingsField,
    register_settings,
)
from shelfmark.csv_lists import CsvListBook, csv_lists_dir, list_csv_lists, load_csv_list
from shelfmark.metadata_providers import (
    BookMetadata,
    DisplayField,
    DynamicSelectSearchField,
    MetadataProvider,
    MetadataSearchOptions,
    SearchField,
    SearchResult,
    SortOrder,
    register_provider,
)


@register_provider("csvlists")
class CsvListsProvider(MetadataProvider):
    """Browse locally imported CSV files as Shelfmark book lists."""

    name = "csvlists"
    display_name = "CSV Lists"
    requires_auth = False
    supported_sorts: ClassVar[tuple[SortOrder, ...]] = (SortOrder.RELEVANCE,)
    search_fields: ClassVar[tuple[SearchField, ...]] = (
        DynamicSelectSearchField(
            key="csv_list",
            label="List",
            options_endpoint="/api/metadata/field-options?provider=csvlists&field=csv_list",
            placeholder="Browse an imported CSV list...",
            description="Browse books from a CSV file stored in Shelfmark",
        ),
    )

    def is_available(self) -> bool:
        """The provider is local and requires no external service."""
        return True

    @staticmethod
    def _to_metadata(list_id: str, book: CsvListBook) -> BookMetadata:
        display_fields: list[DisplayField] = []
        if book.rank is not None:
            display_fields.append(DisplayField(label="Rank", value=str(book.rank), icon="book"))

        return BookMetadata(
            provider="csvlists",
            provider_display_name="CSV Lists",
            provider_id=f"{list_id}:{book.row_number}",
            title=book.title,
            authors=[book.author] if book.author else [],
            isbn_10=book.isbn_10,
            isbn_13=book.isbn_13,
            search_title=book.title,
            search_author=book.author or None,
            display_fields=display_fields,
        )

    def get_search_field_options(
        self,
        field_key: str,
        query: str | None = None,
    ) -> list[dict[str, str]]:
        """Return imported CSV files for the dynamic list dropdown."""
        if field_key != "csv_list":
            return []

        normalized_query = (query or "").strip().casefold()
        options: list[dict[str, str]] = []
        for item in list_csv_lists():
            if normalized_query and normalized_query not in item.name.casefold():
                continue
            options.append(
                {
                    "value": item.list_id,
                    "label": item.name,
                    "description": f"{item.book_count:,} books",
                }
            )
        return options

    def search_paginated(self, options: MetadataSearchOptions) -> SearchResult:
        """Browse one CSV list, preserving source row order and pagination."""
        list_id = str(options.fields.get("csv_list") or "").strip()
        if not list_id:
            books = self.search(options)
            return SearchResult(
                books=books,
                page=options.page,
                total_found=len(books),
                has_more=False,
            )

        try:
            rows = load_csv_list(list_id)
        except FileNotFoundError, ValueError:
            return SearchResult(books=[], page=options.page, total_found=0, has_more=False)

        query = options.query.strip().casefold()
        if query:
            rows = [
                row
                for row in rows
                if query in row.title.casefold() or query in row.author.casefold()
            ]

        limit = max(1, options.limit)
        page = max(1, options.page)
        offset = (page - 1) * limit
        page_rows = rows[offset : offset + limit]
        books = [self._to_metadata(list_id, row) for row in page_rows]

        info = next((item for item in list_csv_lists() if item.list_id == list_id), None)
        source_title = info.name if info else list_id
        return SearchResult(
            books=books,
            page=page,
            total_found=len(rows),
            has_more=offset + len(page_rows) < len(rows),
            source_title=source_title,
        )

    def search(self, options: MetadataSearchOptions) -> list[BookMetadata]:
        """Search within one selected CSV list or across all imported lists."""
        selected_list = str(options.fields.get("csv_list") or "").strip()
        if selected_list:
            return self.search_paginated(options).books

        query = options.query.strip().casefold()
        if not query:
            return []

        matches: list[BookMetadata] = []
        for info in list_csv_lists():
            try:
                rows = load_csv_list(info.list_id)
            except FileNotFoundError, ValueError:
                continue
            for row in rows:
                if query in row.title.casefold() or query in row.author.casefold():
                    matches.append(self._to_metadata(info.list_id, row))
                    if len(matches) >= options.limit:
                        return matches
        return matches

    def get_book(self, book_id: str) -> BookMetadata | None:
        """Resolve a CSV provider ID (list-id:row-number) back to its book."""
        list_id, separator, row_text = book_id.rpartition(":")
        if not separator or not list_id:
            return None
        try:
            row_number = int(row_text)
            rows = load_csv_list(list_id)
        except FileNotFoundError, TypeError, ValueError:
            return None

        row = next((item for item in rows if item.row_number == row_number), None)
        return self._to_metadata(list_id, row) if row else None

    def search_by_isbn(self, isbn: str) -> BookMetadata | None:
        """Find the first imported CSV row matching ISBN-10 or ISBN-13."""
        normalized = "".join(char for char in isbn.upper() if char.isdigit() or char == "X")
        if not normalized:
            return None

        for info in list_csv_lists():
            try:
                rows = load_csv_list(info.list_id)
            except FileNotFoundError, ValueError:
                continue
            for row in rows:
                if normalized in {row.isbn_10, row.isbn_13}:
                    return self._to_metadata(info.list_id, row)
        return None


@register_settings("csvlists", "CSV Lists", icon="list", order=54, group="metadata_providers")
def csvlists_settings() -> list[SettingsField]:
    """Settings shown for the local CSV Lists provider."""
    return [
        HeadingField(
            key="csvlists_heading",
            title="CSV Lists",
            description=(
                "Browse local CSV files as book lists. CSVs require a Title column and may include "
                f"Author, ISBN, ISBN13, and Rank. Files are stored in {csv_lists_dir()}."
            ),
        ),
        CheckboxField(
            key="CSVLISTS_ENABLED",
            label="Enable CSV Lists",
            description="Enable locally imported CSV files as a metadata/list provider",
            default=False,
        ),
        CustomComponentField(
            key="csv_lists_management",
            component="csv_lists_management",
            label="Imported CSV Lists",
            description="Upload, replace, or delete locally stored CSV book lists.",
        ),
    ]
