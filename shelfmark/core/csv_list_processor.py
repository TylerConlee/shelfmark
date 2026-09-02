"""Background CSV list processing through Shelfmark's normal release pipeline."""

from __future__ import annotations

import threading
from dataclasses import asdict
from typing import Any, Callable

from shelfmark.core.grimmory_library import find_grimmory_match
from shelfmark.core.models import QueueStatus
from shelfmark.core.request_policy import PolicyMode, resolve_policy_mode
from shelfmark.core.search_plan import build_release_search_plan
from shelfmark.csv_lists import load_csv_list, load_row_states, save_row_states, update_row_state
from shelfmark.metadata_providers.csvlists import CsvListsProvider
from shelfmark.release_sources import get_source, list_available_sources

_workers: dict[str, threading.Thread] = {}
_worker_lock = threading.Lock()


def is_processing(list_id: str) -> bool:
    with _worker_lock:
        worker = _workers.get(list_id)
        return bool(worker and worker.is_alive())


def reconcile_queue_states(list_id: str, queue_status: Callable[..., dict[str, Any]]) -> None:
    """Reflect live and terminal download states in persisted CSV row state."""
    states = load_row_states(list_id)
    if not states:
        return
    queue = queue_status(user_id=None)
    by_task: dict[str, str] = {}
    for status, tasks in queue.items():
        status_text = status.value if isinstance(status, QueueStatus) else str(status)
        for task_id in tasks:
            by_task[str(task_id)] = status_text

    changed = False
    for state in states.values():
        task_id = str(state.get("task_id") or "")
        queue_state = by_task.get(task_id)
        if not task_id or not queue_state:
            continue
        mapped = (
            "complete"
            if queue_state == QueueStatus.COMPLETE.value
            else "failed"
            if queue_state in {QueueStatus.ERROR.value, QueueStatus.CANCELLED.value}
            else "queued"
            if queue_state == QueueStatus.QUEUED.value
            else "downloading"
        )
        if state.get("status") != mapped:
            state["status"] = mapped
            changed = True
    if changed:
        save_row_states(list_id, states)


def _process_list(
    list_id: str,
    *,
    queue_release: Callable[..., tuple[bool, str | None]],
    global_settings: dict[str, Any],
    user_id: int | None,
    username: str | None,
) -> None:
    provider = CsvListsProvider()
    try:
        for row in load_csv_list(list_id):
            current = load_row_states(list_id).get(str(row.row_number), {})
            # A persisted "searching" row means the prior worker was interrupted (for
            # example by a container restart). It is safe to retry because a live worker
            # visits each row only once. Queued/downloading/complete rows still belong to
            # the download pipeline and must not be submitted twice.
            if current.get("status") in {"queued", "downloading", "complete"}:
                continue
            update_row_state(list_id, row.row_number, "searching")
            try:
                book = provider._to_metadata(list_id, row)
                library_match = find_grimmory_match(
                    title=book.title,
                    authors=book.authors,
                    isbn_10=book.isbn_10,
                    isbn_13=book.isbn_13,
                    user_id=user_id,
                )
                if library_match is not None:
                    update_row_state(
                        list_id,
                        row.row_number,
                        "complete",
                        completion_reason="already_in_library",
                        status_message="Already in Grimmory library",
                        library_book_id=library_match.book_id,
                    )
                    continue
                matches: list[Any] = []
                search_errors: list[str] = []
                # Source ordering, format/language filtering and result ranking are owned by
                # the configured release sources, just as in /api/releases.
                for source_info in list_available_sources():
                    if not source_info.get("enabled"):
                        continue
                    source_name = str(source_info["name"])
                    if (
                        resolve_policy_mode(
                            source=source_name,
                            content_type="ebook",
                            global_settings=global_settings,
                        )
                        != PolicyMode.DOWNLOAD
                    ):
                        continue
                    try:
                        source = get_source(source_name)
                        plan = build_release_search_plan(book)
                        matches.extend(
                            source.search(book, plan, expand_search=False, content_type="ebook")
                        )
                    except Exception as exc:  # noqa: BLE001 - continue with remaining sources
                        search_errors.append(f"{source_name}: {exc}")
                if not matches:
                    if search_errors:
                        update_row_state(
                            list_id,
                            row.row_number,
                            "failed",
                            error="; ".join(search_errors),
                        )
                    else:
                        update_row_state(list_id, row.row_number, "no_match")
                    continue

                release = matches[0]
                payload = asdict(release)
                success, error = queue_release(payload, 0, user_id=user_id, username=username)
                if not success:
                    update_row_state(
                        list_id, row.row_number, "failed", error=error or "Queue failed"
                    )
                    continue
                update_row_state(
                    list_id,
                    row.row_number,
                    "queued",
                    task_id=release.source_id,
                    source=release.source,
                    format=release.format,
                )
            except Exception as exc:  # noqa: BLE001 - isolate provider failures to one row
                update_row_state(list_id, row.row_number, "failed", error=str(exc))
    finally:
        with _worker_lock:
            _workers.pop(list_id, None)


def queue_all(
    list_id: str,
    *,
    queue_release: Callable[..., tuple[bool, str | None]],
    global_settings: dict[str, Any],
    user_id: int | None,
    username: str | None,
) -> bool:
    """Start processing eligible rows. Returns False if this list is already running."""
    with _worker_lock:
        existing = _workers.get(list_id)
        if existing and existing.is_alive():
            return False
        worker = threading.Thread(
            target=_process_list,
            kwargs={
                "list_id": list_id,
                "queue_release": queue_release,
                "global_settings": global_settings,
                "user_id": user_id,
                "username": username,
            },
            daemon=True,
            name=f"csv-list-{list_id}",
        )
        _workers[list_id] = worker
        worker.start()
        return True
