# TUI界面优化实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完善基金实时估值TUI应用的主界面UI，实现标签页切换、基金右键菜单、基金详情页功能

**Architecture:**
- 使用Textual的`TabbedContent`组件替代当前Static标签，实现真正的可点击标签页
- 基金表格添加"持仓"标记列，使用PopupMenu实现右键菜单
- 创建独立的`FundDetailScreen` Screen类展示基金详情，使用`push_screen`/`pop_screen`导航

**Tech Stack:**
- Python 3.9+
- Textual 1.x (当前已使用的版本)
- 自定义Screen和Dialog组件

---

## 调研结论

### 方案选择

| 功能 | 推荐方案 | 理由 |
|------|----------|------|
| 标签页 | `TabbedContent` | 内置Tab切换逻辑，支持键盘导航(left/right)，自动管理TabPane |
| 右键菜单 | 自定义`ContextMenu` Container | Textual没有内置右键菜单，需要用Container模拟弹出菜单 |
| 详情页 | 独立`Screen`类 | Screen支持完整的生命周期管理，可使用`push_screen`/`pop_screen`导航 |

### Textual关键API

```python
# TabbedContent - 标签页切换
from textual.widgets import TabbedContent, TabPane
TabbedContent(
    TabPane("基金", FundPanel()),
    TabPane("商品", CommodityPanel()),
    TabPane("新闻", NewsPanel()),
    initial="fund"  # 默认激活的tab id
)

# Tab切换监听
def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated):
    active_tab = event.pane.id  # 获取当前激活的tab id

# Screen导航
self.push_screen(FundDetailScreen(fund_code))  # 进入详情页
self.pop_screen()  # 返回主界面

# 自定义Screen
class FundDetailScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "返回")]
```

---

## 任务1：完善TUI主界面标签页

**Files:**
- Modify: `src/ui/app.py:142-181` (compose方法)
- Modify: `src/ui/styles.tcss` (Tab样式)
- Create: `src/ui/screens.py` (TabPane容器组件)

### Step 1: 导入TabbedContent组件

**File:** `src/ui/app.py` (在导入部分添加)

```python
from textual.widgets import TabbedContent, TabPane
```

### Step 2: 创建Tab内容容器组件

**File:** `src/ui/screens.py` (新建)

```python
# -*- coding: UTF-8 -*-
"""Tab内容面板组件 - 为每个Tab提供独立的容器"""

from textual.containers import Container
from textual.widgets import Static
from .tables import FundTable
from .widgets import CommodityPairView, NewsList


class FundPanel(Container):
    """基金面板 - 自选基金列表"""

    DEFAULT_CSS = """
    FundPanel {
        layout: vertical;
    }
    .fund-panel-title {
        height: auto;
        color: $primary;
        text-style: bold;
        padding: 0 1;
    }
    """

    def compose(self):
        yield Static("自选基金", classes="fund-panel-title")
        yield FundTable(id="fund-table", classes="fund-table")


class CommodityPanel(Container):
    """商品面板 - 大宗商品列表"""

    DEFAULT_CSS = """
    CommodityPanel {
        layout: vertical;
    }
    .commodity-panel-title {
        height: auto;
        color: $primary;
        text-style: bold;
        padding: 0 1;
    }
    """

    def compose(self):
        yield Static("大宗商品", classes="commodity-panel-title")
        yield CommodityPairView(id="commodity-table", classes="commodity-table")


class NewsPanel(Container):
    """新闻面板 - 财经新闻列表"""

    DEFAULT_CSS = """
    NewsPanel {
        layout: vertical;
    }
    .news-panel-title {
        height: auto;
        color: $primary;
        text-style: bold;
        padding: 0 1;
    }
    """

    def compose(self):
        yield Static("财经新闻", classes="news-panel-title")
        yield NewsList(id="news-list", classes="news-list")
```

### Step 3: 修改主界面使用TabbedContent

**File:** `src/ui/app.py` (compose方法)

```python
# 删除原有的Horizontal标签栏
# 删除第151-157行的:
# yield Horizontal(
#     Static("[b]📊 基金[/b]", id="tab-fund", classes="view-tab active"),
#     Static("  📈 商品  ", id="tab-commodity", classes="view-tab"),
#     Static("  📰 新闻  ", id="tab-news", classes="view-tab"),
#     classes="view-tabs"
# )

# 删除原有的三栏布局Horizontal (第159-181行)
# 用TabbedContent替代:
yield TabbedContent(
    TabPane("📊 基金", FundPanel(), id="fund"),
    TabPane("📈 商品", CommodityPanel(), id="commodity"),
    TabPane("📰 新闻", NewsPanel(), id="news"),
    id="main-tabs",
    initial="fund"
)
```

