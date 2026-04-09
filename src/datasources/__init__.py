"""
数据源模块

提供多类型数据源的统一访问接口:
- 基金数据源 (fund_source)
- 商品数据源 (commodity_source)

- 数据源管理器 (manager)
- 数据网关 (gateway)

使用示例:
    from src.datasources import (
        TiantianFundDataSource,
        AKShareCommoditySource,
        DataSourceManager,
        DataGateway,
    )

    # 创建单个数据源
    fund_source = TiantianFundDataSource()
    result = await fund_source.fetch("161039")

    # 使用管理器
    manager = create_default_manager()
    result = await manager.fetch(DataSourceType.FUND, "161039")

    # 使用网关
    gateway = DataGateway(manager)
    result = await gateway.get_fund("161039")
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
from .cache_cleaner import CacheCleaner, get_cache_cleaner, startup_cleanup
from .commodity_source import (
    AKShareCommoditySource,
    CommodityDataAggregator,
    CommodityDataSource,
    YFinanceCommoditySource,
)
from .fund import Fund123DataSource, TiantianFundDataSource, SinaFundDataSource, EastMoneyFundDataSource
from .gateway import (
    BatchDataRequest,
    BatchDataResponse,
    DataGateway,
    DataRequest,
    DataResponse,
    GatewayStats,
    RequestPriority,
    ResponseStatus,
)
from .hot_backup import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitConfig,
    CircuitState,
    HotBackupManager,
    HotBackupResult,
)
from .manager import DataSourceConfig, DataSourceManager, create_default_manager

__all__ = [
    # 基础类
    "DataSource",
    "DataSourceType",
    "DataSourceResult",
    "DataSourceError",
    "NetworkError",
    "DataParseError",
    "DataSourceUnavailableError",
    # 统一请求/响应模型
    "DataRequest",
    "DataResponse",
    "BatchDataRequest",
    "BatchDataResponse",
    "RequestPriority",
    "ResponseStatus",
    # 数据网关
    "DataGateway",
    "GatewayStats",
    "CircuitConfig",
    # 熔断器
    "CircuitBreaker",
    "CircuitBreakerManager",
    "CircuitState",
    # 热备份
    "HotBackupManager",
    "HotBackupResult",
    # 基金数据源
    "TiantianFundDataSource",
    "SinaFundDataSource",
    "Fund123DataSource",
    # 商品数据源
    "CommodityDataSource",
    "YFinanceCommoditySource",
    "AKShareCommoditySource",
    "CommodityDataAggregator",
    # 数据聚合器
    "DataAggregator",
    "SameSourceAggregator",
    "LoadBalancedAggregator",
    "AggregatorSourceInfo",
    # 管理器
    "DataSourceManager",
    "DataSourceConfig",
    "create_default_manager",
    # 缓存清理器
    "CacheCleaner",
    "get_cache_cleaner",
    "startup_cleanup",
]


__version__ = "0.0.1"
