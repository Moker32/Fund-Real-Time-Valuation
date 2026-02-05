# -*- coding: UTF-8 -*-
"""GUI Components for Fund Real-Time Valuation"""

from collections.abc import Callable

import flet as ft
from flet import (
    Alignment,
    BorderRadius,
    Card,
    Column,
    Container,
    CrossAxisAlignment,
    FontWeight,
    Icon,
    Icons,
    MainAxisAlignment,
    ProgressRing,
    Row,
    Text,
)


class AppColors:
    """Application color scheme"""

    # 基础背景色
    BACKGROUND_DARK = "#000000"  # 纯黑背景
    TAB_BG = "#1E1E1E"  # Tab 背景色（深灰色）
    CARD_DARK = "#2D2D2D"  # 卡片背景色（稍亮的灰色，与Tab背景形成对比）
    CARD_HOVER = "#3D3D3D"
    TEXT_PRIMARY = "#FFFFFF"  # 白色主文字
    TEXT_SECONDARY = "#B0B0B0"  # 亮灰色次要文字，提高对比度
    UP_RED = "#FF3B30"  # 红色
    DOWN_GREEN = "#34C759"  # 绿色
    NEUTRAL = "#8E8E93"  # 中性色
    ACCENT_BLUE = "#007AFF"  # 蓝色
    ACCENT_ORANGE = "#FF9500"  # 橙色
    DIVIDER = "#3A3A3C"  # 分割线颜色


def get_change_color(value: float) -> str:
    """Get up/down color based on value"""
    if value > 0:
        return AppColors.UP_RED
    elif value < 0:
        return AppColors.DOWN_GREEN
    return AppColors.NEUTRAL


def format_number(value: float, decimals: int = 2) -> str:
    """Format number with thousands separator"""
    if abs(value) >= 10000:
        return f"{value / 10000:.2f}wan"
    elif abs(value) >= 1000:
        return f"{value:,.{decimals}f}"
    return f"{value:,.{decimals}f}"


def format_currency(value: float, prefix: str = "¥") -> str:
    """Format currency amount"""
    return f"{prefix}{value:,.2f}"


class MiniChart(Container):
    """Mini trend chart component"""

    def __init__(
        self,
        data: list[float],
        is_up: bool | None = None,
        width: int = 80,
        height: int = 32,
    ):
        self.chart_data = data or [0]

        super().__init__(
            width=width,
            height=height,
        )

        if len(self.chart_data) >= 2:
            is_up = self.chart_data[-1] >= self.chart_data[0]
        else:
            is_up = True

        self.is_up = is_up
        self.chart_color = AppColors.UP_RED if is_up else AppColors.DOWN_GREEN

        change = 0
        if len(self.chart_data) >= 2:
            change = ((self.chart_data[-1] - self.chart_data[0]) / self.chart_data[0]) * 100

        arrow = "up" if change >= 0 else "down"

        self.content = Row(
            controls=[
                Text(arrow, size=16, color=self.chart_color),
                Container(
                    width=50,
                    height=8,
                    bgcolor=f"{self.chart_color}40",  # 25% opacity hex
                ),
            ],
            spacing=2,
            vertical_alignment=CrossAxisAlignment.CENTER,
        )

    def update_data(self, data: list[float], is_up: bool | None = None):
        """Update chart data"""
        self.chart_data = data or [0]

        if len(self.chart_data) >= 2:
            is_up = self.chart_data[-1] >= self.chart_data[0]
        else:
            is_up = True

        self.chart_color = AppColors.UP_RED if is_up else AppColors.DOWN_GREEN
        self.is_up = is_up

        change = 0
        if len(self.chart_data) >= 2:
            change = ((self.chart_data[-1] - self.chart_data[0]) / self.chart_data[0]) * 100

        arrow = "up" if change >= 0 else "down"

        self.content.controls[0].value = arrow
        self.content.controls[0].color = self.chart_color
        self.content.controls[1].bgcolor = f"{self.chart_color}40"

        self.update()


