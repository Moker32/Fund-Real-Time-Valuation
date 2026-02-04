# -*- coding: UTF-8 -*-
"""表格组件模块"""

from textual.widgets import DataTable
from typing import List, Optional
from .models import FundData, CommodityData, SectorData


class FundTable(DataTable):
    """基金数据表格组件"""

    BINDINGS = [
        ("enter", "view_detail", "查看详情"),
        ("a", "add", "添加"),
        ("d", "delete", "删除"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.funds: List[FundData] = []

    def on_mount(self):
        self.add_column("代码", width=10)
        self.add_column("名称", width=20)
        self.add_column("净值", width=12)
        self.add_column("估值", width=12)
        self.add_column("涨跌", width=10)
        self.add_column("持仓", width=8)
        self.add_column("持仓盈亏", width=14)

    def update_funds(self, funds: List[FundData]):
        """更新基金数据"""
        self.funds = funds
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
                holding_mark,
                f"{fund.profit:+.2f}" if fund.profit else "N/A",
            )

    def on_click(self, event):
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
            existing = self.app.query_one("#fund-context-menu", default=None)
            if existing is not None:
                try:
                    existing.remove()
                except:
                    pass

            # 挂载菜单
            from .menus import FundContextMenu
            self.app.mount(FundContextMenu(fund.code, fund.name, has_holding))


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
        self.current_category: Optional[str] = None

    def on_mount(self):
        self.add_column("板块", width=16)
        self.add_column("类别", width=10)
        self.add_column("点位", width=12)
        self.add_column("涨跌", width=10)
        self.add_column("状态", width=8)

    def update_sectors(self, sectors: List[SectorData], category: Optional[str] = None):
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
