"""
商品数据源模块 - 向后兼容垫片

此文件是 commodity/ 子包的向后兼容垫片。
新代码请直接从 commodity 子包导入：
    from src.datasources.commodity import CommodityRealtimeSource

旧导入路径（此文件）仍然可用：
    from src.datasources.commodity_source import CommodityRealtimeSource
"""

# 重新导出所有类，保持旧导入路径兼容
from src.datasources.commodity import (
    MAX_CACHE_SIZE,
    MAX_RETRIES,
    SEARCHABLE_COMMODITIES,
    CommodityDataAggregator,
    CommodityDataSource,
    CommodityRealtimeSource,
    CommoditySearchResponse,
    CommoditySearchResult,
    get_all_available_commodities,
    get_all_commodity_types,
    get_commodities_by_category,
    identify_category,
    search_commodities,
)

__all__ = [
    "CommodityDataSource",
    "CommodityRealtimeSource",
    "CommodityDataAggregator",
    "CommoditySearchResult",
    "CommoditySearchResponse",
    "SEARCHABLE_COMMODITIES",
    "get_all_commodity_types",
    "get_commodities_by_category",
    "identify_category",
    "search_commodities",
    "get_all_available_commodities",
    "MAX_RETRIES",
    "MAX_CACHE_SIZE",
]
