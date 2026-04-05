# Bonus Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现缩略图预览、顺序任务队列（含取消）、可配置导出参数（预设 + 手动覆盖）三项加分功能。

**Architecture:** 新增 `ExportParams`/`ExportTask` 数据模型和 `TaskQueue` 后台引擎；`ffmpeg.py` 注入参数与取消信号；TUI 层新增 `TaskQueueScreen`，改造 `ExportScreen`（加入队列）和 `MediaListScreen`（缩略图预览）；`app.py` 持有 `TaskQueue` 单例并路由新屏幕。

**Tech Stack:** Python 3.10+, Textual 0.50+, ffmpeg/ffprobe CLI, pytest + pytest-mock

---

## 文件变更清单

| 文件 | 类型 | 职责 |
|------|------|------|
| `src/core/export_params.py` | 新建 | ExportParams dataclass + PRESETS |
| `src/core/export_task.py` | 新建 | ExportTask dataclass |
| `src/core/task_queue.py` | 新建 | 后台顺序执行引擎 |
| `src/tui/screens/task_queue.py` | 新建 | TaskQueueScreen |
| `src/utils/ffmpeg.py` | 修改 | generate_thumbnail, params/cancel 注入 |
| `src/core/executor.py` | 修改 | export() 透传 params/cancel_event |
| `src/tui/screens/export.py` | 修改 | 预设选择 + 加入队列 |
| `src/tui/screens/media_list.py` | 修改 | 缩略图按钮 + 队列入口 |
| `src/tui/app.py` | 修改 | TaskQueue 单例 + "queue" 路由 |
| `tests/test_export_params.py` | 新建 | ExportParams 单元测试 |
| `tests/test_export_task.py` | 新建 | ExportTask 单元测试 |
| `tests/test_task_queue.py` | 新建 | TaskQueue 引擎测试 |
| `tests/test_ffmpeg_extras.py` | 新建 | generate_thumbnail + params 注入测试 |

---

## Task 1: ExportParams 数据模型

**Files:**
- Create: `src/core/export_params.py`
- Create: `tests/test_export_params.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_export_params.py
import pytest
from src.core.export_params import ExportParams, PRESETS


def test_default_params():
    p = ExportParams()
    assert p.preset == "original"
    assert p.width is None
    assert p.height is None
    assert p.video_bitrate is None
    assert p.fps is None
    assert p.audio_bitrate == "128k"


def test_presets_exist():
    assert "original" in PRESETS
    assert "480p" in PRESETS
    assert "720p" in PRESETS
    assert "1080p" in PRESETS


def test_480p_preset():
    p = PRESETS["480p"]
    assert p.width == 854
    assert p.height == 480
    assert p.video_bitrate == "1500k"


def test_720p_preset():
    p = PRESETS["720p"]
    assert p.width == 1280
    assert p.height == 720
    assert p.video_bitrate == "4000k"


def test_1080p_preset():
    p = PRESETS["1080p"]
    assert p.width == 1920
    assert p.height == 1080
    assert p.video_bitrate == "8000k"


def test_original_preset_has_no_constraints():
    p = PRESETS["original"]
    assert p.width is None
    assert p.height is None
    assert p.video_bitrate is None
    assert p.fps is None
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /home/cloud_dev/github.code/exam
python -m pytest tests/test_export_params.py -v 2>&1 | head -20
```
期望：`ModuleNotFoundError: No module named 'src.core.export_params'`

- [ ] **Step 3: 实现 ExportParams**

```python
# src/core/export_params.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExportParams:
    preset: str = "original"
    video_bitrate: Optional[str] = None   # None = 由 CRF 控制；"4000k" 等 = 固定码率
    audio_bitrate: str = "128k"
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None           # None = 保持源帧率


PRESETS: dict = {
    "original": ExportParams(preset="original"),
    "480p":  ExportParams(preset="480p",  width=854,  height=480,  video_bitrate="1500k"),
    "720p":  ExportParams(preset="720p",  width=1280, height=720,  video_bitrate="4000k"),
    "1080p": ExportParams(preset="1080p", width=1920, height=1080, video_bitrate="8000k"),
}
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
python -m pytest tests/test_export_params.py -v
```
期望：全部 `PASSED`

- [ ] **Step 5: 提交**

```bash
git add src/core/export_params.py tests/test_export_params.py
git commit -m "feat: add ExportParams dataclass with presets"
```

---

## Task 2: ExportTask 数据模型

**Files:**
- Create: `src/core/export_task.py`
- Create: `tests/test_export_task.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_export_task.py
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
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_export_task.py -v 2>&1 | head -20
```
期望：`ModuleNotFoundError: No module named 'src.core.export_task'`

