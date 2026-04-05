from pathlib import Path
from src.core.export_task import ExportTask
from src.core.export_params import ExportParams
from src.core.project import Project


def test_task_default_status():
    task = ExportTask(
        project=Project(),
        output_path=Path("out.mp4"),
        quality=23,
        params=ExportParams(),
    )
    assert task.status == "pending"
    assert task.progress == 0.0
    assert task.error is None


def test_task_has_unique_id():
    t1 = ExportTask(project=Project(), output_path=Path("a.mp4"), quality=23, params=ExportParams())
    t2 = ExportTask(project=Project(), output_path=Path("b.mp4"), quality=23, params=ExportParams())
    assert t1.id != t2.id
    assert len(t1.id) == 8


def test_task_status_values():
    task = ExportTask(project=Project(), output_path=Path("out.mp4"), quality=23, params=ExportParams())
    for status in ("pending", "running", "done", "failed", "cancelled"):
        task.status = status
        assert task.status == status
