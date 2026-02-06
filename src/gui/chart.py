# -*- coding: UTF-8 -*-
"""基金图表模块

提供分时图/K线图功能，基于 matplotlib 实现。
"""

from dataclasses import dataclass, field
from typing import Optional

import flet as ft
import matplotlib
from flet import (
    AlertDialog,
    Checkbox,
    Column,
    Container,
    Divider,
    Dropdown,
    ElevatedButton,
    Row,
    Text,
)

matplotlib.use("Agg")  # 使用非交互式后端
import base64
import io

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

# 配置 matplotlib 中文字体（只需设置一次）
plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


@dataclass
class FundHistoryData:
    """基金历史数据"""

    fund_code: str
    fund_name: str
    dates: list[str]
    open_values: list[float]
    close_values: list[float]
    high_values: list[float]
    low_values: list[float]
    volumes: list[int] = field(default_factory=list)

    def __post_init__(self):
        """验证数据一致性"""
        n = len(self.dates)
        assert len(self.open_values) == n, "开盘价数据长度不匹配"
        assert len(self.close_values) == n, "收盘价数据长度不匹配"
        assert len(self.high_values) == n, "最高价数据长度不匹配"
        assert len(self.low_values) == n, "最低价数据长度不匹配"
        if self.volumes:
            assert len(self.volumes) == n, "成交量数据长度不匹配"

    def get_price_change(self) -> float:
        """获取价格涨跌幅"""
        if not self.close_values:
            return 0.0
        first_close = self.close_values[0]
        last_close = self.close_values[-1]
        if first_close == 0:
            return 0.0
        return ((last_close - first_close) / first_close) * 100

    def get_latest_price(self) -> float:
        """获取最新价格"""
        if self.close_values:
            return self.close_values[-1]
        return 0.0

    def calculate_ma(self, period: int) -> list[Optional[float]]:
        """计算移动平均线"""
        if len(self.close_values) < period:
            return [None] * len(self.close_values)
        ma_values = []
        for i in range(len(self.close_values)):
            if i < period - 1:
                ma_values.append(None)
            else:
                ma_values.append(np.mean(self.close_values[i - period + 1 : i + 1]))
        return ma_values

    @staticmethod
    def generate_candlestick_chart(
        history: "FundHistoryData",
        show_ma: bool = False,
        ma_periods: list[int] = None,
        figsize: tuple[int, int] = (12, 8),
    ) -> matplotlib.figure.Figure:
        """
        生成K线图

        Args:
            history: 基金历史数据
            show_ma: 是否显示均线
            ma_periods: 均线周期列表
            figsize: 图表尺寸

        Returns:
            matplotlib.figure.Figure 对象
        """
        n = len(history.dates)
        if n == 0:
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, "暂无历史数据", ha="center", va="center")
            return fig

        # 解析日期
        # dates = [datetime.strptime(d, "%Y-%m-%d") for d in history.dates]  # 暂未使用

        # 创建图表
        fig, (ax_price, ax_volume) = plt.subplots(
            2, 1, figsize=figsize, height_ratios=[3, 1], sharex=True
        )

        # 使用 numpy 向量化计算颜色
        closes = np.array(history.close_values)
        opens = np.array(history.open_values)
        colors = np.where(closes >= opens, "#e74c3c", "#27ae60")  # 红色上涨，绿色下跌

        # 绘制K线影线 - 使用 vlines 批量绘制（比循环快）
        x_positions = np.arange(n)
        ax_price.vlines(
            x_positions,
            ymin=history.low_values,
            ymax=history.high_values,
            colors=colors,
            linewidth=1,
        )

        # 绘制K线实体 - 使用 bar 批量绘制
        body_height = np.abs(closes - opens)
        body_height = np.where(body_height < 0.0001, 0.001, body_height)
        body_bottom = np.minimum(opens, closes)
        ax_price.bar(x_positions, body_height, width=0.6, bottom=body_bottom, color=colors)

        # 绘制均线 - 使用 numpy 向量化
        if show_ma and ma_periods:
            closes_arr = np.array(history.close_values)
            for period in ma_periods:
                if len(closes_arr) >= period:
                    # 使用卷积计算移动平均
                    ma_values = np.convolve(closes_arr, np.ones(period) / period, mode='valid')
                    valid_indices = np.arange(period - 1, len(closes_arr))
                    ax_price.plot(valid_indices, ma_values, linewidth=1.5, label=f"MA{period}")

        # 设置价格轴
        ax_price.set_ylabel("净值", fontsize=12)
        ax_price.legend(loc="upper left")
        ax_price.grid(True, alpha=0.3)

        # 绘制成交量 - 批量绘制
        if history.volumes and len(history.volumes) == n:
            ax_volume.bar(x_positions, history.volumes, color=colors, width=0.6)
            ax_volume.set_ylabel("成交量", fontsize=12)
            ax_volume.set_xlabel("日期", fontsize=12)
            ax_volume.grid(True, alpha=0.3)

        # 设置日期格式
        ax_price.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, n // 10)))
        ax_price.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        plt.setp(ax_price.xaxis.get_majorticklabels(), rotation=45)

        # 设置标题
        title = f"{history.fund_name} ({history.fund_code}) - K线图"
        change_pct = history.get_price_change()
        if change_pct >= 0:
            title += f"  最新: {history.get_latest_price():.4f}  (+{change_pct:.2f}%)"
        else:
            title += f"  最新: {history.get_latest_price():.4f}  ({change_pct:.2f}%)"
        fig.suptitle(title, fontsize=14, fontweight="bold")

        # 调整布局
        plt.tight_layout()

        return fig

    def to_chart_image(self, figsize: tuple[int, int] = (10, 6)) -> str:
        """
        生成图表并转换为base64图片

        Args:
            figsize: 图表尺寸

        Returns:
            base64编码的图片字符串
        """
        fig = self.generate_candlestick_chart(self, figsize=figsize)

        # 保存到内存
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        buffer.seek(0)

        # 转换为base64
        img_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        plt.close(fig)

        return img_base64


