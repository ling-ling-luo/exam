import threading
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from src.core.export_task import ExportTask
from src.core.export_params import ExportParams
from src.core.project import Project


def make_task(name="out.mp4"):
    return ExportTask(
        project=Project(),
        output_path=Path(name),
        quality=23,
        params=ExportParams(),
    )


def test_add_task_pending():
    from src.core.task_queue import TaskQueue
    q = TaskQueue(MagicMock())
    task = make_task()
    q.add(task)
    assert task in q.get_tasks()
    assert task.status == "pending"


def test_cancel_pending_task():
    from src.core.task_queue import TaskQueue
    q = TaskQueue(MagicMock())
    task = make_task()
    q.add(task)
    q.cancel(task.id)
    assert task.status == "cancelled"


def test_sequential_execution():
    """两个任务按顺序执行"""
    from src.core.task_queue import TaskQueue

    order = []
    done = threading.Event()

    def fake_export(project, output_path, quality, progress_cb=None, params=None, cancel_event=None):
        order.append(output_path.name)
        if len(order) == 2:
            done.set()

    mock_executor = MagicMock()
    mock_executor.export.side_effect = fake_export

    q = TaskQueue(mock_executor)
    q.start()

    t1 = make_task("a.mp4")
    t2 = make_task("b.mp4")
    q.add(t1)
    q.add(t2)

    done.wait(timeout=5.0)
    q.shutdown()

    assert order == ["a.mp4", "b.mp4"]
    assert t1.status == "done"
    assert t2.status == "done"


def test_cancel_running_sets_cancel_event():
    """取消 running 任务时会触发 cancel_event"""
    from src.core.task_queue import TaskQueue

    received_event = []
    blocking = threading.Event()
    started = threading.Event()

    def fake_export(project, output_path, quality, progress_cb=None, params=None, cancel_event=None):
        received_event.append(cancel_event)
        started.set()
        blocking.wait(timeout=3.0)

    mock_executor = MagicMock()
    mock_executor.export.side_effect = fake_export

    q = TaskQueue(mock_executor)
    q.start()

    task = make_task()
    q.add(task)

    started.wait(timeout=3.0)
    assert task.status == "running"
    q.cancel(task.id)
    assert received_event and received_event[0].is_set()

    blocking.set()
    q.shutdown()


def test_failed_task():
    from src.core.task_queue import TaskQueue

    started = threading.Event()
    finished = threading.Event()

    def fake_export(*args, **kwargs):
        started.set()
        raise RuntimeError("ffmpeg crashed")

    mock_executor = MagicMock()
    mock_executor.export.side_effect = fake_export

    q = TaskQueue(mock_executor)

    def on_updated():
        if q.get_tasks() and q.get_tasks()[0].status in ("failed", "done", "cancelled"):
            finished.set()

    q.set_on_updated(on_updated)
    q.start()

    task = make_task()
    q.add(task)
    finished.wait(timeout=3.0)

    q.shutdown()
    assert task.status == "failed"
    assert "ffmpeg crashed" in task.error
