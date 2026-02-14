"""
数据网关 (DataGateway)

统一所有数据请求入口，提供便捷方法和统计监控
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from src.datasources.base import DataSourceType
from src.datasources.hot_backup import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitConfig,
    HotBackupManager,
)
from src.datasources.manager import DataSourceManager
from src.datasources.unified_models import (
    BatchDataRequest,
    BatchDataResponse,
    DataRequest,
    DataResponse,
    RequestPriority,
    ResponseStatus,
)


@dataclass
class GatewayStats:
    """网关统计数据"""

    total_requests: int = 0
    success_count: int = 0
    failure_count: int = 0
    fallback_count: int = 0
    total_latency_ms: float = 0.0
    request_latencies: list[float] = field(default_factory=list)
    max_latencies: int = 1000  # 最多记录1000条延迟

    def record_request(self, latency_ms: float, success: bool, fallback: bool = False):
        """记录请求结果"""
        self.total_requests += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        if fallback:
            self.fallback_count += 1

        self.total_latency_ms += latency_ms
        self.request_latencies.append(latency_ms)
        if len(self.request_latencies) > self.max_latencies:
            self.request_latencies.pop(0)

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.success_count / self.total_requests

    @property
    def average_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    @property
    def p95_latency_ms(self) -> float:
        if not self.request_latencies:
            return 0.0
        sorted_latencies = sorted(self.request_latencies)
        index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[index] if index < len(sorted_latencies) else sorted_latencies[-1]

    @property
    def p99_latency_ms(self) -> float:
        if not self.request_latencies:
            return 0.0
        sorted_latencies = sorted(self.request_latencies)
        index = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[index] if index < len(sorted_latencies) else sorted_latencies[-1]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "fallback_count": self.fallback_count,
            "success_rate": self.success_rate,
            "average_latency_ms": self.average_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
        }


class DataGateway:
    """
    数据网关

    统一所有数据请求入口，提供:
    - 统一请求/响应模型
    - 批量请求支持
    - 便捷方法
    - 统计监控
    - 熔断保护
    - 热备份
    """

    def __init__(
        self,
        manager: DataSourceManager,
        circuit_config: CircuitConfig | None = None,
        enable_circuit_breaker: bool = True,
        enable_hot_backup: bool = False,
        hot_backup_timeout: float = 10.0,
    ):
        """
        初始化数据网关

        Args:
            manager: DataSourceManager 实例
            circuit_config: 熔断器配置
            enable_circuit_breaker: 是否启用熔断器
            enable_hot_backup: 是否启用热备份
            hot_backup_timeout: 热备份超时时间
        """
        self._manager = manager
        self._stats = GatewayStats()
        self._semaphore = asyncio.Semaphore(50)

        self._circuit_breaker_manager = CircuitBreakerManager() if enable_circuit_breaker else None
        self._circuit_config = circuit_config or CircuitConfig()
        self._enable_hot_backup = enable_hot_backup
        self._hot_backup_manager = (
            HotBackupManager(timeout=hot_backup_timeout) if enable_hot_backup else None
        )

        self._circuit_breaker_stats: dict[str, int] = {}

    def _get_breaker(self, source_type: DataSourceType) -> CircuitBreaker | None:
        if not self._circuit_breaker_manager:
            return None
        return self._circuit_breaker_manager.get_breaker(source_type.value, self._circuit_config)

    async def request(self, req: DataRequest) -> DataResponse:
        """
        处理单个数据请求

        Args:
            req: 数据请求

        Returns:
            DataResponse: 数据响应
        """
        start_time = time.perf_counter()

        breaker = self._get_breaker(req.source_type)

        if breaker and not breaker.can_execute():
            latency_ms = (time.perf_counter() - start_time) * 1000
            response = DataResponse(
                request_id=req.request_id,
                success=False,
                error="Circuit breaker is open",
                status=ResponseStatus.FAILED,
                latency_ms=latency_ms,
                metadata={"circuit_breaker_open": True},
            )
            self._stats.record_request(latency_ms=latency_ms, success=False)
            return response

        try:
            result = await self._manager.fetch(
                req.source_type,
                req.symbol,
                failover=req.allow_fallback,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000
            response = DataResponse.from_result(req, result, latency_ms)

            if breaker:
                if result.success:
                    await breaker.record_success()
                else:
                    await breaker.record_failure()

            self._stats.record_request(
                latency_ms=latency_ms,
                success=response.success,
                fallback=response.fallback_used,
            )

            return response

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            response = DataResponse(
                request_id=req.request_id,
                success=False,
                error=str(e),
                status=ResponseStatus.FAILED,
                latency_ms=latency_ms,
            )

            if breaker:
                await breaker.record_failure()

            self._stats.record_request(
                latency_ms=latency_ms,
                success=False,
            )

            return response

    async def request_batch(self, batch: BatchDataRequest) -> BatchDataResponse:
        """
        批量处理数据请求

        Args:
            batch: 批量请求

        Returns:
            BatchDataResponse: 批量响应
        """
        batch_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        if batch.parallel:
            tasks = [self.request(req) for req in batch.requests]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            valid_responses = []
            for r in responses:
                if isinstance(r, Exception):
                    valid_responses.append(
                        DataResponse(
                            request_id="",
                            success=False,
                            error=str(r),
                            status=ResponseStatus.FAILED,
                        )
                    )
                else:
                    valid_responses.append(r)
        else:
            valid_responses = []
            for req in batch.requests:
                try:
                    response = await self.request(req)
                    valid_responses.append(response)
                except Exception as e:
                    valid_responses.append(
                        DataResponse(
                            request_id=req.request_id,
                            success=False,
                            error=str(e),
                            status=ResponseStatus.FAILED,
                        )
                    )

        total_latency_ms = (time.perf_counter() - start_time) * 1000
        success_count = sum(1 for r in valid_responses if r.success)
        failed_count = len(valid_responses) - success_count

        return BatchDataResponse(
            request_id=batch_id,
            responses=valid_responses,
            total_count=len(valid_responses),
            success_count=success_count,
            failed_count=failed_count,
            total_latency_ms=total_latency_ms,
        )

    async def get_fund(self, code: str, allow_fallback: bool = True) -> DataResponse:
        """
        获取基金数据

        Args:
            code: 基金代码
            allow_fallback: 是否允许降级

        Returns:
            DataResponse: 基金数据响应
        """
        req = DataRequest(
            symbol=code,
            source_type=DataSourceType.FUND,
            allow_fallback=allow_fallback,
        )
        return await self.request(req)

    async def get_stock(self, code: str, allow_fallback: bool = True) -> DataResponse:
        """
        获取股票数据

        Args:
            code: 股票代码
            allow_fallback: 是否允许降级

        Returns:
            DataResponse: 股票数据响应
        """
        req = DataRequest(
            symbol=code,
            source_type=DataSourceType.STOCK,
            allow_fallback=allow_fallback,
        )
        return await self.request(req)

    async def get_commodity(self, name: str, allow_fallback: bool = True) -> DataResponse:
        """
        获取商品数据

        Args:
            name: 商品名称
            allow_fallback: 是否允许降级

        Returns:
            DataResponse: 商品数据响应
        """
        req = DataRequest(
            symbol=name,
            source_type=DataSourceType.COMMODITY,
            allow_fallback=allow_fallback,
        )
        return await self.request(req)

    async def get_crypto(self, symbol: str, allow_fallback: bool = True) -> DataResponse:
        """
        获取加密货币数据

        Args:
            symbol: 加密货币符号 (如 BTC, ETH)
            allow_fallback: 是否允许降级

        Returns:
            DataResponse: 加密货币数据响应
        """
        req = DataRequest(
            symbol=symbol,
            source_type=DataSourceType.CRYPTO,
            allow_fallback=allow_fallback,
        )
        return await self.request(req)

    async def get_bond(self, code: str, allow_fallback: bool = True) -> DataResponse:
        """
        获取债券数据

        Args:
            code: 债券代码
            allow_fallback: 是否允许降级

        Returns:
            DataResponse: 债券数据响应
        """
        req = DataRequest(
            symbol=code,
            source_type=DataSourceType.BOND,
            allow_fallback=allow_fallback,
        )
        return await self.request(req)

    async def get_news(
        self, keywords: str | None = None, allow_fallback: bool = True
    ) -> DataResponse:
        """
        获取财经新闻

        Args:
            keywords: 搜索关键词
            allow_fallback: 是否允许降级

        Returns:
            DataResponse: 新闻数据响应
        """
        req = DataRequest(
            symbol=keywords or "",
            source_type=DataSourceType.NEWS,
            allow_fallback=allow_fallback,
        )
        return await self.request(req)

    async def get_sector(
        self, sector_name: str | None = None, allow_fallback: bool = True
    ) -> DataResponse:
        """
        获取板块数据

        Args:
            sector_name: 板块名称
            allow_fallback: 是否允许降级

        Returns:
            DataResponse: 板块数据响应
        """
        req = DataRequest(
            symbol=sector_name or "",
            source_type=DataSourceType.SECTOR,
            allow_fallback=allow_fallback,
        )
        return await self.request(req)

    def get_stats(self) -> dict[str, Any]:
        """
        获取网关统计信息

        Returns:
            Dict: 统计信息字典
        """
        stats = self._stats.to_dict()
        if self._circuit_breaker_manager:
            stats["circuit_breakers"] = self._circuit_breaker_manager.get_all_stats()
        return stats

    def reset_stats(self):
        """重置统计信息"""
        self._stats = GatewayStats()


__all__ = [
    "DataGateway",
    "GatewayStats",
    "DataRequest",
    "DataResponse",
    "BatchDataRequest",
    "BatchDataResponse",
    "RequestPriority",
    "ResponseStatus",
    "CircuitConfig",
]