### Step 4: 删除旧的标签页样式

**File:** `src/ui/styles.tcss`

删除 `.view-tabs` 和 `.view-tab` 相关样式（约第17-37行）

### Step 5: 添加Tab样式

**File:** `src/ui/styles.tcss` (追加)

```css
/* TabbedContent样式 */
TabbedContent {
    height: 100%;
}

TabPane {
    height: 100%;
}
```

### Step 6: 测试验证

```bash
# 运行应用
./run_tui.py

# 验证项目:
# 1. 默认显示"基金"标签页内容
# 2. 点击"商品"标签，切换显示商品内容
# 3. 点击"新闻"标签，切换显示新闻内容
# 4. 按left/right箭头键切换标签
# 5. 按1/2/3键切换标签
# 6. 主题切换(t键)正常工作
```

---

## 任务2：实现基金标签页功能

**Files:**
- Modify: `src/ui/tables.py:9-41` (FundTable添加持仓列)
- Create: `src/ui/menus.py` (右键菜单组件)
- Modify: `src/ui/app.py:247-317` (添加菜单和导航动作)
- Modify: `src/ui/dialogs.py` (优化对话框)

### Step 1: 添加"持仓"列到FundTable

**File:** `src/ui/tables.py`

```python
class FundTable(DataTable):
    BINDINGS = [
        ("enter", "view_detail", "查看详情"),
        ("a", "add", "添加"),
        ("d", "delete", "删除"),
    ]

    def on_mount(self):
        self.add_column("代码", width=10)
        self.add_column("名称", width=20)
        self.add_column("净值", width=12)
        self.add_column("估值", width=12)
        self.add_column("涨跌", width=10)
        self.add_column("持仓", width=8)  # 新增列
        self.add_column("持仓盈亏", width=14)

    def update_funds(self, funds: List[FundData]):
        self.clear()
        for fund in funds:
            # 持仓标记: 有持仓显示"●"，无持仓显示"○"
            holding_mark = "●" if fund.hold_shares and fund.hold_shares > 0 else "○"
            self.add_row(
                fund.code,
                fund.name,
                f"{fund.net_value:.4f}",
                f"{fund.est_value:.4f}",
                f"{fund.change_pct:+.2f}%" if fund.change_pct else "N/A",
                holding_mark,  # 持仓标记
                f"{fund.profit:+.2f}" if fund.profit else "N/A",
            )
```

### Step 2: 创建右键菜单组件

**File:** `src/ui/menus.py` (新建)

