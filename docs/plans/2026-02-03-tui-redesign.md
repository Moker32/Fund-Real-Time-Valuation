# 基金实时估值 TUI 应用 - 重新设计实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重新设计 TUI 应用，采用响应式架构、模块化组件、现代化主题系统，提升代码可维护性和用户体验

**Architecture:** 采用模块化重构 + 响应式状态管理 + 主题系统
- 拆分 widgets.py 为 tables.py, dialogs.py, charts.py, models.py
- 使用 reactive 响应式属性替代直接更新
- 实现自定义主题系统和 CSS 变量
- 使用 notify() 替代传统提示方式

**Tech Stack:** Python + Textual + Rich + dataclasses

---

## 重构任务

### Task 1: 创建独立的数据模型模块 (models.py)

**Files:**
- Create: `src/ui/models.py`

**Step 1: 创建 models.py 文件**

```python
# src/ui/models.py
"""数据模型模块 - 统一管理所有数据结构"""

from dataclasses import dataclass
from typing import List, Optional


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


@dataclass
class FundHistoryData:
    """基金历史数据结构"""
    fund_code: str
    fund_name: str
    dates: List[str]
    net_values: List[float]
    accumulated_net: Optional[List[float]] = None
```

**Step 2: 更新 widgets.py 导入**

```python
# 在 widgets.py 顶部添加
from .models import FundData, CommodityData, NewsData, SectorData, FundHistoryData
```

**Step 3: 从 widgets.py 移除 dataclass 定义**

删除 widgets.py 中的所有 @dataclass 定义（约30行）

**Step 4: 运行验证**

Run: `python -c "from ui.widgets import FundData, CommodityData, NewsData; print('Import OK')"`
Expected: 无错误

**Step 5: Commit**

```bash
git add src/ui/models.py src/ui/widgets.py
git commit -m "refactor: 拆分数据模型到独立模块"
```

---

### Task 2: 创建表格组件模块 (tables.py)

**Files:**
- Create: `src/ui/tables.py`
- Modify: `src/ui/widgets.py` (移除 FundTable, CommodityTable 等)

**Step 1: 创建 tables.py 文件**

```python
# src/ui/tables.py
"""表格组件模块"""

from textual.widgets import DataTable, Static
from textual.color import Color
from typing import List
from .models import FundData, CommodityData, SectorData


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

    def on_mount(self):
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
        self.add_column("商品", width=20)
        self.add_column("价格", width=14)
        self.add_column("涨跌", width=10)

    def update_commodities(self, commodities: List[CommodityData]):
        self.clear()
        for commodity in commodities:
            self.add_row(
                commodity.name,
                f"{commodity.price:.4f}",
                f"{commodity.change_pct:+.2f}%" if commodity.change_pct else "N/A",
            )


class SectorTable(DataTable):
    """行业板块数据表格组件"""

    BINDINGS = [
        ("c", "filter_category", "筛选类别"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.current_category: str | None = None

    def on_mount(self):
        self.add_column("板块", width=16)
        self.add_column("类别", width=10)
        self.add_column("点位", width=12)
        self.add_column("涨跌", width=10)
        self.add_column("状态", width=8)

    def update_sectors(self, sectors: List[SectorData], category: str | None = None):
        self.clear()
        self.current_category = category
        filtered_sectors = sectors
        if category:
            filtered_sectors = [s for s in sectors if s.category == category]
        for sector in filtered_sectors:
            self.add_row(
                sector.name,
                sector.category,
                f"{sector.current:.2f}",
                f"{sector.change_pct:+.2f}%",
                sector.trading_status,
            )
```

**Step 2: 更新 widgets.py 导入**

```python
# 在 widgets.py 中替换原有的表格类导入
from .tables import FundTable, CommodityTable, SectorTable
```

**Step 3: 从 widgets.py 移除 FundTable, CommodityTable, SectorTable 类**

**Step 4: 运行验证**

Run: `python -c "from ui.tables import FundTable, CommodityTable; print('Import OK')"`
Expected: 无错误

**Step 5: Commit**

```bash
git add src/ui/tables.py src/ui/widgets.py
git commit -m "refactor: 拆分表格组件到独立模块"
```

---

### Task 3: 创建对话框组件模块 (dialogs.py)

**Files:**
- Create: `src/ui/dialogs.py`
- Modify: `src/ui/widgets.py` (移除对话框类)

**Step 1: 创建 dialogs.py 文件**