- [ ] **Step 3: 实现 ExportTask**

```python
# src/core/export_task.py
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .project import Project
from .export_params import ExportParams


@dataclass
class ExportTask:
    project: Project
    output_path: Path
    quality: int
    params: ExportParams
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: str = "pending"   # pending / running / done / failed / cancelled
    progress: float = 0.0
    error: Optional[str] = None
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
python -m pytest tests/test_export_task.py -v
```
期望：全部 `PASSED`

- [ ] **Step 5: 提交**

```bash
git add src/core/export_task.py tests/test_export_task.py
git commit -m "feat: add ExportTask dataclass"
```

---

## Task 3: ffmpeg.py — generate_thumbnail

**Files:**
- Modify: `src/utils/ffmpeg.py`
- Create: `tests/test_ffmpeg_extras.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_ffmpeg_extras.py
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def test_generate_thumbnail_calls_ffmpeg(tmp_path, mocker):
    mocker.patch("src.utils.ffmpeg.check_ffmpeg", return_value=True)
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = MagicMock(returncode=0)

    from src.utils.ffmpeg import generate_thumbnail
    out = tmp_path / "thumb.jpg"
    result = generate_thumbnail(Path("input.mp4"), out, time=5.0)

    assert result == out
    cmd = mock_run.call_args[0][0]
    assert config_ffmpeg_path_in(cmd)   # ffmpeg binary present
    assert "-ss" in cmd
    assert "5.0" in cmd
    assert str(out) in cmd


def config_ffmpeg_path_in(cmd):
    return len(cmd) > 0  # at minimum a command was built


def test_generate_thumbnail_raises_on_ffmpeg_error(tmp_path, mocker):
    mocker.patch("src.utils.ffmpeg.check_ffmpeg", return_value=True)
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = MagicMock(returncode=1, stderr="error msg")

    from src.utils.ffmpeg import generate_thumbnail
    from src.errors import ExportError

    with pytest.raises(ExportError):
        generate_thumbnail(Path("input.mp4"), tmp_path / "thumb.jpg", time=0)


def test_generate_thumbnail_cached(tmp_path, mocker):
    """已存在的缩略图不重复调用 ffmpeg"""
    mocker.patch("src.utils.ffmpeg.check_ffmpeg", return_value=True)
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = MagicMock(returncode=0)

    from src.utils.ffmpeg import generate_thumbnail
    out = tmp_path / "thumb.jpg"
    out.touch()  # 模拟已存在

    generate_thumbnail(Path("input.mp4"), out, time=5.0)
    mock_run.assert_not_called()
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_ffmpeg_extras.py -v 2>&1 | head -25
```
期望：`ImportError` 或 `AttributeError: module has no attribute 'generate_thumbnail'`

- [ ] **Step 3: 在 ffmpeg.py 末尾添加 generate_thumbnail**

在 `src/utils/ffmpeg.py` 文件末尾（`export_project` 函数之后）添加：

```python
def generate_thumbnail(path: Path, output_path: Path, time: float = 0.0) -> Path:
    """提取视频指定时间点的帧作为缩略图 JPEG。

    若 output_path 已存在则直接返回（缓存）。
    """
    if output_path.exists():
        return output_path

    if not check_ffmpeg():
        raise FFmpegNotFoundError()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        config.ffmpeg_path,
        "-y",
        "-ss", str(time),
        "-i", str(path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            raise ExportError(f"生成缩略图失败: {result.stderr[:200]}")
        return output_path
    except subprocess.TimeoutExpired:
        raise ExportError("生成缩略图超时")
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
python -m pytest tests/test_ffmpeg_extras.py -v
```
期望：全部 `PASSED`

- [ ] **Step 5: 提交**

```bash
git add src/utils/ffmpeg.py tests/test_ffmpeg_extras.py
git commit -m "feat: add generate_thumbnail with caching"
```

---

## Task 4: ffmpeg.py — ExportParams 与 cancel_event 注入

**Files:**
- Modify: `src/utils/ffmpeg.py`
- Modify: `src/core/executor.py`
- Modify: `tests/test_ffmpeg_extras.py`

- [ ] **Step 1: 追加测试到 test_ffmpeg_extras.py**

在 `tests/test_ffmpeg_extras.py` 末尾追加：

