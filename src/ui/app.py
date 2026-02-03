# -*- coding: UTF-8 -*-
"""主应用模块 - Textual TUI 应用入口
支持真实基金数据源集成
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, DataTable, Button, Footer, Label
from textual import events, on
from textual.color import Color
from datetime import datetime
from typing import List, Optional, Dict
import asyncio
import os
import sys

# 添加项目根目录到路径，确保可以正确导入 datasources
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from .widgets import FundTable, CommodityTable, NewsList, FundData, CommodityData, NewsData, StatPanel, StatusBar
from .screens import FundScreen, CommodityScreen, NewsScreen, HelpScreen
from datasources.manager import DataSourceManager, create_default_manager
from datasources.base import DataSourceType
from datasources.fund_source import FundDataSource


class FundTUIApp(App):
    """基金实时估值 TUI 应用"""

    # 应用配置
    TITLE = "基金实时估值"
    SUB_TITLE = "Fund Real-Time Valuation"
    CSS_PATH = "styles.tcss"

    # 定义主题
    dark_theme = True

    # 视图索引
    VIEW_FUND = 0
    VIEW_COMMODITY = 1
    VIEW_NEWS = 2

    # 快捷键绑定
    BINDINGS = [
        ("q", "quit", "退出"),
        ("ctrl+c", "quit", "退出"),
        ("F1", "toggle_help", "帮助"),
        ("r", "refresh", "刷新"),
        ("t", "toggle_theme", "切换主题"),
        ("1", "switch_to_fund", "基金"),
        ("2", "switch_to_commodity", "商品"),
        ("3", "switch_to_news", "新闻"),
    ]

    def __init__(self):
        super().__init__()

        # 数据源管理
        self.data_source_manager = create_default_manager()

        # 状态
        self.is_dark_theme = True
        self.last_update_time = ""
        self.refresh_interval = 30  # 秒
        self.auto_refresh_task = None

        # 统计数据
        self.total_profit = 0.0
        self.avg_change = 0.0

        # 基金数据列表
        self.funds: List[FundData] = []
        self._fund_codes = ["161039", "161725", "110022"]  # 默认基金列表

        # 商品数据列表
        self.commodities: List[CommodityData] = []

        # 新闻数据列表
        self.news_list: List[NewsData] = []

        # 当前视图
        self.current_view = self.VIEW_FUND

    # ==================== 组件组合 ====================

    def compose(self) -> ComposeResult:
        """构建应用 UI"""
        # 顶部标题栏
        yield Horizontal(
            Static("[b]基金实时估值系统[/b]", id="app-title"),
            Static("[b]📊 基金[/b] | 📈 商品 | 📰 新闻", id="view-indicator"),
            classes="top-bar"
        )

        # 统计面板
        yield Horizontal(
            StatPanel(id="stat-panel", classes="stat-panel"),
            classes="stats-container"
        )

        # 基金表格
        yield FundTable(id="fund-table", classes="main-table")

        # 商品表格
        yield CommodityTable(id="commodity-table", classes="main-table")

        # 新闻列表
        yield NewsList(id="news-list", classes="main-list")

        # 底部状态栏
        yield StatusBar(id="status-bar", classes="status-bar")

        # 底部导航提示
        yield Footer()

    # ==================== 生命周期方法 ====================

    def on_mount(self) -> None:
        """应用挂载时初始化"""
        # 显示基金视图，隐藏其他
        self.query_one("#commodity-table").display = False
        self.query_one("#news-list").display = False

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

    # ==================== 视图切换 ====================

    def action_switch_to_fund(self) -> None:
        """切换到基金视图"""
        self.current_view = self.VIEW_FUND
        self.query_one("#fund-table").display = True
        self.query_one("#commodity-table").display = False
        self.query_one("#news-list").display = False
        self.query_one("#fund-table").focus()

    def action_switch_to_commodity(self) -> None:
        """切换到商品视图"""
        self.current_view = self.VIEW_COMMODITY
        self.query_one("#fund-table").display = False
        self.query_one("#commodity-table").display = True
        self.query_one("#news-list").display = False
        self.query_one("#commodity-table").focus()

    def action_switch_to_news(self) -> None:
        """切换到新闻视图"""
        self.current_view = self.VIEW_NEWS
        self.query_one("#fund-table").display = False
        self.query_one("#commodity-table").display = False
        self.query_one("#news-list").display = True
        self.query_one("#news-list").focus()

    # ==================== 动作方法 ====================

    def action_refresh(self) -> None:
        """手动刷新数据"""
        asyncio.create_task(self.refresh_data())

    def action_toggle_theme(self) -> None:
        """切换深色/浅色主题"""
        self.is_dark_theme = not self.is_dark_theme
        # 使用 CSS 类切换主题
        if self.is_dark_theme:
            self.dark_theme = True
        else:
            self.dark_theme = False
        self.update_status_bar()

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
                # 更新表格
                table = self.query_one("#fund-table", FundTable)
                table.update_funds(self.funds)
                self.calculate_stats()
                self.update_stats()
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
        """获取基金持仓信息"""
        default_shares = 1000.0
        default_cost = 1.0

        holding_configs = {
            "161039": {"shares": 1000.0, "cost": 1.15},
            "161725": {"shares": 500.0, "cost": 1.08},
            "110022": {"shares": 2000.0, "cost": 2.89},
        }

        config = holding_configs.get(fund_code, {"shares": default_shares, "cost": default_cost})
        hold_shares = config.get("shares", default_shares)
        cost = config.get("cost", default_cost)
        profit = 0.0

        return {
            "hold_shares": hold_shares,
            "cost": cost,
            "profit": profit
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
        # 更新表格
        table = self.query_one("#fund-table", FundTable)
        table.update_funds(self.funds)
        self.calculate_stats()
        self.update_stats()

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
        # 更新表格
        table = self.query_one("#commodity-table", CommodityTable)
        table.update_commodities(self.commodities)

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
                # 更新列表
                news_widget = self.query_one("#news-list", NewsList)
                news_widget.update_news(self.news_list)
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
        # 更新列表
        news_widget = self.query_one("#news-list", NewsList)
        news_widget.update_news(self.news_list)

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
            avg_change=self.avg_change
        )

    def update_status_bar(self) -> None:
        """更新状态栏"""
        status_bar = self.query_one("#status-bar", StatusBar)
        theme = "dark" if self.is_dark_theme else "light"
        status_bar.update_status(
            last_update=self.last_update_time,
            theme=theme,
            auto_refresh=True
        )
