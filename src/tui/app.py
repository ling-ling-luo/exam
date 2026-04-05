"""TUI 主应用"""
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Header, Footer, Static

from ..core.project import Project
from ..core.executor import Executor
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
        Binding("escape", "cancel", "取消", show=True),
    ]

    def __init__(self, video_dir: Optional[Path] = None):
        super().__init__()
        self.video_dir = video_dir or config.video_dir
        self.project = Project()
        self.executor = Executor()

    def on_mount(self) -> None:
        """应用挂载时"""
        self.push_screen(MediaListScreen(self.video_dir, self.executor))

    def navigate_to_editor(self, source_path: Path) -> None:
        """跳转到编辑界面"""
        self.push_screen(EditorScreen(source_path, self.executor))

    def navigate_to_export(self) -> None:
        """跳转到导出界面"""
        self.push_screen(ExportScreen(self.project, self.executor))

    def add_segment_to_project(self, segment) -> None:
        """添加片段到项目"""
        self.project.add_segment(segment)

    def action_quit(self) -> None:
        """退出应用"""
        self.exit()


def run_app(video_dir: Optional[Path] = None) -> None:
    """运行应用"""
    app = VideoClipApp(video_dir)
    app.run()