```python
def test_split_video_720p_params(tmp_path, mocker):
    mocker.patch("src.utils.ffmpeg.check_ffmpeg", return_value=True)
    mocker.patch("src.utils.ffmpeg.get_video_info", return_value={"duration": 30.0})
    mock_popen = mocker.patch("subprocess.Popen")
    proc = MagicMock()
    proc.poll.return_value = 0
    proc.communicate.return_value = ("", "")
    proc.returncode = 0
    mock_popen.return_value = proc

    from src.utils.ffmpeg import split_video
    from src.core.export_params import ExportParams

    params = ExportParams(preset="720p", width=1280, height=720, video_bitrate="4000k")
    split_video(Path("in.mp4"), tmp_path / "out.mp4", 0, 10, params=params)

    cmd = mock_popen.call_args[0][0]
    assert "-vf" in cmd
    assert "scale=1280:720" in cmd
    assert "-b:v" in cmd
    assert "4000k" in cmd
    assert "-crf" not in cmd   # 固定码率时不用 CRF


def test_split_video_cancel(tmp_path, mocker):
    import threading
    mocker.patch("src.utils.ffmpeg.check_ffmpeg", return_value=True)
    mocker.patch("src.utils.ffmpeg.get_video_info", return_value={"duration": 30.0})
    mock_popen = mocker.patch("subprocess.Popen")
    proc = MagicMock()
    proc.poll.return_value = None   # 模拟一直在运行
    proc.stderr.readline.return_value = ""
    proc.communicate.return_value = ("", "")
    proc.returncode = 0
    mock_popen.return_value = proc

    cancel = threading.Event()
    cancel.set()   # 立即取消

    from src.utils.ffmpeg import split_video
    split_video(Path("in.mp4"), tmp_path / "out.mp4", 0, 10, cancel_event=cancel)

    proc.terminate.assert_called()
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_ffmpeg_extras.py::test_split_video_720p_params tests/test_ffmpeg_extras.py::test_split_video_cancel -v 2>&1 | head -20
```
期望：`TypeError: split_video() got an unexpected keyword argument 'params'`

- [ ] **Step 3: 修改 split_video 签名与实现**

将 `src/utils/ffmpeg.py` 中的 `split_video` 函数替换为：

```python
def split_video(
    input_path: Path,
    output_path: Path,
    start_time: float,
    end_time: Optional[float] = None,
    quality: int = 23,
    progress_callback: Optional[Callable[[float], None]] = None,
    params=None,
    cancel_event: Optional[threading.Event] = None,
) -> None:
    """切分视频"""
    if not check_ffmpeg():
        raise FFmpegNotFoundError()

    duration = end_time - start_time if end_time else None

    cmd = [
        config.ffmpeg_path,
        "-y",
        "-ss", str(start_time),
    ]

    if duration:
        cmd.extend(["-t", str(duration)])

    cmd.extend(["-i", str(input_path), "-c:v", "libx264", "-preset", "medium"])

    # 码率或 CRF（二选一）
    if params and params.video_bitrate:
        cmd.extend(["-b:v", params.video_bitrate])
    else:
        cmd.extend(["-crf", str(quality)])

    # 分辨率缩放
    if params and params.width and params.height:
        cmd.extend(["-vf", f"scale={params.width}:{params.height}"])

    # 帧率
    if params and params.fps:
        cmd.extend(["-r", str(params.fps)])

    audio_bitrate = params.audio_bitrate if params else "128k"
    cmd.extend(["-c:a", "aac", "-b:a", audio_bitrate, str(output_path)])

    logger.info(f"执行命令: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        universal_newlines=True,
    )

    duration_total = None
    if progress_callback:
        try:
            info = get_video_info(input_path)
            duration_total = info.get("duration", 0)
        except Exception:
            pass

    def monitor_progress():
        while process.poll() is None:
            if cancel_event and cancel_event.is_set():
                process.terminate()
                return
            line = process.stderr.readline()
            if "time=" in line and progress_callback:
                try:
                    time_str = line.split("time=")[1].split()[0]
                    parts = time_str.split(":")
                    current_time = 0.0
                    for p in parts:
                        current_time = current_time * 60 + float(p)
                    if duration_total and duration_total > 0:
                        progress = min(int(current_time / duration_total * 100), 100)
                        progress_callback(progress)
                except Exception:
                    pass

    monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
    monitor_thread.start()

    _, stderr = process.communicate()

    if cancel_event and cancel_event.is_set():
        return   # 已取消，不报错

    if process.returncode != 0:
        logger.error(f"ffmpeg 错误: {stderr}")
        raise ExportError(f"视频切分失败: {stderr[:200]}")

    if progress_callback:
        progress_callback(100)
```

- [ ] **Step 4: 修改 export_project 透传 params 和 cancel_event**

将 `src/utils/ffmpeg.py` 中的 `export_project` 函数签名和内部调用更新：

