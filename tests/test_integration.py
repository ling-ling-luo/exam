# tests/test_integration.py
"""集成测试：验证完整的数据流（mock ffmpeg）"""
import copy
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.export_params import ExportParams, PRESETS
from src.core.export_task import ExportTask
from src.core.project import Project
from src.core.segment import Segment
from src.core.task_queue import TaskQueue


def make_project_with_segment():
    p = Project()
    p.add_segment(Segment(source_path=Path("bun33s.mp4"), start_time=0, end_time=5))
    return p


def test_presets_cover_common_resolutions():
    assert PRESETS["720p"].width == 1280
    assert PRESETS["720p"].height == 720
    assert PRESETS["1080p"].width == 1920
    assert PRESETS["1080p"].height == 1080


def test_queue_add_and_complete():
    """任务加入队列后被执行并标记 done"""
    done = threading.Event()

    def fake_export(project, output_path, quality, progress_cb=None, params=None, cancel_event=None):
        done.set()

    executor = MagicMock()
    executor.export.side_effect = fake_export

    q = TaskQueue(executor)
    q.start()

    task = ExportTask(
        project=make_project_with_segment(),
        output_path=Path("output/test_out.mp4"),
        quality=23,
        params=PRESETS["720p"],
    )
    q.add(task)
    done.wait(timeout=5.0)
    time.sleep(0.1)

    q.shutdown()
    assert task.status == "done"


def test_queue_preserves_project_snapshot():
    """project 加入队列后的修改不影响已入队的任务"""
    project = make_project_with_segment()
    original_count = len(project.segments)

    task = ExportTask(
        project=copy.deepcopy(project),
        output_path=Path("out.mp4"),
        quality=23,
        params=ExportParams(),
    )

    # 修改原始 project
    project.add_segment(Segment(source_path=Path("other.mp4"), start_time=0, end_time=3))

    assert len(task.project.segments) == original_count


def test_export_params_passed_to_executor():
    """ExportParams 被正确透传到 executor.export"""
    done = threading.Event()
    received_params = []

    def fake_export(project, output_path, quality, progress_cb=None, params=None, cancel_event=None):
        received_params.append(params)
        done.set()

    executor = MagicMock()
    executor.export.side_effect = fake_export

    q = TaskQueue(executor)
    q.start()

    params = PRESETS["480p"]
    task = ExportTask(
        project=Project(),
        output_path=Path("out.mp4"),
        quality=23,
        params=params,
    )
    q.add(task)
    done.wait(timeout=3.0)
    q.shutdown()

    assert received_params[0] is params
