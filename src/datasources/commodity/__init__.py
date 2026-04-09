"""
商品数据源模块

提供多种商品数据源：
- YFinanceCommoditySource: 国际商品期货 + 加密货币
- AKShareCommoditySource: 国内黄金 (上海黄金交易所)
- AKShareForeignFuturesSource: 外盘期货 (LME/NYMEX/CBOT等)
- CommodityDataAggregator: 多数据源聚合器

辅助函数:
- get_all_commodity_types()
- get_commodities_by_category()
"""

from .aggregator import (
    SEARCHABLE_COMMODITIES,
    CommodityDataAggregator,
    get_all_available_commodities,
    get_all_commodity_types,
    get_commodities_by_category,
    identify_category,
    search_commodities,
)
from .akshare_source import AKShareCommoditySource
from .base import (
    MAX_CACHE_SIZE,
    MAX_RETRIES,
    CommodityDataSource,
    CommoditySearchResponse,
    CommoditySearchResult,
)
from .foreign_source import (
    FOREIGN_FUTURES_NAMES,
    FOREIGN_FUTURES_REVERSE,
    FOREIGN_FUTURES_TICKERS,
    AKShareForeignFuturesSource,
)
from .yfinance_source import YFinanceCommoditySource

__all__ = [
    # 基类
    "CommodityDataSource",
    # 数据源
    "YFinanceCommoditySource",
    "AKShareCommoditySource",
    "AKShareForeignFuturesSource",
    "CommodityDataAggregator",
    # 外盘常量
    "FOREIGN_FUTURES_TICKERS",
    "FOREIGN_FUTURES_REVERSE",
    "FOREIGN_FUTURES_NAMES",
    # 搜索
    "SEARCHABLE_COMMODITIES",
    "CommoditySearchResult",
    "CommoditySearchResponse",
    # 辅助函数
    "get_all_commodity_types",
    "get_commodities_by_category",
    "identify_category",
    "search_commodities",
    "get_all_available_commodities",
    # 配置常量
    "MAX_RETRIES",
    "MAX_CACHE_SIZE",
]