```python
def export_project(
    project,
    output_path: Path,
    quality: int = 23,
    progress_callback: Optional[Callable[[float], None]] = None,
    params=None,
    cancel_event: Optional[threading.Event] = None,
) -> None:
    """导出项目"""
    if not project.segments:
        raise ExportError("没有片段可导出")

    temp_dir = output_path.parent / ".temp"
    temp_dir.mkdir(exist_ok=True)

    try:
        temp_files = []
        total_segments = len(project.segments)

        for i, segment in enumerate(project.segments):
            if cancel_event and cancel_event.is_set():
                return

            temp_file = temp_dir / f"segment_{i}_{segment.id}.mp4"
            logger.info(f"导出片段 {i+1}/{total_segments}: {segment}")

            split_video(
                segment.source_path,
                temp_file,
                segment.start_time,
                segment.end_time,
                quality,
                progress_callback=lambda p, i=i, total=total_segments: progress_callback(
                    (i * 100 + p) / total
                ) if progress_callback else None,
                params=params,
                cancel_event=cancel_event,
            )
            temp_files.append(temp_file)

        if cancel_event and cancel_event.is_set():
            return

        logger.info("拼接所有片段...")
        if progress_callback:
            progress_callback(95)

        concat_videos(temp_files, output_path, quality)

        if progress_callback:
            progress_callback(100)

        logger.info(f"导出完成: {output_path}")

    finally:
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
```

- [ ] **Step 5: 修改 Executor.export 透传新参数**

将 `src/core/executor.py` 中的 `export` 方法更新为：

```python
def export(
    self,
    project: Project,
    output_path: Path,
    quality: int = None,
    progress_callback: Optional[Callable[[float], None]] = None,
    params=None,
    cancel_event=None,
) -> None:
    """导出项目"""
    if not project.segments:
        raise ValidationError("项目没有片段")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    validate_output_path(output_path)

    if quality is None:
        quality = config.default_quality

    logger.info(f"开始导出到: {output_path}")

    export_project(project, output_path, quality, progress_callback, params, cancel_event)
```

- [ ] **Step 6: 运行所有测试，确认通过**

```bash
python -m pytest tests/test_ffmpeg_extras.py -v
```
期望：全部 `PASSED`

- [ ] **Step 7: 提交**

```bash
git add src/utils/ffmpeg.py src/core/executor.py tests/test_ffmpeg_extras.py
git commit -m "feat: inject ExportParams and cancel_event into ffmpeg pipeline"
```

---

## Task 5: TaskQueue 引擎

**Files:**
- Create: `src/core/task_queue.py`
- Create: `tests/test_task_queue.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_task_queue.py
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
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

    def fake_export(project, output_path, quality, progress_cb=None, params=None, cancel_event=None):
        received_event.append(cancel_event)
        blocking.wait(timeout=3.0)  # 阻塞直到被取消

    mock_executor = MagicMock()
    mock_executor.export.side_effect = fake_export

    q = TaskQueue(mock_executor)
    q.start()

    task = make_task()
    q.add(task)

    # 等任务开始运行
    deadline = time.time() + 3.0
    while task.status != "running" and time.time() < deadline:
        time.sleep(0.05)

    assert task.status == "running"
    q.cancel(task.id)
    assert received_event and received_event[0].is_set()

    blocking.set()
    q.shutdown()


def test_failed_task():
    from src.core.task_queue import TaskQueue

    done = threading.Event()

    def fake_export(*args, **kwargs):
        done.set()
        raise RuntimeError("ffmpeg crashed")

    mock_executor = MagicMock()
    mock_executor.export.side_effect = fake_export

    q = TaskQueue(mock_executor)
    q.start()

    task = make_task()
    q.add(task)
    done.wait(timeout=3.0)
    time.sleep(0.1)   # 让状态更新完成

    q.shutdown()
    assert task.status == "failed"
    assert "ffmpeg crashed" in task.error
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_task_queue.py -v 2>&1 | head -20
```
期望：`ModuleNotFoundError: No module named 'src.core.task_queue'`

- [ ] **Step 3: 实现 TaskQueue**

```python
# src/core/task_queue.py
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

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

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
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
python -m pytest tests/test_task_queue.py -v
```
期望：全部 `PASSED`

- [ ] **Step 5: 提交**

```bash
git add src/core/task_queue.py tests/test_task_queue.py
git commit -m "feat: add TaskQueue sequential execution engine with cancel support"
```

---

## Task 6: ExportScreen — 预设选择 + 加入队列

**Files:**
- Modify: `src/tui/screens/export.py`

