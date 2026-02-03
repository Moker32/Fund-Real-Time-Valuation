# -*- coding: UTF-8 -*-
"""主应用模块 - Textual TUI 应用入口
支持真实基金数据源集成
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, DataTable, Button, Label
from textual import events, on
from textual.color import Color
from textual.reactive import reactive
from textual.theme import Theme
from datetime import datetime
from typing import List, Optional, Dict
import asyncio
import os
import sys

# 添加项目根目录到路径，确保可以正确导入 datasources
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from .models import FundData, CommodityData, NewsData, FundHistoryData
from .tables import FundTable
from .widgets import CommodityPairView, NewsList, StatPanel
from .charts import ChartDialog
from .dialogs import AddFundDialog, HoldingDialog
from src.datasources.base import DataSourceType
from src.datasources.fund_source import FundDataSource, FundHistorySource


# ==================== 自定义主题定义 ====================

DARK_THEME = Theme(
    name="fund_dark",
    primary="#00D4FF",
    secondary="#00BFFF",
    accent="#FF6B6B",
    foreground="#E8E8E8",
    background="#0A1628",
    success="#4ADE80",
    warning="#FBBF24",
    error="#EF4444",
    surface="#1E3A5F",
    panel="#0F3460",
    dark=True,
)

LIGHT_THEME = Theme(
    name="fund_light",
    primary="#0066CC",
    secondary="#0099FF",
    accent="#FF4757",
    foreground="#1A1A2E",
    background="#F5F7FA",
    success="#22C55E",
    warning="#F59E0B",
    error="#EF4444",
    surface="#FFFFFF",
    panel="#E8EEF2",
    dark=False,
)


class FundTUIApp(App):
    """基金实时估值 TUI 应用"""

    # 应用配置
    TITLE = "基金实时估值"
    SUB_TITLE = "Fund Real-Time Valuation"
    CSS_PATH = "styles.tcss"

    # 定义主题
    dark_theme = True

    # 快捷键绑定
    BINDINGS = [
        ("q", "quit", "退出"),
        ("ctrl+c", "quit", "退出"),
        ("F1", "toggle_help", "帮助"),
        ("r", "refresh", "刷新"),
        ("t", "toggle_theme", "切换主题"),
        ("a", "add_fund", "添加基金"),
        ("d", "delete_fund", "删除基金"),
        ("h", "set_holding", "持仓设置"),
        ("g", "show_chart", "净值图表"),
        ("tab", "next_view", "下一个视图"),
        ("shift+tab", "prev_view", "上一个视图"),
        ("1", "switch_view('fund')", "基金视图"),
        ("2", "switch_view('commodity')", "商品视图"),
        ("3", "switch_view('news')", "新闻视图"),
    ]

    def _safe_query(self, selector: str, widget_type=None):
        """安全查询组件，如果不存在返回 None"""
        try:
            if widget_type:
                return self.query_one(selector, widget_type)
            return self.query_one(selector)
        except:
            return None

    def __init__(self):
        super().__init__()

        # 数据源管理
        self.data_source_manager = create_default_manager()

        # 状态
        self.is_dark_theme = True
        self.last_update_time = ""
        self.refresh_interval = 30  # 秒
        self.auto_refresh_task = None

        # 基金数据列表
        self._fund_codes = ["161039", "161725", "110022"]  # 默认基金列表

    # ==================== 响应式属性 ====================

    # 基金数据列表
    funds = reactive([])

    # 商品数据列表
    commodities = reactive([])

    # 新闻数据列表
    news_list = reactive([])

    # 统计数据
    total_profit = reactive(0.0)
    avg_change = reactive(0.0)

    # 当前活动视图
    active_view = reactive("fund")

    # ==================== 组件组合 ====================

    def compose(self) -> ComposeResult:
        """构建应用 UI - 三栏布局"""
        # 顶部标题栏
        yield Horizontal(
            Static("[b]Fund Real-Time Valuation[/b]", id="app-title"),
            Static("[F1]帮助  [r]刷新  [Tab]切换视图  [Ctrl+C]退出", id="header-hints"),
            classes="top-bar"
        )

        # 视图切换标签
        yield Horizontal(
            Static("[b]📊 基金[/b]", id="tab-fund", classes="view-tab active"),
            Static("  📈 商品  ", id="tab-commodity", classes="view-tab"),
            Static("  📰 新闻  ", id="tab-news", classes="view-tab"),
            classes="view-tabs"
        )

        # 三栏主内容区 - 使用 Horizontal 实现三列并排
        yield Horizontal(
            # 左侧：基金列表
            Vertical(
                Static("自选基金 (3)", classes="column-title"),
                FundTable(id="fund-table", classes="fund-table"),
                classes="column fund-column"
            ),
            # 中间：大宗商品
            Vertical(
                Static("大宗商品 (5)", classes="column-title"),
                CommodityPairView(id="commodity-table", classes="commodity-table"),
                classes="column commodity-column"
            ),
            # 右侧：财经新闻
            Vertical(
                Static("财经新闻 (3)", classes="column-title"),
                NewsList(id="news-list", classes="news-list"),
                classes="column news-column"
            ),
            id="content-container",
            classes="content-container"
        )

        # 底部统计行
        yield Horizontal(
            StatPanel(id="stat-panel", classes="stat-panel"),
            classes="stats-container"
        )

    # ==================== 生命周期方法 ====================

    def on_mount(self) -> None:
        """应用挂载时初始化"""
        # 启动自动刷新
        self.auto_refresh_task = asyncio.create_task(self.auto_refresh())

        # 加载真实基金数据
        self.call_after_refresh(self.load_fund_data)

        # 加载真实商品数据
        self.call_after_refresh(self.load_commodity_data)

        # 加载真实新闻数据
        self.call_after_refresh(self.load_news_data)

        # 更新状态栏
        self.update_status_bar()

    def on_unmount(self) -> None:
        """应用卸载时清理"""
        if self.auto_refresh_task:
            self.auto_refresh_task.cancel()

    # ==================== 动作方法 ====================

    def action_refresh(self) -> None:
        """手动刷新数据"""
        asyncio.create_task(self.refresh_data())

    def action_toggle_help(self) -> None:
        """切换帮助面板显示"""
        help_content = """
