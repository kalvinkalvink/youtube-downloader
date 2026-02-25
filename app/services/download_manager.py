from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional

from app.core.models import DownloadStatus, DownloadTask
from app.core.settings import AppSettings
from app.services.download_service import DownloadService


UpdateCallback = Callable[[], None]


class DownloadManager:
    def __init__(self, settings: AppSettings):
        self._settings = settings
        self._tasks: Dict[str, DownloadTask] = {}
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._lock = threading.Lock()
        self._workers: List[threading.Thread] = []
        self._stop_event = threading.Event()
        self._on_update: Optional[UpdateCallback] = None
        self._running_processes: Dict[str, threading.Event] = {}
        self._update_lock = threading.Lock()

        self._ensure_download_dir()
        self._start_workers()

    def _ensure_download_dir(self) -> None:
        Path(self._settings.download_dir).mkdir(parents=True, exist_ok=True)

    def _start_workers(self) -> None:
        for _ in range(self._settings.max_concurrent_downloads):
            t = threading.Thread(target=self._worker_loop, daemon=True)
            t.start()
            self._workers.append(t)

    def _notify_update(self) -> None:
        if not self._on_update:
            return

        with self._update_lock:
            self._on_update()

    def set_update_callback(self, callback: UpdateCallback) -> None:
        self._on_update = callback

    def add_task(self, task: DownloadTask) -> None:
        with self._lock:
            self._tasks[task.id] = task
            self._queue.put(task.id)
        self._notify_update()

    def get_tasks(self) -> List[DownloadTask]:
        with self._lock:
            return list(self._tasks.values())

    def update_settings(self, settings: AppSettings) -> None:
        with self._lock:
            self._settings = settings
            self._ensure_download_dir()
            # For simplicity we do not resize existing worker threads dynamically.

    def cancel_task(self, task_id: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task.mark_status(DownloadStatus.CANCELED)

        cancel_event = self._running_processes.get(task_id)
        if cancel_event:
            cancel_event.set()

        self._notify_update()

    def clear_completed_tasks(self) -> None:
        with self._lock:
            completed_ids = [
                tid
                for tid, task in self._tasks.items()
                if task.status is DownloadStatus.COMPLETED
            ]
            for tid in completed_ids:
                self._tasks.pop(tid, None)
        self._notify_update()

    def cancel_all_downloading(self) -> None:
        with self._lock:
            active_tasks = [
                task
                for task in self._tasks.values()
                if task.status in (DownloadStatus.QUEUED, DownloadStatus.DOWNLOADING)
            ]

        for task in active_tasks:
            self.cancel_task(task.id)

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                task_id = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            cancel_event = threading.Event()
            self._running_processes[task_id] = cancel_event

            with self._lock:
                task = self._tasks.get(task_id)
                if not task or task.status is DownloadStatus.CANCELED:
                    self._running_processes.pop(task_id, None)
                    continue
                task.mark_status(DownloadStatus.DOWNLOADING)
            self._notify_update()

            try:

                def progress_callback(progress: float) -> None:
                    with self._lock:
                        task = self._tasks.get(task_id)
                        if task and task.status is DownloadStatus.DOWNLOADING:
                            task.progress = progress
                    self._notify_update()

                success, error = DownloadService.download(
                    task,
                    progress_callback=progress_callback,
                    cancel_event=cancel_event,
                )

                with self._lock:
                    task = self._tasks.get(task_id)
                    if not task:
                        continue
                    if cancel_event.is_set():
                        task.mark_status(DownloadStatus.CANCELED)
                    elif success:
                        task.progress = 100.0
                        task.mark_status(DownloadStatus.COMPLETED)
                    else:
                        task.mark_status(DownloadStatus.FAILED, error=error)
            except Exception as exc:
                with self._lock:
                    task = self._tasks.get(task_id)
                    if task:
                        task.mark_status(DownloadStatus.FAILED, error=str(exc))
            finally:
                self._running_processes.pop(task_id, None)
                self._notify_update()
                self._queue.task_done()

    def stop(self) -> None:
        self._stop_event.set()
        for t in self._workers:
            t.join(timeout=0.5)
