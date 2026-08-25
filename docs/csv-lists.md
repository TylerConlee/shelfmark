# CSV Lists

Shelfmark can treat local CSV files as named book lists through the **CSV Lists** metadata provider.

This is useful for importing exported reading lists without first copying them into Hardcover, Goodreads, StoryGraph, or Open Library.

## Enable CSV Lists

1. Open **Settings**.
2. Open the **CSV Lists** metadata-provider section.
3. Enable **CSV Lists** and save the setting.
4. Use **Imported CSV Lists** on the same page to upload one or more CSV files.

Each uploaded CSV becomes an independent Shelfmark list. Uploading another file with the same list name replaces the existing list.

## Supported CSV format

`Title` is required. `Author`, `ISBN`, `ISBN13`, and `Rank` are optional. Header matching is case-insensitive and also accepts common variants such as `Authors`, `Book Title`, `ISBN10`, and `Position`.

A minimal file looks like:

```csv
Title,Author
Project Hail Mary,Andy Weir
Piranesi,Susanna Clarke
```

The batch files produced by the earlier Hardcover conversion workflow are accepted directly, for example:

```csv
Title,Author,Status
Project Hail Mary,Andy Weir,Want to Read
Piranesi,Susanna Clarke,Want to Read
```

Extra columns are ignored.

## Importing batched lists

For files such as:

```text
hardcover_import_part_1.csv
hardcover_import_part_2.csv
hardcover_import_part_3.csv
```

upload each file separately. If no custom list name is entered, Shelfmark uses the filename without `.csv` as the list name. You can instead assign clearer names such as:

```text
Best Books of the 2020s - Part 01
Best Books of the 2020s - Part 02
Best Books of the 2020s - Part 03
```

Row order is preserved, so ranked source lists remain in their imported order.

## Browsing an imported list

After importing:

1. Select **CSV Lists** as the metadata provider.
2. Choose an imported file from the **List** field.
3. Browse the list using Shelfmark's normal paginated metadata results.
4. Selecting a book continues through Shelfmark's existing book workflow.

CSV Lists does not copy books into another tracking service and does not modify the source CSV after import.

## Storage

Imported files are stored under:

```text
CONFIG_DIR/csv-lists/
```

In a typical container installation this is inside Shelfmark's persistent `/config` volume, so imported lists survive container recreation and upgrades as long as that volume is preserved.

## Limits and validation

- Maximum uploaded CSV size: 10 MB.
- Input must be UTF-8; UTF-8 BOM files are supported.
- Rows without a title are skipped.
- A file with no usable titled rows is rejected.
- ISBN punctuation is normalized before matching.
- CSV list management is restricted to administrators when authentication is enabled.
