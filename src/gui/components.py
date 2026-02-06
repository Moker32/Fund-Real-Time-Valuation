# -*- coding: UTF-8 -*-
"""GUI Components for Fund Real-Time Valuation"""

from collections.abc import Callable
from typing import Optional
import logging

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

logger = logging.getLogger(__name__)


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


def with_opacity(opacity: float, color: str) -> str:
    """Apply opacity to a hex color using Flet's colors.with_opacity

    Args:
        opacity: Opacity value between 0 and 1 (e.g., 0.25 for 25%)
        color: Hex color string (e.g., "#FF3B30")

    Returns:
        Color with applied opacity
    """
    return ft.colors.with_opacity(opacity, color)


class MiniChart(Container):
    """Mini trend chart component"""

    def __init__(
        self,
        data: list[float],
        is_up: Optional[bool] = None,
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

        change: float = 0.0
        if len(self.chart_data) >= 2:
            change = ((self.chart_data[-1] - self.chart_data[0]) / self.chart_data[0]) * 100

        arrow = "up" if change >= 0 else "down"

        self.content = Row(
            controls=[
                Text(arrow, size=16, color=self.chart_color),
                Container(
                    width=50,
                    height=8,
                    bgcolor=with_opacity(0.25, self.chart_color),
                ),
            ],
            spacing=2,
            vertical_alignment=CrossAxisAlignment.CENTER,
        )

    def update_data(self, data: list[float], is_up: Optional[bool] = None):
        """Update chart data"""
        self.chart_data = data or [0]

        if len(self.chart_data) >= 2:
            is_up = self.chart_data[-1] >= self.chart_data[0]
        else:
            is_up = True

        self.chart_color = AppColors.UP_RED if is_up else AppColors.DOWN_GREEN
        self.is_up = is_up

        change: float = 0.0
        if len(self.chart_data) >= 2:
            change = ((self.chart_data[-1] - self.chart_data[0]) / self.chart_data[0]) * 100

        arrow = "up" if change >= 0 else "down"

        # 更新图表内容
        if self.content is not None and hasattr(self.content, "controls"):
            self.content.controls[0].value = arrow
            self.content.controls[0].color = self.chart_color
            self.content.controls[1].bgcolor = with_opacity(0.25, self.chart_color)

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
        chart_data: Optional[list[float]] = None,
        on_click: Optional[Callable] = None,
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
            bgcolor=with_opacity(0.9, AppColors.BACKGROUND_DARK),
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
        if on_click and self.content is not None:
            # self.content 是 _card_stack，它是 ft.Stack 类型
            self.content.on_click = on_click  # type: ignore
            self.content.ink = True  # type: ignore

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
                    bgcolor=with_opacity(0.25, self.change_color),
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

    def _update_values(self):
        """Update displayed values without rebuilding components"""
        # Get the card content container (it's a Stack, first control is Container)
        if not hasattr(self, '_card_stack'):
            return

        card_content = self._card_stack.controls[0]  # Container with bgcolor
        if not isinstance(card_content, Container):
            return

        inner_content = card_content.content  # Column
        if not isinstance(inner_content, Column):
            return

        # Column structure: [header (Row), height12, price_row (Row), height8/4, change_row (Row)]
        # Header -> Row -> controls[1] is mini_chart
        # Price row -> Row -> controls[0] Column (net value) -> controls[1] is net value Text
        # Price row -> Row -> controls[2] Column (est value) -> controls[1] is est value Text
        # Change row -> Row -> controls[0] Container -> Row -> controls[1] is change Text

        try:
            # Update net value text (header Row, Column controls[1], Text)
            header = inner_content.controls[0]
            if isinstance(header, Row):
                # Skip if header doesn't have the expected structure
                pass

            # Update price row texts
            price_row = inner_content.controls[2]
            if isinstance(price_row, Row):
                # Net value Column, second Text (the value)
                net_col = price_row.controls[0]
                if isinstance(net_col, Column) and len(net_col.controls) >= 2:
                    net_value_text = net_col.controls[1]
                    if isinstance(net_value_text, Text):
                        net_value_text.value = f"{self.net_value:.4f}"

                # Est value Column, second Text (the value)
                est_col = price_row.controls[2]
                if isinstance(est_col, Column) and len(est_col.controls) >= 2:
                    est_value_text = est_col.controls[1]
                    if isinstance(est_value_text, Text):
                        est_value_text.value = f"{self.est_value:.4f}"

            # Update change row (index 4 if exists, otherwise skip)
            if len(inner_content.controls) > 4:
                change_row = inner_content.controls[4]
                if isinstance(change_row, Row):
                    # Change indicator container
                    change_container = change_row.controls[0]
                    if isinstance(change_container, Container):
                        change_inner = change_container.content
                        if isinstance(change_inner, Row):
                            if len(change_inner.controls) >= 2:
                                change_text = change_inner.controls[1]
                                if isinstance(change_text, Text):
                                    change_text.value = f"{self.change_pct:+.2f}%"
                                    change_text.color = self.change_color

                                # Update icon color
                                change_icon = change_inner.controls[0]
                                if isinstance(change_icon, Icon):
                                    change_icon.color = self.change_color

                                # Update container bgcolor
                                change_container.bgcolor = with_opacity(0.25, self.change_color)

                            # Update the inner Row's bgcolor
                            change_inner.bgcolor = with_opacity(0.25, self.change_color)

                    # Profit column (index 2 if exists)
                    if len(change_row.controls) > 2:
                        profit_col = change_row.controls[2]
                        if isinstance(profit_col, Column):
                            if len(profit_col.controls) >= 1:
                                profit_text = profit_col.controls[0]
                                if isinstance(profit_text, Text):
                                    profit_text.value = f"{self.profit:+.2f}"
                                    profit_text.color = self.profit_color

                            if len(profit_col.controls) >= 2:
                                rate_text = profit_col.controls[1]
                                if isinstance(rate_text, Text):
                                    rate_text.value = f"({self.profit_rate:+.2f}%)"
                                    rate_text.color = self.profit_color

            # Update tooltip
            tooltip_text = f"{self.name}\ncode: {self.code}\nnet_value: {self.net_value:.4f}\nest_value: {self.est_value:.4f}\nchange: {self.change_pct:+.2f}%"
            if self.hold_shares > 0:
                tooltip_text += (
                    f"\nholdings: {self.hold_shares:.2f}\ncost: {self.cost:.4f}\nprofit: {self.profit:+.2f}"
                )
            self.tooltip = tooltip_text

        except (IndexError, AttributeError) as e:
            # If structure doesn't match expected, fall back to rebuild
            logger.debug(f"FundCard _update_values failed: {e}, falling back to rebuild")
            self.content = self._build_content()
            return

        self.update()

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
        chart_data: Optional[list[float]] = None,
    ):
        """Update card data - only modify values, don't rebuild components"""
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

        # Only update values without rebuilding components
        self._update_values()


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
        """Update data - only modify values, don't rebuild components"""
        self.daily_color = get_change_color(daily_profit)
        self.total_color = get_change_color(total_profit)

        # Only update values without rebuilding components
        self._update_values(
            total_assets, daily_profit, total_profit, profit_rate, fund_count, hold_count
        )

    def _update_values(
        self,
        total_assets: float,
        daily_profit: float,
        total_profit: float,
        profit_rate: float,
        fund_count: int,
        hold_count: int,
    ):
        """Update displayed values without rebuilding components"""
        # Structure: Card -> Container (bgcolor) -> Column -> [title, height16, assets, height16, stats]
        try:
            card_content = self.content
            if not isinstance(card_content, Container):
                self._fallback_update(
                    total_assets, daily_profit, total_profit, profit_rate, fund_count, hold_count
                )
                return

            inner_column = card_content.content
            if not isinstance(inner_column, Column):
                self._fallback_update(
                    total_assets, daily_profit, total_profit, profit_rate, fund_count, hold_count
                )
                return

            # Update title row (index 2 is the Text with counts)
            title_row = inner_column.controls[0]
            if isinstance(title_row, Row) and len(title_row.controls) >= 3:
                count_text = title_row.controls[2]
                if isinstance(count_text, Text):
                    count_text.value = f"{fund_count} funds  {hold_count} holdings"

            # Update total assets (index 2 is the Column with assets)
            assets_column = inner_column.controls[2]
            if isinstance(assets_column, Column) and len(assets_column.controls) >= 2:
                assets_text = assets_column.controls[1]
                if isinstance(assets_text, Text):
                    assets_text.value = format_currency(total_assets)

            # Update stats row (index 4 is the Row with stats)
            stats_row = inner_column.controls[4]
            if isinstance(stats_row, Row):
                # Daily profit section (controls[0] is Column)
                daily_col = stats_row.controls[0]
                if isinstance(daily_col, Column) and len(daily_col.controls) >= 2:
                    daily_row = daily_col.controls[1]
                    if isinstance(daily_row, Row):
                        # Icon
                        if len(daily_row.controls) >= 1:
                            daily_icon = daily_row.controls[0]
                            if isinstance(daily_icon, Icon):
                                daily_icon.icon = (
                                    Icons.ARROW_DROP_UP if daily_profit >= 0 else Icons.ARROW_DROP_DOWN
                                )
                                daily_icon.color = self.daily_color
                            # Text
                            if len(daily_row.controls) >= 2:
                                daily_text = daily_row.controls[1]
                                if isinstance(daily_text, Text):
                                    daily_text.value = format_currency(daily_profit)
                                    daily_text.color = self.daily_color

                # Total profit section (controls[2] is Column)
                total_col = stats_row.controls[2]
                if isinstance(total_col, Column) and len(total_col.controls) >= 2:
                    total_row = total_col.controls[1]
                    if isinstance(total_row, Row):
                        # Icon
                        if len(total_row.controls) >= 1:
                            total_icon = total_row.controls[0]
                            if isinstance(total_icon, Icon):
                                total_icon.icon = (
                                    Icons.ARROW_DROP_UP if total_profit >= 0 else Icons.ARROW_DROP_DOWN
                                )
                                total_icon.color = self.total_color
                            # Text
                            if len(total_row.controls) >= 2:
                                total_text = total_row.controls[1]
                                if isinstance(total_text, Text):
                                    total_text.value = format_currency(total_profit)
                                    total_text.color = self.total_color
                            # Rate text
                            if len(total_row.controls) >= 3:
                                rate_text = total_row.controls[2]
                                if isinstance(rate_text, Text):
                                    rate_text.value = f" ({profit_rate:+.2f}%)"
                                    rate_text.color = self.total_color

        except (IndexError, AttributeError) as e:
            logger.debug(f"FundPortfolioCard _update_values failed: {e}, falling back to rebuild")
            self._fallback_update(
                total_assets, daily_profit, total_profit, profit_rate, fund_count, hold_count
            )
            return

        self.update()

    def _fallback_update(
        self,
        total_assets: float,
        daily_profit: float,
        total_profit: float,
        profit_rate: float,
        fund_count: int,
        hold_count: int,
    ):
        """Fallback to rebuild content if structure doesn't match"""
        self.content.content = self._build_content(
            total_assets, daily_profit, total_profit, profit_rate, fund_count, hold_count
        )
        self.update()


