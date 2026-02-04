# -*- coding: UTF-8 -*-
"""Flet GUI 主应用

基金实时估值图形化界面，基于 Flet 0.28.3 框架开发。
参考 Apple Stocks + 支付宝基金设计风格。
"""

import flet as ft
from flet import (
    Column,
    Row,
    Container,
    Text,
    ElevatedButton,
    TextField,
    ProgressRing,
    Divider,
    AlertDialog,
    SnackBar,
    Tabs as FletTabs,
    Tab as FletTab,
    Icon,
    Icons,
    IconButton,
    ScrollMode,
)
from .detail import FundDetailDialog
from .theme import (
    ChangeColors,
    get_change_color,
    format_change_text,
)
from .components import (
    FundCard,
    FundPortfolioCard,
    MiniChart,
    SearchBar,
    QuickActionButton,
    AppColors,
)
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.manager import create_default_manager
from src.datasources.base import DataSourceType
from src.db.database import DatabaseManager, ConfigDAO


@dataclass
class FundDisplayData:
    """基金显示数据"""

    code: str
    name: str
    net_value: float
    est_value: float
    change_pct: float
    profit: float
    hold_shares: float
    cost: float
    sector: str = ""  # 板块标注
    is_hold: bool = False  # 持有标记
    chart_data: List[float] = field(default_factory=list)  # 迷你走势图数据


