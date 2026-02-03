# -*- coding: UTF-8 -*-
"""自定义 UI 组件模块"""

from textual.widget import Widget
from textual.message import Message
from textual.widgets import DataTable, Static, ListView, ListItem, Label, Button, Input, TextArea
from textual.containers import Container, Vertical, Horizontal
from textual.color import Color
from dataclasses import dataclass
from typing import List, Optional
import math
from datetime import datetime


# ==================== 数据结构定义 ====================

@dataclass
class FundData:
    """基金数据结构"""
    code: str           # 基金代码
    name: str           # 基金名称
    net_value: float    # 单位净值
    est_value: float    # 估算净值
    change_pct: float   # 涨跌幅 (%)
    profit: float = 0.0       # 持仓盈亏 (可选)
    hold_shares: float = 0.0  # 持有份额 (可选)
    cost: float = 0.0         # 成本价 (可选)


@dataclass
class CommodityData:
    """商品数据结构"""
    name: str           # 商品名称
    price: float        # 当前价格
    change_pct: float   # 涨跌幅 (%)
    change: float = 0.0      # 价格变化值 (可选)
    currency: str = "CNY"    # 货币 (可选)
    exchange: str = ""       # 交易所 (可选)
    time: str = ""           # 更新时间 (可选)
    symbol: str = ""         # 商品代码 (可选)


@dataclass
class NewsData:
    """新闻数据结构"""
    time: str       # 发布时间
    title: str      # 标题
    url: str        # 链接


@dataclass
class SectorData:
    """行业板块数据结构"""
    code: str           # 板块代码
    name: str           # 板块名称
    category: str       # 板块类别
    current: float      # 当前点位
    change_pct: float   # 涨跌幅 (%)
    change: float = 0.0     # 涨跌值 (可选)
    trading_status: str = ""  # 交易状态 (可选)
    time: str = ""           # 更新时间 (可选)


# ==================== 自定义组件 ====================

