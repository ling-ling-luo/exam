"""时间线屏幕 - 片段顺序管理"""
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, Button, DataTable
from textual import on

from ...core.project import Project
from ...core.segment import Segment
from ...core.validator import format_time_code


class TimelineScreen(ModalScreen):
    """时间线屏幕"""

    def __init__(self, project: Project):
        super().__init__()
        self.project = project

    def compose(self) -> ComposeResult:
        yield Container(
            Static("📋 时间线", classes="title"),
            DataTable(id="timeline-table"),
            Static("", id="timeline-info"),
            Horizontal(
                Button("上移", id="btn-up"),
                Button("下移", id="btn-down"),
                Button("删除", id="btn-delete", variant="danger"),
                Button("清空", id="btn-clear", variant="error"),
                Button("关闭", id="btn-close"),
                id="timeline-buttons"
            ),
            id="timeline-container"
        )

    def on_mount(self) -> None:
        """加载时间线数据"""
        self._load_timeline()

    def _load_timeline(self) -> None:
        """加载时间线"""
        table = self.query_one("#timeline-table", DataTable)
        table.clear()

        if not self.project.segments:
            self.query_one("#timeline-info", Static).update("时间线为空")
            self._disable_buttons(True)
            return

        self._disable_buttons(False)

        # 添加列
        if not table.columns:
            table.add_columns("序号", "文件名", "入点", "出点", "时长")

        for i, seg in enumerate(self.project.segments):
            start = format_time_code(seg.start_time)
            end = format_time_code(seg.end_time) if seg.end_time else "结束"
            duration = format_time_code(seg.duration)

            table.add_row(
                str(i + 1),
                seg.display_name[:20],
                start,
                end,
                duration
            )

        total_duration = self.project.get_total_duration()
        self.query_one("#timeline-info", Static).update(
            f"共 {len(self.project.segments)} 个片段，总时长: {format_time_code(total_duration)}"
        )

    def _disable_buttons(self, disabled: bool) -> None:
        """禁用/启用按钮"""
        for btn_id in ["btn-up", "btn-down", "btn-delete", "btn-clear"]:
            self.query_one(f"#{btn_id}", Button).disabled = disabled

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击事件"""
        table = self.query_one("#timeline-table", DataTable)
        selected_row = table.cursor_row

        if event.button.id == "btn-close":
            self.dismiss()
            return

        if selected_row is None:
            self.notify("请先选择一个片段", severity="warning")
            return

        if event.button.id == "btn-up":
            if selected_row > 0:
                self.project.move_segment(selected_row, selected_row - 1)
                self._load_timeline()

        elif event.button.id == "btn-down":
            if selected_row < len(self.project.segments) - 1:
                self.project.move_segment(selected_row, selected_row + 1)
                self._load_timeline()

        elif event.button.id == "btn-delete":
            seg = self.project.segments[selected_row]
            self.project.remove_segment(seg.id)
            self._load_timeline()

        elif event.button.id == "btn-clear":
            self.project.clear()
            self._load_timeline()