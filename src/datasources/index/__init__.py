"""
全球市场指数数据源模块

提供多种指数数据源：
- Yahoo Finance (YahooIndexSource)
- 腾讯财经 (TencentIndexSource)
- AKShare (AKShareIndexSource)
- 混合数据源 (HybridIndexSource) - 自动选择最佳数据源

常量:
- TENCENT_CODES, YAHOO_TICKERS, INDEX_TICKERS, AKSHARE_INDEX_CODES
- INDEX_REGIONS, INDEX_NAMES
- uses_tencent()

使用示例:
    from src.datasources.index import HybridIndexSource

    source = HybridIndexSource()
    result = await source.fetch("shanghai")
"""

from .akshare_source import AKShareIndexSource
from .base import (
    AKSHARE_INDEX_CODES,
    INDEX_NAMES,
    INDEX_REGIONS,
    INDEX_TICKERS,
    TENCENT_CODES,
    YAHOO_TICKERS,
    IndexDataSource,
    uses_tencent,
)
from .hybrid_source import HybridIndexSource
from .tencent_source import TencentIndexSource
from .yahoo_source import YahooIndexSource

__all__ = [
    # 基类
    "IndexDataSource",
    # 数据源
    "YahooIndexSource",
    "TencentIndexSource",
    "AKShareIndexSource",
    "HybridIndexSource",
    # 常量
    "TENCENT_CODES",
    "YAHOO_TICKERS",
    "INDEX_TICKERS",
    "AKSHARE_INDEX_CODES",
    "INDEX_REGIONS",
    "INDEX_NAMES",
    "uses_tencent",
]
