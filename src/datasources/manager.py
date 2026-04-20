"""
数据源管理器
支持多数据源自动切换、负载均衡、健康检查等功能
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .base import DataSource, DataSourceResult, DataSourceType
from .health import DataSourceHealthChecker, HealthCheckInterceptor, HealthCheckResult, HealthStatus

logger = logging.getLogger(__name__)


@dataclass
class DataSourceConfig:
    """数据源配置"""

    source_class: type[DataSource]
    name: str
    source_type: DataSourceType
    enabled: bool = True
    priority: int = 0  # 优先级，数值越小优先级越高
    config: dict[str, Any] = field(default_factory=dict)


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

    def __init__(
        self,
        max_concurrent: int = 20,
        enable_load_balancing: bool = False,
        health_check_interval: int = 60,
    ):
        """
        初始化数据源管理器

        Args:
            max_concurrent: 最大并发请求数
            enable_load_balancing: 是否启用负载均衡
            health_check_interval: 健康检查间隔（秒）
        """
        self._sources: dict[str, DataSource] = {}
        self._source_configs: dict[str, DataSourceConfig] = {}
        self._type_sources: dict[DataSourceType, list[str]] = {
            DataSourceType.FUND: [],
            DataSourceType.COMMODITY: [],
            DataSourceType.NEWS: [],
            DataSourceType.SECTOR: [],
            DataSourceType.STOCK: [],  # 指数数据源复用此类型
        }
        self._max_concurrent = max_concurrent  # 单个全局 semaphore 的最大并发
        self._semaphores: dict[DataSourceType, asyncio.Semaphore] = {}  # 按类型分桶，避免跨类型争抢
        self._enable_load_balancing = enable_load_balancing
        self._round_robin_index: dict[DataSourceType, int] = {
            DataSourceType.FUND: 0,
            DataSourceType.COMMODITY: 0,
            DataSourceType.NEWS: 0,
            DataSourceType.SECTOR: 0,
            DataSourceType.STOCK: 0,  # 指数数据源复用此类型
        }
        self._request_history: list[dict[str, Any]] = []
        self._max_history = 1000

        # 健康检查器
        self._health_checker = DataSourceHealthChecker(check_interval=health_check_interval)
        self._health_interceptor = HealthCheckInterceptor(self._health_checker)

    async def _get_semaphore(self, source_type: DataSourceType | None = None) -> asyncio.Semaphore:
        """延迟初始化 semaphore（按类型分桶，避免跨类型争抢）"""
        key = source_type or DataSourceType.STOCK  # fetch_with_source 调用时无 type，用 STOCK 作为兜底
        if key not in self._semaphores:
            self._semaphores[key] = asyncio.Semaphore(self._max_concurrent)
        return self._semaphores[key]

    def register(self, source: DataSource, config: DataSourceConfig | None = None) -> None:
        """
        注册数据源

        Args:
            source: 数据源实例
            config: 可选的配置
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
                priority=len(self._type_sources[source.source_type]),
            )

        logger.info(
            "数据源注册",
            extra={
                "source_id": source_id,
                "source_type": source.source_type.value,
                "priority": self._source_configs[source_id].priority,
                "enabled": self._source_configs[source_id].enabled,
            },
        )

    def unregister(self, source_name: str) -> None:
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

        logger.info(
            "数据源注销",
            extra={
                "source_name": source_name,
                "source_type": source.source_type.value,
            },
        )

    def get_source(self, source_name: str) -> DataSource | None:
        """
        获取指定数据源

        Args:
            source_name: 数据源名称

        Returns:
            DataSource: 数据源实例，不存在返回 None
        """
        return self._sources.get(source_name)

    def get_sources_by_type(self, source_type: DataSourceType) -> list[DataSource]:
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
        *args: Any,
        failover: bool = True,
        health_aware: bool = True,
        **kwargs: Any,
    ) -> DataSourceResult:
        """
        获取数据（自动选择数据源）

        Args:
            source_type: 数据源类型
            *args: 位置参数传递给数据源
            failover: 是否启用故障切换
            health_aware: 是否启用健康感知选择
            **kwargs: 关键字参数传递给数据源

        Returns:
            DataSourceResult: 第一个成功的数据源结果
        """
        start_time = time.time()
        async with await self._get_semaphore(source_type):
            sources = self._get_ordered_sources(source_type)
            errors = []

            # 如果启用健康感知，尝试获取最健康的数据源
            if health_aware and failover:
                healthy_source = await self._health_interceptor.get_healthy_source(
                    sources, prefer_healthy=True
                )
                if healthy_source:
                    # 将健康的数据源排在前面
                    sources = [healthy_source] + [s for s in sources if s != healthy_source]

            for source in sources:
                if not self._source_configs.get(
                    source.name,
                    DataSourceConfig(
                        source_class=type(source), name=source.name, source_type=source.source_type
                    ),
                ).enabled:
                    continue

                # 如果启用健康感知，跳过不健康的数据源
                if health_aware and self._health_interceptor.should_skip_source(source.name):
                    errors.append(f"{source.name}: 数据源不健康")
                    logger.warning(
                        "跳过不健康的数据源",
                        extra={
                            "source_name": source.name,
                            "source_type": source_type.value,
                        },
                    )
                    continue

                try:
                    result = await source.fetch(*args, **kwargs)

                    # 记录请求
                    self._record_request(source.name, source_type, result)

                    if result.success:
                        # 更新健康检查状态
                        if health_aware:
                            await self._health_checker.check_source(source)
                        duration_ms = (time.time() - start_time) * 1000
                        logger.info(
                            "数据源获取成功",
                            extra={
                                "source_name": source.name,
                                "source_type": source_type.value,
                                "duration_ms": round(duration_ms, 2),
                                "failover_count": len(errors),
                            },
                        )
                        return result

                    errors.append(f"{source.name}: {result.error}")
                    logger.warning(
                        "数据源获取失败",
                        extra={
                            "source_name": source.name,
                            "source_type": source_type.value,
                            "error": result.error,
                        },
                    )

                except Exception as e:
                    errors.append(f"{source.name}: {str(e)}")
                    self._record_request(source.name, source_type, None, error=str(e))
                    logger.error(
                        "数据源请求异常",
                        extra={
                            "source_name": source.name,
                            "source_type": source_type.value,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                        exc_info=True,
                    )

            # 所有数据源都失败
            duration_ms = (time.time() - start_time) * 1000
            if failover and errors:
                logger.error(
                    "所有数据源均失败",
                    extra={
                        "source_type": source_type.value,
                        "duration_ms": round(duration_ms, 2),
                        "source_count": len(sources),
                        "errors": errors,
                    },
                )
                return DataSourceResult(
                    success=False,
                    error=f"所有数据源均失败: {'; '.join(errors)}",
                    timestamp=time.time(),
                    source="manager",
                    metadata={"source_type": source_type.value, "errors": errors},
                )

            logger.warning(
                "没有可用的数据源",
                extra={
                    "source_type": source_type.value,
                    "available_sources": len(sources),
                },
            )
            return DataSourceResult(
                success=False,
                error="没有可用的数据源",
                timestamp=time.time(),
                source="manager",
                metadata={"source_type": source_type.value},
            )

    async def fetch_with_source(
        self, source_name: str, *args: Any, **kwargs: Any
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
            logger.warning(
                "数据源不存在",
                extra={"source_name": source_name},
            )
            return DataSourceResult(
                success=False,
                error=f"数据源不存在: {source_name}",
                timestamp=time.time(),
                source="manager",
            )

        async with await self._get_semaphore():
            try:
                result = await source.fetch(*args, **kwargs)
                self._record_request(source_name, source.source_type, result)
                if result.success:
                    logger.debug(
                        "指定数据源获取成功",
                        extra={
                            "source_name": source_name,
                            "source_type": source.source_type.value,
                        },
                    )
                else:
                    logger.warning(
                        "指定数据源获取失败",
                        extra={
                            "source_name": source_name,
                            "source_type": source.source_type.value,
                            "error": result.error,
                        },
                    )
                return result
            except Exception as e:
                self._record_request(source_name, source.source_type, None, error=str(e))
                logger.error(
                    "指定数据源请求异常",
                    extra={
                        "source_name": source_name,
                        "source_type": source.source_type.value,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise

    async def fetch_batch(
        self,
        source_type: DataSourceType,
        params_list: list[dict[str, Any]],
        *args: Any,
        parallel: bool = True,
        failover: bool = True,
        **kwargs: Any,
    ) -> list[DataSourceResult]:
        """
        批量获取数据

        Args:
            source_type: 数据源类型
            params_list: 参数列表，每个元素包含 args 和 kwargs
            *args: 通用位置参数
            parallel: 是否并行执行请求
            failover: 是否启用故障切换（一个数据源失败后尝试下一个）
            **kwargs: 通用关键字参数

        Returns:
            List[DataSourceResult]: 结果列表
        """
        start_time = time.time()
        sources = self._get_ordered_sources(source_type)
        if not sources:
            logger.warning(
                "批量获取失败: 没有可用的数据源",
                extra={
                    "source_type": source_type.value,
                    "batch_size": len(params_list),
                },
            )
            return [
                DataSourceResult(
                    success=False, error="没有可用的数据源", timestamp=time.time(), source="manager"
                )
            ] * len(params_list)

        logger.debug(
            "批量获取开始",
            extra={
                "source_type": source_type.value,
                "batch_size": len(params_list),
                "available_sources": [s.name for s in sources],
                "parallel": parallel,
            },
        )

        # 并行执行 - 使用信号量限制并发数
        async def fetch_one(params: dict[str, Any]) -> DataSourceResult:
            async with await self._get_semaphore(source_type):
                source_args = params.get("args", args)
                source_kwargs = {**kwargs, **params.get("kwargs", {})}

                # 故障切换：依次尝试所有数据源
                errors = []
                for source in sources:
                    # 跳过禁用的数据源
                    config = self._source_configs.get(source.name)
                    if config and not config.enabled:
                        continue

                    try:
                        result = await source.fetch(*source_args, **source_kwargs)
                        self._record_request(source.name, source_type, result)

                        if result.success:
                            return result
                        errors.append(f"{source.name}: {result.error}")
                    except Exception as e:
                        errors.append(f"{source.name}: {str(e)}")
                        self._record_request(source.name, source_type, None, error=str(e))

                # 所有数据源都失败
                return DataSourceResult(
                    success=False,
                    error=f"所有数据源均失败: {'; '.join(errors)}",
                    timestamp=time.time(),
                    source="manager",
                    metadata={"errors": errors},
                )

        # 使用 gather 并行执行所有请求
        tasks = [fetch_one(params) for params in params_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常情况
        processed_results = []
        success_count = 0
        fail_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False, error=str(result), timestamp=time.time(), source="manager"
                    )
                )
                fail_count += 1
            else:
                processed_results.append(result)
                if result.success:
                    success_count += 1
                else:
                    fail_count += 1

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "批量获取完成",
            extra={
                "source_type": source_type.value,
                "batch_size": len(params_list),
                "success_count": success_count,
                "fail_count": fail_count,
                "duration_ms": round(duration_ms, 2),
            },
        )

        return processed_results

    def _get_ordered_sources(self, source_type: DataSourceType) -> list[DataSource]:
        """
        获取排序后的数据源列表

        Returns:
            List[DataSource]: 按优先级排序的数据源
        """
        source_ids = self._type_sources[source_type]

        if not self._enable_load_balancing or len(source_ids) <= 1:
            # 按优先级排序
            def get_priority(sid: str) -> int:
                config = self._source_configs.get(sid)
                if config:
                    return config.priority
                return 0

            return [self._sources[sid] for sid in sorted(source_ids, key=get_priority)]

        # 负载均衡模式
        idx = self._round_robin_index[source_type] % len(source_ids)
        self._round_robin_index[source_type] += 1

        # 轮询选择
        ordered = source_ids[idx:] + source_ids[:idx]
        return [self._sources[sid] for sid in ordered]

    async def health_check(self, source_name: str | None = None) -> dict[str, Any]:
        """
        执行健康检查

        Args:
            source_name: 可选，指定检查的数据源

        Returns:
            Dict: 健康检查结果
        """
        from .health import get_mini_racer_status

        mini_racer_status = get_mini_racer_status()

        if source_name:
            source = self._sources.get(source_name)
            if not source:
                return {"status": "unknown", "error": f"数据源不存在: {source_name}"}

            result = await self._health_checker.check_source(source)
            return {
                "source": source_name,
                "status": result.status.value,
                "response_time_ms": result.response_time_ms,
                "error_count": result.error_count,
                "last_check": result.last_check.isoformat(),
                "message": result.message,
                "details": result.details,
                "mini_racer": mini_racer_status,
            }

        # 检查所有数据源
        sources = list(self._sources.values())
        results = await self._health_checker.check_all_sources(sources)

        healthy_count = sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for r in results.values() if r.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for r in results.values() if r.status == HealthStatus.UNHEALTHY)

        return {
            "total_sources": len(results),
            "healthy_count": healthy_count,
            "degraded_count": degraded_count,
            "unhealthy_count": unhealthy_count,
            "sources": {name: result.to_dict() for name, result in results.items()},
            "mini_racer": mini_racer_status,
        }

    async def health_check_all_sources(self) -> dict[str, HealthCheckResult]:
        """
        并行检查所有已注册数据源的健康状态

        Returns:
            Dict[str, HealthCheckResult]: 数据源名称到健康检查结果的映射
        """
        sources = list(self._sources.values())
        return await self._health_checker.check_all_sources(sources)

    def get_source_health(self, source_name: str) -> HealthCheckResult | None:
        """
        获取数据源最近健康状态

        Args:
            source_name: 数据源名称

        Returns:
            HealthCheckResult: 最近一次检查结果，不存在返回 None
        """
        return self._health_checker.get_source_health(source_name)

    def get_health_history(self, source_name: str, limit: int = 10) -> list[HealthCheckResult]:
        """
        获取数据源健康历史

        Args:
            source_name: 数据源名称
            limit: 返回记录数量限制

        Returns:
            List[HealthCheckResult]: 健康检查历史列表
        """
        return self._health_checker.get_health_history(source_name, limit)

    def get_health_statistics(self) -> dict[str, Any]:
        """
        获取健康检查统计数据

        Returns:
            Dict: 统计数据字典
        """
        return self._health_checker.get_statistics()

    def get_unhealthy_sources(self) -> list[str]:
        """
        获取所有不健康的数据源名称

        Returns:
            List[str]: 不健康的数据源名称列表
        """
        return self._health_checker.get_unhealthy_sources()

    def get_healthy_sources(self) -> list[str]:
        """
        获取所有健康的数据源名称

        Returns:
            List[str]: 健康的数据源名称列表
        """
        return self._health_checker.get_healthy_sources()

    async def start_background_health_check(self) -> None:
        """启动后台健康检查任务"""
        sources = list(self._sources.values())
        await self._health_checker.start_background_check(sources)

    def stop_background_health_check(self) -> None:
        """停止后台健康检查任务"""
        self._health_checker.stop_background_check()

    def set_source_enabled(self, source_name: str, enabled: bool) -> None:
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

        logger.info(
            "数据源启用/禁用状态变更",
            extra={
                "source_name": source_name,
                "enabled": enabled,
            },
        )

    def set_source_priority(self, source_name: str, priority: int) -> None:
        """
        设置数据源优先级

        Args:
            source_name: 数据源名称
            priority: 优先级（数值越小优先级越高）
        """
        if source_name not in self._source_configs:
            raise ValueError(f"数据源 '{source_name}' 未注册")

        old_priority = self._source_configs[source_name].priority
        self._source_configs[source_name].priority = priority

        logger.info(
            "数据源优先级变更",
            extra={
                "source_name": source_name,
                "old_priority": old_priority,
                "new_priority": priority,
            },
        )

    def _record_request(
        self,
        source_name: str,
        source_type: DataSourceType,
        result: DataSourceResult | None,
        error: str | None = None,
    ) -> None:
        """
        记录请求历史

        Args:
            source_name: 数据源名称
            source_type: 数据源类型
            result: 结果
            error: 错误信息
        """
        self._request_history.append(
            {
                "timestamp": time.time(),
                "source": source_name,
                "type": source_type.value,
                "success": result.success if result else False,
                "error": error or (result.error if result else None),
            }
        )

        # 限制历史记录数量
        if len(self._request_history) > self._max_history:
            self._request_history = self._request_history[-self._max_history :]

    def get_statistics(self) -> dict[str, Any]:
        """
        获取统计数据

        Returns:
            Dict: 统计数据
        """
        total_requests = len(self._request_history)
        successful_requests = sum(1 for r in self._request_history if r["success"])
        failed_requests = total_requests - successful_requests

        # 按数据源统计
        source_stats: dict[str, dict[str, Any]] = {}
        for source_name in self._sources:
            source_requests = [r for r in self._request_history if r["source"] == source_name]
            if source_requests:
                source_stats[source_name] = {
                    "total": len(source_requests),
                    "success": sum(1 for r in source_requests if r["success"]),
                    "failed": sum(1 for r in source_requests if not r["success"]),
                    "success_rate": sum(1 for r in source_requests if r["success"])
                    / len(source_requests),
                }

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "overall_success_rate": successful_requests / total_requests
            if total_requests > 0
            else 0,
            "source_statistics": source_stats,
            "registered_sources": {
                name: {
                    "type": s.source_type.value,
                    "enabled": self._source_configs.get(
                        name,
                        DataSourceConfig(
                            source_class=type(s), name=name, source_type=s.source_type
                        ),
                    ).enabled,
                    "priority": self._source_configs.get(
                        name,
                        DataSourceConfig(
                            source_class=type(s), name=name, source_type=s.source_type
                        ),
                    ).priority,
                }
                for name, s in self._sources.items()
            },
            "max_concurrent": self._semaphore._value
            if self._semaphore and hasattr(self._semaphore, "_value")
            else None,
        }

    def list_sources(self) -> list[dict[str, Any]]:
        """
        列出所有已注册的数据源

        Returns:
            List[Dict]: 数据源信息列表
        """
        return [
            {"name": name, "type": source.source_type.value, "status": source.get_status()}
            for name, source in self._sources.items()
        ]

    async def close_all(self) -> None:
        """关闭所有数据源的连接"""
        for source in self._sources.values():
            try:
                await source.close()
            except Exception:
                pass