class QuickActionButton(Column):
    """Quick action button"""

    def __init__(
        self,
        icon: Icons,
        label: str,
        on_click: Callable[..., None],
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
                        icon=icon,  # type: ignore
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

    def __init__(self, on_search: Optional[Callable[[str], None]] = None, placeholder: str = "Search fund code/name"):
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


class CommodityCard(Card):
    """Commodity card component for displaying commodity prices"""

    def __init__(
        self,
        symbol: str,
        name: str,
        price: float,
        currency: str = "CNY",
        change_percent: float = 0,
    ):
        self.symbol = symbol
        self.name = name
        self.price = price
        self.currency = currency
        self.change_percent = change_percent

        # Determine color based on change
        self.change_color = AppColors.UP_RED if change_percent >= 0 else AppColors.DOWN_GREEN

        # Build content
        super().__init__(
            elevation=0,
            margin=ft.padding.only(bottom=4),
            content=Container(
                bgcolor=AppColors.CARD_DARK,
                border_radius=BorderRadius(top_left=8, top_right=8, bottom_left=8, bottom_right=8),
                padding=12,
                content=self._build_content(),
            ),
        )

    def _build_content(self) -> Row:
        """Build card content"""
        return Row(
            controls=[
                Column(
                    controls=[
                        Text(
                            self.name,
                            size=14,
                            weight=FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                        Text(
                            f"{self.price} {self.currency}",
                            size=16,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                    ],
                    expand=True,
                ),
                Text(
                    f"{self.change_percent:+.2f}%",
                    color=self.change_color,
                    size=16,
                    weight=FontWeight.BOLD,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def update_data(
        self,
        price: float,
        currency: str = "CNY",
        change_percent: float = 0,
    ):
        """Update commodity data - only modify values, don't rebuild components"""
        self.price = price
        self.currency = currency
        self.change_percent = change_percent

        self.change_color = AppColors.UP_RED if change_percent >= 0 else AppColors.DOWN_GREEN

        # Update values directly
        self._update_values()

    def _update_values(self):
        """Update displayed values without rebuilding components"""
        try:
            container = self.content
            if not isinstance(container, Container):
                self._fallback_update()
                return

            row = container.content
            if not isinstance(row, Row):
                self._fallback_update()
                return

            # Price column (index 0)
            price_col = row.controls[0]
            if isinstance(price_col, Column) and len(price_col.controls) >= 2:
                price_text = price_col.controls[1]
                if isinstance(price_text, Text):
                    price_text.value = f"{self.price} {self.currency}"

            # Change percent (index 1)
            change_text = row.controls[1]
            if isinstance(change_text, Text):
                change_text.value = f"{self.change_percent:+.2f}%"
                change_text.color = self.change_color

        except (IndexError, AttributeError) as e:
            logger.debug(f"CommodityCard _update_values failed: {e}, falling back to rebuild")
            self._fallback_update()
            return

        self.update()

    def _fallback_update(self):
        """Fallback to rebuild content if structure doesn't match"""
        self.content.content = self._build_content()
        self.update()


class NewsCard(Card):
    """News card component for displaying news items"""

    def __init__(
        self,
        title: str,
        time: str = "",
        source: str = "未知",
    ):
        self.title = title
        self.time = time
        self.source = source

        super().__init__(
            elevation=0,
            margin=ft.padding.only(bottom=4),
            content=Container(
                bgcolor=AppColors.CARD_DARK,
                border_radius=BorderRadius(top_left=8, top_right=8, bottom_left=8, bottom_right=8),
                padding=12,
                content=self._build_content(),
            ),
        )

    def _build_content(self) -> Column:
        """Build card content"""
        return Column(
            controls=[
                Text(
                    self.title,
                    size=14,
                    max_lines=2,
                    color=AppColors.TEXT_PRIMARY,
                ),
                Row(
                    controls=[
                        Icon(
                            Icons.ACCESS_TIME,
                            size=12,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        Text(
                            self.time,
                            size=11,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                        Text(" - ", color=AppColors.TEXT_SECONDARY),
                        Text(
                            self.source,
                            size=11,
                            color=AppColors.ACCENT_BLUE,
                        ),
                    ],
                    spacing=4,
                ),
            ],
            spacing=4,
        )

    def update_data(
        self,
        title: str = None,
        time: str = None,
        source: str = None,
    ):
        """Update news data - only modify values, don't rebuild components"""
        if title is not None:
            self.title = title
        if time is not None:
            self.time = time
        if source is not None:
            self.source = source

        self._update_values()

    def _update_values(self):
        """Update displayed values without rebuilding components"""
        try:
            container = self.content
            if not isinstance(container, Container):
                self._fallback_update()
                return

            column = container.content
            if not isinstance(column, Column):
                self._fallback_update()
                return

            # Title (index 0)
            if len(column.controls) >= 1:
                title_text = column.controls[0]
                if isinstance(title_text, Text):
                    title_text.value = self.title

            # Info row (index 1)
            if len(column.controls) >= 2:
                info_row = column.controls[1]
                if isinstance(info_row, Row):
                    if len(info_row.controls) >= 2:
                        time_text = info_row.controls[1]
                        if isinstance(time_text, Text):
                            time_text.value = self.time
                    if len(info_row.controls) >= 4:
                        source_text = info_row.controls[3]
                        if isinstance(source_text, Text):
                            source_text.value = self.source

        except (IndexError, AttributeError) as e:
            logger.debug(f"NewsCard _update_values failed: {e}, falling back to rebuild")
            self._fallback_update()
            return

        self.update()

    def _fallback_update(self):
        """Fallback to rebuild content if structure doesn't match"""
        self.content.content = self._build_content()
        self.update()
