# -*- coding: UTF-8 -*-
"""对话框组件模块"""

from textual.widget import Widget
from textual.message import Message
from textual.widgets import Static, Button, Input
from textual.containers import Container, Vertical, Horizontal
from typing import Optional


class AddFundDialog(Container):
    """添加基金对话框"""

    DEFAULT_CSS = """
    AddFundDialog {
        align: center middle;
        width: 60;
        height: auto;
        border: solid cyan;
        background: $surface;
        padding: 1;
    }
    AddFundDialog > Vertical { width: 100%; }
    AddFundDialog Input { margin-bottom: 1; }
    AddFundDialog .dialog-buttons {
        margin-top: 1;
        align: right middle;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "取消"),
        ("enter", "confirm", "确认"),
    ]

    def __init__(self):
        super().__init__(id="add-fund-dialog")
        self.result_code: Optional[str] = None
        self.result_name: Optional[str] = None

    def compose(self):
        yield Vertical(
            Static("请输入基金代码和名称:", classes="dialog-label"),
            Input(placeholder="基金代码 (如: 161039)", id="fund-code-input"),
            Input(placeholder="基金名称 (如: 富国中证新能源汽车指数)", id="fund-name-input"),
            Horizontal(
                Button("取消", id="cancel-btn", variant="default"),
                Button("添加", id="confirm-btn", variant="primary"),
                classes="dialog-buttons"
            )
        )

    def action_confirm(self) -> None:
        """确认添加"""
        code_input = self.query_one("#fund-code-input", Input)
        name_input = self.query_one("#fund-name-input", Input)
        code = code_input.value.strip()
        name = name_input.value.strip()
        if code and name:
            self.result_code = code
            self.result_name = name
            self.remove()
            self.post_message(self.Confirm())
        else:
            self.notify("请填写完整的基金信息", severity="warning")

    def action_cancel(self) -> None:
        """取消"""
        self.remove()
        self.post_message(self.Cancel())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-btn":
            self.action_confirm()
        else:
            self.action_cancel()

    class Confirm(Message):
        """确认添加消息"""
        pass

    class Cancel(Message):
        """取消消息"""
        pass


class HoldingDialog(Container):
    """持仓设置对话框"""

    DEFAULT_CSS = """
    HoldingDialog {
        align: center middle;
        width: 60;
        height: auto;
        border: solid cyan;
        background: $surface;
        padding: 1;
    }
    HoldingDialog > Vertical { width: 100%; }
    HoldingDialog Input { margin-bottom: 1; }
    HoldingDialog .dialog-buttons {
        margin-top: 1;
        align: right middle;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "取消"),
    ]

    def __init__(self, fund_code: str, fund_name: str, current_shares: float = 0.0, current_cost: float = 0.0):
        super().__init__(id="holding-dialog")
        self.fund_code = fund_code
        self.fund_name = fund_name
        self.result_shares = current_shares
        self.result_cost = current_cost
        self.is_holding = current_shares > 0

    def compose(self):
        action_text = "取消持仓" if self.is_holding else "设为持仓"
        yield Vertical(
            Static(f"基金: {self.fund_name} ({self.fund_code})", classes="dialog-label"),
            Input(placeholder=f"持有份额 (当前: {self.result_shares:.2f})", id="shares-input",
                  value=str(self.result_shares) if self.result_shares > 0 else ""),
            Input(placeholder=f"成本价 (当前: {self.result_cost:.4f})", id="cost-input",
                  value=str(self.result_cost) if self.result_cost > 0 else ""),
            Horizontal(
                Button("取消", id="cancel-btn", variant="default"),
                Button(action_text, id="confirm-btn", variant="primary"),
                classes="dialog-buttons"
            )
        )

    def action_confirm(self) -> None:
        """确认设置"""
        shares_input = self.query_one("#shares-input", Input)
        cost_input = self.query_one("#cost-input", Input)
        shares_str = shares_input.value.strip()
        cost_str = cost_input.value.strip()
        if shares_str:
            try:
                shares = float(shares_str)
                cost = float(cost_str) if cost_str else 0.0
                self.result_shares = shares
                self.result_cost = cost
                self.is_holding = True
                self.remove()
                self.post_message(self.Confirm())
            except ValueError:
                self.notify("请输入有效的数字", severity="error")
        else:
            self.result_shares = 0.0
            self.result_cost = 0.0
            self.is_holding = False
            self.remove()
            self.post_message(self.Confirm())

    def action_cancel(self) -> None:
        """取消"""
        self.remove()
        self.post_message(self.Cancel())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-btn":
            self.action_confirm()
        else:
            self.action_cancel()

    class Confirm(Message):
        """确认消息"""
        pass

    class Cancel(Message):
        """取消消息"""
        pass
