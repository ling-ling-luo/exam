"""导出屏幕"""
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Input, Label, ProgressBar
from textual import on

from ...core.project import Project
from ...core.executor import Executor
from ...utils.config import config


class ExportScreen(ModalScreen):
    """导出屏幕"""

    def __init__(self, project: Project, executor: Executor):
        super().__init__()
        self.project = project
        self.executor = executor

    def compose(self) -> ComposeResult:
        yield Container(
            Static("📤 导出设置", classes="title"),
            Vertical(
                Label("输出文件名:"),
                Input(value="output.mp4", id="input-filename"),
                Label("导出质量 (CRF, 数值越低越好):"),
                Input(value=str(config.default_quality), id="input-quality"),
                id="export-settings"
            ),
            Static("", id="export-progress"),
            ProgressBar(total=100, id="progress-bar"),
            Static("", id="export-status"),
            Horizontal(
                Button("开始导出", id="btn-export", variant="primary"),
                Button("返回", id="btn-back", variant="default"),
                id="export-buttons"
            ),
            id="export-container"
        )

    def on_mount(self) -> None:
        """显示项目信息"""
        if self.project.segments:
            duration = self.project.get_total_duration()
            info = f"片段数量: {len(self.project.segments)} | 总时长: {duration:.2f}秒"
            self.query_one("#export-status", Static).update(info)
        else:
            self.query_one("#btn-export", Button).disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击事件"""
        if event.button.id == "btn-export":
            self._start_export()
        elif event.button.id == "btn-back":
            self.dismiss()

    def _start_export(self) -> None:
        """开始导出"""
        filename_input = self.query_one("#input-filename", Input)
        quality_input = self.query_one("#input-quality", Input)

        filename = filename_input.value.strip() or "output.mp4"
        if not filename.endswith((".mp4", ".avi", ".mov", ".flv", ".mkv")):
            filename += ".mp4"

        try:
            quality = int(quality_input.value.strip())
            if quality < 0 or quality > 51:
                raise ValueError()
        except ValueError:
            self.notify("质量值必须是 0-51 之间的整数", severity="warning")
            return

        # 设置输出路径
        output_path = config.output_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 更新状态
        self.query_one("#btn-export", Button).disabled = True
        self.query_one("#export-status", Static).update(f"正在导出到: {output_path}")

        # 执行导出
        def progress_callback(progress: float):
            self.call_later(
                lambda p: self.query_one("#progress-bar", ProgressBar).update(p),
                int(progress)
            )

        try:
            self.executor.export(
                self.project,
                output_path,
                quality,
                progress_callback
            )

            self.query_one("#export-status", Static).update(
                f"✅ 导出完成! 文件: {output_path}"
            )
            self.notify(f"导出成功: {output_path}", severity="information")

        except Exception as e:
            self.query_one("#btn-export", Button).disabled = False
            self.notify(f"导出失败: {e}", severity="error")