# -*- coding: UTF-8 -*-
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
