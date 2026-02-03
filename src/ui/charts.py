# -*- coding: UTF-8 -*-
"""图表组件模块"""

from textual.widgets import Static, Button
from textual.containers import Container, Vertical, Horizontal
from typing import List, Optional
from .models import FundHistoryData


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
    ChartDialog > Vertical { width: 100%; }
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
        align: right middle;
    }
    ChartDialog .period-selector { margin-bottom: 1; }
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
        self._update_title()
        self._update_period_buttons()
        self._render_chart()

    def _update_title(self) -> None:
        title = f"[b]净值走势图 - {self.fund_name} ({self.fund_code})[/b]"
        self.query_one("#chart-title", Static).update(title)

    def _update_period_buttons(self) -> None:
        periods = ["近一月", "近三月", "近六月", "近一年"]
        buttons = "[周期:] "
        for i, period in enumerate(periods):
            if period == self.current_period:
                buttons += f"[bold][{period}][/]  "
            else:
                buttons += f"[{period}]  "
        self.query_one("#period-buttons", Static).update(buttons)

    def _render_chart(self) -> None:
        if not self.history_data or not self.history_data.net_values:
            self.query_one("#chart-content", Static).update("暂无历史数据")
            self.query_one("#chart-legend", Static).update("")
            return

        net_values = self.history_data.net_values
        dates = self.history_data.dates

        max_points = {"近一月": 30, "近三月": 90, "近六月": 180, "近一年": 365}.get(self.current_period, 365)

        if len(net_values) > max_points:
            step = len(net_values) // max_points
            net_values = net_values[::step]
            dates = dates[::step]

        chart_ascii = self._generate_ascii_chart(net_values, dates)

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
        if not values or len(values) < 2:
            return "数据不足，无法生成图表"

        min_val = min(values)
        max_val = max(values)
        val_range = max_val - min_val
        if val_range < 0.0001:
            min_val = min_val * 0.999
            max_val = max_val * 1.001
            val_range = max_val - min_val

        lines = []
        lines.append(" " + "_" * width)

        chars = []
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

        for row in chars:
            lines.append(f"|{row}|")

        lines.append(" " + "-" * width)

        y_labels = []
        for row in range(height):
            y = max_val - (row / (height - 1)) * val_range
            y_labels.append(f"{y:.4f}")

        result = []
        for i, row in enumerate(chars):
            if i < len(y_labels):
                result.append(f"{y_labels[i]:>10} |{row}|")
            else:
                result.append(f"{'':>10} |{row}|")

        result.append(f"{'':>10} " + "-" * width)

        date_line = " " * 10
        step_x = max(1, len(dates) // 10)
        for i in range(0, len(dates), step_x):
            date_str = dates[i][-5:] if len(dates[i]) > 5 else dates[i]
            date_line += f"{date_str:<7}"
        result.append(date_line)

        return "\n".join(result)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.remove()


class ChartPreview(Static):
    """图表预览组件"""

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
        self.history_data = history_data
        if not history_data or not history_data.net_values:
            self.query_one("#preview-content", Static).update("暂无数据")
            return

        values = history_data.net_values[-30:]
        dates = history_data.dates[-30:]

        if len(values) < 2:
            self.query_one("#preview-content", Static).update("数据不足")
            return

        chart = self._generate_simple_ascii(values, dates, width, height)
        self.query_one("#preview-content", Static).update(chart)

    def _generate_simple_ascii(self, values: List[float], dates: List[str], width: int, height: int) -> str:
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
                idx = values.index(val)
                x_val = min_val + (idx / (len(values) - 1)) * val_range if len(values) > 1 else min_val
                if abs(val - y) < val_range / (height * 2):
                    row_chars.append("*")
                else:
                    row_chars.append(" ")
            lines.append("".join(row_chars))

        return "\n".join(lines)
