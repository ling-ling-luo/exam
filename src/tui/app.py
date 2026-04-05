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