# 工厂函数
def create_default_manager(
    enable_load_balancing: bool = False, health_check_interval: int = 60
) -> DataSourceManager:
    """
    创建默认配置的数据源管理器

    Args:
        enable_load_balancing: 是否启用负载均衡
        health_check_interval: 健康检查间隔（秒）

    Returns:
        DataSourceManager: 配置好的管理器实例
    """
    from .commodity_source import AKShareCommoditySource, YFinanceCommoditySource
    from .fund_source import Fund123DataSource
    from .sector_source import (
        EastMoneyConceptDetailSource,
        EastMoneyDirectSource,
        EastMoneyIndustryDetailSource,
        EastMoneySectorSource,
        FundFlowConceptSource,
        FundFlowIndustrySource,
        SinaSectorDataSource,
    )

    manager = DataSourceManager(
        enable_load_balancing=enable_load_balancing, health_check_interval=health_check_interval
    )

    # 注册基金数据源（按优先级排序）
    # 优先级数值越小优先级越高

    # fund123.cn 接口（主数据源 - 最快 ~0.1秒/请求）
    fund123 = Fund123DataSource()
    manager.register(
        fund123,
        DataSourceConfig(
            source_class=type(fund123),
            name=fund123.name,
            source_type=DataSourceType.FUND,
            enabled=True,
            priority=1,  # 最高优先级
        ),
    )

    # 注册商品数据源
    commodity_source = AKShareCommoditySource()
    manager.register(commodity_source)

    # 注册 YFinance 商品数据源（国际商品 + 贵金属/基本金属预留）
    yfinance_commodity_source = YFinanceCommoditySource()
    manager.register(yfinance_commodity_source)

    # === 新增 AKShare 舆情数据源 ===
    from .akshare_sentiment_source import (
        AKShareEconomicNewsDataSource,
        AKShareSentimentAggregatorDataSource,
        AKShareWeiboSentimentDataSource,
    )

    manager.register(AKShareEconomicNewsDataSource())
    manager.register(AKShareWeiboSentimentDataSource())
    manager.register(AKShareSentimentAggregatorDataSource())

    # 注册行业板块数据源
    # 概念板块数据源优先级：
    # 1. FundFlowConceptSource - 资金流向接口，非交易时间可用（需要 mini_racer）
    # 2. EastMoneySectorSource - 实时行情接口，交易时间更及时
    # 3. EastMoneyDirectSource - 直连 API，兜底
    #
    # 注意：FundFlowConceptSource 和 FundFlowIndustrySource 依赖 py_mini_racer/mini_racer
    # 如果版本不兼容会导致进程崩溃。当前默认禁用，改用 EastMoneyDirectSource 作为主数据源。
    # 如需启用：
    # 1. 确认 pyproject.toml 中的版本约束已安装（mini-racer<0.14 或 py-mini-racer<0.7）
    # 2. 通过 /api/datasource/health 接口检查 mini_racer.working 是否为 true
    # 3. 将 enabled 改为 True

    # 概念板块资金流向数据源（非交易时间可用，优先级最高）
    fundflow_concept_source = FundFlowConceptSource()
    manager.register(
        fundflow_concept_source,
        DataSourceConfig(
            source_class=type(fundflow_concept_source),
            name=fundflow_concept_source.name,
            source_type=DataSourceType.SECTOR,
            enabled=False,
            priority=0,
        ),
    )

    # 行业板块资金流向数据源（非交易时间可用）
    fundflow_industry_source = FundFlowIndustrySource()
    manager.register(
        fundflow_industry_source,
        DataSourceConfig(
            source_class=type(fundflow_industry_source),
            name=fundflow_industry_source.name,
            source_type=DataSourceType.SECTOR,
            enabled=False,
            priority=0,
        ),
    )

    # AKShare _spot_em 接口（实时行情，数据更完整，交易时间优先）
    eastmoney_sector_source = EastMoneySectorSource()
    manager.register(
        eastmoney_sector_source,
        DataSourceConfig(
            source_class=type(eastmoney_sector_source),
            name=eastmoney_sector_source.name,
            source_type=DataSourceType.SECTOR,
            enabled=True,
            priority=1,  # 次高优先级（实时行情接口）
        ),
    )

    # EastMoney 直连 API（包含资金流向数据，作为备用）
    eastmoney_direct_source = EastMoneyDirectSource()
    manager.register(
        eastmoney_direct_source,
        DataSourceConfig(
            source_class=type(eastmoney_direct_source),
            name=eastmoney_direct_source.name,
            source_type=DataSourceType.SECTOR,
            enabled=True,
            priority=2,  # 备用（包含资金流向）
        ),
    )

    # Sina 板块数据源（已禁用：API 被代理软件拦截导致 SSL 连接失败）
    # 原因：quote.sina.com.cn 被代理软件 DNS 拦截，导致 SSL 握手失败
    # 替代方案：sector_eastmoney_direct (70ms) 作为主数据源
    sector_source = SinaSectorDataSource()
    manager.register(
        sector_source,
        DataSourceConfig(
            source_class=type(sector_source),
            name=sector_source.name,
            source_type=DataSourceType.SECTOR,
            enabled=False,  # 禁用：网络层不可用
            priority=5,
        ),
    )

    # 注册东方财富板块详情数据源
    industry_detail_source = EastMoneyIndustryDetailSource()
    manager.register(
        industry_detail_source,
        DataSourceConfig(
            source_class=type(industry_detail_source),
            name=industry_detail_source.name,
            source_type=DataSourceType.SECTOR,
            enabled=True,
            priority=10,
        ),
    )

    concept_detail_source = EastMoneyConceptDetailSource()
    manager.register(
        concept_detail_source,
        DataSourceConfig(
            source_class=type(concept_detail_source),
            name=concept_detail_source.name,
            source_type=DataSourceType.SECTOR,
            enabled=True,
            priority=10,
        ),
    )

    # === 新增全球指数数据源 ===
    from .index_source import HybridIndexSource

    manager.register(HybridIndexSource())

    return manager


# 导出
__all__ = ["DataSourceManager", "DataSourceConfig", "create_default_manager"]
