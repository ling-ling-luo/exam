"""确认对话框"""
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Button


class ConfirmScreen(ModalScreen):
    """确认对话框"""

    def __init__(self, message: str, title: str = "确认"):
        super().__init__()
        self.message = message
        self.title_text = title

    def compose(self) -> ComposeResult:
        yield Container(
            Static(self.title_text, classes="dialog-title"),
            Static(self.message, classes="dialog-message"),
            Horizontal(
                Button("确认", id="btn-confirm", variant="primary"),
                Button("取消", id="btn-cancel", variant="default"),
                id="dialog-buttons"
            ),
            id="confirm-dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击事件"""
        if event.button.id == "btn-confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)