```python
# -*- coding: UTF-8 -*-
"""上下文菜单组件 - 基金右键菜单"""

from textual.widgets import Static, Button
from textual.containers import Container, Vertical
from textual.color import Color


class FundContextMenu(Container):
    """基金上下文菜单"""

    DEFAULT_CSS = """
    FundContextMenu {
        width: 24;
        height: auto;
        border: solid $primary;
        background: $surface;
        layer: overlay;
    }
    FundContextMenu .menu-item {
        height: 1;
        padding: 0 2;
        &:hover {
            background: $primary 30%;
        }
    }
    FundContextMenu .menu-separator {
        height: 1;
        content: "─" * 20;
        color: $foreground-muted;
    }
    FundContextMenu .menu-title {
        height: 1;
        padding: 0 2;
        color: $primary;
        text-style: bold;
        background: $panel;
    }
    """

    BINDINGS = [
        ("escape", "close", "关闭"),
        ("up", "move_up", "上移"),
        ("down", "move_down", "下移"),
        ("enter", "select", "选择"),
    ]

    def __init__(self, fund_code: str, fund_name: str, has_holding: bool = False):
        super().__init__(id="fund-context-menu")
        self.fund_code = fund_code
        self.fund_name = fund_name
        self.has_holding = has_holding
        self.selected_index = 0
        self.menu_items = [
            ("查看详情", "view_detail", "Enter"),
            ("净值图表", "show_chart", "g"),
            ("持仓设置", "set_holding", "h"),
            ("sep1", "separator", ""),
            ("删除自选", "delete", "d"),
        ]

    def compose(self):
        # 菜单标题
        yield Static(f"  {self.fund_name}", classes="menu-title")
        yield Static("─" * 20, classes="menu-separator")

        # 菜单项
        for idx, (label, action, key) in enumerate(self.menu_items):
            if action == "separator":
                yield Static("─" * 20, classes="menu-separator")
            else:
                key_hint = f" [{key}]" if key else ""
                classes = "menu-item"
                if idx == self.selected_index:
                    classes += " selected"
                yield Static(f"  {label}{key_hint}", id=f"menu-item-{idx}", classes=classes)

    def action_close(self):
        """关闭菜单"""
        self.remove()

    def action_move_up(self):
        """上移选择"""
        self.selected_index = max(0, self.selected_index - 1)
        self._update_selection()

    def action_move_down(self):
        """下移选择"""
        valid_items = [i for i, item in enumerate(self.menu_items) if item[1] != "separator"]
        self.selected_index = min(valid_items[-1], self.selected_index + 1)
        self._update_selection()

    def action_select(self):
        """选择当前项"""
        valid_items = [
            (idx, item) for idx, item in enumerate(self.menu_items) if item[1] != "separator"
        ]
        for idx, (_, action, _) in valid_items:
            if idx == self.selected_index:
                self.post_message(self.MenuSelected(action, self.fund_code))
                break
        self.remove()

    def _update_selection(self):
        """更新选择状态显示"""
        for idx, (_, action, _) in enumerate(self.menu_items):
            if action != "separator":
                item = self.query_one(f"#menu-item-{idx}", Static)
                if idx == self.selected_index:
                    item.update(f"▶ {item.renderable[2:]}")  # 添加选中标记
                else:
                    item.update(f"  {item.renderable[2:]}")

    class MenuSelected(Message):
        """菜单选择消息"""
        def __init__(self, action: str, fund_code: str):
            self.action = action
            self.fund_code = fund_code
            super().__init__()
```

### Step 3: 修改FundTable添加菜单触发

**File:** `src/ui/tables.py` (FundTable类追加)

```python
class FundTable(DataTable):
    # ... 现有代码 ...

    def _on_click(self, event: events.Click) -> None:
        """处理点击事件 - 弹出上下文菜单"""
        # 延迟弹出菜单，等待事件完成
        self.app.call_later(self._show_context_menu)

    def _show_context_menu(self):
        """显示上下文菜单"""
        cursor_row = self.cursor_row
        if cursor_row < len(self.funds):
            fund = self.funds[cursor_row]
            has_holding = fund.hold_shares and fund.hold_shares > 0

            # 检查是否已存在菜单
            existing = self.app._safe_query("#fund-context-menu")
            if existing:
                existing.remove()

            # 挂载菜单
            from .menus import FundContextMenu
            self.app.mount(FundContextMenu(fund.code, fund.name, has_holding))
```

### Step 4: 修改App处理菜单消息

**File:** `src/ui/app.py` (在action方法后添加)

```python
# 在FundTUIApp类中添加消息处理
def on_fund_context_menu_selected(self, event: "FundContextMenu.MenuSelected") -> None:
    """处理基金菜单选择"""
    action = event.action
    fund_code = event.fund_code

    # 查找选中的基金
    fund = None
    for f in self.funds:
        if f.code == fund_code:
            fund = f
            break

    if fund is None:
        return

    # 执行对应操作
    if action == "view_detail":
        self.push_screen(FundDetailScreen(fund))
    elif action == "show_chart":
        asyncio.create_task(self._show_fund_chart(fund.code, fund.name))
    elif action == "set_holding":
        # 打开持仓对话框
        self._is_opening_dialog = True
        from .dialogs import HoldingDialog
        current_shares = fund.hold_shares if hasattr(fund, 'hold_shares') else 0.0
        current_cost = fund.cost if hasattr(fund, 'cost') else 0.0
        self.mount(HoldingDialog(fund.code, fund.name, current_shares, current_cost))
    elif action == "delete":
        # 删除基金
        from config.manager import ConfigManager
        config_manager = ConfigManager()
        if config_manager.remove_watchlist(fund_code):
            self.notify(f"已从自选移除: {fund.name}", severity="information")
            if fund_code in self._fund_codes:
                self._fund_codes.remove(fund_code)
                asyncio.create_task(self.load_fund_data())
```

### Step 5: 测试验证

