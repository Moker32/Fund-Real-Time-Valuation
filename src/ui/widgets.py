# -*- coding: UTF-8 -*-
"""自定义 UI 组件模块"""

from textual.widget import Widget
from textual.widgets import DataTable, Static, ListView, ListItem, Label, Button
from textual.color import Color
from dataclasses import dataclass
from typing import List, Optional


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
[r]       - 手动刷新
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