```python
# src/ui/dialogs.py
"""对话框组件模块"""

from textual.widget import Widget
from textual.message import Message
from textual.widgets import DataTable, Static, Button, Input
from textual.containers import Container, Vertical, Horizontal
from typing import Optional
from .models import FundHistoryData


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
    AddFundDialog > Vertical { width: 100%; }
    AddFundDialog Input { margin-bottom: 1; }
    AddFundDialog .dialog-buttons {
        margin-top: 1;
        align: right middle;
    }
    """

    def __init__(self):
        super().__init__(id="add-fund-dialog")
        self.result_code: str | None = None
        self.result_name: str | None = None

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
        if event.button.id == "confirm-btn":
            code_input = self.query_one("#fund-code-input", Input)
            name_input = self.query_one("#fund-name-input", Input)
            code = code_input.value.strip()
            name = name_input.value.strip()
            if code and name:
                self.result_code = code
                self.result_name = name
                self.remove()
                self.post_message(self.Confirm())
            else:
                self.notify("请填写完整的基金信息", severity="warning")
        else:
            self.remove()
            self.post_message(self.Cancel())

    class Confirm(Message):
        pass

    class Cancel(Message):
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
    HoldingDialog > Vertical { width: 100%; }
    HoldingDialog Input { margin-bottom: 1; }
    HoldingDialog .dialog-buttons {
        margin-top: 1;
        align: right middle;
    }
    """

    def __init__(self, fund_code: str, fund_name: str, current_shares: float = 0.0, current_cost: float = 0.0):
        super().__init__(id="holding-dialog")
        self.fund_code = fund_code
        self.fund_name = fund_name
        self.result_shares = current_shares
        self.result_cost = current_cost
        self.is_holding = current_shares > 0

    def compose(self):
        action_text = "取消持仓" if self.is_holding else "设为持仓"
        yield Vertical(
            Static(f"基金: {self.fund_name} ({self.fund_code})", classes="dialog-label"),
            Input(placeholder=f"持有份额 (当前: {self.result_shares:.2f})", id="shares-input",
                  value=str(self.result_shares) if self.result_shares > 0 else ""),
            Input(placeholder=f"成本价 (当前: {self.result_cost:.4f})", id="cost-input",
                  value=str(self.result_cost) if self.result_cost > 0 else ""),
            Horizontal(
                Button("取消", id="cancel-btn", variant="default"),
                Button(action_text, id="confirm-btn", variant="primary"),
                classes="dialog-buttons"
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-btn":
            shares_input = self.query_one("#shares-input", Input)
            cost_input = self.query_one("#cost-input", Input)
            shares_str = shares_input.value.strip()
            cost_str = cost_input.value.strip()
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
                self.result_shares = 0.0
                self.result_cost = 0.0
                self.is_holding = False
                self.remove()
                self.post_message(self.Confirm())
        else:
            self.remove()
            self.post_message(self.Cancel())

    class Confirm(Message):
        pass

    class Cancel(Message):
        pass
```

**Step 2: 更新 widgets.py 导入**

```python
from .dialogs import AddFundDialog, HoldingDialog
```

**Step 3: 从 widgets.py 移除 AddFundDialog, HoldingDialog 类**

**Step 4: 运行验证**

Run: `python -c "from ui.dialogs import AddFundDialog, HoldingDialog; print('Import OK')"`
Expected: 无错误

**Step 5: Commit**

```bash
git add src/ui/dialogs.py src/ui/widgets.py
git commit -m "refactor: 拆分对话框组件到独立模块"
```

---

### Task 4: 创建图表组件模块 (charts.py)

**Files:**
- Create: `src/ui/charts.py`
- Modify: `src/ui/widgets.py` (移除图表相关类)

**Step 1: 创建 charts.py 文件**

```python
# src/ui/charts.py
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
```

**Step 2: 更新 widgets.py 导入**

```python
from .charts import ChartDialog, ChartPreview
```

**Step 3: 从 widgets.py 移除 ChartDialog, ChartPreview 类**

**Step 4: 运行验证**

Run: `python -c "from ui.charts import ChartDialog, ChartPreview; print('Import OK')"`
Expected: 无错误

**Step 5: Commit**

```bash
git add src/ui/charts.py src/ui/widgets.py
git commit -m "refactor: 拆分图表组件到独立模块"
```

---

### Task 5: 重构 app.py 使用响应式状态

**Files:**
- Modify: `src/ui/app.py`

**Step 1: 添加响应式属性**

```python
from textual.reactive import reactive

class FundTUIApp(App):
    # 响应式属性
    funds = reactive([])
    commodities = reactive([])
    news_list = reactive([])
    total_profit = reactive(0.0)
    avg_change = reactive(0.0)

    # ... 其他属性保持不变
```

**Step 2: 添加 watcher 方法**

