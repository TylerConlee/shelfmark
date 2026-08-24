"""Tests for CSV list management routes."""

import io
from pathlib import Path

import pytest
from flask import Flask

from shelfmark import csv_lists
from shelfmark.core import admin_routes
from shelfmark.core.csv_list_routes import register_csv_list_routes


@pytest.fixture
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.setattr(csv_lists, "CONFIG_DIR", str(tmp_path))
    flask_app = Flask(__name__)

    def passthrough(view):
        return view

    register_csv_list_routes(flask_app, passthrough)
    flask_app.config["TESTING"] = True
    return flask_app


def test_upload_list_and_delete_csv(app: Flask) -> None:
    client = app.test_client()
    payload = b"Title,Author\nProject Hail Mary,Andy Weir\nPiranesi,Susanna Clarke\n"

    upload = client.post(
        "/api/csv-lists",
        data={
            "name": "Goodreads 2020s Part 01",
            "file": (io.BytesIO(payload), "hardcover_import_part_1.csv"),
        },
        content_type="multipart/form-data",
    )

    assert upload.status_code == 201
    assert upload.get_json() == {
        "id": "Goodreads-2020s-Part-01",
        "name": "Goodreads 2020s Part 01",
        "filename": "Goodreads-2020s-Part-01.csv",
        "book_count": 2,
    }

    listing = client.get("/api/csv-lists")
    assert listing.status_code == 200
    assert listing.get_json()[0]["book_count"] == 2

    deleted = client.delete("/api/csv-lists/Goodreads-2020s-Part-01")
    assert deleted.status_code == 200
    assert deleted.get_json()["success"] is True
    assert client.get("/api/csv-lists").get_json() == []


def test_upload_uses_filename_as_default_list_name(app: Flask) -> None:
    client = app.test_client()
    response = client.post(
        "/api/csv-lists",
        data={"file": (io.BytesIO(b"Title,Author\nDune,Frank Herbert\n"), "batch_03.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert response.get_json()["id"] == "batch_03"


def test_upload_rejects_non_csv_and_invalid_csv(app: Flask) -> None:
    client = app.test_client()

    wrong_extension = client.post(
        "/api/csv-lists",
        data={"file": (io.BytesIO(b"Title,Author\nDune,Frank Herbert\n"), "batch.txt")},
        content_type="multipart/form-data",
    )
    assert wrong_extension.status_code == 400

    missing_title = client.post(
        "/api/csv-lists",
        data={"file": (io.BytesIO(b"Author\nFrank Herbert\n"), "batch.csv")},
        content_type="multipart/form-data",
    )
    assert missing_title.status_code == 400
    assert "Title" in missing_title.get_json()["error"]


def test_delete_unknown_list_returns_404(app: Flask) -> None:
    response = app.test_client().delete("/api/csv-lists/no-such-list")
    assert response.status_code == 404


def test_admin_routes_register_csv_management(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CSV management is reachable through Shelfmark's existing admin registrar."""
    monkeypatch.setattr(csv_lists, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(admin_routes, "load_active_auth_mode", lambda *_args, **_kwargs: "none")

    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    admin_routes.register_admin_routes(flask_app, object())

    response = flask_app.test_client().post(
        "/api/csv-lists",
        data={"file": (io.BytesIO(b"Title,Author\nDune,Frank Herbert\n"), "batch.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert response.get_json()["book_count"] == 1