class FundCard(Card):
    """Fund card component (Alipay/Apple Stocks style)"""

    def __init__(
        self,
        code: str,
        name: str,
        net_value: float,
        est_value: float,
        change_pct: float,
        profit: float,
        hold_shares: float = 0,
        cost: float = 0,
        sector: str = "",
        is_hold: bool = False,
        chart_data: list[float] | None = None,
        on_click: Callable | None = None,
    ):
        self.code = code
        self.name = name
        self.net_value = net_value
        self.est_value = est_value
        self.change_pct = change_pct
        self.profit = profit
        self.hold_shares = hold_shares
        self.cost = cost
        self.sector = sector
        self.is_hold = is_hold
        self.chart_data = chart_data or [net_value] * 10

        # Calculate profit rate
        if self.cost > 0:
            self.profit_rate = (net_value - self.cost) / self.cost * 100
        else:
            self.profit_rate = 0

        # Change colors
        self.change_color = get_change_color(change_pct)
        self.profit_color = get_change_color(profit)
        self.rate_color = get_change_color(self.profit_rate)

        # Change icon
        self.change_icon = Icons.ARROW_DROP_UP if change_pct >= 0 else Icons.ARROW_DROP_DOWN

        # Loading state
        self._loading = False
        self._loading_progress_ring = None

        # Mini chart
        self.mini_chart = MiniChart(
            self.chart_data,
            is_up=change_pct >= 0,
            width=80,
            height=32,
        )

        # Build content
        content = self._build_content()

        # Tooltips
        tooltip_text = f"{name}\ncode: {code}\nnet_value: {net_value:.4f}\nest_value: {est_value:.4f}\nchange: {change_pct:+.2f}%"
        if hold_shares > 0:
            tooltip_text += (
                f"\nholdings: {hold_shares:.2f}\ncost: {cost:.4f}\nprofit: {profit:+.2f}"
            )

        # Create loading progress ring
        self.progress_ring = ProgressRing(
            width=40,
            height=40,
            stroke_width=3,
            color=AppColors.ACCENT_BLUE,
            visible=False,
        )

        # Loading overlay container
        self._loading_overlay = Container(
            content=self.progress_ring,
            alignment=Alignment(0.5, 0.5),
            visible=False,
            bgcolor=f"{AppColors.BACKGROUND_DARK}E6",  # 90% opacity
            border_radius=BorderRadius(top_left=12, top_right=12, bottom_left=12, bottom_right=12),
        )

        # Card 组件使用 Container 设置背景色和圆角
        card_content = Container(
            bgcolor=AppColors.CARD_DARK,
            border_radius=BorderRadius(top_left=12, top_right=12, bottom_left=12, bottom_right=12),
            padding=12,
            content=content,
        )

        # Stack: card content + loading overlay
        self._card_stack = ft.Stack(
            controls=[card_content, self._loading_overlay],
            expand=True,
        )

        super().__init__(
            elevation=2,
            tooltip=tooltip_text,
            content=self._card_stack,
            margin=0,
        )

        # 添加点击事件到 Card 的内容
        if on_click:
            self.content.on_click = on_click
            self.content.ink = True

    def _build_content(self) -> Column:
        """Build card content"""
        # Header: fund name + mini chart
        header = Row(
            controls=[
                Column(
                    controls=[
                        Text(
                            self.name,
                            size=18,
                            weight=FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                        Row(
                            controls=[
                                Text(
                                    self.code,
                                    size=13,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                                Text(
                                    f"  {self.sector}" if self.sector else "",
                                    size=13,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                                Container(width=8),
                                Text(
                                    "[HOLD]" if self.is_hold else "",
                                    size=11,
                                    color=AppColors.UP_RED,
                                    weight=FontWeight.BOLD,
                                )
                                if self.is_hold
                                else Container(),
                            ],
                            spacing=4,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                self.mini_chart,
            ],
            alignment=MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=CrossAxisAlignment.CENTER,
        )

        # Price row: net value + est value
        price_row = Row(
            controls=[
                Column(
                    controls=[
                        Text(
                            "Net Value",
                            size=11,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        Text(
                            f"{self.net_value:.4f}",
                            size=20,
                            weight=FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                            font_family="monospace",
                        ),
                    ],
                    spacing=2,
                ),
                Container(expand=True),
                Column(
                    controls=[
                        Text(
                            "Est Value",
                            size=11,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        Text(
                            f"{self.est_value:.4f}",
                            size=18,
                            weight=FontWeight.W_500,
                            color=AppColors.TEXT_PRIMARY,
                            font_family="monospace",
                        ),
                    ],
                    spacing=2,
                    horizontal_alignment=CrossAxisAlignment.END,
                ),
            ],
            alignment=MainAxisAlignment.SPACE_BETWEEN,
        )

        # Change + profit row
        change_row = Row(
            controls=[
                Container(
                    padding=8,
                    border_radius=BorderRadius(
                        top_left=8, top_right=8, bottom_left=8, bottom_right=8
                    ),
                    bgcolor=f"{self.change_color}40",  # 25% opacity hex
                    content=Row(
                        controls=[
                            Icon(
                                self.change_icon,
                                color=self.change_color,
                                size=20,
                            ),
                            Text(
                                f"{self.change_pct:+.2f}%",
                                color=self.change_color,
                                weight=FontWeight.BOLD,
                            ),
                        ],
                        spacing=0,
                        vertical_alignment=CrossAxisAlignment.CENTER,
                    ),
                ),
                Container(width=16),
                Column(
                    controls=[
                        Text(
                            f"{self.profit:+.2f}",
                            size=14,
                            weight=FontWeight.BOLD,
                            color=self.profit_color,
                        ),
                        Text(
                            f"({self.profit_rate:+.2f}%)",
                            size=11,
                            color=self.profit_color,
                        )
                        if self.hold_shares > 0
                        else Container(),
                    ],
                    spacing=0,
                    horizontal_alignment=CrossAxisAlignment.START,
                )
                if self.hold_shares > 0
                else Container(),
            ],
            alignment=MainAxisAlignment.START,
        )

        return Column(
            controls=[
                header,
                Container(height=12),
                price_row,
                Container(height=8) if self.hold_shares > 0 else Container(height=4),
                change_row if self.hold_shares > 0 else Container(),
            ],
            spacing=0,
        )

    @property
    def loading(self) -> bool:
        """Get loading state"""
        return self._loading

    @loading.setter
    def loading(self, value: bool):
        """Set loading state"""
        self._loading = value
        self._update_loading_state()

    def _update_loading_state(self):
        """Update loading UI state"""
        if self._loading_overlay:
            self._loading_overlay.visible = self._loading
        if self.progress_ring:
            self.progress_ring.visible = self._loading
        # Only update if card is added to page
        try:
            if hasattr(self, '_card_stack') and self._card_stack:
                self._card_stack.update()
        except RuntimeError:
            # Card not added to page yet, skip update
            pass

    def set_loading(self, value: bool):
        """Set loading state"""
        self.loading = value

    def toggle_loading(self):
        """Toggle loading state"""
        self.loading = not self._loading

    def update_data(
        self,
        net_value: float,
        est_value: float,
        change_pct: float,
        profit: float,
        chart_data: list[float] | None = None,
    ):
        """Update card data - replace content"""
        self.net_value = net_value
        self.est_value = est_value
        self.change_pct = change_pct
        self.profit = profit

        if self.cost > 0:
            self.profit_rate = (net_value - self.cost) / self.cost * 100
        else:
            self.profit_rate = 0

        self.change_color = get_change_color(change_pct)
        self.profit_color = get_change_color(profit)
        self.rate_color = get_change_color(self.profit_rate)
        self.change_icon = Icons.ARROW_DROP_UP if change_pct >= 0 else Icons.ARROW_DROP_DOWN

        if chart_data:
            self.chart_data = chart_data
            self.mini_chart.update_data(chart_data, is_up=change_pct >= 0)

        self.content = self._build_content()


class FundPortfolioCard(Card):
    """Portfolio overview card (Alipay style)"""

    def __init__(
        self,
        total_assets: float = 0,
        daily_profit: float = 0,
        total_profit: float = 0,
        profit_rate: float = 0,
        fund_count: int = 0,
        hold_count: int = 0,
    ):
        self.daily_color = get_change_color(daily_profit)
        self.total_color = get_change_color(total_profit)

        super().__init__(
            elevation=0,
            content=Container(
                bgcolor=AppColors.CARD_DARK,
                border_radius=BorderRadius(top_left=16, top_right=16, bottom_left=16, bottom_right=16),
                content=self._build_content(
                    total_assets,
                    daily_profit,
                    total_profit,
                    profit_rate,
                    fund_count,
                    hold_count,
                ),
                padding=16,
            ),
        )

    def _build_content(
        self,
        total_assets: float,
        daily_profit: float,
        total_profit: float,
        profit_rate: float,
        fund_count: int,
        hold_count: int,
    ) -> Column:
        # Title row
        title = Row(
            controls=[
                Text(
                    "Portfolio",
                    size=20,
                    weight=FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                Container(expand=True),
                Text(
                    f"{fund_count} funds  {hold_count} holdings",
                    size=13,
                    color=AppColors.TEXT_SECONDARY,
                ),
            ],
            alignment=MainAxisAlignment.SPACE_BETWEEN,
        )

        # Total assets
        total_assets_row = Column(
            controls=[
                Text(
                    "Total Assets",
                    size=13,
                    color=AppColors.TEXT_SECONDARY,
                ),
                Text(
                    format_currency(total_assets),
                    size=32,
                    weight=FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
            ],
            spacing=2,
        )

        # Stats row
        stats_row = Row(
            controls=[
                # Daily profit
                Column(
                    controls=[
                        Text(
                            "Daily Profit",
                            size=13,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        Row(
                            controls=[
                                Icon(
                                    Icons.ARROW_DROP_UP
                                    if daily_profit >= 0
                                    else Icons.ARROW_DROP_DOWN,
                                    color=self.daily_color,
                                    size=20,
                                ),
                                Text(
                                    format_currency(daily_profit),
                                    size=18,
                                    weight=FontWeight.BOLD,
                                    color=self.daily_color,
                                ),
                            ],
                            spacing=0,
                        ),
                    ],
                    spacing=2,
                ),
                Container(expand=True),
                # Total profit
                Column(
                    controls=[
                        Text(
                            "Total Profit",
                            size=13,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        Row(
                            controls=[
                                Icon(
                                    Icons.ARROW_DROP_UP
                                    if total_profit >= 0
                                    else Icons.ARROW_DROP_DOWN,
                                    color=self.total_color,
                                    size=20,
                                ),
                                Text(
                                    format_currency(total_profit),
                                    size=18,
                                    weight=FontWeight.BOLD,
                                    color=self.total_color,
                                ),
                                Text(
                                    f" ({profit_rate:+.2f}%)",
                                    size=13,
                                    color=self.total_color,
                                ),
                            ],
                            spacing=0,
                        ),
                    ],
                    spacing=2,
                    horizontal_alignment=CrossAxisAlignment.END,
                ),
            ],
            alignment=MainAxisAlignment.SPACE_BETWEEN,
        )

        return Column(
            controls=[
                title,
                Container(height=16),
                total_assets_row,
                Container(height=16),
                stats_row,
            ],
            spacing=0,
        )

    def update_data(
        self,
        total_assets: float,
        daily_profit: float,
        total_profit: float,
        profit_rate: float,
        fund_count: int,
        hold_count: int,
    ):
        """Update data"""
        self.daily_color = get_change_color(daily_profit)
        self.total_color = get_change_color(total_profit)

        self.content = self._build_content(
            total_assets,
            daily_profit,
            total_profit,
            profit_rate,
            fund_count,
            hold_count,
        )
        self.update()


class QuickActionButton(Column):
    """Quick action button"""

    def __init__(
        self,
        icon: str,
        label: str,
        on_click: callable,
        accent_color: str = AppColors.ACCENT_BLUE,
    ):
        self.accent_color = accent_color

        super().__init__(
            controls=[
                Container(
                    width=48,
                    height=48,
                    border_radius=BorderRadius(
                        top_left=24, top_right=24, bottom_left=24, bottom_right=24
                    ),
                    bgcolor="#FF950026",
                    content=Icon(
                        icon,
                        color=accent_color,
                        size=24,
                    ),
                    on_click=on_click,
                    ink=True,
                ),
                Text(
                    label,
                    size=12,
                    color=AppColors.TEXT_PRIMARY,
                    weight=FontWeight.NORMAL,
                ),
            ],
            horizontal_alignment=CrossAxisAlignment.CENTER,
            spacing=6,
        )


class SearchBar(Container):
    """Search bar component"""

    def __init__(self, on_search: callable = None, placeholder: str = "Search fund code/name"):
        self.on_search = on_search

        self.text_field = ft.TextField(
            hint_text=placeholder,
            filled=True,
            fill_color=AppColors.CARD_HOVER,
            border_radius=10,
            height=44,
            on_change=self._on_text_change,
            border=ft.InputBorder.NONE,
        )

        super().__init__(
            content=self.text_field,
            padding=16,
        )

    def _on_text_change(self, e):
        """Text change callback"""
        if self.on_search:
            self.on_search(e.control.value)

    def get_value(self) -> str:
        """Get search text"""
        return self.text_field.value or ""

    def clear(self):
        """Clear search"""
        self.text_field.value = ""
        self.text_field.update()
