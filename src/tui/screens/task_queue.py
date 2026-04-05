# src/tui/screens/task_queue.py
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Button, DataTable


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
