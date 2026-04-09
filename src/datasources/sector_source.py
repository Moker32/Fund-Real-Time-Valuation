"""
行业板块数据源模块 - 向后兼容垫片

此文件是 sector/ 子包的向后兼容垫片。
新代码请直接从 sector 子包导入：
    from src.datasources.sector import SinaSectorDataSource

旧导入路径（此文件）仍然可用：
    from src.datasources.sector_source import SinaSectorDataSource
"""

# 重新导出所有类，保持旧导入路径兼容
from src.datasources.sector import (
    EastMoneyConceptDetailSource,
    EastMoneyDirectSource,
    EastMoneyIndustryDetailSource,
    EastMoneySectorDataSource,
    EastMoneySectorSource,
    FundFlowConceptSource,
    FundFlowIndustrySource,
    SectorDataAggregator,
    SinaSectorDataSource,
    get_last_trading_day,
    is_trading_day,
)

__all__ = [
    "SinaSectorDataSource",
    "EastMoneySectorDataSource",
    "SectorDataAggregator",
    "EastMoneyDirectSource",
    "EastMoneySectorSource",
    "EastMoneyIndustryDetailSource",
    "EastMoneyConceptDetailSource",
    "FundFlowConceptSource",
    "FundFlowIndustrySource",
    "get_last_trading_day",
    "is_trading_day",
]