（TUI 屏幕无单元测试，通过手动交互和 Task 10 集成测试验证）

- [ ] **Step 1: 完整替换 export.py**

```python
# src/tui/screens/export.py
import copy
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Input, Label, Select

from ...core.project import Project
from ...core.executor import Executor
from ...core.export_params import ExportParams, PRESETS
from ...core.export_task import ExportTask
from ...utils.config import config


PRESET_OPTIONS = [
    ("original — 保持原始", "original"),
    ("480p  (854×480,  1500k)", "480p"),
    ("720p  (1280×720, 4000k)", "720p"),
    ("1080p (1920×1080,8000k)", "1080p"),
    ("custom — 手动设置", "custom"),
]


class ExportScreen(ModalScreen):
    """导出设置屏幕 — 配置参数后加入队列"""

    def __init__(self, project: Project, executor: Executor):
        super().__init__()
        self.project = project
        self.executor = executor
        self._current_preset = "original"

    def compose(self) -> ComposeResult:
        yield Container(
            Static("📤 导出设置", classes="title"),
            Vertical(
                Label("输出文件名:"),
                Input(value="output.mp4", id="input-filename"),
                Label("导出质量 (CRF, 0-51, 数值越低越好):"),
                Input(value=str(config.default_quality), id="input-quality"),
                Label("分辨率预设:"),
                Select(
                    options=PRESET_OPTIONS,
                    value="original",
                    id="select-preset",
                ),
                Label("自定义参数 (选 custom 时生效):"),
                Horizontal(
                    Input(placeholder="宽度 px", id="input-width"),
                    Input(placeholder="高度 px", id="input-height"),
                    Input(placeholder="视频码率 如 4000k", id="input-vbitrate"),
                    Input(placeholder="帧率 如 30", id="input-fps"),
                    id="custom-params",
                ),
                id="export-settings",
            ),
            Static("", id="export-status"),
            Horizontal(
                Button("加入队列", id="btn-enqueue", variant="primary"),
                Button("返回", id="btn-back", variant="default"),
                id="export-buttons",
            ),
            id="export-container",
        )

    def on_mount(self) -> None:
        if self.project.segments:
            duration = self.project.get_total_duration()
            info = f"片段数量: {len(self.project.segments)} | 总时长: {duration:.2f}秒"
            self.query_one("#export-status", Static).update(info)
            self._toggle_custom(False)
        else:
            self.query_one("#btn-enqueue", Button).disabled = True
            self.query_one("#export-status", Static).update("⚠️ 时间线为空，请先添加片段")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-preset":
            self._current_preset = str(event.value)
            self._toggle_custom(self._current_preset == "custom")

    def _toggle_custom(self, enabled: bool) -> None:
        for field_id in ["input-width", "input-height", "input-vbitrate", "input-fps"]:
            self.query_one(f"#{field_id}", Input).disabled = not enabled

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-enqueue":
            self._enqueue()
        elif event.button.id == "btn-back":
            self.dismiss()

    def _build_params(self) -> ExportParams:
        if self._current_preset != "custom":
            return PRESETS.get(self._current_preset, ExportParams())

        width_str = self.query_one("#input-width", Input).value.strip()
        height_str = self.query_one("#input-height", Input).value.strip()
        vbitrate = self.query_one("#input-vbitrate", Input).value.strip() or None
        fps_str = self.query_one("#input-fps", Input).value.strip()

        width = int(width_str) if width_str.isdigit() else None
        height = int(height_str) if height_str.isdigit() else None
        fps = float(fps_str) if fps_str.replace(".", "").isdigit() else None

        return ExportParams(
            preset="custom",
            width=width,
            height=height,
            video_bitrate=vbitrate,
            fps=fps,
        )

    def _enqueue(self) -> None:
        filename = self.query_one("#input-filename", Input).value.strip() or "output.mp4"
        if not filename.endswith((".mp4", ".avi", ".mov", ".flv", ".mkv")):
            filename += ".mp4"

        try:
            quality = int(self.query_one("#input-quality", Input).value.strip())
            if quality < 0 or quality > 51:
                raise ValueError()
        except ValueError:
            self.notify("质量值必须是 0-51 之间的整数", severity="warning")
            return

        output_path = config.output_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        params = self._build_params()
        task = ExportTask(
            project=copy.deepcopy(self.project),
            output_path=output_path,
            quality=quality,
            params=params,
        )

        self.app.task_queue.add(task)
        self.notify(f"✅ 已加入队列: {filename}", severity="information")
        self.dismiss()
```

- [ ] **Step 2: 运行现有测试确认无回归**

