"""素材列表屏幕"""
from pathlib import Path
from typing import List

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Input, Label
from textual.events import Key
from textual import on

from ...core.executor import Executor
from ...utils.config import config


class MediaListScreen(ModalScreen):
    """素材列表屏幕"""

    def __init__(self, video_dir: Path, executor: Executor):
        super().__init__()
        self.video_dir = video_dir
        self.executor = executor
        self.media_files: List[Path] = []

    def compose(self) -> ComposeResult:
        yield Container(
            Static("📁 素材列表", classes="title"),
            Static("", id="media_count"),
            id="media-list-container"
        )

    def on_mount(self) -> None:
        """加载素材列表"""
        self._load_media_files()

    def _load_media_files(self) -> None:
        """加载媒体文件"""
        if not self.video_dir.exists():
            self.notify("视频目录不存在", severity="error")
            return

        supported = config.supported_formats
        self.media_files = [
            f for f in self.video_dir.iterdir()
            if f.is_file() and f.suffix.lstrip(".").lower() in supported
        ]

        self.media_files.sort(key=lambda x: x.name)

        container = self.query_one("#media-list-container")
        container.remove_children()

        if not self.media_files:
            container.mount(Static("没有找到可用的视频文件", classes="empty"))
        else:
            # 文件数量
            container.mount(
                Static(f"共找到 {len(self.media_files)} 个视频文件", id="media_count")
            )

            # 渲染文件列表（简化版）
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

            # 添加说明
            container.mount(
                Static("\n[Enter] 选择视频  [T] 时间线  [E] 导出  [J] 队列  [Q] 退出", classes="help")
            )
            container.mount(Button("📋 查看时间线 (T)", id="btn_timeline", classes="nav-btn"))
            container.mount(Button("📤 开始导出 (E)", id="btn_export", classes="nav-btn"))
            container.mount(Button("📬 任务队列 (J)", id="btn_queue", classes="nav-btn"))

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


class MediaListDialog(ModalScreen):
    """素材选择对话框"""

    def __init__(self, video_dir: Path, executor: Executor):
        super().__init__()
        self.video_dir = video_dir
        self.executor = executor
        self.media_files: List[Path] = []

    def compose(self) -> ComposeResult:
        yield Container(
            Static("📁 选择视频素材", classes="dialog-title"),
            id="media-dialog-content"
        )

    def on_mount(self) -> None:
        """加载素材列表"""
        self._load_media_files()

    def _load_media_files(self) -> None:
        """加载媒体文件"""
        if not self.video_dir.exists():
            self.notify("视频目录不存在", severity="error")
            return

        supported = config.supported_formats
        self.media_files = [
            f for f in self.video_dir.iterdir()
            if f.is_file() and f.suffix.lstrip(".").lower() in supported
        ]

        self.media_files.sort(key=lambda x: x.name)

        container = self.query_one("#media-dialog-content")
        container.remove_children()

        # 标题
        container.mount(Static("📁 选择视频素材", classes="dialog-title"))

        if not self.media_files:
            container.mount(Static("没有找到可用的视频文件", classes="empty"))
        else:
            # 使用 DataTable 表格
            from textual.widgets import DataTable

            table = DataTable(id="media-table")
            table.add_columns("序号", "文件名", "大小")
            table.cursor_type = "row"

            for i, f in enumerate(self.media_files):
                size_mb = f.stat().st_size / (1024 * 1024)
                table.add_row(str(i + 1), f.name, f"{size_mb:.1f} MB")

            table.focus()
            container.mount(table)

            # 帮助
            container.mount(
                Static("\n[Enter] 确认选择  [Esc] 取消", classes="help")
            )

    def on_data_table_row_selected(self, event) -> None:
        """行选择事件"""
        table = self.query_one("#media-table")
        row_index = table.cursor_row
        if 0 <= row_index < len(self.media_files):
            self.dismiss(self.media_files[row_index])

    def on_key(self, event: Key) -> None:
        """按键事件"""
        if event.key == "enter":
            table = self.query_one("#media-table")
            row_index = table.cursor_row
            if 0 <= row_index < len(self.media_files):
                self.dismiss(self.media_files[row_index])
        elif event.key == "escape":
            self.dismiss(None)