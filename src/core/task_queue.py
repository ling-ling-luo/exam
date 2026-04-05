import threading
from typing import List, Optional, Callable

from .export_task import ExportTask


class TaskQueue:
    """顺序执行导出任务的后台队列"""

    def __init__(self, executor):
        self._executor = executor
        self._tasks: List[ExportTask] = []
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._shutdown = threading.Event()
        self._cancel_event: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None
        self._on_updated: Optional[Callable] = None

    def set_on_updated(self, callback: Callable) -> None:
        self._on_updated = callback

    def add(self, task: ExportTask) -> None:
        with self._lock:
            self._tasks.append(task)
        self._wake.set()
        self._notify()

    def cancel(self, task_id: str) -> None:
        with self._lock:
            for task in self._tasks:
                if task.id == task_id:
                    if task.status == "pending":
                        task.status = "cancelled"
                        self._notify()
                        return
                    elif task.status == "running" and self._cancel_event:
                        self._cancel_event.set()
                        return

    def get_tasks(self) -> List[ExportTask]:
        with self._lock:
            return list(self._tasks)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def shutdown(self) -> None:
        self._shutdown.set()
        self._wake.set()

    def _notify(self) -> None:
        if self._on_updated:
            self._on_updated()

    def _next_pending(self) -> Optional[ExportTask]:
        with self._lock:
            for t in self._tasks:
                if t.status == "pending":
                    return t
        return None

    def _run(self) -> None:
        while not self._shutdown.is_set():
            self._wake.wait(timeout=1.0)
            self._wake.clear()
            while True:
                task = self._next_pending()
                if task is None:
                    break
                self._execute(task)

    def _execute(self, task: ExportTask) -> None:
        cancel_event = threading.Event()
        with self._lock:
            task.status = "running"
            self._cancel_event = cancel_event
        self._notify()

        def progress_cb(p: float) -> None:
            with self._lock:
                task.progress = p
            self._notify()

        try:
            self._executor.export(
                task.project,
                task.output_path,
                task.quality,
                progress_cb,
                params=task.params,
                cancel_event=cancel_event,
            )
            with self._lock:
                if cancel_event.is_set():
                    task.status = "cancelled"
                else:
                    task.status = "done"
                    task.progress = 100.0
        except Exception as e:
            with self._lock:
                task.status = "failed"
                task.error = str(e)
        finally:
            with self._lock:
                self._cancel_event = None
        self._notify()