```bash
# 运行应用
./run_tui.py

# 验证项目:
# 1. 基金表格显示"持仓"列，有持仓显示"●"
# 2. 选中基金按Enter，弹出右键菜单
# 3. 上下键在菜单中移动选择
# 4. 按Enter执行选中操作
# 5. 按Esc关闭菜单
# 6. 菜单项功能正常（详情、图表、持仓、删除）
```

---

## 任务3：创建基金详情页

**Files:**
- Create: `src/ui/fund_detail_screen.py` (详情页Screen)
- Modify: `src/ui/__init__.py` (导出新组件)
- Modify: `src/ui/app.py` (导入和使用详情页)

### Step 1: 创建FundDetailScreen

**File:** `src/ui/fund_detail_screen.py` (新建)

```python
# -*- coding: UTF-8 -*-
"""基金详情页Screen - 展示基金详细信息和图表"""

import asyncio
from textual.screen import Screen
from textual.widgets import Static, Button, Label
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.message import Message
from textual.app import ComposeResult
from textual.reactive import reactive
from .models import FundData, FundHistoryData
from .charts import ChartPreview


class FundDetailScreen(Screen):
    """基金详情页面"""

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("escape", "app.pop_screen", "返回"),
        ("q", "app.pop_screen", "返回"),
        ("h", "set_holding", "持仓设置"),
        ("g", "show_chart", "净值图表"),
        ("r", "refresh", "刷新数据"),
        ("up", "focus_prev", "上移"),
        ("down", "focus_next", "下移"),
    ]

    def __init__(self, fund: FundData):
        super().__init__(id="fund-detail-screen")
        self.fund = fund
        self.history_data: FundHistoryData | None = None

    def compose(self) -> ComposeResult:
        # 顶部：返回按钮 + 基金标题
        yield Horizontal(
            Button("< 返回", id="back-btn", variant="default"),
            Static(f"[b]{self.fund.name}[/b] ({self.fund.code})", classes="detail-title"),
            id="detail-header"
        )

        # 主体内容
        yield Horizontal(
            # 左侧：基金基本信息
            Vertical(
                Static("基本信息", classes="section-title"),
                Grid(
                    Label("单位净值:", classes="label"),
                    Static(f"{self.fund.net_value:.4f}", id="net-value", classes="value"),
                    Label("估算净值:", classes="label"),
                    Static(f"{self.fund.est_value:.4f}", id="est-value", classes="value"),
                    Label("估算涨跌:", classes="label"),
                    Static(f"{self.fund.change_pct:+.2f}%", id="change-pct", classes="value"),
                    Label("持仓份额:", classes="label"),
                    Static(f"{self.fund.hold_shares:.2f}" if self.fund.hold_shares else "0.00",
                          id="hold-shares", classes="value"),
                    Label("持仓成本:", classes="label"),
                    Static(f"{self.fund.cost:.4f}" if self.fund.cost else "0.0000",
                          id="hold-cost", classes="value"),
                    Label("持仓盈亏:", classes="label"),
                    Static(f"{self.fund.profit:+.2f}" if self.fund.profit else "0.00",
                          id="profit", classes="value profit-positive" if self.fund.profit and self.fund.profit > 0 else "value profit-negative"),
                    classes="info-grid"
                ),
                id="left-panel"
            ),
            # 右侧：迷你图表 + 操作按钮
            Vertical(
                Static("净值走势", classes="section-title"),
                ChartPreview(id="mini-chart"),
                Horizontal(
                    Button("持仓设置 (h)", id="holding-btn"),
                    Button("完整图表 (g)", id="chart-btn"),
                    Button("刷新 (r)", id="refresh-btn"),
                    classes="action-buttons"
                ),
                id="right-panel"
            ),
            id="detail-content"
        )

        # 底部：快捷键提示
        yield Horizontal(
            Static("[Esc/q]返回  [h]持仓设置  [g]净值图表  [r]刷新", classes="help-hint"),
            id="detail-footer"
        )

    def on_mount(self) -> None:
        """页面挂载时加载历史数据"""
        # 异步加载历史数据用于图表
        asyncio.create_task(self._load_history())

    async def _load_history(self):
        """加载基金历史数据"""
        try:
            from src.datasources.fund_source import FundHistorySource
            history_source = FundHistorySource()
            result = await history_source.fetch(self.fund.code, period="近一年")

            if result.success and result.data:
                history_list = result.data.get("history", [])
                if history_list:
                    from .models import FundHistoryData
                    self.history_data = FundHistoryData(
                        fund_code=self.fund.code,
                        fund_name=self.fund.name,
                        dates=[item["date"] for item in history_list],
                        net_values=[item["net_value"] for item in history_list],
                        accumulated_net=[item.get("accumulated_net") for item in history_list]
                    )
                    # 更新迷你图表
                    chart = self.query_one("#mini-chart", ChartPreview)
                    chart.update_preview(self.history_data, width=50, height=8)
        except Exception as e:
            self.app.log(f"加载历史数据失败: {e}")

    def action_set_holding(self) -> None:
        """打开持仓设置"""
        from .dialogs import HoldingDialog
        self.app._is_opening_dialog = True
        current_shares = self.fund.hold_shares or 0.0
        current_cost = self.fund.cost or 0.0
        self.app.mount(HoldingDialog(self.fund.code, self.fund.name, current_shares, current_cost))

    def action_show_chart(self) -> None:
        """显示完整图表"""
        if self.history_data:
            from .charts import ChartDialog
            self.app.mount(ChartDialog(self.fund.code, self.fund.name, self.history_data))
        else:
            self.notify("正在加载历史数据，请稍候...", severity="information")
            asyncio.create_task(self._load_history())
            # 等待加载完成后显示
            async def wait_and_show():
                await asyncio.sleep(2)
                if self.history_data:
                    from .charts import ChartDialog
                    self.app.mount(ChartDialog(self.fund.code, self.fund.name, self.history_data))
            asyncio.create_task(wait_and_show())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "holding-btn":
            self.action_set_holding()
        elif event.button.id == "chart-btn":
            self.action_show_chart()
        elif event.button.id == "refresh-btn":
            asyncio.create_task(self._refresh_data())

    async def _refresh_data(self):
        """刷新基金数据"""
        self.notify("正在刷新数据...", severity="information")
        # 重新加载基金数据
        await self.app.load_fund_data()
        # 重新加载历史数据
        await self._load_history()
        self.notify("数据已刷新", severity="success")
```