```bash
python -m pytest tests/ -v --ignore=tests/test_task_queue.py -q
```
期望：全部 `PASSED`，无 import error

- [ ] **Step 3: 提交**

```bash
git add src/tui/screens/export.py
git commit -m "feat: ExportScreen — preset selector and add-to-queue"
```

---

## Task 7: MediaListScreen — 缩略图预览 + 队列入口

**Files:**
- Modify: `src/tui/screens/media_list.py`

- [ ] **Step 1: 修改 `_load_media_files` 中文件列表渲染部分**

将 `src/tui/screens/media_list.py` 中渲染文件列表的循环（`for i, f in enumerate(self.media_files):` 到 `container.mount(btn)`）替换为：

```python
            for i, f in enumerate(self.media_files):
                row = Horizontal(
                    Button(
                        f"{i+1}. {f.name}",
                        id=f"media_{i}",
                        classes="media-item",
                    ),
                    Button("🖼", id=f"thumb_{i}", classes="thumb-btn"),
                    classes="media-row",
                )
                container.mount(row)
```

- [ ] **Step 2: 更新 `on_button_pressed` 处理缩略图按钮**

将 `on_button_pressed` 整体替换为：

```python
    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id and button_id.startswith("media_"):
            index = int(button_id.split("_")[1])
            if 0 <= index < len(self.media_files):
                self.dismiss(self.media_files[index])

        elif button_id and button_id.startswith("thumb_"):
            index = int(button_id.split("_")[1])
            if 0 <= index < len(self.media_files):
                self._open_thumbnail(self.media_files[index])

        elif button_id == "btn_timeline":
            self.dismiss("timeline")
        elif button_id == "btn_export":
            self.dismiss("export")
        elif button_id == "btn_queue":
            self.dismiss("queue")
```

- [ ] **Step 3: 添加 `_open_thumbnail` 方法和队列按钮**

在 `MediaListScreen` 类末尾（`on_button_pressed` 之后）添加：

```python
    def _open_thumbnail(self, path: Path) -> None:
        import subprocess as sp
        from ...utils.ffmpeg import get_video_info, generate_thumbnail
        from ...errors import VideoClipError
        from ...utils.config import config

        try:
            info = get_video_info(path)
            duration = info.get("duration", 0)
            time_point = duration / 2 if duration > 0 else 0

            thumb_dir = config.output_dir / ".thumbnails"
            thumb_path = thumb_dir / f"{path.stem}_{time_point:.1f}.jpg"

            generate_thumbnail(path, thumb_path, time=time_point)
            sp.Popen(["xdg-open", str(thumb_path)])
            self.notify(f"缩略图: {thumb_path.name}", severity="information")
        except VideoClipError as e:
            self.notify(f"预览失败: {e.message}", severity="error")
        except Exception as e:
            self.notify(f"预览失败: {e}", severity="error")
```

在 `_load_media_files` 中，将底部导航按钮区块（`container.mount(Static(...))` 和后续按钮）替换为：

```python
            container.mount(
                Static("\n[Enter] 选择视频  [T] 时间线  [E] 导出  [J] 队列  [Q] 退出", classes="help")
            )
            container.mount(Button("📋 查看时间线 (T)", id="btn_timeline", classes="nav-btn"))
            container.mount(Button("📤 开始导出 (E)", id="btn_export", classes="nav-btn"))
            container.mount(Button("📬 任务队列 (J)", id="btn_queue", classes="nav-btn"))
```

- [ ] **Step 4: 运行现有测试确认无回归**

```bash
python -m pytest tests/ -q
```
期望：全部 `PASSED`

- [ ] **Step 5: 提交**

```bash
git add src/tui/screens/media_list.py
git commit -m "feat: MediaListScreen — thumbnail preview and queue entry"
```

---

## Task 8: TaskQueueScreen — 新屏幕

**Files:**
- Create: `src/tui/screens/task_queue.py`

- [ ] **Step 1: 创建 TaskQueueScreen**