[操作说明]

[a]       - 添加基金
[d]       - 删除基金
[g]       - 净值图表
[h]       - 持仓设置
[r]       - 手动刷新
[t]       - 切换主题
[F1]      - 显示帮助
[1/2/3]   - 切换视图
[Tab]     - 视图切换
[Ctrl+C]  - 退出应用
    """
        self.notify(help_content, title="操作说明", severity="information")

    def action_toggle_theme(self) -> None:
        """切换深色/浅色主题"""
        self.is_dark_theme = not self.is_dark_theme
        if self.is_dark_theme:
            self.theme = "fund_dark"
        else:
            self.theme = "fund_light"
        self.notify(f"已切换至{'深色' if self.is_dark_theme else '浅色'}主题", severity="information")
        self.update_status_bar()

    def action_add_fund(self) -> None:
        """添加基金"""
        from .widgets import AddFundDialog
        # 挂载对话框
        self.mount(AddFundDialog())

    def action_delete_fund(self) -> None:
        """删除基金"""
        table = self.query_one("#fund-table", FundTable)
        cursor_row = table.cursor_row

        if cursor_row >= len(self.funds):
            self.notify("请先选择要删除的基金", severity="warning")
            return

        fund = self.funds[cursor_row]
        from config.manager import ConfigManager
        config_manager = ConfigManager()

        # 从配置中移除
        if config_manager.remove_watchlist(fund.code):
            self.notify(f"已从自选移除: {fund.name}", severity="information")
            # 从基金代码列表中移除
            if fund.code in self._fund_codes:
                self._fund_codes.remove(fund.code)
                # 刷新数据
                asyncio.create_task(self.load_fund_data())
        else:
            self.notify("基金不在自选列表中", severity="warning")

    def action_set_holding(self) -> None:
        """设置持仓"""
        table = self.query_one("#fund-table", FundTable)
        cursor_row = table.cursor_row

        if cursor_row >= len(self.funds):
            self.notify("请先选择要设置持仓的基金", severity="warning")
            return

        fund = self.funds[cursor_row]

        # 获取当前持仓信息
        current_shares = fund.hold_shares if hasattr(fund, 'hold_shares') else 0.0
        current_cost = fund.cost if hasattr(fund, 'cost') else 0.0

        from .widgets import HoldingDialog
        # 挂载对话框
        self.mount(HoldingDialog(fund.code, fund.name, current_shares, current_cost))

    def action_show_chart(self) -> None:
        """显示基金净值走势图"""
        table = self.query_one("#fund-table", FundTable)
        cursor_row = table.cursor_row

        if cursor_row >= len(self.funds):
            self.notify("请先选择要查看图表的基金", severity="warning")
            return

        fund = self.funds[cursor_row]

        # 异步加载历史数据并显示图表
        asyncio.create_task(self._show_fund_chart(fund.code, fund.name))

    # ==================== 视图切换动作 ====================

    def action_next_view(self) -> None:
        """切换到下一个视图"""
        views = ["fund", "commodity", "news"]
        current_idx = views.index(self.active_view)
        next_idx = (current_idx + 1) % len(views)
        self.active_view = views[next_idx]

    def action_prev_view(self) -> None:
        """切换到上一个视图"""
        views = ["fund", "commodity", "news"]
        current_idx = views.index(self.active_view)
        prev_idx = (current_idx - 1) % len(views)
        self.active_view = views[prev_idx]

    def action_switch_view(self, view: str) -> None:
        """切换到指定视图"""
        self.active_view = view

    # ==================== 响应式属性监视器 ====================

    def watch_funds(self, new_funds: list) -> None:
        """当 funds 变化时自动更新表格"""
        table = self._safe_query("#fund-table", FundTable)
        if table:
            table.update_funds(new_funds)
        self.calculate_stats()
        self.update_stats()

    def watch_commodities(self, new_commodities: list) -> None:
        """当 commodities 变化时自动更新"""
        view = self._safe_query("#commodity-table", CommodityPairView)
        if view:
            view.update_commodities(new_commodities)

    def watch_news_list(self, new_news: list) -> None:
        """当 news_list 变化时自动更新"""
        news_widget = self._safe_query("#news-list", NewsList)
        if news_widget:
            news_widget.update_news(new_news)

    def watch_total_profit(self, value: float) -> None:
        """总收益变化时更新"""
        self.update_stats()

    def watch_active_view(self, view: str) -> None:
        """切换活动视图时更新样式"""
        # 视图标签的原始文本
        tab_texts = {
            "fund": "📊 基金",
            "commodity": "📈 商品",
            "news": "📰 新闻"
        }
        for tab_id, tab_view in [("tab-fund", "fund"), ("tab-commodity", "commodity"), ("tab-news", "news")]:
            tab = self._safe_query(f"#{tab_id}", Static)
            if tab:
                if tab_view == view:
                    tab.update(f"[b]{tab_texts[tab_view]}[/b]")
                else:
                    tab.update(f"  {tab_texts[tab_view]}  ")

    # ==================== 对话框消息处理 ====================

    def on_add_fund_dialog_dismiss(self, event: AddFundDialog.Dismiss) -> None:
        """处理添加基金对话框关闭"""
        dialog = self.query_one("#add-fund-dialog", AddFundDialog)
        if event.result and dialog.result_code and dialog.result_name:
            # 添加到配置
            from config.manager import ConfigManager
            from config.models import Fund
            config_manager = ConfigManager()
            fund = Fund(code=dialog.result_code, name=dialog.result_name)
            if config_manager.add_watchlist(fund):
                self.notify(f"已添加基金: {dialog.result_name}", severity="information")
                # 添加到基金代码列表并刷新
                if dialog.result_code not in self._fund_codes:
                    self._fund_codes.append(dialog.result_code)
                    asyncio.create_task(self.load_fund_data())
            else:
                self.notify("基金已存在于自选列表中", severity="warning")

    def on_holding_dialog_dismiss(self, event: HoldingDialog.Dismiss) -> None:
        """处理持仓设置对话框关闭"""
        if not event.result:
            return

        dialog = self.query_one("#holding-dialog", HoldingDialog)
        # 更新持仓配置
        from config.manager import ConfigManager
        from config.models import Holding
        config_manager = ConfigManager()

        if dialog.is_holding:
            holding = Holding(
                code=dialog.fund_code,
                name=dialog.fund_name,
                shares=dialog.result_shares,
                cost=dialog.result_cost
            )
            if config_manager.add_holding(holding):
                self.notify(f"已设置持仓: {dialog.fund_name}", severity="information")
        else:
            if config_manager.remove_holding(dialog.fund_code):
                self.notify(f"已取消持仓: {dialog.fund_name}", severity="information")

        # 刷新数据
        asyncio.create_task(self.load_fund_data())

    # ==================== 数据刷新 ====================

    async def auto_refresh(self) -> None:
        """自动刷新任务"""
        while True:
            try:
                await asyncio.sleep(self.refresh_interval)
                await self.refresh_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log(f"自动刷新失败: {e}")

    async def refresh_data(self) -> None:
        """刷新所有数据"""
        try:
            # 刷新基金数据
            await self.load_fund_data()
            # 刷新商品数据
            await self.load_commodity_data()
            # 刷新新闻数据
            await self.load_news_data()
        except Exception as e:
            self.log(f"刷新数据失败: {e}")

    async def load_fund_data(self) -> None:
        """从真实数据源加载基金数据"""
        if not self._fund_codes:
            self.notify("没有配置基金代码", severity="warning")
            return

        try:
            # 使用 DataSourceManager 批量获取基金数据
            params_list = [dict(kwargs=dict(fund_code=code)) for code in self._fund_codes]
            results = await self.data_source_manager.fetch_batch(
                DataSourceType.FUND,
                params_list
            )

            funds = []
            for result in results:
                if result.success and result.data:
                    # 从天天基金接口返回的数据
                    raw_data = result.data

                    # 获取用户持仓信息 (如果有)
                    holding = self._get_holding_info(raw_data.get("fund_code", ""))

                    # 计算估算涨跌幅
                    est_value = raw_data.get("estimated_net_value")
                    net_value = raw_data.get("unit_net_value")
                    change_pct = raw_data.get("estimated_growth_rate")

                    # 如果没有估算涨跌幅，尝试计算
                    if change_pct is None and est_value and net_value:
                        change_pct = ((est_value - net_value) / net_value) * 100

                    # 转换数据格式以匹配 FundData
                    fund_data = FundData(
                        code=raw_data.get("fund_code", ""),
                        name=raw_data.get("name", ""),
                        net_value=net_value or 0.0,
                        est_value=est_value or 0.0,
                        change_pct=change_pct or 0.0,
                        profit=holding["profit"],
                        hold_shares=holding["hold_shares"],
                        cost=holding["cost"]
                    )
                    funds.append(fund_data)

            if funds:
                self.funds = funds
                self.notify(f"成功加载 {len(funds)} 只基金数据", severity="information")
            else:
                self.notify("未能获取到任何基金数据", severity="warning")
                # 加载失败时使用示例数据
                self.load_sample_funds()

        except Exception as e:
            self.log(f"加载基金数据失败: {e}")
            self.notify(f"加载基金数据失败: {e}", severity="error")
            # 加载失败时使用示例数据
            self.load_sample_funds()

    def _get_holding_info(self, fund_code: str) -> Dict[str, float]:
        """获取基金持仓信息，从配置文件加载"""
        try:
            from config.manager import ConfigManager
            config_manager = ConfigManager()
            funds_config = config_manager.load_funds()

            # 查找持仓
            holding = funds_config.get_holding(fund_code)
            if holding:
                # 计算持仓盈亏
                profit = 0.0
                # 需要从基金数据中获取当前净值来计算
                for fund in self.funds:
                    if fund.code == fund_code:
                        if holding.shares > 0 and holding.cost > 0:
                            profit = (fund.net_value - holding.cost) * holding.shares
                        break

                return {
                    "hold_shares": holding.shares,
                    "cost": holding.cost,
                    "profit": profit
                }
        except Exception as e:
            self.log(f"加载持仓配置失败: {e}")

        # 默认值
        return {
            "hold_shares": 0.0,
            "cost": 0.0,
            "profit": 0.0
        }

    def load_sample_funds(self) -> None:
        """加载示例基金数据"""
        self.funds = [
            FundData(
                code="161039",
                name="富国中证新能源汽车指数",
                net_value=1.2456,
                est_value=1.2589,
                change_pct=1.23,
                profit=156.78,
                hold_shares=1000.0,
                cost=1.15
            ),
            FundData(
                code="161725",
                name="招商中证白酒指数(LOF)",
                net_value=1.0234,
                est_value=1.0356,
                change_pct=-0.45,
                profit=-89.32,
                hold_shares=500.0,
                cost=1.08
            ),
            FundData(
                code="110022",
                name="易方达消费行业股票",
                net_value=3.4567,
                est_value=3.4789,
                change_pct=0.87,
                profit=234.56,
                hold_shares=2000.0,
                cost=2.89
            ),
        ]

    async def load_commodity_data(self) -> None:
        """从真实数据源加载商品数据"""
        default_commodities = [
            {"symbol": "gold_cny", "name": "Au99.99 (上海黄金)", "source": "akshare"},
            {"symbol": "gold", "name": "黄金 (COMEX)", "source": "yfinance"},
            {"symbol": "wti", "name": "WTI原油", "source": "yfinance"},
            {"symbol": "silver", "name": "白银", "source": "yfinance"},
            {"symbol": "natural_gas", "name": "天然气", "source": "yfinance"},
        ]

        try:
            from config.manager import ConfigManager
            config_manager = ConfigManager()
            commodities_config = config_manager.load_commodities()

            if commodities_config.commodities:
                commodity_list = [
                    {"symbol": c.symbol, "name": c.name, "source": c.source}
                    for c in commodities_config.commodities
                ]
            else:
                commodity_list = default_commodities
        except Exception as e:
            self.log(f"加载商品配置失败，使用默认配置: {e}")
            commodity_list = default_commodities

        commodities = []
        for item in commodity_list:
            symbol = item["symbol"]

            try:
                result = await self.data_source_manager.fetch(
                    DataSourceType.COMMODITY,
                    symbol
                )

                if result.success:
                    data = result.data
                    commodities.append(CommodityData(
                        name=data.get("name", item["name"]),
                        price=data.get("price", 0.0),
                        change_pct=data.get("change_percent", data.get("change_pct", 0.0)),
                        change=data.get("change", 0.0),
                        currency=data.get("currency", "CNY"),
                        exchange=data.get("exchange", ""),
                        time=str(data.get("time", "")),
                        symbol=symbol
                    ))
                else:
                    commodities.append(CommodityData(
                        name=item["name"],
                        price=0.0,
                        change_pct=0.0,
                        symbol=symbol
                    ))
            except Exception as e:
                self.log(f"获取商品 {symbol} 数据失败: {e}")
                commodities.append(CommodityData(
                    name=item["name"],
                    price=0.0,
                    change_pct=0.0,
                    symbol=symbol
                ))

        self.commodities = commodities

    async def load_news_data(self) -> None:
        """从真实新闻源加载财经新闻"""
        try:
            result = await self.data_source_manager.fetch(
                DataSourceType.NEWS,
                category="finance"
            )

            if result.success and result.data:
                news_list = []
                for news_item in result.data:
                    time_str = news_item.get("time", "")
                    if not time_str:
                        time_str = "未知"

                    news_list.append(NewsData(
                        time=time_str,
                        title=news_item.get("title", "无标题"),
                        url=news_item.get("url", "")
                    ))

                self.news_list = news_list
                self.notify(f"成功加载 {len(news_list)} 条财经新闻", severity="information")
            else:
                self.load_sample_news()
        except Exception as e:
            self.log(f"加载新闻数据失败: {e}")
            self.load_sample_news()

    def load_sample_news(self):
        """加载示例新闻数据（备用）"""
        self.news_list = [
            NewsData(
                time="10:30",
                title="央行宣布降息25个基点，稳增长政策再加码",
                url="https://finance.sina.com.cn/news/1"
            ),
            NewsData(
                time="09:45",
                title="A股三大指数集体收涨，成交量突破万亿",
                url="https://finance.sina.com.cn/news/2"
            ),
            NewsData(
                time="09:15",
                title="人民币汇率中间价上调123点",
                url="https://finance.sina.com.cn/news/3"
            ),
        ]

    # ==================== 统计信息 ====================

    def calculate_stats(self) -> None:
        """计算统计数据"""
        if not self.funds:
            self.total_profit = 0.0
            self.avg_change = 0.0
            return

        # 计算总收益（使用 change_pct 估算）
        total_pct = sum(fund.change_pct for fund in self.funds)
        self.avg_change = total_pct / len(self.funds)

        # 简化计算：假设每只基金投入 10000 元
        self.total_profit = sum(
            fund.change_pct * 100 for fund in self.funds
        )

    def update_stats(self) -> None:
        """更新统计面板"""
        stat_panel = self.query_one("#stat-panel", StatPanel)
        stat_panel.update_stats(
            total_profit=self.total_profit,
            fund_count=len(self.funds),
            avg_change=self.avg_change,
            data_source="新浪财经",
            last_update=self.last_update_time
        )

    def update_status_bar(self) -> None:
        """更新状态栏 - 保留兼容，已合并到 StatPanel"""
        # 状态栏功能已合并到底部统计行
        pass

    # ==================== 图表功能 ====================

    async def _show_fund_chart(self, fund_code: str, fund_name: str) -> None:
        """显示基金净值图表"""
        try:
            self.notify(f"正在加载 {fund_name} 的历史数据...", severity="information")

            # 使用 FundHistorySource 获取历史数据
            history_source = FundHistorySource()
            result = await history_source.fetch(fund_code, period="近一年")

            if result.success and result.data:
                history_list = result.data.get("history", [])

                if not history_list:
                    self.notify("未获取到历史数据", severity="warning")
                    return

                # 提取日期和净值数据
                dates = [item["date"] for item in history_list]
                net_values = [item["net_value"] for item in history_list]
                accumulated_net = [item.get("accumulated_net") for item in history_list]

                # 创建历史数据对象
                history_data = FundHistoryData(
                    fund_code=fund_code,
                    fund_name=fund_name,
                    dates=dates,
                    net_values=net_values,
                    accumulated_net=accumulated_net if any(accumulated_net) else None
                )

                # 显示图表对话框
                self.mount(ChartDialog(fund_code, fund_name, history_data))
            else:
                error_msg = result.error or "未知错误"
                self.notify(f"获取历史数据失败: {error_msg}", severity="warning")

        except Exception as e:
            self.log(f"显示图表失败: {e}")
            self.notify(f"显示图表失败: {str(e)}", severity="error")

    async def load_fund_history(self, fund_code: str) -> Optional[FundHistoryData]:
        """加载基金历史数据（供其他方法使用）"""
        try:
            history_source = FundHistorySource()
            result = await history_source.fetch(fund_code, period="近一年")

            if result.success and result.data:
                history_list = result.data.get("history", [])

                if not history_list:
                    return None

                dates = [item["date"] for item in history_list]
                net_values = [item["net_value"] for item in history_list]
                accumulated_net = [item.get("accumulated_net") for item in history_list]

                return FundHistoryData(
                    fund_code=fund_code,
                    fund_name=result.data.get("fund_name", ""),
                    dates=dates,
                    net_values=net_values,
                    accumulated_net=accumulated_net if any(accumulated_net) else None
                )

        except Exception as e:
            self.log(f"加载基金历史数据失败: {e}")

        return None
