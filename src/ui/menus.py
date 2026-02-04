# -*- coding: UTF-8 -*-
"""上下文菜单组件 - 基金右键菜单"""

from textual.widgets import Static
from textual.containers import Container, Vertical
from textual.message import Message


class FundContextMenu(Container):
    """基金上下文菜单"""

    DEFAULT_CSS = """
    FundContextMenu {
        width: 24;
        height: auto;
        border: solid $primary;
        background: $surface;
        layer: overlay;
    }
    FundContextMenu .menu-item {
        height: 1;
        padding: 0 2;
    }
    FundContextMenu .menu-item:hover,
    FundContextMenu .menu-item.selected {
        background: $primary 30%;
    }
    FundContextMenu .menu-separator {
        height: 1;
        color: $foreground-muted;
        content: "─" * 20;
    }
    FundContextMenu .menu-title {
        height: 1;
        padding: 0 2;
        color: $primary;
        text-style: bold;
        background: $panel;
    }
    FundContextMenu .menu-item.selected::before {
        content: "▶ ";
        color: $primary;
    }
    """

    BINDINGS = [
        ("escape", "close", "关闭"),
        ("up", "move_up", "上移"),
        ("down", "move_down", "下移"),
        ("enter", "select", "选择"),
    ]

    def __init__(self, fund_code: str, fund_name: str, has_holding: bool = False):
        super().__init__(id="fund-context-menu")
        self.fund_code = fund_code
        self.fund_name = fund_name
        self.has_holding = has_holding
        self.selected_index = 0
        self.menu_items = [
            ("查看详情", "view_detail", "Enter"),
            ("净值图表", "show_chart", "g"),
            ("持仓设置", "set_holding", "h"),
            ("sep1", "separator", ""),
            ("删除自选", "delete", "d"),
        ]

    def compose(self):
        # 菜单标题
        yield Static(f"  {self.fund_name}", classes="menu-title")
        yield Static("─" * 20, classes="menu-separator")

        # 菜单项
        for idx, (label, action, key) in enumerate(self.menu_items):
            if action == "separator":
                yield Static("─" * 20, classes="menu-separator")
            else:
                key_hint = f" [{key}]" if key else ""
                yield Static(f"  {label}{key_hint}", id=f"menu-item-{idx}", classes="menu-item")

    def action_close(self):
        """关闭菜单"""
        self.remove()

    def action_move_up(self):
        """上移选择"""
        valid_items = [
            i for i, item in enumerate(self.menu_items) if item[1] != "separator"
        ]
        if not valid_items:
            return
        self.selected_index = max(valid_items[0], self.selected_index - 1)
        self._update_selection()

    def action_move_down(self):
        """下移选择"""
        valid_items = [
            i for i, item in enumerate(self.menu_items) if item[1] != "separator"
        ]
        if not valid_items:
            return
        self.selected_index = min(valid_items[-1], self.selected_index + 1)
        self._update_selection()

    def action_select(self):
        """选择当前项"""
        valid_items = [
            (idx, item) for idx, item in enumerate(self.menu_items) if item[1] != "separator"
        ]
        for idx, (_, action, _) in valid_items:
            if idx == self.selected_index:
                self.post_message(self.MenuSelected(action, self.fund_code))
                break
        self.remove()

    def _update_selection(self):
        """更新选择状态显示"""
        for idx, item in enumerate(self.menu_items):
            if item[1] == "separator":
                continue
            item_widget = self.query_one(f"#menu-item-{idx}", Static)
            label = item[0]
            key = item[2]
            key_hint = f" [{key}]" if key else ""

            if idx == self.selected_index:
                item_widget.update(f"▶ {label}{key_hint}")
                item_widget.add_class("selected")
            else:
                item_widget.update(f"  {label}{key_hint}")
                item_widget.remove_class("selected")

    class MenuSelected(Message):
        """菜单选择消息"""

        def __init__(self, action: str, fund_code: str):
            self.action = action
            self.fund_code = fund_code
            super().__init__()