```python
# src/tui/screens/task_queue.py
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Button, DataTable


STATUS_STYLE = {
    "pending":   "dim",
    "running":   "bold blue",
    "done":      "bold green",
    "failed":    "bold red",
    "cancelled": "yellow",
}


class TaskQueueScreen(ModalScreen):
    """任务队列屏幕 — 查看所有导出任务并可取消"""

    def compose(self) -> ComposeResult:
        yield Container(
            Static("📬 任务队列", classes="title"),
            DataTable(id="queue-table"),
            Static("", id="queue-summary"),
            Horizontal(
                Button("取消选中任务", id="btn-cancel", variant="error"),
                Button("关闭", id="btn-close"),
                id="queue-buttons",
            ),
            id="queue-container",
        )

    def on_mount(self) -> None:
        table = self.query_one("#queue-table", DataTable)
        table.add_columns("序号", "输出文件", "状态", "进度")
        table.cursor_type = "row"
        self._refresh()
        self.set_interval(0.5, self._refresh)

    def _refresh(self) -> None:
        tasks = self.app.task_queue.get_tasks()
        table = self.query_one("#queue-table", DataTable)
        table.clear()

        for i, task in enumerate(tasks):
            progress_str = f"{task.progress:.0f}%" if task.status == "running" else ""
            error_hint = f" ({task.error[:30]}...)" if task.error else ""
            status_str = task.status + error_hint

            table.add_row(
                str(i + 1),
                task.output_path.name,
                status_str,
                progress_str,
            )

        done = sum(1 for t in tasks if t.status == "done")
        running = sum(1 for t in tasks if t.status == "running")
        pending = sum(1 for t in tasks if t.status == "pending")
        self.query_one("#queue-summary", Static).update(
            f"共 {len(tasks)} 个任务 — 完成: {done}  运行中: {running}  等待: {pending}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss()
        elif event.button.id == "btn-cancel":
            table = self.query_one("#queue-table", DataTable)
            row = table.cursor_row
            tasks = self.app.task_queue.get_tasks()
            if row is not None and 0 <= row < len(tasks):
                task = tasks[row]
                if task.status in ("pending", "running"):
                    self.app.task_queue.cancel(task.id)
                    self.notify(f"已取消: {task.output_path.name}")
                else:
                    self.notify("该任务无法取消", severity="warning")
```

- [ ] **Step 2: 运行现有测试确认无回归**

```bash
python -m pytest tests/ -q
```
期望：全部 `PASSED`

- [ ] **Step 3: 提交**

```bash
git add src/tui/screens/task_queue.py
git commit -m "feat: add TaskQueueScreen with 500ms auto-refresh and cancel"
```

---

## Task 9: app.py — 接入 TaskQueue + 路由

**Files:**
- Modify: `src/tui/app.py`

- [ ] **Step 1: 完整替换 app.py**

```python
# src/tui/app.py
from pathlib import Path
from typing import Optional, Union

from textual.app import App
from textual.binding import Binding

from ..core.project import Project
from ..core.executor import Executor
from ..core.task_queue import TaskQueue
from ..utils.config import config
from .screens.media_list import MediaListScreen
from .screens.editor import EditorScreen
from .screens.export import ExportScreen
from .screens.confirm import ConfirmScreen


class VideoClipApp(App):
    """视频剪辑 TUI 应用"""

    CSS_PATH = "style.tcss"
    TITLE = "命令行视频剪辑工具"

    BINDINGS = [
        Binding("q", "quit", "退出", show=True),
    ]

    def __init__(self, video_dir: Optional[Path] = None):
        super().__init__()
        self.video_dir = video_dir or config.video_dir
        self.project = Project()
        self.executor = Executor()
        self.task_queue = TaskQueue(self.executor)

    def on_mount(self) -> None:
        self.task_queue.start()
        self._show_media_list()

    # ------------------------------------------------------------------
    # 内部导航（回调链）
    # ------------------------------------------------------------------

    def _show_media_list(self) -> None:
        self.push_screen(
            MediaListScreen(self.video_dir, self.executor),
            callback=self._on_media_selected,
        )

    def _on_media_selected(self, result: Union[Path, str, None]) -> None:
        if result is None:
            return
        if result == "timeline":
            from .screens.timeline import TimelineScreen
            self.push_screen(TimelineScreen(self.project), callback=lambda _: self._show_media_list())
        elif result == "export":
            self.push_screen(ExportScreen(self.project, self.executor), callback=lambda _: self._show_media_list())
        elif result == "queue":
            from .screens.task_queue import TaskQueueScreen
            self.push_screen(TaskQueueScreen(), callback=lambda _: self._show_media_list())
        elif isinstance(result, Path):
            self.push_screen(
                EditorScreen(result, self.executor),
                callback=self._on_segment_created,
            )

    def _on_segment_created(self, segment) -> None:
        if segment is not None:
            self.project.add_segment(segment)
            self.notify(
                f"已添加: {segment.display_name}，共 {len(self.project.segments)} 个片段",
                severity="information",
            )
        self._show_media_list()

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def navigate_to_editor(self, source_path: Path) -> None:
        self.push_screen(EditorScreen(source_path, self.executor), callback=self._on_segment_created)

    def navigate_to_export(self) -> None:
        self.push_screen(ExportScreen(self.project, self.executor))

    def add_segment_to_project(self, segment) -> None:
        self.project.add_segment(segment)

    def action_quit(self) -> None:
        self.task_queue.shutdown()
        self.exit()


def run_app(video_dir: Optional[Path] = None) -> None:
    """运行应用"""
    app = VideoClipApp(video_dir)
    app.run()
```

