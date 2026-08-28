"""Tests for persisted download-history helpers."""

from __future__ import annotations

import os
import tempfile

from shelfmark.core.download_history_service import DownloadHistoryService
from shelfmark.core.user_db import UserDB


def test_iso_to_epoch_treats_naive_sqlite_timestamp_as_utc():
    epoch = DownloadHistoryService._iso_to_epoch("2026-01-02 03:04:05")
    assert epoch == 1767323045.0


def test_record_download_stores_utc_iso_timestamps():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "users.db")
        user_db = UserDB(db_path)
        user_db.initialize()
        service = DownloadHistoryService(db_path)

        service.record_download(
            task_id="task-1",
            user_id=None,
            username=None,
            request_id=None,
            source="direct_download",
            source_display_name="Direct Download",
            title="Example",
            author=None,
            file_format=None,
            size=None,
            preview=None,
            content_type="ebook",
            origin="direct",
        )

        conn = user_db._connect()
        try:
            row = conn.execute(
                "SELECT queued_at, terminal_at FROM download_history WHERE task_id = ?",
                ("task-1",),
            ).fetchone()
        finally:
            conn.close()

        assert row is not None
        assert "+00:00" in row["queued_at"]
        assert "+00:00" in row["terminal_at"]


def test_list_active_returns_all_rows_in_queue_order_and_deserializes_retry_payload():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "users.db")
        user_db = UserDB(db_path)
        user_db.initialize()
        service = DownloadHistoryService(db_path)

        for task_id in ("first", "second", "finished"):
            service.record_download(
                task_id=task_id,
                user_id=None,
                username=None,
                request_id=None,
                source="direct_download",
                source_display_name="Direct Download",
                title=task_id.title(),
                author=None,
                file_format="epub",
                size=None,
                preview=None,
                content_type="ebook",
                origin="direct",
                retry_payload={"task_id": task_id},
            )
        service.finalize_download(task_id="finished", final_status="complete")

        rows = service.list_active()

        assert [row["task_id"] for row in rows] == ["first", "second"]
        assert rows[0]["retry_payload"] == {"task_id": "first"}
