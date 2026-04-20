"""
商品数据源模块

提供单一商品数据源：
- CommodityDataSource: 商品数据源基类
- CommodityDataAggregator: 多数据源聚合器
- CommodityRealtimeSource: akshare 国际大宗商品实时行情 + Binance BTC

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
from .base import (
    MAX_CACHE_SIZE,
    MAX_RETRIES,
    CommodityDataSource,
    CommoditySearchResponse,
    CommoditySearchResult,
)
from .akshare_source import CommodityRealtimeSource

__all__ = [
    # 基类
    "CommodityDataSource",
    # 数据源
    "CommodityRealtimeSource",
    "CommodityDataAggregator",
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