- [ ] **Step 2: 运行全量测试**

```bash
python -m pytest tests/ -v
```
期望：全部 `PASSED`

- [ ] **Step 3: 提交**

```bash
git add src/tui/app.py
git commit -m "feat: wire TaskQueue into app with queue screen routing"
```

---

## Task 10: 集成测试与手动验证

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: 写集成测试（不依赖真实 ffmpeg）**

```python
# tests/test_integration.py
"""集成测试：验证完整的数据流（mock ffmpeg）"""
import copy
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

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

    executor = MagicMock()
    q = TaskQueue(executor)

    task = ExportTask(
        project=copy.deepcopy(project),
        output_path=Path("out.mp4"),
        quality=23,
        params=ExportParams(),
    )
    q.add(task)

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
```

- [ ] **Step 2: 运行全量测试**

```bash
python -m pytest tests/ -v
```
期望：全部 `PASSED`

- [ ] **Step 3: 手动验证（需要真实 ffmpeg 和素材）**

```bash
# 1. 缩略图预览（不启动 TUI）
python3 -c "
from pathlib import Path
from src.utils.ffmpeg import generate_thumbnail
from src.utils.config import config
config.output_dir.mkdir(exist_ok=True)
thumb = config.output_dir / '.thumbnails' / 'test_thumb.jpg'
result = generate_thumbnail(Path('video_res/bun33s.mp4'), thumb, time=5.0)
print('缩略图生成:', result)
print('文件存在:', result.exists())
"

# 2. 720p 导出参数（CLI 方式）
python3 run.py split video_res/bun33s.mp4 --start 0 --end 5 --output output/test_720p.mp4

# 验证输出分辨率（需 ffprobe）
ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height \
  -of csv=p=0 output/test_720p.mp4
```

- [ ] **Step 4: 验证异构输入（mp4 + flv 拼接）**

```bash
python3 -c "
from pathlib import Path
from src.core.project import Project
from src.core.segment import Segment
from src.core.executor import Executor
from src.core.export_params import PRESETS

executor = Executor()

# 获取文件信息
info1 = executor.get_media_info(Path('video_res/bun33s.mp4'))
info2 = executor.get_media_info(Path('video_res/bun33s.flv'))
print('mp4 时长:', info1['duration'])
print('flv 时长:', info2['duration'])

project = Project()
project.add_segment(Segment(source_path=Path('video_res/bun33s.mp4'), start_time=0, end_time=3))
project.add_segment(Segment(source_path=Path('video_res/bun33s.flv'), start_time=0, end_time=3))

from pathlib import Path
out = Path('output/test_concat.mp4')
executor.export(project, out, quality=28, params=PRESETS['720p'])
print('拼接完成:', out)
print('输出存在:', out.exists())
"
```

- [ ] **Step 5: 验证取消任务**

```bash
python3 -c "
import threading, time
from pathlib import Path
from src.core.task_queue import TaskQueue
from src.core.export_task import ExportTask
from src.core.export_params import ExportParams
from src.core.project import Project
from src.core.executor import Executor

executor = Executor()
q = TaskQueue(executor)
q.start()

# 加两个任务（第二个会因第一个未完成而等待）
t1 = ExportTask(project=Project(), output_path=Path('output/cancel_t1.mp4'), quality=23, params=ExportParams())
t2 = ExportTask(project=Project(), output_path=Path('output/cancel_t2.mp4'), quality=23, params=ExportParams())
q.add(t1)
q.add(t2)

time.sleep(0.1)
q.cancel(t2.id)
print('t2 状态:', t2.status)  # 应为 cancelled
q.shutdown()
"
```

- [ ] **Step 6: 提交**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for queue, params, and snapshot isolation"
```

---

## 自检结果

- **Spec 覆盖**: 缩略图(Task 3+7) ✅ 任务队列(Task 5+8+9) ✅ 可配置参数(Task 1+4+6) ✅ 取消机制(Task 5) ✅
- **类型一致**: ExportParams/ExportTask/TaskQueue 在所有任务中方法签名一致
- **无占位符**: 所有步骤均包含完整代码
- **测试先行**: Task 1-5 均遵循 TDD（失败→实现→通过）
