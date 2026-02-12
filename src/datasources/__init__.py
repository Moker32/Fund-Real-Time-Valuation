"""
数据源模块

提供多类型数据源的统一访问接口:
- 基金数据源 (fund_source)
- 商品数据源 (commodity_source)
- 债券数据源 (bond_source)
- 新闻数据源 (news_source)
- 数据源管理器 (manager)

使用示例:
    from src.datasources import (
        FundDataSource,
        AKShareCommoditySource,
        SinaNewsDataSource,
        DataSourceManager
    )

    # 创建单个数据源
    fund_source = FundDataSource()
    result = await fund_source.fetch("161039")

    # 使用管理器
    manager = create_default_manager()
    result = await manager.fetch(DataSourceType.FUND, "161039")
"""

from .aggregator import (
    AggregatorSourceInfo,
    DataAggregator,
    LoadBalancedAggregator,
    SameSourceAggregator,
)
from .base import (
    DataParseError,
    DataSource,
    DataSourceError,
    DataSourceResult,
    DataSourceType,
    DataSourceUnavailableError,
    NetworkError,
)
from .bond_source import AKShareBondSource, EastMoneyBondSource, SinaBondDataSource
from .cache_cleaner import CacheCleaner, get_cache_cleaner, startup_cleanup
from .commodity_source import (
    AKShareCommoditySource,
    CommodityDataAggregator,
    CommodityDataSource,
    YFinanceCommoditySource,
)
from .fund_source import Fund123DataSource, FundDataSource, SinaFundDataSource
from .manager import DataSourceConfig, DataSourceManager, create_default_manager
from .news_source import NewsAggregatorDataSource, SinaNewsDataSource
from .portfolio import (
    AssetType,
    PortfolioAllocation,
    PortfolioAnalyzer,
    PortfolioPosition,
    PortfolioResult,
)

__all__ = [
    # 基础类
    "DataSource",
    "DataSourceType",
    "DataSourceResult",
    "DataSourceError",
    "NetworkError",
    "DataParseError",
    "DataSourceUnavailableError",

    # 基金数据源
    "FundDataSource",
    "SinaFundDataSource",
    "Fund123DataSource",

    # 商品数据源
    "CommodityDataSource",
    "YFinanceCommoditySource",
    "AKShareCommoditySource",
    "CommodityDataAggregator",

    # 新闻数据源
    "SinaNewsDataSource",
    "NewsAggregatorDataSource",

    # 债券数据源
    "SinaBondDataSource",
    "AKShareBondSource",
    "EastMoneyBondSource",

    # 数据聚合器
    "DataAggregator",
    "SameSourceAggregator",
    "LoadBalancedAggregator",
    "AggregatorSourceInfo",

    # 组合分析器
    "AssetType",
    "PortfolioPosition",
    "PortfolioAllocation",
    "PortfolioResult",
    "PortfolioAnalyzer",

    # 管理器
    "DataSourceManager",
    "DataSourceConfig",
    "create_default_manager",

    # 缓存清理器
    "CacheCleaner",
    "get_cache_cleaner",
    "startup_cleanup"
]


__version__ = "0.0.1"
