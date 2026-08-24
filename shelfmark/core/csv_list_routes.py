"""CSV list management API routes.

The routes are registered from the application bootstrap and reuse Shelfmark's
existing authentication decorator. CSV contents stay local under CONFIG_DIR.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import Flask, Response, jsonify, request

from shelfmark.csv_lists import CsvListInfo, delete_csv_list, list_csv_lists, save_csv_list

if TYPE_CHECKING:
    from collections.abc import Callable

    from flask.typing import ResponseReturnValue


def _serialize_list(item: CsvListInfo) -> dict[str, object]:
    return {
        "id": item.list_id,
        "name": item.name,
        "filename": item.filename,
        "book_count": item.book_count,
    }


def register_csv_list_routes(
    app: Flask,
    login_required: Callable[[Callable[..., ResponseReturnValue]], Callable[..., ResponseReturnValue]],
) -> None:
    """Register authenticated CSV list management endpoints."""

    @app.route("/api/csv-lists", methods=["GET"])
    @login_required
    def api_csv_lists() -> Response:
        return jsonify([_serialize_list(item) for item in list_csv_lists()])

    @app.route("/api/csv-lists", methods=["POST"])
    @login_required
    def api_csv_lists_upload() -> Response | tuple[Response, int]:
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return jsonify({"error": "CSV file is required"}), 400

        if not upload.filename.lower().endswith(".csv"):
            return jsonify({"error": "Only .csv files are supported"}), 400

        name = (request.form.get("name") or "").strip()
        if not name:
            name = upload.filename.rsplit(".", 1)[0]

        try:
            info = save_csv_list(upload.read(), name)
        except (OSError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

        return jsonify(_serialize_list(info)), 201

    @app.route("/api/csv-lists/<list_id>", methods=["DELETE"])
    @login_required
    def api_csv_lists_delete(list_id: str) -> Response | tuple[Response, int]:
        try:
            deleted = delete_csv_list(list_id)
        except (OSError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

        if not deleted:
            return jsonify({"error": "CSV list not found"}), 404
        return jsonify({"success": True, "id": list_id})
