# -*- coding: UTF-8 -*-
"""自定义 UI 组件模块"""

from textual.widget import Widget
from textual.message import Message
from textual.widgets import DataTable, Static, ListView, ListItem, Label, Button, Input, TextArea
from textual.containers import Container, Vertical, Horizontal
from textual.color import Color
from typing import List, Optional
import math
from datetime import datetime

from .models import FundData, CommodityData, NewsData, SectorData, FundHistoryData

from .tables import FundTable, CommodityTable, SectorTable

# 从对话框模块导入对话框类
from .dialogs import AddFundDialog, HoldingDialog

# 从图表模块导入图表组件
from .charts import ChartDialog, ChartPreview


# ==================== 自定义组件 ====================

class CommodityPairView(Static):
    """商品横向对比视图 - 以成对形式显示商品"""

    DEFAULT_CSS = """
    CommodityPairView {
        height: auto;
        layout: vertical;
    }
    CommodityPairView .pair-row {
        height: auto;
        margin-bottom: 0;
    }
    CommodityPairView .pair-separator {
        color: gray;
        margin: 0 1;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commodities: List[CommodityData] = []

    def compose(self):
        yield Static(id="commodity-pairs")

    def update_commodities(self, commodities: List[CommodityData]):
        """更新商品数据，以横向对比格式显示"""
        self.commodities = commodities

        if not commodities:
            self.query_one("#commodity-pairs", Static).update("暂无商品数据")
            return

        # 将商品配对显示
        pairs = []
        for i in range(0, len(commodities), 2):
            left = commodities[i]
            right = commodities[i + 1] if i + 1 < len(commodities) else None

            left_str = self._format_commodity(left)
            if right:
                right_str = self._format_commodity(right)
                pair_row = f"{left_str}  ←→  {right_str}"
            else:
                pair_row = left_str
            pairs.append(pair_row)

        content = "\n".join(pairs)
        self.query_one("#commodity-pairs", Static).update(content)

    def _format_commodity(self, commodity: CommodityData) -> str:
        """格式化单个商品"""
        change_str = f"{commodity.change_pct:+.2f}%"
        color = "green" if commodity.change_pct >= 0 else "red" if commodity.change_pct else "gray"
        return f"[{color}]{commodity.name}[/] {commodity.price:.2f} {change_str}"


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
    """统计信息面板 / 底部状态行"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_profit = 0.0
        self.fund_count = 0
        self.avg_change = 0.0
        self.data_source = "新浪财经"
        self.last_update = ""

    def compose(self):
        yield Static(id="stat-content")

    def update_stats(self, total_profit: float, fund_count: int, avg_change: float, data_source: str = "新浪财经", last_update: str = ""):
        """更新统计数据"""
        self.total_profit = total_profit
        self.fund_count = fund_count
        self.avg_change = avg_change
        self.data_source = data_source
        self.last_update = last_update

        profit_color = "green" if total_profit >= 0 else "red"
        change_color = "green" if avg_change >= 0 else "red"

        content = f"总收益: [{profit_color}]{total_profit:+.2f}[/] ([{change_color}]{avg_change:+.2f}%[/])  数据源: {data_source}  最后刷新: {last_update}"
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