class FundTable(DataTable):
    """基金数据表格组件"""

    BINDINGS = [
        ("a", "add", "添加"),
        ("d", "delete", "删除"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True

    def compose(self):
        yield from super().compose()

    def on_mount(self):
        """组件挂载时初始化列"""
        self.add_column("代码", width=10)
        self.add_column("名称", width=20)
        self.add_column("净值", width=12)
        self.add_column("估值", width=12)
        self.add_column("涨跌", width=10)
        self.add_column("持仓盈亏", width=14)

    def update_funds(self, funds: List[FundData]):
        """更新基金数据"""
        self.clear()
        for fund in funds:
            # 计算涨跌幅颜色
            change_color = "green" if fund.change_pct >= 0 else "red"
            profit_color = "green" if fund.profit >= 0 else "red"

            self.add_row(
                fund.code,
                fund.name,
                f"{fund.net_value:.4f}",
                f"{fund.est_value:.4f}",
                f"{fund.change_pct:+.2f}%" if fund.change_pct else "N/A",
                f"{fund.profit:+.2f}" if fund.profit else "N/A",
            )


class CommodityTable(DataTable):
    """商品数据表格组件"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True

    def on_mount(self):
        """组件挂载时初始化列"""
        self.add_column("商品", width=20)
        self.add_column("价格", width=14)
        self.add_column("涨跌", width=10)

    def update_commodities(self, commodities: List[CommodityData]):
        """更新商品数据"""
        self.clear()
        for commodity in commodities:
            change_color = "green" if commodity.change_pct >= 0 else "red"
            self.add_row(
                commodity.name,
                f"{commodity.price:.4f}",
                f"{commodity.change_pct:+.2f}%" if commodity.change_pct else "N/A",
            )


class NewsList(ListView):
    """新闻列表组件"""

    BINDINGS = [
        ("r", "refresh", "刷新"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.highlight_style = None

    def compose(self):
        yield from super().compose()

    def on_mount(self):
        """组件挂载时初始化"""
        pass

    def update_news(self, news_list: List[NewsData]):
        """更新新闻列表"""
        self.clear()
        for news in news_list:
            self.append(NewsItem(news))

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """处理新闻选择事件"""
        if isinstance(event.item, NewsItem):
            # 可以在这里添加打开链接的逻辑
            pass


class NewsItem(ListItem):
    """新闻列表项"""

    def __init__(self, news: NewsData, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.news = news
        self.label = Static(f"[{news.time}] {news.title}")

    def compose(self):
        yield self.label


class StatPanel(Static):
    """统计信息面板"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_profit = 0.0
        self.fund_count = 0

    def compose(self):
        yield Static(id="stat-content")

    def update_stats(self, total_profit: float, fund_count: int, avg_change: float):
        """更新统计数据"""
        self.total_profit = total_profit
        self.fund_count = fund_count

        profit_color = "green" if total_profit >= 0 else "red"
        change_color = "green" if avg_change >= 0 else "red"

        content = f"""
[统计信息]
基金数量: {fund_count}
总收益: [{profit_color}]{total_profit:+.2f}[/]
平均涨跌: [{change_color}]{avg_change:+.2f}%[/]
"""
        self.query_one("#stat-content", Static).update(content)


class StatusBar(Static):
    """状态栏组件"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_update = ""
        self.refresh_interval = 30

    def compose(self):
        yield Static(id="status-content")

    def update_status(self, last_update: str, theme: str = "dark", auto_refresh: bool = True):
        """更新状态栏信息"""
        refresh_status = "自动刷新" if auto_refresh else "手动刷新"
        theme_status = "深色" if theme == "dark" else "浅色"

        content = f"最后更新: {last_update} | 刷新: {self.refresh_interval}秒 | 主题: {theme_status} | {refresh_status}"
        self.query_one("#status-content", Static).update(content)


class HelpPanel(Static):
    """帮助面板组件"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compose(self):
        yield Static(id="help-content")

    def show_help(self):
        """显示帮助信息"""
        help_content = """
[操作说明]

[a]       - 添加基金
[d]       - 删除基金
[g]       - 净值图表
[h]       - 持仓设置
[r]       - 手动刷新
[t]       - 切换主题
[F1]      - 显示帮助
[Ctrl+C]  - 退出应用

[布局说明]

左侧 50%  - 基金列表 (自选/持仓)
中间 25%  - 商品行情 (贵金属/能源)
右侧 25%  - 财经新闻 (实时资讯)
"""
        self.query_one("#help-content", Static).update(help_content)


class ThemeToggle(Button):
    """主题切换按钮"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = "主题"
        self.variant = "default"


class SectorTable(DataTable):
    """行业板块数据表格组件"""

    BINDINGS = [
        ("c", "filter_category", "筛选类别"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.current_category: Optional[str] = None

    def on_mount(self):
        """组件挂载时初始化列"""
        self.add_column("板块", width=16)
        self.add_column("类别", width=10)
        self.add_column("点位", width=12)
        self.add_column("涨跌", width=10)
        self.add_column("状态", width=8)

    def update_sectors(self, sectors: List[SectorData], category: Optional[str] = None):
        """更新板块数据"""
        self.clear()
        self.current_category = category

        # 按类别筛选
        filtered_sectors = sectors
        if category:
            filtered_sectors = [s for s in sectors if s.category == category]

        for sector in filtered_sectors:
            change_color = "green" if sector.change_pct >= 0 else "red"
            status_color = "yellow" if sector.trading_status == "竞价" else "green" if sector.trading_status == "交易" else "grey"

            self.add_row(
                sector.name,
                sector.category,
                f"{sector.current:.2f}",
                f"{sector.change_pct:+.2f}%",
                sector.trading_status,
            )

    def filter_by_category(self, category: str):
        """按类别筛选（预留方法）"""
        pass


class SectorCategoryFilter(Static):
    """板块类别筛选面板"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.categories = ["全部", "消费", "新能源", "医药", "科技", "金融", "周期", "制造"]
        self.current_filter = "全部"

    def compose(self):
        yield Static(id="category-filter-content")

    def update_filter(self, selected: str):
        """更新筛选状态"""
        if selected in self.categories:
            self.current_filter = selected
            content = f"[类别筛选]: {selected}"
            self.query_one("#category-filter-content", Static).update(content)


class AddFundDialog(Container):
    """添加基金对话框"""

    DEFAULT_CSS = """
    AddFundDialog {
        align: center middle;
        width: 60;
        height: auto;
        border: solid cyan;
        background: $surface;
        padding: 1;
    }
    AddFundDialog > Vertical {
        width: 100%;
    }
    AddFundDialog Input {
        margin-bottom: 1;
    }
    AddFundDialog .dialog-buttons {
        margin-top: 1;
        align: right;
    }
    """

    def __init__(self):
        super().__init__(id="add-fund-dialog")
        self.result_code = None
        self.result_name = None

    def compose(self):
        yield Vertical(
            Static("请输入基金代码和名称:", classes="dialog-label"),
            Input(placeholder="基金代码 (如: 161039)", id="fund-code-input", maxlength=10),
            Input(placeholder="基金名称 (如: 富国中证新能源汽车指数)", id="fund-name-input"),
            Horizontal(
                Button("取消", id="cancel-btn", variant="default"),
                Button("添加", id="confirm-btn", variant="primary"),
                classes="dialog-buttons"
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "confirm-btn":
            code_input = self.query_one("#fund-code-input", Input)
            name_input = self.query_one("#fund-name-input", Input)
            code = code_input.value.strip()
            name = name_input.value.strip()

            if code and name:
                self.result_code = code
                self.result_name = name
                self.remove()  # 移除对话框
                self.post_message(self.Confirm())
            else:
                from textual.app import ComposeResult
                self.notify("请填写完整的基金信息", severity="warning")
        else:
            self.remove()
            self.post_message(self.Cancel())

    class Confirm(Message):
        """确认消息"""
        pass

    class Cancel(Message):
        """取消消息"""
        pass


class HoldingDialog(Container):
    """持仓设置对话框"""

    DEFAULT_CSS = """
    HoldingDialog {
        align: center middle;
        width: 60;
        height: auto;
        border: solid cyan;
        background: $surface;
        padding: 1;
    }
    HoldingDialog > Vertical {
        width: 100%;
    }
    HoldingDialog Input {
        margin-bottom: 1;
    }
    HoldingDialog .dialog-buttons {
        margin-top: 1;
        align: right;
    }
    """

    def __init__(self, fund_code: str, fund_name: str, current_shares: float = 0.0, current_cost: float = 0.0):
        super().__init__(id="holding-dialog")
        self.fund_code = fund_code
        self.fund_name = fund_name
        self.result_shares = current_shares
        self.result_cost = current_cost
        self.is_holding = current_shares > 0  # 当前是否为持仓状态

    def compose(self):
        action_text = "取消持仓" if self.is_holding else "设为持仓"
        yield Vertical(
            Static(f"基金: {self.fund_name} ({self.fund_code})", classes="dialog-label"),
            Input(placeholder=f"持有份额 (当前: {self.result_shares:.2f})", id="shares-input", value=str(self.result_shares) if self.result_shares > 0 else ""),
            Input(placeholder=f"成本价 (当前: {self.result_cost:.4f})", id="cost-input", value=str(self.result_cost) if self.result_cost > 0 else ""),
            Horizontal(
                Button("取消", id="cancel-btn", variant="default"),
                Button(action_text, id="confirm-btn", variant="primary"),
                classes="dialog-buttons"
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "confirm-btn":
            shares_input = self.query_one("#shares-input", Input)
            cost_input = self.query_one("#cost-input", Input)

            shares_str = shares_input.value.strip()
            cost_str = cost_input.value.strip()

            # 如果填写了份额，视为持仓
            if shares_str:
                try:
                    shares = float(shares_str)
                    cost = float(cost_str) if cost_str else 0.0
                    self.result_shares = shares
                    self.result_cost = cost
                    self.is_holding = True
                    self.remove()
                    self.post_message(self.Confirm())
                except ValueError:
                    self.notify("请输入有效的数字", severity="error")
            else:
                # 清空持仓
                self.result_shares = 0.0
                self.result_cost = 0.0
                self.is_holding = False
                self.remove()
                self.post_message(self.Confirm())
        else:
            self.remove()
            self.post_message(self.Cancel())

    class Confirm(Message):
        """确认消息"""
        pass

    class Cancel(Message):
        """取消消息"""
        pass


@dataclass
class FundHistoryData:
    """基金历史数据结构"""
    fund_code: str
    fund_name: str
    dates: List[str]
    net_values: List[float]
    accumulated_net: Optional[List[float]] = None


class ChartDialog(Container):
    """图表对话框 - 显示基金净值走势图"""

    DEFAULT_CSS = """
    ChartDialog {
        align: center middle;
        width: 80;
        height: auto;
        max-height: 35;
        border: solid cyan;
        background: $surface;
        padding: 1;
    }
    ChartDialog > Vertical {
        width: 100%;
    }
    ChartDialog .chart-title {
        margin-bottom: 1;
        text-align: center;
        color: cyan;
    }
    ChartDialog .chart-content {
        margin-bottom: 1;
        font-family: monospace;
        font-size: 8;
    }
    ChartDialog .chart-legend {
        margin-top: 1;
        color: gray;
        font-size: 8;
    }
    ChartDialog .dialog-buttons {
        margin-top: 1;
        align: right;
    }
    ChartDialog .period-selector {
        margin-bottom: 1;
    }
    """

    def __init__(self, fund_code: str, fund_name: str, history_data: Optional[FundHistoryData] = None):
        super().__init__(id="chart-dialog")
        self.fund_code = fund_code
        self.fund_name = fund_name
        self.history_data = history_data
        self.current_period = "近一年"

    def compose(self):
        yield Vertical(
            Static(id="chart-title", classes="chart-title"),
            Static(id="period-buttons", classes="period-selector"),
            Static(id="chart-content", classes="chart-content"),
            Static(id="chart-legend", classes="chart-legend"),
            Horizontal(
                Button("关闭", id="close-btn", variant="default"),
                classes="dialog-buttons"
            )
        )

    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self._update_title()
        self._update_period_buttons()
        self._render_chart()

    def _update_title(self) -> None:
        """更新标题"""
        title = f"[b]净值走势图 - {self.fund_name} ({self.fund_code})[/b]"
        self.query_one("#chart-title", Static).update(title)

    def _update_period_buttons(self) -> None:
        """更新周期选择按钮"""
        periods = ["近一月", "近三月", "近六月", "近一年"]
        buttons = "[周期:] "
        for i, period in enumerate(periods):
            if period == self.current_period:
                buttons += f"[bold][{period}][/]  "
            else:
                buttons += f"[{period}]  "
        self.query_one("#period-buttons", Static).update(buttons)

    def _render_chart(self) -> None:
        """渲染图表"""
        if not self.history_data or not self.history_data.net_values:
            self.query_one("#chart-content", Static).update("暂无历史数据")
            self.query_one("#chart-legend", Static).update("")
            return

        # 根据选择的周期筛选数据
        net_values = self.history_data.net_values
        dates = self.history_data.dates

        # 根据周期限制数据点数量
        max_points = {
            "近一月": 30,
            "近三月": 90,
            "近六月": 180,
            "近一年": 365
        }.get(self.current_period, 365)

        # 如果数据太多，进行采样
        if len(net_values) > max_points:
            step = len(net_values) // max_points
            net_values = net_values[::step]
            dates = dates[::step]

        # 生成 ASCII 图表
        chart_ascii = self._generate_ascii_chart(net_values, dates)

        # 生成图例信息
        if net_values:
            first_val = net_values[0]
            last_val = net_values[-1]
            change_pct = ((last_val - first_val) / first_val * 100) if first_val != 0 else 0
            legend = f"起始: {first_val:.4f}  |  最新: {last_val:.4f}  |  涨跌: {change_pct:+.2f}%  |  数据点数: {len(net_values)}"
        else:
            legend = ""

        self.query_one("#chart-content", Static).update(chart_ascii)
        self.query_one("#chart-legend", Static).update(legend)

    def _generate_ascii_chart(self, values: List[float], dates: List[str], width: int = 70, height: int = 12) -> str:
        """
        生成 ASCII 格式的折线图

        Args:
            values: 净值列表
            dates: 日期列表
            width: 图表宽度
            height: 图表高度

        Returns:
            str: ASCII 图表字符串
        """
        if not values or len(values) < 2:
            return "数据不足，无法生成图表"

        # 计算最小值和最大值
        min_val = min(values)
        max_val = max(values)

        # 如果范围太小，稍微扩展以便显示
        val_range = max_val - min_val
        if val_range < 0.0001:
            min_val = min_val * 0.999
            max_val = max_val * 1.001
            val_range = max_val - min_val

        # 计算每个数据点在图表中的位置
        chars = []  # 存储每一行的字符
        for row in range(height):
            y = max_val - (row / (height - 1)) * val_range
            row_chars = []
            for i, val in enumerate(values):
                x_val = min_val + (i / (len(values) - 1)) * val_range
                if abs(val - y) < val_range / (height * 2):
                    row_chars.append("*")
                else:
                    row_chars.append(" ")
            chars.append("".join(row_chars))

        # 构建最终图表
        lines = []
        lines.append(" " + "_" * width)

        for row in chars:
            lines.append(f"|{row}|")

        lines.append(" " + "-" * width)

        # 添加 Y 轴标签
        y_labels = []
        for row in range(height):
            y = max_val - (row / (height - 1)) * val_range
            y_labels.append(f"{y:.4f}")

        # 添加 X 轴日期标签（只显示部分日期）
        x_labels = []
        step = max(1, len(dates) // 5)
        for i in range(0, len(dates), step):
            date_str = dates[i][-5:] if len(dates[i]) > 5 else dates[i]
            x_labels.append(date_str)
        while len(x_labels) < 5:
            x_labels.append("")

        # 输出图表
        result = []
        for i, row in enumerate(chars):
            if i < len(y_labels):
                result.append(f"{y_labels[i]:>10} |{row}|")
            else:
                result.append(f"{'':>10} |{row}|")

        result.append(f"{'':>10} " + "-" * width)

        # 添加日期标签
        date_line = " " * 10
        step_x = max(1, len(dates) // 10)
        for i in range(0, len(dates), step_x):
            date_str = dates[i][-5:] if len(dates[i]) > 5 else dates[i]
            date_line += f"{date_str:<7}"
        result.append(date_line)

        return "\n".join(result)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "close-btn":
            self.remove()


class ChartPreview(Static):
    """图表预览组件 - 显示在主界面中的小图表"""

    DEFAULT_CSS = """
    ChartPreview {
        height: auto;
        border: solid gray;
        padding: 1;
    }
    ChartPreview .preview-content {
        font-family: monospace;
        font-size: 6;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history_data: Optional[FundHistoryData] = None

    def compose(self):
        yield Static(id="preview-content", classes="preview-content")

    def update_preview(self, history_data: FundHistoryData, width: int = 40, height: int = 6) -> None:
        """更新图表预览"""
        self.history_data = history_data

        if not history_data or not history_data.net_values:
            self.query_one("#preview-content", Static).update("暂无数据")
            return

        values = history_data.net_values[-30:]  # 只显示最近30天
        dates = history_data.dates[-30:]

        if len(values) < 2:
            self.query_one("#preview-content", Static).update("数据不足")
            return

        # 生成简化的 ASCII 图表
        chart = self._generate_simple_ascii(values, dates, width, height)
        self.query_one("#preview-content", Static).update(chart)

    def _generate_simple_ascii(self, values: List[float], dates: List[str], width: int, height: int) -> str:
        """生成简化的 ASCII 图表"""
        if not values:
            return ""

        min_val = min(values)
        max_val = max(values)

        val_range = max_val - min_val
        if val_range < 0.0001:
            min_val = min_val * 0.999
            max_val = max_val * 1.001
            val_range = max_val - min_val

        lines = []
        for row in range(height):
            y = max_val - (row / (height - 1)) * val_range
            row_chars = []
            for val in values:
                x_val = min_val + (values.index(val) / (len(values) - 1)) * val_range if len(values) > 1 else min_val
                if abs(val - y) < val_range / (height * 2):
                    row_chars.append("*")
                else:
                    row_chars.append(" ")
            lines.append("".join(row_chars))

        return "\n".join(lines)
