# -*- coding: UTF-8 -*-
"""基金详情页Screen - 展示基金详细信息和图表"""

import asyncio
from textual.screen import Screen
from textual.widgets import Static, Button, Label
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.message import Message
from textual.app import ComposeResult
from textual.reactive import reactive
from .models import FundData, FundHistoryData
from .charts import ChartPreview


class FundDetailScreen(Screen):
    """基金详情页面"""

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("escape", "app.pop_screen", "返回"),
        ("q", "app.pop_screen", "返回"),
        ("h", "set_holding", "持仓设置"),
        ("g", "show_chart", "净值图表"),
        ("r", "refresh", "刷新数据"),
        ("up", "focus_prev", "上移"),
        ("down", "focus_next", "下移"),
    ]

    def __init__(self, fund: FundData):
        super().__init__(id="fund-detail-screen")
        self.fund = fund
        self.history_data: FundHistoryData | None = None

    def compose(self) -> ComposeResult:
        # 顶部：返回按钮 + 基金标题
        yield Horizontal(
            Button("< 返回", id="back-btn", variant="default"),
            Static(f"[b]{self.fund.name}[/b] ({self.fund.code})", classes="detail-title"),
            id="detail-header"
        )

        # 主体内容
        yield Horizontal(
            # 左侧：基金基本信息
            Vertical(
                Static("基本信息", classes="section-title"),
                Grid(
                    Label("单位净值:", classes="label"),
                    Static(f"{self.fund.net_value:.4f}", id="net-value", classes="value"),
                    Label("估算净值:", classes="label"),
                    Static(f"{self.fund.est_value:.4f}", id="est-value", classes="value"),
                    Label("估算涨跌:", classes="label"),
                    Static(f"{self.fund.change_pct:+.2f}%", id="change-pct", classes="value"),
                    Label("持仓份额:", classes="label"),
                    Static(f"{self.fund.hold_shares:.2f}" if self.fund.hold_shares else "0.00",
                          id="hold-shares", classes="value"),
                    Label("持仓成本:", classes="label"),
                    Static(f"{self.fund.cost:.4f}" if self.fund.cost else "0.0000",
                          id="hold-cost", classes="value"),
                    Label("持仓盈亏:", classes="label"),
                    Static(f"{self.fund.profit:+.2f}" if self.fund.profit else "0.00",
                          id="profit", classes="value profit-positive" if self.fund.profit and self.fund.profit > 0 else "value profit-negative"),
                    classes="info-grid"
                ),
                id="left-panel"
            ),
            # 右侧：迷你图表 + 操作按钮
            Vertical(
                Static("净值走势", classes="section-title"),
                ChartPreview(id="mini-chart"),
                Horizontal(
                    Button("持仓设置 (h)", id="holding-btn"),
                    Button("完整图表 (g)", id="chart-btn"),
                    Button("刷新 (r)", id="refresh-btn"),
                    classes="action-buttons"
                ),
                id="right-panel"
            ),
            id="detail-content"
        )

        # 底部：快捷键提示
        yield Horizontal(
            Static("[Esc/q]返回  [h]持仓设置  [g]净值图表  [r]刷新", classes="help-hint"),
            id="detail-footer"
        )

    def on_mount(self) -> None:
        """页面挂载时加载历史数据"""
        # 异步加载历史数据用于图表
        asyncio.create_task(self._load_history())

    async def _load_history(self):
        """加载基金历史数据"""
        try:
            from src.datasources.fund_source import FundHistorySource
            history_source = FundHistorySource()
            result = await history_source.fetch(self.fund.code, period="近一年")

            if result.success and result.data:
                history_list = result.data.get("history", [])
                if history_list:
                    self.history_data = FundHistoryData(
                        fund_code=self.fund.code,
                        fund_name=self.fund.name,
                        dates=[item["date"] for item in history_list],
                        net_values=[item["net_value"] for item in history_list],
                        accumulated_net=[item.get("accumulated_net") for item in history_list]
                    )
                    # 更新迷你图表
                    chart = self.query_one("#mini-chart", ChartPreview)
                    chart.update_preview(self.history_data, width=50, height=8)
        except Exception as e:
            self.app.log(f"加载历史数据失败: {e}")

    def action_set_holding(self) -> None:
        """打开持仓设置"""
        from .dialogs import HoldingDialog
        self.app._is_opening_dialog = True
        current_shares = self.fund.hold_shares or 0.0
        current_cost = self.fund.cost or 0.0
        self.app.mount(HoldingDialog(self.fund.code, self.fund.name, current_shares, current_cost))

    def action_show_chart(self) -> None:
        """显示完整图表"""
        if self.history_data:
            from .charts import ChartDialog
            self.app.mount(ChartDialog(self.fund.code, self.fund.name, self.history_data))
        else:
            self.notify("正在加载历史数据，请稍候...", severity="information")
            asyncio.create_task(self._load_history())
            # 等待加载完成后显示
            async def wait_and_show():
                await asyncio.sleep(2)
                if self.history_data:
                    from .charts import ChartDialog
                    self.app.mount(ChartDialog(self.fund.code, self.fund.name, self.history_data))
            asyncio.create_task(wait_and_show())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "holding-btn":
            self.action_set_holding()
        elif event.button.id == "chart-btn":
            self.action_show_chart()
        elif event.button.id == "refresh-btn":
            asyncio.create_task(self._refresh_data())

    async def _refresh_data(self):
        """刷新基金数据"""
        self.notify("正在刷新数据...", severity="information")
        # 重新加载基金数据
        await self.app.load_fund_data()
        # 重新加载历史数据
        await self._load_history()
        self.notify("数据已刷新", severity="success")
