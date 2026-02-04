# -*- coding: UTF-8 -*-
"""Flet GUI 主应用

基金实时估值图形化界面，基于 Flet 0.28.3 框架开发。
"""

import flet as ft
from flet import (
    Column,
    Row,
    Container,
    Text,
    DataTable,
    DataColumn,
    DataRow,
    DataCell,
    ElevatedButton,
    TextField,
    ProgressRing,
    Divider,
    AlertDialog,
    SnackBar,
    Card,
    Tabs as FletTabs,
    Tab as FletTab,
    margin,
    Icon,
    Icons,
)
from typing import List, Optional
from dataclasses import dataclass
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
        """构建 UI"""
        # 顶部标题
        header = Container(
            content=Row(
                [
                    Text(
                        "基金实时估值",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE,
                    ),
                    Container(expand=True),
                    ElevatedButton(
                        "刷新", icon=Icons.REFRESH, on_click=self._on_refresh
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=15,
            bgcolor=ft.Colors.BLUE_900,
        )

        # 标签页
        self.tabs = FletTabs(
            selected_index=0,
            animation_duration=300,
            on_change=self._on_tab_change,
            tabs=[
                FletTab(
                    text="📊 基金",
                    icon=Icons.ACCOUNT_BALANCE,
                    content=self._build_fund_page(),
                ),
                FletTab(
                    text="📈 商品",
                    icon=Icons.TRENDING_UP,
                    content=self._build_commodity_page(),
                ),
                FletTab(
                    text="📰 新闻",
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
                    Text("等待更新...", size=12, color=ft.Colors.WHITE70),
                    Container(expand=True),
                    Text("数据源: 新浪财经", size=12, color=ft.Colors.WHITE70),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=10,
            bgcolor=ft.Colors.SURFACE,
        )

        self.page.add(header)
        self.page.add(self.tabs)
        self.page.add(self.status_bar)

        # 加载初始数据
        asyncio.create_task(self._load_fund_data())

    def _build_fund_page(self) -> Container:
        """构建基金页面"""
        # 基金表格
        self.fund_table = DataTable(
            columns=[
                DataColumn(Text("代码"), width=100),
                DataColumn(Text("名称"), width=250),
                DataColumn(Text("单位净值"), width=100),
                DataColumn(Text("估算净值"), width=100),
                DataColumn(Text("涨跌幅"), width=100),
                DataColumn(Text("持仓盈亏"), width=120),
            ],
            rows=[],
            heading_row_color=ft.Colors.BLUE_900,
            heading_row_height=40,
            data_row_min_height=40,
            column_spacing=10,
        )

        # 操作按钮
        action_row = Row(
            [
                ElevatedButton("添加", icon=Icons.ADD, on_click=self._show_add_fund),
                ElevatedButton("持仓", icon=Icons.EDIT, on_click=self._show_holding),
                ElevatedButton("删除", icon=Icons.DELETE, on_click=self._delete_fund),
            ],
            spacing=10,
        )

        return Container(
            content=Column(
                [
                    action_row,
                    self.fund_table,
                ],
                spacing=10,
                expand=True,
            ),
            padding=10,
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
                        )
                        self.funds.append(fund_data)
                except Exception as ex:
                    print(f"获取基金 {fund.code} 数据失败: {ex}")

            self._update_fund_table()
            now = datetime.now().strftime("%H:%M:%S")
            self.status_bar.content.controls[0].value = f"最后更新: {now}"

        except Exception as e:
            self._show_snackbar(f"加载失败: {str(e)}")

    def _update_fund_table(self):
        """更新基金表格"""
        self.fund_table.rows = []

        for fund in self.funds:
            change_color = ft.Colors.GREEN if fund.change_pct >= 0 else ft.Colors.RED
            profit_color = ft.Colors.GREEN if fund.profit >= 0 else ft.Colors.RED

            row = DataRow(
                cells=[
                    DataCell(Text(fund.code, width=95)),
                    DataCell(
                        Text(
                            fund.name,
                            width=245,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        )
                    ),
                    DataCell(Text(f"{fund.net_value:.4f}", width=95)),
                    DataCell(Text(f"{fund.est_value:.4f}", width=95)),
                    DataCell(
                        Text(
                            f"{fund.change_pct:+.2f}%",
                            color=change_color,
                            weight=ft.FontWeight.BOLD,
                            width=95,
                        )
                    ),
                    DataCell(
                        Text(
                            f"{fund.profit:+.2f}",
                            color=profit_color,
                            weight=ft.FontWeight.BOLD,
                            width=115,
                        )
                    ),
                ],
                data=fund.code,
            )
            self.fund_table.rows.append(row)

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

    def _get_selected_fund_code(self) -> Optional[str]:
        """获取当前选中的基金代码"""
        # 检查是否有选中行
        if hasattr(self, "_selected_fund_code") and self._selected_fund_code:
            return self._selected_fund_code
        return None

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
            asyncio.create_task(self._load_fund_data())
        elif self.current_tab == 1:
            asyncio.create_task(self._load_commodity_data())
        elif self.current_tab == 2:
            asyncio.create_task(self._load_news_data())


class AddFundDialog(AlertDialog):
    """添加基金对话框"""

    def __init__(self, app: FundGUIApp):
        super().__init__()
        self.app = app

        self.code_field = TextField(
            label="基金代码", hint_text="例如: 161039", width=200
        )
        self.name_field = TextField(
            label="基金名称", hint_text="例如: 富国中证新能源汽车", expand=True
        )

        self.modal = True
        self.title = Text("添加基金")
        self.content = Container(
            content=Row([self.code_field, self.name_field], spacing=8),
            width=400,
        )
        self.actions = [
            ElevatedButton("取消", on_click=self._cancel),
            ElevatedButton("添加", on_click=self._confirm),
        ]

    def _cancel(self, e):
        self.open = False
        self.app.page.update()

    def _confirm(self, e):
        code = self.code_field.value.strip()
        name = self.name_field.value.strip()

        if not code or not name:
            self.app._show_snackbar("请填写完整信息")
            return

        self.app.config_dao.add_fund(code, name, watchlist=True)
        asyncio.create_task(self.app._load_fund_data())

        self.open = False
        self.app.page.update()
        self.app._show_snackbar(f"已添加基金: {name}")


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
        # 重新加载基金数据
        asyncio.create_task(self.app._load_fund_data())

        self.open = False
        self.app.page.update()
        self.app._show_snackbar(f"已删除基金: {self.fund_name}")


def main():
    """主入口"""

    def _main(page: ft.Page):
        app = FundGUIApp()
        app.run(page)

    ft.app(target=_main)


if __name__ == "__main__":
    main()
