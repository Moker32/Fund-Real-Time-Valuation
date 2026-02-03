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

from .base import (
    DataSource,
    DataSourceType,
    DataSourceResult,
    DataSourceError,
    NetworkError,
    DataParseError,
    DataSourceUnavailableError
)

from .fund_source import (
    FundDataSource,
    SinaFundDataSource
)

from .commodity_source import (
    CommodityDataSource,
    YFinanceCommoditySource,
    AKShareCommoditySource,
    CommodityDataAggregator
)

from .news_source import (
    SinaNewsDataSource,
    NewsAggregatorDataSource
)

from .bond_source import (
    SinaBondDataSource,
    AKShareBondSource,
    EastMoneyBondSource
)

from .manager import (
    DataSourceManager,
    DataSourceConfig,
    create_default_manager
)

from .aggregator import (
    DataAggregator,
    SameSourceAggregator,
    LoadBalancedAggregator,
    AggregatorSourceInfo
)

from .portfolio import (
    AssetType,
    PortfolioPosition,
    PortfolioAllocation,
    PortfolioResult,
    PortfolioAnalyzer
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
    "create_default_manager"
]


__version__ = "0.0.1"
