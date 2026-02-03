# -*- coding: UTF-8 -*-
"""屏幕模块 - 定义三个视图屏幕"""

from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, DataTable, ListView, ListItem, Label, Button
from textual import events
from typing import List, Optional, TYPE_CHECKING

from .widgets import FundTable, CommodityTable, NewsList, NewsItem, FundData, CommodityData, NewsData


class FundScreen(Screen):
    """基金视图屏幕"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.funds: List[FundData] = []

    def compose(self):
        """构建基金视图 UI"""
        yield Container(
            Vertical(
                Static("[b]基金列表[/b]", classes="screen-title"),
                FundTable(id="fund-table", classes="main-table"),
                classes="screen-content"
            ),
            id="fund-screen"
        )

    def on_mount(self):
        """屏幕挂载时初始化"""
        table = self.query_one("#fund-table", FundTable)
        table.focus()

    def update_funds(self, funds: List[FundData]):
        """更新基金数据"""
        self.funds = funds
        table = self.query_one("#fund-table", FundTable)
        table.update_funds(funds)


class CommodityScreen(Screen):
    """商品视图屏幕"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commodities: List[CommodityData] = []

    def compose(self):
        """构建商品视图 UI"""
        yield Container(
            Vertical(
                Static("[b]商品行情[/b]", classes="screen-title"),
                CommodityTable(id="commodity-table", classes="main-table"),
                classes="screen-content"
            ),
            id="commodity-screen"
        )

    def on_mount(self):
        """屏幕挂载时初始化"""
        table = self.query_one("#commodity-table", CommodityTable)
        table.focus()

    def update_commodities(self, commodities: List[CommodityData]):
        """更新商品数据"""
        self.commodities = commodities
        table = self.query_one("#commodity-table", CommodityTable)
        table.update_commodities(commodities)


class NewsScreen(Screen):
    """新闻视图屏幕"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.news_list: List[NewsData] = []

    def compose(self):
        """构建新闻视图 UI"""
        yield Container(
            Vertical(
                Static("[b]财经新闻[/b]", classes="screen-title"),
                NewsList(id="news-list", classes="main-list"),
                classes="screen-content"
            ),
            id="news-screen"
        )

    def on_mount(self):
        """屏幕挂载时初始化"""
        news_list = self.query_one("#news-list", NewsList)
        news_list.focus()

    def update_news(self, news_list: List[NewsData]):
        """更新新闻数据"""
        self.news_list = news_list
        news_widget = self.query_one("#news-list", NewsList)
        news_widget.update_news(news_list)


class HelpScreen(Screen):
    """帮助屏幕"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compose(self):
        """构建帮助视图 UI"""
        yield Container(
            Vertical(
                Static("[b]操作帮助[/b]", classes="screen-title"),
                Static(
                    """
[b]快捷键说明[/b]

[Tab]       切换视图
[a]         添加基金
[d]         删除选中基金
[r]         手动刷新数据
[F1]        显示/隐藏帮助
[Ctrl+C]    退出应用

[b]视图说明[/b]

[1] 基金视图 - 显示基金净值、估算值、涨跌幅
[2] 商品视图 - 显示商品价格及涨跌幅
[3] 新闻视图 - 显示最新财经新闻

[b]提示[/b]

按 [ESC] 返回主界面
                    """,
                    id="help-content",
                    classes="help-content"
                ),
                Button("返回 (ESC)", id="help-close-btn", classes="close-btn"),
                classes="screen-content"
            ),
            id="help-screen"
        )

    def on_mount(self):
        """屏幕挂载时初始化"""
        btn = self.query_one("#help-close-btn", Button)
        btn.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        if event.button.id == "help-close-btn":
            self.app.pop_screen()
