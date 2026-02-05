"""
数据源管理器
支持多数据源自动切换、负载均衡、健康检查等功能
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
from .base import (
    DataSource,
    DataSourceType,
    DataSourceResult,
    DataSourceError
)


@dataclass
class DataSourceConfig:
    """数据源配置"""
    source_class: Type[DataSource]
    name: str
    source_type: DataSourceType
    enabled: bool = True
    priority: int = 0  # 优先级，数值越小优先级越高
    config: Dict[str, Any] = field(default_factory=dict)


class DataSourceManager:
    """
    数据源管理器

    功能:
    - 注册和管理多个数据源
    - 支持多数据源自动切换 (failover)
    - 支持负载均衡 (round-robin)
    - 健康检查和状态监控
    - 请求限流
    """

    def __init__(self, max_concurrent: int = 10, enable_load_balancing: bool = False):
        """
        初始化数据源管理器

        Args:
            max_concurrent: 最大并发请求数
            enable_load_balancing: 是否启用负载均衡
        """
        self._sources: Dict[str, DataSource] = {}
        self._source_configs: Dict[str, DataSourceConfig] = {}
        self._type_sources: Dict[DataSourceType, List[str]] = {
            DataSourceType.FUND: [],
            DataSourceType.COMMODITY: [],
            DataSourceType.NEWS: [],
            DataSourceType.SECTOR: [],
            DataSourceType.STOCK: [],
            DataSourceType.BOND: [],
            DataSourceType.CRYPTO: []
        }
        self._max_concurrent = max_concurrent  # 延迟创建 semaphore
        self._semaphore: Optional[asyncio.Semaphore] = None  # 延迟初始化
        self._enable_load_balancing = enable_load_balancing
        self._round_robin_index: Dict[DataSourceType, int] = {
            DataSourceType.FUND: 0,
            DataSourceType.COMMODITY: 0,
            DataSourceType.NEWS: 0,
            DataSourceType.SECTOR: 0,
            DataSourceType.STOCK: 0,
            DataSourceType.BOND: 0,
            DataSourceType.CRYPTO: 0
        }
        self._request_history: List[Dict[str, Any]] = []
        self._max_history = 1000

    async def _get_semaphore(self) -> asyncio.Semaphore:
        """延迟初始化 semaphore"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrent)
        return self._semaphore

    def register(self, source: DataSource, config: Optional[DataSourceConfig] = None):
        """
        注册数据源

        Args:
            source: 数据源实例
            config: 可选的数据源配置
        """
        source_id = source.name

        if source_id in self._sources:
            raise ValueError(f"数据源 '{source_id}' 已注册")

        self._sources[source_id] = source
        self._type_sources[source.source_type].append(source_id)

        if config:
            self._source_configs[source_id] = config
        else:
            self._source_configs[source_id] = DataSourceConfig(
                source_class=type(source),
                name=source.name,
                source_type=source.source_type,
                enabled=True,
                priority=len(self._type_sources[source.source_type])
            )

    def unregister(self, source_name: str):
        """
        注销数据源

        Args:
            source_name: 数据源名称
        """
        if source_name not in self._sources:
            raise ValueError(f"数据源 '{source_name}' 未注册")

        source = self._sources.pop(source_name)
        self._type_sources[source.source_type].remove(source_name)
        self._source_configs.pop(source_name, None)

    def get_source(self, source_name: str) -> Optional[DataSource]:
        """
        获取指定数据源

        Args:
            source_name: 数据源名称

        Returns:
            DataSource: 数据源实例，不存在返回 None
        """
        return self._sources.get(source_name)

    def get_sources_by_type(self, source_type: DataSourceType) -> List[DataSource]:
        """
        按类型获取数据源列表

        Args:
            source_type: 数据源类型

        Returns:
            List[DataSource]: 数据源列表
        """
        return [self._sources[name] for name in self._type_sources[source_type]]

    async def fetch(
        self,
        source_type: DataSourceType,
        *args,
        failover: bool = True,
        **kwargs
    ) -> DataSourceResult:
        """
        获取数据（自动选择数据源）

        Args:
            source_type: 数据源类型
            *args: 位置参数传递给数据源
            failover: 是否启用故障切换
            **kwargs: 关键字参数传递给数据源

        Returns:
            DataSourceResult: 第一个成功的数据源结果
        """
        async with await self._get_semaphore():
            sources = self._get_ordered_sources(source_type)
            errors = []

            for source in sources:
                if not self._source_configs.get(source.name, DataSourceConfig(
                    source_class=type(source),
                    name=source.name,
                    source_type=source.source_type
                )).enabled:
                    continue

                try:
                    result = await source.fetch(*args, **kwargs)

                    # 记录请求
                    self._record_request(source.name, source_type, result)

                    if result.success:
                        return result

                    errors.append(f"{source.name}: {result.error}")

                except Exception as e:
                    errors.append(f"{source.name}: {str(e)}")
                    self._record_request(source.name, source_type, None, error=str(e))

            # 所有数据源都失败
            if failover and errors:
                return DataSourceResult(
                    success=False,
                    error=f"所有数据源均失败: {'; '.join(errors)}",
                    timestamp=time.time(),
                    source="manager",
                    metadata={"source_type": source_type.value, "errors": errors}
                )

            return DataSourceResult(
                success=False,
                error="没有可用的数据源",
                timestamp=time.time(),
                source="manager",
                metadata={"source_type": source_type.value}
            )

    async def fetch_with_source(
        self,
        source_name: str,
        *args,
        **kwargs
    ) -> DataSourceResult:
        """
        使用指定数据源获取数据

        Args:
            source_name: 数据源名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            DataSourceResult: 数据源返回结果
        """
        source = self._sources.get(source_name)
        if not source:
            return DataSourceResult(
                success=False,
                error=f"数据源不存在: {source_name}",
                timestamp=time.time(),
                source="manager"
            )

        async with await self._get_semaphore():
            try:
                result = await source.fetch(*args, **kwargs)
                self._record_request(source_name, source.source_type, result)
                return result
            except Exception as e:
                self._record_request(source_name, source.source_type, None, error=str(e))
                raise

    async def fetch_batch(
        self,
        source_type: DataSourceType,
        params_list: List[Dict[str, Any]],
        *args,
        parallel: bool = True,
        **kwargs
    ) -> List[DataSourceResult]:
        """
        批量获取数据

        Args:
            source_type: 数据源类型
            params_list: 参数列表，每个元素包含 args 和 kwargs
            *args: 通用位置参数
            parallel: 是否并行执行请求
            **kwargs: 通用关键字参数

        Returns:
            List[DataSourceResult]: 结果列表
        """
        sources = self._get_ordered_sources(source_type)
        if not sources:
            return [
                DataSourceResult(
                    success=False,
                    error="没有可用的数据源",
                    timestamp=time.time(),
                    source="manager"
                )
            ] * len(params_list)

        primary_source = sources[0]

        if not parallel:
            # 串行执行（兼容旧行为）
            results = []
            for params in params_list:
                async with await self._get_semaphore():
                    try:
                        result = await primary_source.fetch(
                            *params.get("args", args),
                            **kwargs,
                            **params.get("kwargs", {})
                        )
                        results.append(result)
                    except Exception as e:
                        results.append(
                            DataSourceResult(
                                success=False,
                                error=str(e),
                                timestamp=time.time(),
                                source=primary_source.name
                            )
                        )
            return results

        # 并行执行 - 使用信号量限制并发数
        async def fetch_one(params: Dict[str, Any]) -> DataSourceResult:
            async with await self._get_semaphore():
                try:
                    result = await primary_source.fetch(
                        *params.get("args", args),
                        **kwargs,
                        **params.get("kwargs", {})
                    )
                    return result
                except Exception as e:
                    return DataSourceResult(
                        success=False,
                        error=str(e),
                        timestamp=time.time(),
                        source=primary_source.name
                    )

        # 使用 gather 并行执行所有请求
        tasks = [fetch_one(params) for params in params_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常情况
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=primary_source.name
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def _get_ordered_sources(self, source_type: DataSourceType) -> List[DataSource]:
        """
        获取排序后的数据源列表

        Returns:
            List[DataSource]: 按优先级排序的数据源
        """
        source_ids = self._type_sources[source_type]

        if not self._enable_load_balancing or len(source_ids) <= 1:
            # 按优先级排序
            def get_priority(sid):
                config = self._source_configs.get(sid)
                if config:
                    return config.priority
                return 0
            return [
                self._sources[sid]
                for sid in sorted(source_ids, key=get_priority)
            ]

        # 负载均衡模式
        idx = self._round_robin_index[source_type] % len(source_ids)
        self._round_robin_index[source_type] += 1

        # 轮询选择
        ordered = source_ids[idx:] + source_ids[:idx]
        return [self._sources[sid] for sid in ordered]

    async def health_check(self, source_name: Optional[str] = None) -> Dict[str, Any]:
        """
        执行健康检查

        Args:
            source_name: 可选，指定检查的数据源

        Returns:
            Dict: 健康检查结果
        """
        if source_name:
            source = self._sources.get(source_name)
            if not source:
                return {"status": "unknown", "error": f"数据源不存在: {source_name}"}

            healthy = await source.health_check()
            return {
                "source": source_name,
                "status": "healthy" if healthy else "unhealthy",
                "details": source.get_status()
            }

        # 检查所有数据源
        results = {}
        for name, source in self._sources.items():
            try:
                healthy = await source.health_check()
                results[name] = {
                    "status": "healthy" if healthy else "unhealthy",
                    "details": source.get_status()
                }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e)
                }

        healthy_count = sum(1 for r in results.values() if r["status"] == "healthy")
        total_count = len(results)

        return {
            "total_sources": total_count,
            "healthy_count": healthy_count,
            "unhealthy_count": total_count - healthy_count,
            "sources": results
        }

    def set_source_enabled(self, source_name: str, enabled: bool):
        """
        设置数据源启用/禁用状态

        Args:
            source_name: 数据源名称
            enabled: 是否启用
        """
        if source_name not in self._source_configs:
            raise ValueError(f"数据源 '{source_name}' 未注册")

        config = self._source_configs[source_name]
        config.enabled = enabled

    def set_source_priority(self, source_name: str, priority: int):
        """
        设置数据源优先级

        Args:
            source_name: 数据源名称
            priority: 优先级（数值越小优先级越高）
        """
        if source_name not in self._source_configs:
            raise ValueError(f"数据源 '{source_name}' 未注册")

        self._source_configs[source_name].priority = priority

    def _record_request(
        self,
        source_name: str,
        source_type: DataSourceType,
        result: Optional[DataSourceResult],
        error: Optional[str] = None
    ):
        """
        记录请求历史

        Args:
            source_name: 数据源名称
            source_type: 数据源类型
            result: 结果
            error: 错误信息
        """
        self._request_history.append({
            "timestamp": time.time(),
            "source": source_name,
            "type": source_type.value,
            "success": result.success if result else False,
            "error": error or (result.error if result else None)
        })

        # 限制历史记录数量
        if len(self._request_history) > self._max_history:
            self._request_history = self._request_history[-self._max_history:]

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计数据

        Returns:
            Dict: 统计数据
        """
        total_requests = len(self._request_history)
        successful_requests = sum(1 for r in self._request_history if r["success"])
        failed_requests = total_requests - successful_requests

        # 按数据源统计
        source_stats: Dict[str, Dict[str, Any]] = {}
        for source_name in self._sources:
            source_requests = [r for r in self._request_history if r["source"] == source_name]
            if source_requests:
                source_stats[source_name] = {
                    "total": len(source_requests),
                    "success": sum(1 for r in source_requests if r["success"]),
                    "failed": sum(1 for r in source_requests if not r["success"]),
                    "success_rate": sum(1 for r in source_requests if r["success"]) / len(source_requests)
                }

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "overall_success_rate": successful_requests / total_requests if total_requests > 0 else 0,
            "source_statistics": source_stats,
            "registered_sources": {
                name: {
                    "type": s.source_type.value,
                    "enabled": self._source_configs.get(name, DataSourceConfig(
                        source_class=type(s),
                        name=name,
                        source_type=s.source_type
                    )).enabled,
                    "priority": self._source_configs.get(name, DataSourceConfig(
                        source_class=type(s),
                        name=name,
                        source_type=s.source_type
                    )).priority
                }
                for name, s in self._sources.items()
            },
            "max_concurrent": self._semaphore._value if hasattr(self._semaphore, '_value') else None
        }

    def list_sources(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册的数据源

        Returns:
            List[Dict]: 数据源信息列表
        """
        return [
            {
                "name": name,
                "type": source.source_type.value,
                "status": source.get_status()
            }
            for name, source in self._sources.items()
        ]

    async def close_all(self):
        """关闭所有数据源的连接"""
        for source in self._sources.values():
            if hasattr(source, 'close'):
                try:
                    await source.close()
                except Exception:
                    pass