class FundGUIApp:
    """基金实时估值 GUI 应用"""

    def __init__(self):
        self.page: Optional[ft.Page] = None
        self.data_source_manager = create_default_manager()
        self.db_manager = DatabaseManager()
        self.config_dao = ConfigDAO(self.db_manager)

        self.funds: List[FundDisplayData] = []
        self.refresh_interval = 30
        self.current_tab = 0
        self._fund_cards: dict[str, FundCard] = {}  # 缓存基金卡片组件
        self._fund_list: Optional[Column] = None  # 基金列表容器

    def run(self, page: ft.Page):
        """运行应用"""
        self.page = page
        page.title = "基金实时估值"
        page.theme_mode = ft.ThemeMode.DARK

        self.config_dao.init_default_funds()
        self.config_dao.init_default_commodities()

        self._build_ui()
        page.update()

    def _build_ui(self):
        """构建 UI（Apple Stocks + 支付宝风格）"""
        # 顶部导航栏（简洁风格）
        top_bar = Container(
            padding=ft.padding.only(left=16, right=16, top=12, bottom=8),
            content=Row(
                [
                    Text(
                        "基金",
                        size=34,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    Container(expand=True),
                    IconButton(
                        icon=Icons.NOTIFICATIONS_OUTLINED,
                        icon_color=AppColors.TEXT_PRIMARY,
                        tooltip="通知",
                        on_click=self._show_notifications,
                    ),
                    IconButton(
                        icon=Icons.SETTINGS_OUTLINED,
                        icon_color=AppColors.TEXT_PRIMARY,
                        tooltip="设置",
                        on_click=self._show_settings,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        # 标签栏（带动画）
        self.tabs = FletTabs(
            selected_index=0,
            animation_duration=350,  # 稍微延长动画时间，更流畅
            on_change=self._on_tab_change,
            tabs=[
                FletTab(
                    text="自选",
                    icon=Icons.STAR_BORDER,
                    content=self._build_fund_page(),
                ),
                FletTab(
                    text="商品",
                    icon=Icons.TRENDING_UP,
                    content=self._build_commodity_page(),
                ),
                FletTab(
                    text="新闻",
                    icon=Icons.NEWSPAPER,
                    content=self._build_news_page(),
                ),
            ],
            expand=1,
        )

        # 底部状态栏
        self.status_bar = Container(
            content=Row(
                [
                    Text("等待更新...", size=12, color=AppColors.TEXT_SECONDARY),
                    Container(expand=True),
                    Text("数据源: 新浪财经", size=12, color=AppColors.TEXT_SECONDARY),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=10,
            bgcolor=AppColors.CARD_DARK,
        )

        self.page.add(top_bar)
        self.page.add(self.tabs)
        self.page.add(self.status_bar)

        # 加载初始数据
        self.page.run_task(self._load_fund_data)

    def _build_fund_page(self) -> Container:
        """构建基金页面（卡片式布局）"""
        # 资产概览卡片
        self.portfolio_card = FundPortfolioCard(
            total_assets=0,
            daily_profit=0,
            total_profit=0,
            profit_rate=0,
            fund_count=0,
            hold_count=0,
        )

        # 快捷操作按钮
        action_row = Row(
            [
                QuickActionButton(
                    Icons.ADD,
                    "添加",
                    self._show_add_fund,
                    accent_color=AppColors.ACCENT_BLUE,
                ),
                QuickActionButton(
                    Icons.INFO,
                    "详情",
                    self._show_detail,
                    accent_color=AppColors.ACCENT_ORANGE,
                ),
                QuickActionButton(
                    Icons.EDIT,
                    "持仓",
                    self._show_holding,
                    accent_color=AppColors.UP_RED,
                ),
                QuickActionButton(
                    Icons.STAR,
                    "持有",
                    self._show_hold,
                    accent_color=AppColors.DOWN_GREEN,
                ),
            ],
            spacing=24,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        # 搜索栏
        self.search_bar = SearchBar(
            on_search=self._on_fund_search,
            placeholder="搜索基金代码或名称",
        )

        # 基金列表（使用 Column + Scroll）
        self._fund_list = Column(
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        # 返回包含所有元素的 Column
        return Container(
            content=Column(
                [
                    # 资产概览卡片
                    Container(
                        padding=ft.padding.symmetric(horizontal=16),
                        content=self.portfolio_card,
                    ),
                    Container(height=8),
                    # 快捷操作
                    Container(
                        padding=ft.padding.symmetric(horizontal=16),
                        content=action_row,
                    ),
                    Container(height=8),
                    # 搜索栏
                    Container(
                        padding=ft.padding.symmetric(horizontal=16),
                        content=self.search_bar,
                    ),
                    Container(height=12),
                    # 基金列表容器 - 需要expand
                    Container(
                        expand=True,
                        content=self._fund_list,
                    ),
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
            padding=ft.padding.only(top=8),
        )

    def _build_commodity_page(self) -> Container:
        """构建商品页面"""
        self.commodity_list = Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)

        return Container(
            content=Column(
                [
                    Text("大宗商品行情", size=18, weight=ft.FontWeight.BOLD),
                    Divider(),
                    self.commodity_list,
                ],
                expand=True,
            ),
            padding=10,
        )

    def _build_news_page(self) -> Container:
        """构建新闻页面"""
        self.news_list = Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)

        return Container(
            content=Column(
                [
                    Text("财经新闻", size=18, weight=ft.FontWeight.BOLD),
                    Divider(),
                    self.news_list,
                ],
                expand=True,
            ),
            padding=10,
        )

    async def _on_refresh(self, e):
        """刷新数据"""
        if self.current_tab == 0:
            await self._load_fund_data()
        elif self.current_tab == 1:
            await self._load_commodity_data()
        elif self.current_tab == 2:
            await self._load_news_data()

        self._show_snackbar("数据已刷新")

    def _show_notifications(self, e):
        """显示通知"""
        self._show_snackbar("通知功能开发中")

    def _show_settings(self, e):
        """显示设置"""
        self._show_snackbar("设置功能开发中")

    def _on_fund_search(self, query: str):
        """基金搜索"""
        if query:
            filtered = [
                f
                for f in self.funds
                if query.lower() in f.code.lower() or query.lower() in f.name.lower()
            ]
            # 过滤显示
            for code, card in self._fund_cards.items():
                card.visible = code in {f.code for f in filtered}
        else:
            # 显示全部
            for card in self._fund_cards.values():
                card.visible = True

        if self._fund_list:
            self._fund_list.update()

    def _on_fund_click(self, e, fund: FundDisplayData):
        """基金卡片点击"""
        self._show_detail(e, fund)

    def _show_snackbar(self, message: str):
        """显示提示"""
        sb = SnackBar(Text(message), open=True)
        self.page.overlay.append(sb)
        self.page.update()

    async def _load_fund_data(self):
        """加载基金数据"""
        try:
            watchlist = self.config_dao.get_watchlist()
            holdings = self.config_dao.get_holdings()

            self.funds = []
            for fund in watchlist:
                try:
                    result = await self.data_source_manager.fetch(
                        DataSourceType.FUND, fund.code
                    )

                    if result.success and result.data:
                        raw_data = result.data
                        holding = next(
                            (h for h in holdings if h.code == fund.code), None
                        )

                        fund_data = FundDisplayData(
                            code=raw_data.get("fund_code", fund.code),
                            name=raw_data.get("name", fund.name),
                            net_value=raw_data.get("unit_net_value", 0.0),
                            est_value=raw_data.get("estimated_net_value", 0.0),
                            change_pct=raw_data.get("estimated_growth_rate", 0.0),
                            profit=holding.shares
                            * (raw_data.get("unit_net_value", 0.0) - holding.cost)
                            if holding
                            else 0.0,
                            hold_shares=holding.shares if holding else 0.0,
                            cost=holding.cost if holding else 0.0,
                            sector=fund.sector if fund else "",
                            is_hold=fund.is_holding if fund else False,
                        )
                        self.funds.append(fund_data)
                except Exception as ex:
                    pass

            self._update_fund_table()
            now = datetime.now().strftime("%H:%M:%S")
            self.status_bar.content.controls[0].value = f"Last Update: {now}"
            self.status_bar.content.update()

        except Exception as e:
            self._show_snackbar(f"Load failed: {str(e)}")

    def _update_fund_table(self):
        """更新基金卡片列表（卡片式布局）"""
        # 计算资产概览数据
        total_assets = sum(
            f.net_value * f.hold_shares for f in self.funds if f.hold_shares > 0
        )
        total_cost = sum(
            f.cost * f.hold_shares for f in self.funds if f.hold_shares > 0
        )
        daily_profit = sum(f.profit for f in self.funds if f.hold_shares > 0)
        total_profit = total_assets - total_cost
        profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else 0
        hold_count = sum(1 for f in self.funds if f.hold_shares > 0)

        # 更新资产概览卡片
        if hasattr(self, "portfolio_card") and self.portfolio_card:
            self.portfolio_card.update_data(
                total_assets=total_assets,
                daily_profit=daily_profit,
                total_profit=total_profit,
                profit_rate=profit_rate,
                fund_count=len(self.funds),
                hold_count=hold_count,
            )

        # 获取当前基金代码集合
        current_codes = {fund.code for fund in self.funds}
        cached_codes = (
            set(self._fund_cards.keys()) if hasattr(self, "_fund_cards") else set()
        )

        # 确保 _fund_cards 存在
        if not hasattr(self, "_fund_cards"):
            self._fund_cards = {}

        # 1. 移除已删除的基金卡片
        removed_codes = cached_codes - current_codes
        for code in removed_codes:
            if code in self._fund_cards:
                card = self._fund_cards.pop(code)
                if self._fund_list and card in self._fund_list.controls:
                    self._fund_list.controls.remove(card)

        # 2. 更新或创建基金卡片
        for fund in self.funds:
            if fund.code in self._fund_cards:
                # 更新已有卡片
                self._fund_cards[fund.code].update_data(
                    net_value=fund.net_value,
                    est_value=fund.est_value,
                    change_pct=fund.change_pct,
                    profit=fund.profit,
                    chart_data=fund.chart_data if fund.chart_data else None,
                )
            else:
                # 创建新卡片
                fund_code = fund.code  # 闭包修复：复制变量
                try:
                    card = FundCard(
                        code=fund.code,
                        name=fund.name,
                        net_value=fund.net_value,
                        est_value=fund.est_value,
                        change_pct=fund.change_pct,
                        profit=fund.profit,
                        hold_shares=fund.hold_shares,
                        cost=fund.cost,
                        sector=fund.sector,
                        is_hold=fund.is_hold,
                        chart_data=fund.chart_data if fund.chart_data else None,
                        on_click=lambda e, f=fund: self._on_fund_click(e, f),
                    )
                except Exception as e:
                    continue

                self._fund_cards[fund.code] = card
                if self._fund_list:
                    self._fund_list.controls.append(card)

        # 刷新基金列表
        if self._fund_list:
            self._fund_list.update()

        # 更新状态栏
        if self.status_bar and self.status_bar.content:
            self.status_bar.content.controls[
                0
            ].value = f"Last Update: {datetime.now().strftime('%H:%M:%S')}"
            self.status_bar.content.update()

        if self.page:
            self.page.update()

    async def _load_commodity_data(self):
        """加载商品数据"""
        try:
            commodities = self.config_dao.get_commodities(enabled_only=True)

            self.commodity_list.controls.clear()

            for commodity in commodities:
                try:
                    result = await self.data_source_manager.fetch(
                        DataSourceType.COMMODITY, commodity.symbol
                    )

                    if result.success and result.data:
                        data = result.data
                        change_color = (
                            ft.Colors.GREEN
                            if data.get("change_percent", 0) >= 0
                            else ft.Colors.RED
                        )

                        card = Card(
                            content=Container(
                                content=Row(
                                    [
                                        Column(
                                            [
                                                Text(
                                                    data.get("name", commodity.name),
                                                    size=14,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                Text(
                                                    f"{data.get('price', 0)} {data.get('currency', 'CNY')}",
                                                    size=16,
                                                ),
                                            ],
                                            expand=True,
                                        ),
                                        Text(
                                            f"{data.get('change_percent', 0):+.2f}%",
                                            color=change_color,
                                            size=16,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                padding=12,
                            ),
                            margin=margin.only(bottom=4),
                        )
                        self.commodity_list.controls.append(card)
                except Exception as ex:
                    print(f"获取商品 {commodity.symbol} 数据失败: {ex}")

            self.page.update()

        except Exception as e:
            self._show_snackbar(f"加载商品失败: {str(e)}")

    async def _load_news_data(self):
        """加载新闻数据"""
        try:
            result = await self.data_source_manager.fetch(
                DataSourceType.NEWS, "finance"
            )

            self.news_list.controls.clear()

            if result.success and result.data:
                for item in result.data:
                    card = Card(
                        content=Container(
                            content=Column(
                                [
                                    Text(
                                        item.get("title", "无标题"),
                                        size=14,
                                        max_lines=2,
                                    ),
                                    Row(
                                        [
                                            Icon(
                                                Icons.ACCESS_TIME,
                                                size=12,
                                                color=ft.Colors.WHITE70,
                                            ),
                                            Text(
                                                item.get("time", ""),
                                                size=11,
                                                color=ft.Colors.WHITE70,
                                            ),
                                            Text(" - "),
                                            Text(
                                                item.get("source", "未知"),
                                                size=11,
                                                color=ft.Colors.BLUE_200,
                                            ),
                                        ],
                                        spacing=4,
                                    ),
                                ],
                                spacing=4,
                            ),
                            padding=12,
                        ),
                        margin=margin.only(bottom=4),
                    )
                    self.news_list.controls.append(card)
            else:
                self._load_sample_news()

            self.page.update()

        except Exception as e:
            print(f"加载新闻失败: {e}")
            self._load_sample_news()
            self.page.update()

    def _load_sample_news(self):
        """加载示例新闻"""
        sample_news = [
            {"title": "央行宣布降息25个基点", "time": "10:30", "source": "新浪财经"},
            {"title": "A股三大指数集体收涨", "time": "09:45", "source": "新浪财经"},
        ]

        for news in sample_news:
            card = Card(
                content=Container(
                    content=Column(
                        [
                            Text(news["title"], size=14, max_lines=2),
                            Row(
                                [
                                    Icon(
                                        Icons.ACCESS_TIME,
                                        size=12,
                                        color=ft.Colors.WHITE70,
                                    ),
                                    Text(
                                        news["time"], size=11, color=ft.Colors.WHITE70
                                    ),
                                    Text(" - "),
                                    Text(
                                        news["source"],
                                        size=11,
                                        color=ft.Colors.BLUE_200,
                                    ),
                                ],
                                spacing=4,
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=12,
                ),
                margin=margin.only(bottom=4),
            )
            self.news_list.controls.append(card)

    def _show_add_fund(self, e):
        """显示添加基金对话框"""
        dialog = AddFundDialog(self)
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _show_detail(self, e):
        """显示基金详情对话框"""
        # 获取当前选中的基金
        selected_code = self._get_selected_fund_code()
        if not selected_code:
            self._show_snackbar("请先选择要查看详情的基金")
            return

        # 获取基金信息
        fund = next((f for f in self.funds if f.code == selected_code), None)
        if not fund:
            self._show_snackbar("未找到选中的基金信息")
            return

        # 创建详情数据（使用 FundDetailDialog 期望的数据结构）
        from .detail import FundDetailData

        detail_data = FundDetailData(
            code=fund.code,
            name=fund.name,
            net_value=fund.net_value,
            est_value=fund.est_value,
            change_pct=fund.change_pct,
            profit=fund.profit,
            hold_shares=fund.hold_shares,
            cost=fund.cost,
        )

        # 显示详情对话框
        dialog = FundDetailDialog(self, detail_data)
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _show_holding(self, e):
        """显示持仓设置对话框"""
        # 获取当前选中的基金
        selected_code = self._get_selected_fund_code()
        if not selected_code:
            self._show_snackbar("请先选择要设置持仓的基金")
            return

        # 获取基金信息
        fund = next((f for f in self.funds if f.code == selected_code), None)
        if not fund:
            self._show_snackbar("未找到选中的基金信息")
            return

        dialog = HoldingDialog(self, fund)
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _show_hold(self, e):
        """显示持有标记设置对话框"""
        # 获取当前选中的基金
        selected_code = self._get_selected_fund_code()
        if not selected_code:
            self._show_snackbar("请先选择要设置持有标记的基金")
            return

        # 获取基金信息
        fund = next((f for f in self.funds if f.code == selected_code), None)
        if not fund:
            self._show_snackbar("未找到选中的基金信息")
            return

        # 获取当前持有标记状态
        db_fund = self.config_dao.get_fund(selected_code)
        current_is_hold = db_fund.is_holding if db_fund else False

        # 显示持有标记设置对话框
        dialog = SetHoldDialog(self, selected_code, fund.name, current_is_hold)
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _delete_fund(self, e):
        """删除基金"""
        # 获取当前选中的基金
        selected_code = self._get_selected_fund_code()
        if not selected_code:
            self._show_snackbar("请先选择要删除的基金")
            return

        # 获取基金名称
        fund_name = next(
            (f.name for f in self.funds if f.code == selected_code), selected_code
        )

        # 显示确认对话框
        dialog = DeleteConfirmDialog(self, selected_code, fund_name)
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _show_sector(self, e):
        """显示板块标注对话框"""
        # 获取当前选中的基金
        selected_code = self._get_selected_fund_code()
        if not selected_code:
            self._show_snackbar("请先选择要设置板块的基金")
            return

        # 获取基金信息
        fund = next((f for f in self.funds if f.code == selected_code), None)
        if not fund:
            self._show_snackbar("未找到选中的基金信息")
            return

        # 获取当前板块标注
        db_fund = self.config_dao.get_fund(selected_code)
        current_sector = db_fund.sector if db_fund else ""

        # 显示板块设置对话框
        dialog = SetSectorDialog(self, selected_code, fund.name, current_sector)
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _on_row_select(self, e):
        """处理表格行选择事件（复选框点击）"""
        if e.data:
            # e.data 是选中行的 data 字段值（基金代码）
            self._selected_fund_code = e.data

    def _on_fund_checkbox_change(self, e, fund_code: str):
        """处理基金复选框选择变更"""
        if e.control.value:
            # 选中
            self._selected_funds.add(fund_code)
        else:
            # 取消选中
            self._selected_funds.discard(fund_code)

    def _get_selected_fund_code(self) -> Optional[str]:
        """获取当前选中的基金代码（单选）"""
        # 优先使用复选框选中的基金
        if hasattr(self, "_selected_funds") and self._selected_funds:
            # 返回最后一个选中的基金
            return list(self._selected_funds)[-1]
        # 检查是否有选中行（旧方式）
        if hasattr(self, "_selected_fund_code") and self._selected_fund_code:
            return self._selected_fund_code
        return None

    def _get_selected_fund_codes(self) -> list[str]:
        """获取所有选中的基金代码（多选）"""
        return list(getattr(self, "_selected_funds", set()))

    def _on_fund_table_row_selected(self, e):
        """处理基金表格行选择事件"""
        if e.data:
            self._selected_fund_code = e.data
            # 高亮显示选中行
            for i, row in enumerate(self.fund_table.rows):
                if row.data == e.data:
                    row.selected = True
                else:
                    row.selected = False
            self.page.update()

    def _on_tab_change(self, e):
        """处理标签页切换"""
        self.current_tab = self.tabs.selected_index
        # 切换到对应标签页时加载数据
        if self.current_tab == 0:
            self.page.run_task(self._load_fund_data)
        elif self.current_tab == 1:
            self.page.run_task(self._load_commodity_data)
        elif self.current_tab == 2:
            self.page.run_task(self._load_news_data)


class AddFundDialog(AlertDialog):
    """添加基金对话框

    功能特性：
    - 输入基金代码后自动查询（6位数字 + 回车）
    - 防抖功能避免频繁查询
    - 键盘快捷键支持（Enter 查询，Ctrl+Enter 添加）
    - 重复基金检测
    - 查询状态图标反馈
    """

    def __init__(self, app: FundGUIApp):
        super().__init__()
        self.app = app

        # 查询状态管理
        self._fetching = False
        self._fund_name = ""
        self._last_query_code = ""  # 上次查询的代码，用于检测重复
        self._debounce_task = None  # 防抖任务

        # 查询状态图标
        self.status_icon = Icon(
            Icons.HELP_OUTLINE, size=20, color=ft.Colors.GREY_400, visible=True
        )

        # 基金代码输入框
        self.code_field = TextField(
            label="基金代码",
            hint_text="输入6位代码后自动查询",
            width=200,
            max_length=6,
            on_change=self._on_code_change,
            on_submit=self._on_code_submit,
        )

        # 基金名称显示字段（只读）
        self.name_field = TextField(
            label="基金名称",
            hint_text="查询后自动显示",
            read_only=True,
            value="",
            width=200,  # 固定宽度而不是 expand
        )

        # 刷新按钮（用于重新查询）
        self.refresh_button = IconButton(
            icon=Icons.REFRESH,
            tooltip="重新查询",
            on_click=self._query_fund,
            visible=False,
        )

        # 加载状态指示器
        self.loading_indicator = ProgressRing(
            width=16, height=16, stroke_width=2, visible=False
        )

        # 加载提示文本
        self.loading_text = Text(
            "查询中...", size=11, color=ft.Colors.BLUE_300, visible=False
        )

        self.modal = True
        self.title = Row(
            [
                Text("添加基金", weight=ft.FontWeight.BOLD),
                Container(expand=True),
                Text(
                    "按 Enter 查询，Ctrl+Enter 添加", size=10, color=ft.Colors.WHITE54
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        )
        self.content = Container(
            content=Column(
                [
                    Row(
                        [
                            self.code_field,
                            self.status_icon,
                            self.loading_indicator,
                            self.loading_text,
                            self.refresh_button,
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    Row([self.name_field], spacing=8),
                    self._build_error_container(),  # 错误提示区域
                ],
                spacing=12,
            ),
            # 自适应宽度，最小 400px
            width=max(400, int(self.app.page.width * 0.5)) if self.app.page else 400,
        )
        self.actions = [
            ElevatedButton("取消", on_click=self._cancel),
            ElevatedButton("添加", on_click=self._confirm),
        ]

    def _build_error_container(self):
        """构建错误提示容器"""
        self.error_text = Text("", size=11, color=ft.Colors.RED_300, visible=False)
        return Container(
            content=self.error_text,
            padding=ft.padding.only(left=8),
            visible=False,
        )

    def _show_error(self, message: str):
        """显示错误信息"""
        self.error_text.value = message
        self.error_text.visible = True
        self.app.page.update()

    def _hide_error(self):
        """隐藏错误信息"""
        self.error_text.value = ""
        self.error_text.visible = False

    def _on_code_change(self, e):
        """基金代码输入变化事件"""
        self._hide_error()
        code = self.code_field.value.strip()

        # 检测是否修改了代码（需要重新查询）
        if code and code != self._last_query_code:
            self._fund_name = ""
            self.name_field.value = ""
            self.status_icon.icon = Icons.HELP_OUTLINE
            self.status_icon.color = ft.Colors.GREY_400
            self.refresh_button.visible = False

        # 6位数字时启用状态
        if len(code) == 6 and code.isdigit():
            self.status_icon.icon = Icons.CHECK_CIRCLE_OUTLINE
            self.status_icon.color = ft.Colors.ORANGE_300
        elif code:
            self.status_icon.icon = Icons.ERROR_OUTLINE
            self.status_icon.color = ft.Colors.RED_300

        self.app.page.update()

    def _on_code_submit(self, e):
        """回车键提交事件"""
        code = self.code_field.value.strip()
        if len(code) == 6 and code.isdigit():
            # 防抖：取消之前的查询任务
            if self._debounce_task and not self._debounce_task.done():
                self._debounce_task.cancel()
            # 触发查询
            self.app.page.run_task(self._query_fund)

    def _cancel_debounce(self):
        """取消防抖任务"""
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
            self._debounce_task = None

    async def _query_fund(self, e=None):
        """查询基金信息（带防抖）"""
        code = self.code_field.value.strip()

        # 验证基金代码格式
        if not code or len(code) != 6 or not code.isdigit():
            self._show_error("请输入6位数字基金代码")
            return

        # 避免重复查询相同代码
        if code == self._last_query_code and self._fund_name:
            self._show_error("该基金已查询过，请直接添加或修改代码重新查询")
            return

        # 更新UI状态为加载中
        self._set_loading(True)
        self._last_query_code = code

        try:
            # 调用数据源查询基金
            result = await self.app.data_source_manager.fetch(DataSourceType.FUND, code)

            if result.success and result.data:
                # 查询成功，更新基金名称
                self._fund_name = result.data.get("name", "")
                self.name_field.value = self._fund_name

                # 更新状态图标
                self.status_icon.icon = Icons.CHECK_CIRCLE
                self.status_icon.color = ft.Colors.GREEN_400
                self.refresh_button.visible = True

                self.app._show_snackbar(f"✓ 基金查询成功: {self._fund_name}")
            else:
                # 查询失败
                self._fund_name = ""
                self.name_field.value = ""
                error_msg = result.error or "基金不存在"
                self._show_error(f"查询失败: {error_msg}")

                # 更新状态图标
                self.status_icon.icon = Icons.ERROR
                self.status_icon.color = ft.Colors.RED_400
                self.refresh_button.visible = True

        except Exception as ex:
            self._show_error(f"查询异常: {str(ex)}")
            self.status_icon.icon = Icons.ERROR
            self.status_icon.color = ft.Colors.RED_400
        finally:
            # 恢复UI状态
            self._set_loading(False)

    def _set_loading(self, loading: bool):
        """设置加载状态"""
        self._fetching = loading
        self.loading_indicator.visible = loading
        self.loading_text.visible = loading

        # 加载时禁用代码输入
        self.code_field.disabled = loading
        self.app.page.update()

    def _cancel(self, e):
        # 清理防抖任务
        self._cancel_debounce()
        self.open = False
        self.app.page.update()

    def _confirm(self, e):
        code = self.code_field.value.strip()

        # 验证基金代码
        if not code:
            self._show_error("请输入基金代码")
            return

        if not code.isdigit() or len(code) != 6:
            self._show_error("基金代码必须是6位数字")
            return

        # 验证是否已查询
        if not self._fund_name:
            self._show_error("请先查询基金信息（按 Enter 键）")
            return

        # 检测是否重复添加
        watchlist = self.app.config_dao.get_watchlist()
        existing_codes = [f.code for f in watchlist]
        if code in existing_codes:
            self._show_error(f"基金 {code} 已在自选列表中")
            return

        # 添加基金（默认标记为持有）
        self.app.config_dao.add_fund(
            code, self._fund_name, watchlist=True, is_hold=True
        )
        self.app.page.run_task(self.app._load_fund_data)

        self.open = False
        self.app.page.update()
        self.app._show_snackbar(f"✓ 已添加基金: {self._fund_name}")


class HoldingDialog(AlertDialog):
    """持仓设置对话框"""

    def __init__(self, app: FundGUIApp, fund: FundDisplayData):
        super().__init__()
        self.app = app
        self.fund = fund

        self.shares_field = TextField(
            label="持有份额",
            value=str(fund.hold_shares) if fund.hold_shares > 0 else "",
            hint_text="例如: 1000.00",
            width=200,
        )
        self.cost_field = TextField(
            label="成本价",
            value=str(fund.cost) if fund.cost > 0 else "",
            hint_text="例如: 1.2345",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        self.modal = True
        self.title = Text(f"设置持仓 - {fund.name}")
        self.content = Container(
            content=Column(
                [
                    Text(f"基金代码: {fund.code}", size=12, color=ft.Colors.WHITE70),
                    Row([self.shares_field, self.cost_field], spacing=10),
                    Text("成本价用于计算持仓盈亏", size=11, color=ft.Colors.WHITE70),
                ],
                spacing=10,
            ),
            width=400,
        )
        self.actions = [
            ElevatedButton("取消", on_click=self._cancel),
            ElevatedButton("保存", on_click=self._confirm),
        ]

    def _cancel(self, e):
        self.open = False
        self.app.page.update()

    def _confirm(self, e):
        shares_str = self.shares_field.value.strip()
        cost_str = self.cost_field.value.strip()

        try:
            shares = float(shares_str) if shares_str else 0.0
            cost = float(cost_str) if cost_str else 0.0

            # 更新持仓配置
            self.app.config_dao.update_fund(
                self.fund.code,
                shares=shares,
                cost=cost,
            )

            # 重新加载基金数据
            asyncio.create_task(self.app._load_fund_data())

            self.open = False
            self.app.page.update()
            self.app._show_snackbar(f"已保存持仓: {self.fund.name}")

        except ValueError:
            self.app._show_snackbar("请输入有效的数字")


class DeleteConfirmDialog(AlertDialog):
    """删除基金确认对话框"""

    def __init__(self, app: FundGUIApp, fund_code: str, fund_name: str):
        super().__init__()
        self.app = app
        self.fund_code = fund_code
        self.fund_name = fund_name

        self.modal = True
        self.title = Text("确认删除")
        self.content = Container(
            content=Column(
                [
                    Text(f"确定要从自选列表中删除以下基金吗？", size=14),
                    Text(
                        f"{fund_name} ({fund_code})",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ORANGE,
                    ),
                    Text("此操作不可撤销", size=11, color=ft.Colors.RED),
                ],
                spacing=10,
            ),
            width=400,
        )
        self.actions = [
            ElevatedButton("取消", on_click=self._cancel),
            ElevatedButton(
                "删除",
                on_click=self._confirm,
                style=ft.ButtonStyle(bgcolor=ft.Colors.RED),
            ),
        ]

    def _cancel(self, e):
        self.open = False
        self.app.page.update()

    def _confirm(self, e):
        # 从配置中删除
        self.app.config_dao.remove_fund(self.fund_code)
        # 清空选中状态
        if hasattr(self.app, "_selected_fund_code"):
            self.app._selected_fund_code = None
        if hasattr(self.app, "_selected_funds"):
            self.app._selected_funds.discard(self.fund_code)
        # 重新加载基金数据
        self.app.page.run_task(self.app._load_fund_data)

        self.open = False
        self.app.page.update()
        self.app._show_snackbar(f"已删除基金: {self.fund_name}")


# 常用板块列表（可扩展）
SECTOR_OPTIONS = [
    "消费",
    "医疗",
    "科技",
    "新能源",
    "半导体",
    "金融",
    "地产",
    "军工",
    "农业",
    "传媒",
    "基建",
    "周期",
    "港股",
    "美股",
    "黄金",
    "油气",
    "其他",
]


class SetSectorDialog(AlertDialog):
    """设置基金板块标注对话框"""

    def __init__(
        self, app: FundGUIApp, fund_code: str, fund_name: str, current_sector: str = ""
    ):
        super().__init__()
        self.app = app
        self.fund_code = fund_code
        self.fund_name = fund_name

        # 板块选择下拉框
        self.sector_dropdown = ft.Dropdown(
            label="选择板块",
            width=250,
            options=[ft.dropdown.Option(sector) for sector in SECTOR_OPTIONS],
            value=current_sector if current_sector else None,
        )

        # 自定义板块输入
        self.custom_sector_field = TextField(
            label="或输入自定义板块",
            hint_text="例如: 元宇宙、创新药",
            width=250,
            visible=current_sector and current_sector not in SECTOR_OPTIONS,
        )

        if current_sector and current_sector not in SECTOR_OPTIONS:
            self.custom_sector_field.value = current_sector

        self.modal = True
        self.title = Text("设置板块标注")
        self.content = Container(
            content=Column(
                [
                    Text(f"基金: {fund_name}", size=12, color=ft.Colors.WHITE70),
                    Text(f"代码: {fund_code}", size=12, color=ft.Colors.WHITE70),
                    Divider(),
                    Text(
                        "选择或输入板块标签，便于分类管理",
                        size=11,
                        color=ft.Colors.WHITE54,
                    ),
                    Row([self.sector_dropdown, self.custom_sector_field], spacing=10),
                ],
                spacing=12,
            ),
            width=450,
        )
        self.actions = [
            ElevatedButton("清除标注", on_click=self._clear),
            ElevatedButton("取消", on_click=self._cancel),
            ElevatedButton("保存", on_click=self._confirm),
        ]

    def _cancel(self, e):
        self.open = False
        self.app.page.update()

    def _clear(self, e):
        """清除板块标注"""
        self.app.config_dao.update_fund(self.fund_code, sector="")
        self.app.page.run_task(self.app._load_fund_data)
        self.open = False
        self.app.page.update()
        self.app._show_snackbar(f"已清除 {self.fund_name} 的板块标注")

    def _confirm(self, e):
        """保存板块标注"""
        # 获取选择的板块
        sector = (
            self.custom_sector_field.value.strip()
            if self.custom_sector_field.value.strip()
            else self.sector_dropdown.value
        )

        if not sector:
            self.app._show_snackbar("请选择或输入板块")
            return

        # 更新配置
        self.app.config_dao.update_fund(self.fund_code, sector=sector)

        # 重新加载数据
        self.app.page.run_task(self.app._load_fund_data)

        self.open = False
        self.app.page.update()
        self.app._show_snackbar(f"已设置 {self.fund_name} 的板块为: {sector}")


class SetHoldDialog(AlertDialog):
    """设置持有标记对话框"""

    def __init__(
        self,
        app: FundGUIApp,
        fund_code: str,
        fund_name: str,
        current_is_hold: bool = False,
    ):
        super().__init__()
        self.app = app
        self.fund_code = fund_code
        self.fund_name = fund_name

        # 持有状态开关
        self.hold_switch = ft.Switch(
            label="标记为持有",
            value=current_is_hold,
            active_color=ft.Colors.GREEN,
        )

        self.modal = True
        self.title = Row(
            [
                Text("持有标记", weight=ft.FontWeight.BOLD),
                Container(expand=True),
                Icon(
                    Icons.STAR,
                    color=ft.Colors.AMBER if current_is_hold else ft.Colors.GREY,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        )
        self.content = Container(
            content=Column(
                [
                    Text(f"基金: {fund_name}", size=12, color=ft.Colors.WHITE70),
                    Text(f"代码: {fund_code}", size=12, color=ft.Colors.WHITE70),
                    Divider(),
                    Text(
                        "持有标记用于标识您重点关注的基金",
                        size=11,
                        color=ft.Colors.WHITE54,
                    ),
                    Row([self.hold_switch], spacing=10),
                ],
                spacing=12,
            ),
            width=400,
        )
        self.actions = [
            ElevatedButton("取消", on_click=self._cancel),
            ElevatedButton("保存", on_click=self._confirm),
        ]

    def _cancel(self, e):
        self.open = False
        self.app.page.update()

    def _confirm(self, e):
        """保存持有标记"""
        is_hold = self.hold_switch.value

        # 更新配置
        self.app.config_dao.toggle_hold(self.fund_code, is_hold)

        # 重新加载数据
        self.app.page.run_task(self.app._load_fund_data)

        self.open = False
        self.app.page.update()

        status = "持有" if is_hold else "不持有"
        self.app._show_snackbar(f"{self.fund_name} 已标记为 {status}")


def main():
    """主入口"""

    def _main(page: ft.Page):
        app = FundGUIApp()
        app.run(page)

    ft.app(target=_main)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