### Step 2: 添加详情页样式

**File:** `src/ui/styles.tcss` (追加)

```css
/* 基金详情页样式 */
#fund-detail-screen {
    width: 100%;
    height: 100%;
}

.detail-title {
    color: $primary;
    text-style: bold;
    font-size: 16;
}

#detail-header {
    height: 2;
    background: $surface;
    padding: 0 1;
    align: center middle;
}

.section-title {
    color: $primary;
    text-style: bold;
    height: auto;
    margin-bottom: 1;
}

#detail-content {
    height: auto;
    flex-grow: 1;
}

#left-panel {
    width: 50%;
    height: 100%;
    border: solid $panel;
    padding: 1;
}

#right-panel {
    width: 50%;
    height: 100%;
    border: solid $panel;
    border-left: none;
    padding: 1;
}

.info-grid {
    layout: grid;
    grid-size: 2;
    grid-columns: 1fr 1fr;
    row-gap: 1;
    column-gap: 1;
}

.info-grid .label {
    color: $foreground-muted;
    width: 10;
}

.info-grid .value {
    color: $foreground;
}

.profit-positive {
    color: $success;
}

.profit-negative {
    color: $error;
}

.action-buttons {
    margin-top: 2;
    align: center middle;
    spacing: 2;
}

#detail-footer {
    height: 1;
    background: $panel;
    color: $foreground-muted;
    padding: 0 2;
}

.help-hint {
    color: $foreground-muted;
    font-size: 8;
}
```

### Step 3: 导出组件

**File:** `src/ui/__init__.py`

```python
from .app import FundTUIApp
from .tables import FundTable
from .widgets import CommodityPairView, NewsList, StatPanel
from .charts import ChartDialog
from .dialogs import AddFundDialog, HoldingDialog
from .fund_detail_screen import FundDetailScreen  # 新增

__all__ = [
    "FundTUIApp",
    "FundTable",
    "CommodityPairView",
    "NewsList",
    "StatPanel",
    "ChartDialog",
    "AddFundDialog",
    "HoldingDialog",
    "FundDetailScreen",  # 新增
]
```

### Step 4: 测试验证

```bash
# 运行应用
./run_tui.py

# 验证项目:
# 1. 选中基金按Enter，进入详情页
# 2. 显示基金代码、名称
# 3. 显示净值、估值、涨跌幅
# 4. 显示持仓信息（份额、成本、盈亏）
# 5. 显示迷你净值图表
# 6. 按h打开持仓设置对话框
# 7. 按g显示完整图表
# 8. 按r刷新数据
# 9. 按Esc/q返回主界面
# 10. 切换基金后信息更新
```

