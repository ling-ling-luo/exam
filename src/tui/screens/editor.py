"""编辑屏幕 - 设置切分区间"""
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Input, Label
from textual.events import Key
from textual import on

from ...core.executor import Executor
from ...core.segment import Segment
from ...core.validator import parse_time_code, format_time_code, ValidationError


class EditorScreen(ModalScreen):
    """编辑屏幕"""

    def __init__(self, source_path: Path, executor: Executor):
        super().__init__()
        self.source_path = source_path
        self.executor = executor
        self.media_info = None
        self.start_time: float = 0.0
        self.end_time: Optional[float] = None

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"✂️ 编辑: {self.source_path.name}", classes="title"),
            Static("", id="media-info"),
            Vertical(
                Label("入点时间 (HH:MM:SS 或秒数):"),
                Input(placeholder="00:00:00", id="input-start"),
                Label("出点时间 (留空表示视频末尾):"),
                Input(placeholder="00:00:00", id="input-end"),
                id="input-section"
            ),
            Static("", id="preview-text"),
            Horizontal(
                Button("添加到时间线", id="btn-add", variant="primary"),
                Button("返回", id="btn-back", variant="default"),
                id="button-section"
            ),
            id="editor-container"
        )

    def on_mount(self) -> None:
        """加载媒体信息"""
        try:
            self.media_info = self.executor.get_media_info(self.source_path)
            duration = self.media_info.get("duration", 0)

            # 更新显示
            info_text = f"时长: {format_time_code(duration)} | " \
                       f"分辨率: {self.media_info.get('video', {}).get('width', 'N/A')}x" \
                       f"{self.media_info.get('video', {}).get('height', 'N/A')}"

            self.query_one("#media-info", Static).update(info_text)
            self.query_one("#input-end", Input).placeholder = format_time_code(duration)

            self.end_time = duration

        except Exception as e:
            self.notify(f"获取媒体信息失败: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击事件"""
        if event.button.id == "btn-add":
            self._add_segment()
        elif event.button.id == "btn-back":
            self.dismiss()

    def on_input_changed(self, event: Input.Changed) -> None:
        """输入变化事件"""
        self._update_preview()

    def _update_preview(self) -> None:
        """更新预览"""
        try:
            start_input = self.query_one("#input-start", Input)
            end_input = self.query_one("#input-end", Input)

            start_str = start_input.value.strip()
            end_str = end_input.value.strip()

            if start_str:
                self.start_time = parse_time_code(start_str)

            if end_str:
                self.end_time = parse_time_code(end_str)
            elif self.media_info:
                self.end_time = self.media_info.get("duration", 0)

            if self.start_time < self.end_time:
                duration = self.end_time - self.start_time
                preview = f"预览: {format_time_code(self.start_time)} → {format_time_code(self.end_time)} " \
                         f"(时长: {format_time_code(duration)})"
                self.query_one("#preview-text", Static).update(preview)
            else:
                self.query_one("#preview-text", Static).update("")

        except ValidationError as e:
            self.query_one("#preview-text", Static).update(f"⚠️ {e.message}")
        except Exception:
            pass

    def _add_segment(self) -> None:
        """添加片段"""
        try:
            start_input = self.query_one("#input-start", Input)
            end_input = self.query_one("#input-end", Input)

            start_str = start_input.value.strip()
            end_str = end_input.value.strip()

            if not start_str:
                self.notify("请输入入点时间", severity="warning")
                return

            start_time = parse_time_code(start_str)

            if end_str:
                end_time = parse_time_code(end_str)
            else:
                end_time = self.media_info.get("duration", 0) if self.media_info else None

            if end_time and start_time >= end_time:
                self.notify("入点时间必须小于出点时间", severity="warning")
                return

            # 创建片段
            segment = Segment(
                source_path=self.source_path,
                start_time=start_time,
                end_time=end_time,
                name=self.source_path.name
            )

            self.notify(f"✅ 已添加片段: {segment.display_name}", severity="information")

            # 返回片段
            self.dismiss(segment)

        except ValidationError as e:
            self.notify(e.message, severity="error")
        except Exception as e:
            self.notify(f"添加失败: {e}", severity="error")

    def on_key(self, event: Key) -> None:
        """按键事件"""
        if event.key == "escape":
            self.dismiss()