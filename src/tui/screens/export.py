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