# 工厂函数
def create_default_manager() -> DataSourceManager:
    """
    创建默认配置的数据源管理器

    Returns:
        DataSourceManager: 配置好的管理器实例
    """
    from .fund_source import FundDataSource, SinaFundDataSource
    from .commodity_source import AKShareCommoditySource, YFinanceCommoditySource
    from .news_source import SinaNewsDataSource
    from .sector_source import SinaSectorDataSource, EastMoneySectorSource

    manager = DataSourceManager()

    # 注册基金数据源
    fund_source = FundDataSource()
    manager.register(fund_source)

    # 注册商品数据源
    commodity_source = AKShareCommoditySource()
    manager.register(commodity_source)

    # 注册 YFinance 商品数据源（国际商品 + 贵金属/基本金属预留）
    yfinance_commodity_source = YFinanceCommoditySource()
    manager.register(yfinance_commodity_source)

    # 注册新闻数据源
    news_source = SinaNewsDataSource()
    manager.register(news_source)

    # 注册行业板块数据源
    sector_source = SinaSectorDataSource()
    manager.register(sector_source)

    # 注册东方财富板块数据源 (预留接口)
    eastmoney_sector_source = EastMoneySectorSource()
    manager.register(eastmoney_sector_source)

    # === 新增股票数据源 ===
    from .stock_source import SinaStockDataSource, YahooStockSource
    manager.register(SinaStockDataSource())
    manager.register(YahooStockSource())

    # === 新增债券数据源 ===
    from .bond_source import SinaBondDataSource, AKShareBondSource
    manager.register(SinaBondDataSource())
    manager.register(AKShareBondSource())

    # === 新增加密货币数据源 ===
    from .crypto_source import BinanceCryptoSource, CoinGeckoCryptoSource
    manager.register(BinanceCryptoSource())
    manager.register(CoinGeckoCryptoSource())

    return manager


# 导出
__all__ = ["DataSourceManager", "DataSourceConfig", "create_default_manager"]
