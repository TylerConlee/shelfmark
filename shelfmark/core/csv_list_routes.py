"""CSV list management API routes.

The routes are registered from the application bootstrap and reuse Shelfmark's
existing authentication decorator. CSV contents stay local under CONFIG_DIR.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import Flask, Response, jsonify, request, session

from shelfmark.core.csv_list_processor import is_processing, queue_all, reconcile_queue_states
from shelfmark.csv_lists import (
    CsvListInfo,
    delete_csv_list,
    list_csv_lists,
    load_csv_list,
    save_csv_list,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from flask.typing import ResponseReturnValue


def _serialize_list(item: CsvListInfo) -> dict[str, object]:
    return {
        "id": item.list_id,
        "name": item.name,
        "filename": item.filename,
        "book_count": item.book_count,
        "counts": item.counts,
        "processing": is_processing(item.list_id),
    }


def register_csv_list_routes(
    app: Flask,
    login_required: Callable[
        [Callable[..., ResponseReturnValue]], Callable[..., ResponseReturnValue]
    ],
    *,
    queue_release: Callable[..., tuple[bool, str | None]] | None = None,
    queue_status: Callable[..., dict] | None = None,
    load_policy_settings: Callable[[], dict] | None = None,
) -> None:
    """Register authenticated CSV list management endpoints."""

    @app.route("/api/csv-lists", methods=["GET"])
    @login_required
    def api_csv_lists() -> Response:
        if queue_status is not None:
            for item in list_csv_lists():
                reconcile_queue_states(item.list_id, queue_status)
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

    @app.route("/api/csv-lists/<list_id>/queue-all", methods=["POST"])
    @login_required
    def api_csv_list_queue_all(list_id: str) -> Response | tuple[Response, int]:
        if queue_release is None or load_policy_settings is None:
            return jsonify({"error": "CSV queue processing is unavailable"}), 503
        try:
            load_csv_list(list_id)
        except OSError, ValueError:
            return jsonify({"error": "CSV list not found"}), 404

        started = queue_all(
            list_id,
            queue_release=queue_release,
            global_settings=load_policy_settings(),
            user_id=session.get("db_user_id"),
            username=session.get("user_id"),
        )
        return jsonify({"started": started, "id": list_id}), 202