class FundChartDialog(AlertDialog):
    """基金图表对话框 - 显示K线图"""

    def __init__(
        self,
        app,
        fund_code: str,
        fund_name: str,
        history_data: Optional[FundHistoryData] = None,
    ):
        super().__init__()
        self.app = app
        self.fund_code = fund_code
        self.fund_name = fund_name
        self.history_data = history_data

        # 控件
        self.chart_image: Optional[ft.Image] = None
        self.period_dropdown = Dropdown(
            label="时间周期",
            width=120,
            options=[
                ft.dropdown.Option("5日", "5d"),
                ft.dropdown.Option("10日", "10d"),
                ft.dropdown.Option("20日", "20d"),
                ft.dropdown.Option("60日", "60d"),
                ft.dropdown.Option("全部", "all"),
            ],
            value="all",
            on_change=self._on_period_change,
        )
        self.ma_checkbox = Checkbox(
            label="显示均线", value=True, on_change=self._on_ma_change
        )
        self.period_options = {
            "5d": 5,
            "10d": 10,
            "20d": 20,
            "60d": 60,
            "all": None,
        }

        # 设置对话框内容
        self.modal = True
        self.title = Text(f"净值走势图 - {fund_name}")
        self.content = self._build_content()
        self.actions = [
            ElevatedButton("关闭", on_click=self._close),
        ]
        self.actions_alignment = ft.MainAxisAlignment.END

    def _build_content(self) -> Container:
        """构建对话框内容"""
        # 统计信息
        stats_text = ""
        if self.history_data:
            change = self.history_data.get_price_change()
            latest = self.history_data.get_latest_price()
            stats_text = f"最新净值: {latest:.4f}  "
            if change >= 0:
                stats_text += f"(+{change:.2f}%)"
            else:
                stats_text += f"({change:.2f}%)"

        return Container(
            content=Column(
                [
                    # 控制栏
                    Row(
                        [
                            Text("周期:", size=14),
                            self.period_dropdown,
                            Container(width=20),
                            self.ma_checkbox,
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    Divider(),
                    # 图表区域
                    Container(
                        content=self._build_chart_container(),
                        height=450,
                        alignment=ft.alignment.center,
                    ),
                    Divider(),
                    # 统计信息
                    Text(
                        stats_text if stats_text else "正在加载历史数据...",
                        size=14,
                        color=ft.Colors.WHITE70,
                    ),
                ],
                spacing=10,
            ),
            width=900,
        )

    def _build_chart_container(self) -> ft.Control:
        """构建图表容器"""
        if not self.history_data or not self.history_data.dates:
            return Text("暂无历史数据", size=16, color=ft.Colors.GREY)

        try:
            # 生成图表
            # show_ma = self.ma_checkbox.value  # 暂未使用
            # ma_periods = [5, 10, 20] if show_ma else None  # 暂未使用

            img_base64 = self.history_data.to_chart_image(figsize=(10, 6))

            self.chart_image = ft.Image(
                src_base64=img_base64,
                width=850,
                height=400,
                fit=ft.ImageFit.CONTAIN,
            )

            return self.chart_image

        except Exception as e:
            return Text(f"生成图表失败: {str(e)}", size=14, color=ft.Colors.RED)

    def _on_period_change(self, e):
        """处理周期变化"""
        pass  # 暂时不实现动态切换

    def _on_ma_change(self, e):
        """处理均线显示变化 - 只更新图片，不重建容器"""
        self._update_chart_image()

    def _update_chart_image(self):
        """更新图表图片 - 复用 Image 组件"""
        if not self.history_data or not self.history_data.dates:
            return

        try:
            img_base64 = self.history_data.to_chart_image(figsize=(10, 6))

            # 复用现有的 Image 组件，只更新 src_base64
            if self.chart_image is None:
                self.chart_image = ft.Image(
                    width=850,
                    height=400,
                    fit=ft.ImageFit.CONTAIN,
                )

            self.chart_image.src_base64 = img_base64

            # 更新内容
            self.app.page.update()

        except Exception as e:
            # 如果更新失败，显示错误信息
            self._show_chart_error(str(e))

    def _show_chart_error(self, error_msg: str):
        """显示图表错误"""
        # 找到图表容器并显示错误
        inner_column = self.content.content
        if isinstance(inner_column, Column) and len(inner_column.controls) > 2:
            chart_container = inner_column.controls[2]
            if isinstance(chart_container, Container):
                chart_container.content = Text(f"生成图表失败: {error_msg}", size=14, color=ft.Colors.RED)
                self.app.page.update()

    def _close(self, e):
        """关闭对话框"""
        self.open = False
        self.app.page.update()


class FundChartCard(Container):
    """基金图表卡片 - 用于显示在详情页"""

    def __init__(self, fund_code: str, fund_name: str):
        super().__init__()
        self.fund_code = fund_code
        self.fund_name = fund_name
        self.history_data: Optional[FundHistoryData] = None
        self._chart_image: Optional[ft.Image] = None  # 缓存 Image 组件
        self._placeholder: Optional[Text] = None  # 缓存占位符

        self.content = Column(
            [
                Text(fund_name, size=16, weight=ft.FontWeight.BOLD),
                Container(
                    self._create_placeholder(),
                    height=150,
                    alignment=ft.alignment.center,
                ),
                ElevatedButton("查看详情", on_click=self._show_chart),
            ],
            spacing=5,
        )

    def _create_placeholder(self) -> Text:
        """创建占位符"""
        self._placeholder = Text("点击查看完整K线图", size=12, color=ft.Colors.GREY)
        return self._placeholder

    def _show_chart(self, e):
        """显示图表对话框"""
        if hasattr(self.app, "page") and self.history_data:
            dialog = FundChartDialog(
                self.app, self.fund_code, self.fund_name, self.history_data
            )
            self.app.page.overlay.append(dialog)
            dialog.open = True
            self.app.page.update()

    def update_history(self, history_data: FundHistoryData):
        """更新历史数据 - 增量更新"""
        self.history_data = history_data
        if history_data and history_data.dates:
            try:
                img_base64 = history_data.to_chart_image(figsize=(6, 3))

                # 复用或创建 Image 组件
                if self._chart_image is None:
                    self._chart_image = ft.Image(
                        width=280,
                        height=140,
                        fit=ft.ImageFit.CONTAIN,
                    )

                self._chart_image.src_base64 = img_base64

                # 更新容器内容
                container = self.content.controls[1]
                if isinstance(container, Container):
                    container.content = self._chart_image
                    if hasattr(self.app, "page"):
                        self.app.page.update()

            except Exception:
                pass
