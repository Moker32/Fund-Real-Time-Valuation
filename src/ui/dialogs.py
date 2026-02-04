# -*- coding: UTF-8 -*-
"""对话框组件模块"""

import re
import asyncio
from typing import Optional

from textual.widget import Widget
from textual.message import Message
from textual.widgets import Static, Button, Input
from textual.containers import Container, Vertical, Horizontal

from src.datasources.fund_source import FundDataSource


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
        layer: overlay;
    }
    AddFundDialog > Vertical { width: 100%; }
    AddFundDialog Input { margin-bottom: 1; }
    AddFundDialog .dialog-buttons {
        margin-top: 1;
        align: right middle;
    }
    AddFundDialog .query-status {
        margin-bottom: 1;
        color: $warning;
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
        self._fund_source = FundDataSource()
        self._is_querying = False

    def compose(self):
        yield Vertical(
            Static("请输入基金代码和名称:", classes="dialog-label"),
            Input(placeholder="基金代码 (如: 161039)", id="fund-code-input"),
            Static("", id="query-status", classes="query-status"),
            Input(placeholder="基金名称 (如: 富国中证新能源汽车指数)", id="fund-name-input"),
            Horizontal(
                Button("取消", id="cancel-btn", variant="default"),
                Button("添加", id="confirm-btn", variant="primary"),
                classes="dialog-buttons"
            )
        )

    def _validate_fund_code(self, code: str) -> bool:
        """验证基金代码格式 (6位数字)"""
        return bool(re.match(r"^\d{6}$", code))

    async def query_fund_name(self, code: str) -> Optional[str]:
        """
        根据基金代码查询基金名称

        Args:
            code: 基金代码

        Returns:
            基金名称，查询失败返回 None
        """
        if not self._validate_fund_code(code):
            return None

        try:
            result = await self._fund_source.fetch(code)
            if result.success and result.data:
                return result.data.get("name")
        except Exception:
            pass
        return None

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理输入框回车事件 - 基金代码输入框回车时触发查询"""
        if event.input.id == "fund-code-input":
            code = event.value.strip()
            if code and self._validate_fund_code(code):
                # 触发异步查询
                asyncio.create_task(self._do_query(code))

    async def _do_query(self, code: str):
        """执行基金名称查询"""
        if self._is_querying:
            return

        self._is_querying = True
        status = self.query_one("#query-status", Static)
        status.update("正在查询...")

        name = await self.query_fund_name(code)

        if name:
            # 查询成功，自动填充名称
            name_input = self.query_one("#fund-name-input", Input)
            name_input.value = name
            status.update("")
            self.notify(f"已获取基金名称: {name}", severity="information")
        else:
            # 查询失败
            status.update("查询失败，请手动输入名称")

        self._is_querying = False

    async def action_confirm(self) -> None:
        """确认添加 - 先验证基金有效性再添加"""
        code_input = self.query_one("#fund-code-input", Input)
        name_input = self.query_one("#fund-name-input", Input)
        code = code_input.value.strip()
        name = name_input.value.strip()

        # 基础验证
        if not code:
            self.notify("请填写基金代码", severity="warning")
            return
        if not name:
            self.notify("请填写基金名称", severity="warning")
            return

        # 验证基金代码格式
        if not self._validate_fund_code(code):
            self.notify("基金代码格式错误", severity="error")
            return

        # 验证基金有效性
        status = self.query_one("#query-status", Static)
        status.update("正在验证基金...")
        fund_name = await self.query_fund_name(code)

        if fund_name is None:
            # 验证失败
            status.update("基金不存在或网络错误")
            self.notify("基金不存在或网络错误", severity="error")
            return

        # 验证成功 - 更新基金名称（如果用户手动输入的名称不同）
        if name != fund_name:
            name_input.value = fund_name
            name = fund_name

        status.update("")
        self.notify(f"基金验证成功: {fund_name}", severity="success")

        # 执行添加
        self.result_code = code
        self.result_name = name
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
        layer: overlay;
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