```python
def watch_funds(self, new_funds: List[FundData]) -> None:
    """当 funds 变化时自动更新表格"""
    table = self._safe_query("#fund-table", FundTable)
    if table:
        table.update_funds(new_funds)
    self.calculate_stats()
    self.update_stats()

def watch_commodities(self, new_commodities: List[CommodityData]) -> None:
    """当 commodities 变化时自动更新"""
    view = self._safe_query("#commodity-table", CommodityPairView)
    if view:
        view.update_commodities(new_commodities)

def watch_news_list(self, new_news: List[NewsData]) -> None:
    """当 news_list 变化时自动更新"""
    news_widget = self._safe_query("#news-list", NewsList)
    if news_widget:
        news_widget.update_news(new_news)

def watch_total_profit(self, value: float) -> None:
    """总收益变化时更新状态面板"""
    self.update_stats()
```

**Step 3: 更新数据加载方法使用响应式赋值**

```python
async def load_fund_data(self) -> None:
    # ... 数据获取逻辑 ...
    if funds:
        self.funds = funds  # 使用响应式赋值
        self.notify(f"成功加载 {len(funds)} 只基金数据", severity="information")
    else:
        self.notify("未能获取到任何基金数据", severity="warning")
```

**Step 4: 移除手动更新调用**

在 `load_fund_data` 等方法中移除 `table.update_funds()` 等直接调用，改为赋值给响应式属性

**Step 5: 运行验证**

Run: `python -c "from ui.app import FundTUIApp; print('App loads OK')"`
Expected: 无错误

**Step 6: Commit**

```bash
git add src/ui/app.py
git commit -m "refactor: 迁移到响应式状态管理"
```

---

### Task 6: 实现现代化主题系统

**Files:**
- Modify: `src/ui/app.py`
- Modify: `src/ui/styles.tcss`

**Step 1: 定义自定义主题**

```python
from textual.theme import Theme

# 自定义主题配置
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
    variables={
        "block-cursor-foreground": "#00D4FF",
        "input-selection-background": "#00D4FF40",
    }
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
    variables={
        "block-cursor-foreground": "#0066CC",
        "input-selection-background": "#0066CC20",
    }
)
```

**Step 2: 注册主题**

```python
class FundTUIApp(App):
    THEMES = [DARK_THEME, LIGHT_THEME]
    # ...
```

**Step 3: 更新主题切换逻辑**

```python
def action_toggle_theme(self) -> None:
    self.is_dark_theme = not self.is_dark_theme
    if self.is_dark_theme:
        self.theme = "fund_dark"
    else:
        self.theme = "fund_light"
    self.notify(f"已切换至{'深色' if self.is_dark_theme else '浅色'}主题", severity="information")
```

**Step 4: 更新 styles.tcss 使用 CSS 变量**

```css
/* 通用样式 */
Screen {
    background: $background;
    color: $foreground;
}

/* 顶部栏 */
.top-bar {
    background: $surface;
    color: $foreground;
}

/* 视图标签 */
.view-tabs {
    background: $panel;
    color: $foreground-muted;
}

.view-tabs :hover {
    color: $primary;
}

/* 表格样式 */
.fund-table, .commodity-table, .news-list {
    background: $surface;
    border: solid $panel;
}

/* 统计面板 */
.stat-panel {
    background: $panel;
    color: $foreground-muted;
}

/* 涨跌颜色语义 */
.positive { color: $success; }
.negative { color: $error; }
```

**Step 5: 运行验证**

Run: `python run_tui.py` (手动测试主题切换)
Expected: 主题切换正常工作

**Step 6: Commit**

```bash
git add src/ui/app.py src/ui/styles.tcss
git commit -m "feat: 实现现代化主题系统"
```

---

### Task 7: 完善 Tab 视图切换功能

**Files:**
- Modify: `src/ui/app.py`
- Modify: `src/ui/styles.tcss`

**Step 1: 添加 Tab 切换绑定**

```python
class FundTUIApp(App):
    BINDINGS = [
        # ... 现有绑定
        ("tab", "next_view", "下一个视图"),
        ("shift+tab", "prev_view", "上一个视图"),
        ("1", "switch_view('fund')", "基金视图"),
        ("2", "switch_view('commodity')", "商品视图"),
        ("3", "switch_view('news')", "新闻视图"),
    ]

    # 当前活动视图
    active_view = reactive("fund")

    def compose(self) -> ComposeResult:
        # ... 现有布局
        yield Horizontal(
            Static("[b]📊 基金[/b]", id="tab-fund", classes="view-tab active"),
            Static("  📈 商品  ", id="tab-commodity", classes="view-tab"),
            Static("  📰 新闻  ", id="tab-news", classes="view-tab"),
            classes="view-tabs"
        )
        # ...
```

