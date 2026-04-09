"""
全球市场指数数据源模块 - 向后兼容垫片

此文件是 index/ 子包的向后兼容垫片。
新代码请直接从 index 子包导入：
    from src.datasources.index import HybridIndexSource

旧导入路径（此文件）仍然可用：
    from src.datasources.index_source import HybridIndexSource
"""

# 重新导出所有类，保持旧导入路径兼容
from src.datasources.index import (
    AKShareIndexSource,
    HybridIndexSource,
    IndexDataSource,
    TencentIndexSource,
    YahooIndexSource,
)

# 重新导出常量（兼容旧代码）
from src.datasources.index.base import (
    AKSHARE_INDEX_CODES,
    INDEX_NAMES,
    INDEX_REGIONS,
    INDEX_TICKERS,
    MARKET_HOURS,
    TENCENT_CODES,
    YAHOO_TICKERS,
    uses_tencent,
)

__all__ = [
    "IndexDataSource",
    "YahooIndexSource",
    "TencentIndexSource",
    "AKShareIndexSource",
    "HybridIndexSource",
    "TENCENT_CODES",
    "YAHOO_TICKERS",
    "INDEX_TICKERS",
    "AKSHARE_INDEX_CODES",
    "INDEX_REGIONS",
    "INDEX_NAMES",
    "MARKET_HOURS",
    "uses_tencent",
]
