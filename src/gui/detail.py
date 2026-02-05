# -*- coding: UTF-8 -*-
"""基金详情模块

提供基金详情展示功能，包括基本信息和统计。
"""

from dataclasses import dataclass

import flet as ft
from flet import (
    AlertDialog,
    Card,
    Column,
    Container,
    Divider,
    ElevatedButton,
    Icons,
    Row,
    Text,
)


@dataclass
class FundDetailData:
    """基金详情数据"""

    code: str
    name: str
    net_value: float
    est_value: float
    change_pct: float
    profit: float
    hold_shares: float
    cost: float
    update_time: str = ""


class FundDetailDialog(AlertDialog):
    """基金详情对话框"""

    def __init__(self, app, fund_data):
        super().__init__()
        self.app = app
        self.fund_code = fund_data.code
        self.fund_name = fund_data.name
        self.fund = fund_data

        # 计算统计数据
        self.profit_rate = self._get_profit_rate()
        self.total_value = self._get_total_value()
        self.cost_basis = self._get_cost_basis()

        # 设置对话框
        self.modal = True
        self.title = Text(f"基金详情 - {fund_data.name}")
        self.content = self._build_content()
        self.actions = [
            ElevatedButton("持仓设置", icon=Icons.EDIT, on_click=self._edit_holding),
            ElevatedButton(
                "查看图表", icon=Icons.SHOW_CHART, on_click=self._show_chart
            ),
            ElevatedButton("关闭", on_click=self._close),
        ]
        self.actions_alignment = ft.MainAxisAlignment.END

    def _get_profit_rate(self) -> float:
        """计算收益率"""
        if self.fund.cost > 0:
            return ((self.fund.net_value - self.fund.cost) / self.fund.cost) * 100
        return 0.0

    def _get_total_value(self) -> float:
        """计算总市值"""
        return self.fund.net_value * self.fund.hold_shares

    def _get_cost_basis(self) -> float:
        """计算成本总额"""
        return self.fund.cost * self.fund.hold_shares

    def _build_content(self) -> Container:
        """构建详情内容"""
        return Container(
            content=Column(
                [
                    # 基本信息卡片
                    self._build_basic_info_card(),
                    Divider(),
                    # 估值信息卡片
                    self._build_valuation_card(),
                    Divider(),
                    # 持仓信息卡片
                    self._build_holding_card(),
                    Divider(),
                    # 统计信息卡片
                    self._build_stats_card(),
                ],
                spacing=10,
            ),
            width=500,
        )

    def _build_basic_info_card(self) -> Card:
        """构建基本信息卡片"""
        return Card(
            content=Container(
                content=Column(
                    [
                        Text("基本信息", size=16, weight=ft.FontWeight.BOLD),
                        self._build_info_row("基金代码:", self.fund_code),
                        self._build_info_row("基金名称:", self.fund.name),
                    ],
                    spacing=8,
                ),
                padding=15,
            )
        )

    def _build_valuation_card(self) -> Card:
        """构建估值信息卡片"""
        change_color = ft.Colors.GREEN if self.fund.change_pct >= 0 else ft.Colors.RED
        return Card(
            content=Container(
                content=Column(
                    [
                        Text("估值信息", size=16, weight=ft.FontWeight.BOLD),
                        Row(
                            [
                                Column(
                                    [
                                        Text(
                                            "单位净值", size=12, color=ft.Colors.WHITE70
                                        ),
                                        Text(
                                            f"{self.fund.net_value:.4f}",
                                            size=20,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                    ],
                                    expand=1,
                                ),
                                Column(
                                    [
                                        Text(
                                            "估算净值", size=12, color=ft.Colors.WHITE70
                                        ),
                                        Text(
                                            f"{self.fund.est_value:.4f}",
                                            size=20,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                    ],
                                    expand=1,
                                ),
                            ]
                        ),
                        Row(
                            [
                                Text("估算涨跌:", size=12, color=ft.Colors.WHITE70),
                                Text(
                                    f"{self.fund.change_pct:+.2f}%",
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color=change_color,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                    ],
                    spacing=10,
                ),
                padding=15,
            )
        )

    def _build_holding_card(self) -> Card:
        """构建持仓信息卡片"""
        has_holding = self.fund.hold_shares > 0

        if has_holding:
            return Card(
                content=Container(
                    content=Column(
                        [
                            Text("持仓信息", size=16, weight=ft.FontWeight.BOLD),
                            Row(
                                [
                                    Column(
                                        [
                                            Text(
                                                "持有份额",
                                                size=12,
                                                color=ft.Colors.WHITE70,
                                            ),
                                            Text(
                                                f"{self.fund.hold_shares:,.2f}",
                                                size=18,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                        ],
                                        expand=1,
                                    ),
                                    Column(
                                        [
                                            Text(
                                                "成本价",
                                                size=12,
                                                color=ft.Colors.WHITE70,
                                            ),
                                            Text(
                                                f"{self.fund.cost:.4f}",
                                                size=18,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                        ],
                                        expand=1,
                                    ),
                                ]
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=15,
                )
            )
        else:
            return Card(
                content=Container(
                    content=Column(
                        [
                            Text("持仓信息", size=16, weight=ft.FontWeight.BOLD),
                            Text(
                                "暂未设置持仓，点击上方按钮添加",
                                size=12,
                                color=ft.Colors.WHITE70,
                            ),
                        ],
                        spacing=8,
                    ),
                    padding=15,
                )
            )

    def _build_stats_card(self) -> Card:
        """构建统计信息卡片"""
        profit_color = ft.Colors.GREEN if self.fund.profit >= 0 else ft.Colors.RED
        rate_color = ft.Colors.GREEN if self.profit_rate >= 0 else ft.Colors.RED

        return Card(
            content=Container(
                content=Column(
                    [
                        Text("收益统计", size=16, weight=ft.FontWeight.BOLD),
                        Row(
                            [
                                Column(
                                    [
                                        Text(
                                            "持仓盈亏", size=12, color=ft.Colors.WHITE70
                                        ),
                                        Text(
                                            f"{self.fund.profit:+,.2f}",
                                            size=18,
                                            weight=ft.FontWeight.BOLD,
                                            color=profit_color,
                                        ),
                                    ],
                                    expand=1,
                                ),
                                Column(
                                    [
                                        Text(
                                            "收益率", size=12, color=ft.Colors.WHITE70
                                        ),
                                        Text(
                                            f"{self.profit_rate:+.2f}%",
                                            size=18,
                                            weight=ft.FontWeight.BOLD,
                                            color=rate_color,
                                        ),
                                    ],
                                    expand=1,
                                ),
                            ]
                        ),
                        Row(
                            [
                                Text("总市值:", size=12, color=ft.Colors.WHITE70),
                                Text(f"{self.total_value:,.2f}", size=14),
                                Container(expand=True),
                                Text("成本:", size=12, color=ft.Colors.WHITE70),
                                Text(f"{self.cost_basis:,.2f}", size=14),
                            ]
                        ),
                    ],
                    spacing=10,
                ),
                padding=15,
            )
        )

    def _build_info_row(self, label: str, value: str) -> Row:
        """构建信息行"""
        return Row(
            [
                Text(label, size=13, color=ft.Colors.WHITE70),
                Text(value, size=14, weight=ft.FontWeight.BOLD),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

    def _edit_holding(self, e):
        """编辑持仓"""
        # 打开持仓设置对话框
        if hasattr(self.app, "_show_holding"):
            self.open = False
            self.app.page.update()
            self.app._show_holding(None)

    def _show_chart(self, e):
        """显示图表"""
        # 打开图表对话框
        if hasattr(self.app, "_show_fund_chart"):
            self.open = False
            self.app.page.update()
            self.app._show_fund_chart(self.fund_code, self.fund_name)

    def _close(self, e):
        """关闭对话框"""
        self.open = False
        self.app.page.update()