**Step 2: 添加视图切换逻辑**

```python
def watch_active_view(self, view: str) -> None:
    """切换活动视图时更新样式"""
    for tab_id in ["tab-fund", "tab-commodity", "tab-news"]:
        tab = self.query_one(f"#{tab_id}", Static)
        if tab_id == f"tab-{view}":
            tab.update(f"[b]{tab.renderable}[/b]")
        else:
            # 移除粗体
            text = tab.renderable
            text = text.replace("[b]", "").replace("[/b]", "")
            tab.update(text)

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
```

**Step 3: 更新 CSS 样式**

```css
.view-tab {
    padding: 0 1;
    color: $foreground-muted;
}

.view-tab.active {
    color: $primary;
    text-style: bold;
}

.view-tab:hover {
    color: $foreground;
}
```

**Step 4: 运行验证**

Run: `python run_tui.py` (测试 Tab 切换)
Expected: 1/2/3 和 Tab 键可以切换视图

**Step 5: Commit**

```bash
git add src/ui/app.py src/ui/styles.tcss
git commit -m "feat: 实现Tab视图切换功能"
```

---

### Task 8: 优化帮助面板和用户反馈

**Files:**
- Modify: `src/ui/app.py`
- Modify: `src/ui/styles.tcss`

**Step 1: 使用 Toast 替代 mount/remove 方式**

```python
def action_toggle_help(self) -> None:
    """使用 Overlay 显示帮助"""
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
```

**Step 2: 更新帮助面板样式（如果保留）**

```css
.help-panel {
    align: center middle;
    width: 60;
    height: auto;
    border: solid $primary;
    background: $surface;
    padding: 1;
}
```

**Step 3: 运行验证**

Run: `python run_tui.py` (测试 F1 帮助)
Expected: 显示通知而非弹窗

**Step 4: Commit**

```bash
git add src/ui/app.py src/ui/styles.tcss
git commit -m "refactor: 使用Toast通知替代弹窗帮助"
```

---

### Task 9: 更新 __init__.py 导出

**Files:**
- Modify: `src/ui/__init__.py`

**Step 1: 更新模块导出**

```python
"""UI 模块 - 基金实时估值 TUI 界面层"""

from .app import FundTUIApp
from .widgets import (
    FundTable,
    CommodityPairView,
    NewsList,
    NewsItem,
    StatPanel,
    StatusBar,
    HelpPanel,
    ThemeToggle,
    SectorCategoryFilter,
)
from .tables import FundTable, CommodityTable, SectorTable
from .dialogs import AddFundDialog, HoldingDialog
from .charts import ChartDialog, ChartPreview
from .models import FundData, CommodityData, NewsData, SectorData, FundHistoryData

__all__ = [
    "FundTUIApp",
    "FundTable",
    "CommodityTable",
    "CommodityPairView",
    "NewsList",
    "NewsItem",
    "StatPanel",
    "StatusBar",
    "HelpPanel",
    "ThemeToggle",
    "SectorCategoryFilter",
    "AddFundDialog",
    "HoldingDialog",
    "ChartDialog",
    "ChartPreview",
    "FundData",
    "CommodityData",
    "NewsData",
    "SectorData",
    "FundHistoryData",
]
```

**Step 2: 运行验证**

Run: `python -c "from ui import FundTUIApp, FundData, AddFundDialog; print('All exports OK')"`
Expected: 无错误

**Step 3: Commit**

```bash
git add src/ui/__init__.py
git commit -m "refactor: 更新模块导出"
```

---

### Task 10: 清理未使用的 screens.py

**Files:**
- Modify/Delete: `src/ui/screens.py`

**决策点**: 根据实际使用情况决定是删除还是保留
- 如果 Tab 切换使用新实现，则删除 screens.py
- 如果 screens.py 有其他用途，清理未使用的屏幕

```bash
# 删除未使用的屏幕文件
git rm src/ui/screens.py
git commit -m "refactor: 移除未使用的屏幕模块"
```

---

## 总结

完成所有任务后，代码结构将变为：

```
src/ui/
├── __init__.py        # 模块导出
├── app.py             # 主应用 (响应式重构)
├── styles.tcss        # 样式 (CSS变量)
├── models.py          # 数据模型 (新增)
├── tables.py          # 表格组件 (新增)
├── dialogs.py         # 对话框组件 (新增)
├── charts.py          # 图表组件 (新增)
└── widgets.py         # 剩余组件 (精简)
```

**主要改进**:
- 模块化重构，易于维护
- 响应式状态管理，代码更简洁
- 现代化主题系统
- Tab 视图切换
- Toast 通知替代弹窗
- 清晰的模块职责划分