---

## 任务4：测试和优化UI交互

**Files:**
- Modify: `src/ui/app.py` (问题修复)
- Modify: `src/ui/styles.tcss` (样式优化)
- Create: `tests/test_tui.py` (自动化测试)

### Step 1: 编写TUI自动化测试

**File:** `tests/test_tui.py` (新建)

```python
# -*- coding: UTF-8 -*-
"""TUI应用自动化测试"""

import pytest
from textual.app import App
from textual.widgets import Static, DataTable


class TestFundTUI:
    """基金TUI应用测试类"""

    @pytest.fixture
    def app(self):
        """创建测试应用实例"""
        from src.ui.app import FundTUIApp
        return FundTUIApp()

    def test_app_initial_state(self, app):
        """测试应用初始状态"""
        assert app.active_view == "fund"
        assert app.is_dark_theme == True

    def test_fund_table_columns(self):
        """测试基金表格列"""
        from src.ui.tables import FundTable
        table = FundTable()
        # 验证列定义存在
        assert table is not None

    def test_fund_data_model(self):
        """测试基金数据模型"""
        from src.ui.models import FundData
        fund = FundData(
            code="161039",
            name="测试基金",
            net_value=1.0000,
            est_value=1.0100,
            change_pct=1.0,
            profit=100.0,
            hold_shares=1000.0,
            cost=1.0000
        )
        assert fund.code == "161039"
        assert fund.hold_shares == 1000.0


def test_app_compose():
    """测试应用Compose"""
    from src.ui.app import FundTUIApp
    app = FundTUIApp()
    # 测试能够正常compose
    assert app is not None


def test_tabbed_content_import():
    """测试TabbedContent导入"""
    from textual.widgets import TabbedContent, TabPane
    assert TabbedContent is not None
    assert TabPane is not None


def test_screen_import():
    """测试Screen导入"""
    from textual.screen import Screen
    assert Screen is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Step 2: 运行测试

```bash
# 运行所有测试
pytest tests/test_tui.py -v

# 运行特定测试
pytest tests/test_tui.py::TestFundTUI::test_app_initial_state -v
```

### Step 3: 手动功能测试清单

```markdown
## 功能测试清单

### 标签页功能
- [ ] 默认显示基金标签页
- [ ] 点击商品标签切换
- [ ] 点击新闻标签切换
- [ ] 按1/2/3切换标签
- [ ] 按Tab循环切换
- [ ] 按left/right箭头切换
- [ ] 主题切换正常

### 基金表格功能
- [ ] 显示基金列表
- [ ] 显示"持仓"列
- [ ] 有持仓显示"●"
- [ ] 上下键移动光标
- [ ] Enter进入详情页
- [ ] 右键弹出菜单

### 右键菜单功能
- [ ] 菜单显示基金名称
- [ ] 上下键移动选择
- [ ] Enter执行操作
- [ ] Esc关闭菜单
- [ ] 查看详情功能
- [ ] 持仓设置功能
- [ ] 净值图表功能
- [ ] 删除自选功能

### 详情页功能
- [ ] 进入详情页
- [ ] 显示基本信息
- [ ] 显示持仓信息
- [ ] 显示迷你图表
- [ ] 持仓设置按钮
- [ ] 完整图表按钮
- [ ] 刷新按钮
- [ ] Esc返回
- [ ] q返回
- [ ] 切换基金更新

### 对话框功能
- [ ] 添加基金对话框
- [ ] 持仓设置对话框
- [ ] 图表对话框
```

---

## 依赖关系

```
任务1: 完善标签页
  └─ 任务2: 基金功能 (依赖任务1的TabPane容器)
      └─ 任务3: 详情页 (依赖任务2的导航逻辑)
          └─ 任务4: 测试优化 (依赖所有任务)
```

---

## 执行顺序

1. **任务1**: 完善TUI主界面标签页 (基础)
2. **任务2**: 实现基金标签页功能 (依赖1)
3. **任务3**: 创建基金详情页 (依赖2)
4. **任务4**: 测试和优化UI交互 (依赖1-3)

---

## 注意事项

1. **回滚策略**: 每个任务完成后测试验证，如有问题可git回滚
2. **性能考虑**: 历史数据异步加载，避免阻塞UI
3. **主题兼容**: 所有样式使用CSS变量，支持深色/浅色主题
4. **键盘导航**: 确保所有功能都有键盘操作支持
