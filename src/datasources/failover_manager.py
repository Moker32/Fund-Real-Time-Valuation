"""
故障转移管理器模块
负责故障检测、数据源健康状态跟踪和自动切换
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .base import DataSource
from .health import HealthStatus

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """健康检查结果"""

    source_name: str
    status: HealthStatus
    response_time_ms: float
    error_count: int
    last_check: datetime
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "source_name": self.source_name,
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "error_count": self.error_count,
            "last_check": self.last_check.isoformat(),
            "message": self.message,
            "details": self.details,
        }


class FailoverManager:
    """
    故障转移管理器

    负责：
    - 故障检测和状态跟踪
    - 连续失败计数
    - 自动切换不健康的数据源
    """

    MAX_HISTORY = 100

    def __init__(
        self,
        check_interval: int = 60,
        timeout: float = 10.0,
        max_response_time_ms: float = 5000.0,
        consecutive_failure_threshold: int = 3,
    ):
        """
        初始化故障转移管理器

        Args:
            check_interval: 检查间隔（秒）
            timeout: 请求超时时间（秒）
            max_response_time_ms: 最大响应时间（毫秒），超过此值视为降级
            consecutive_failure_threshold: 连续失败次数阈值
        """
        self.check_interval = check_interval
        self.timeout = timeout
        self.max_response_time_ms = max_response_time_ms
        self.consecutive_failure_threshold = consecutive_failure_threshold

        self._health_history: dict[str, deque[HealthCheckResult]] = {}
        self._check_tasks: dict[str, asyncio.Task] = {}
        self._running = False
        self._consecutive_failures: dict[str, int] = {}

    async def check_source(
        self, source: DataSource, save_history: bool = True
    ) -> HealthCheckResult:
        """
        检查单个数据源健康状态

        Args:
            source: 数据源实例
            save_history: 是否保存到历史记录

        Returns:
            HealthCheckResult: 健康检查结果
        """
        source_name = source.name
        start_time = time.perf_counter()

        try:
            is_healthy = await asyncio.wait_for(source.health_check(), timeout=self.timeout)

            response_time_ms = (time.perf_counter() - start_time) * 1000

            if is_healthy:
                self._consecutive_failures[source_name] = 0

                if response_time_ms > self.max_response_time_ms:
                    status = HealthStatus.DEGRADED
                    message = f"响应时间过长: {response_time_ms:.2f}ms"
                else:
                    status = HealthStatus.HEALTHY
                    message = "数据源健康"

                result = HealthCheckResult(
                    source_name=source_name,
                    status=status,
                    response_time_ms=response_time_ms,
                    error_count=0,
                    last_check=datetime.now(),
                    message=message,
                    details={"response_time_threshold": self.max_response_time_ms},
                )
            else:
                self._consecutive_failures[source_name] = (
                    self._consecutive_failures.get(source_name, 0) + 1
                )

                error_count = self._consecutive_failures[source_name]

                if error_count >= self.consecutive_failure_threshold:
                    status = HealthStatus.UNHEALTHY
                    message = f"连续 {error_count} 次检查失败"
                else:
                    status = HealthStatus.DEGRADED
                    message = f"检查失败 {error_count} 次"

                result = HealthCheckResult(
                    source_name=source_name,
                    status=status,
                    response_time_ms=response_time_ms,
                    error_count=error_count,
                    last_check=datetime.now(),
                    message=message,
                )

            if save_history:
                if source_name not in self._health_history:
                    self._health_history[source_name] = deque(maxlen=self.MAX_HISTORY)
                self._health_history[source_name].append(result)

            return result

        except asyncio.TimeoutError:
            response_time_ms = (time.perf_counter() - start_time) * 1000
            self._consecutive_failures[source_name] = (
                self._consecutive_failures.get(source_name, 0) + 1
            )
            error_count = self._consecutive_failures[source_name]

            logger.warning(
                f"Health check timeout for source '{source_name}' "
                f"(consecutive failures: {error_count}, response_time: {response_time_ms:.2f}ms)"
            )

            result = HealthCheckResult(
                source_name=source_name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time_ms,
                error_count=error_count,
                last_check=datetime.now(),
                message=f"健康检查超时（>{self.timeout}s）",
                details={"error_type": "TimeoutError", "timeout": self.timeout},
            )

            if save_history:
                if source_name not in self._health_history:
                    self._health_history[source_name] = deque(maxlen=self.MAX_HISTORY)
                self._health_history[source_name].append(result)

            return result

        except Exception as e:
            response_time_ms = (time.perf_counter() - start_time) * 1000
            self._consecutive_failures[source_name] = (
                self._consecutive_failures.get(source_name, 0) + 1
            )
            error_count = self._consecutive_failures[source_name]
            error_type = type(e).__name__

            logger.error(
                f"Health check failed for source '{source_name}': "
                f"{error_type}: {str(e)} "
                f"(consecutive failures: {error_count})",
                exc_info=True,
            )

            result = HealthCheckResult(
                source_name=source_name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time_ms,
                error_count=error_count,
                last_check=datetime.now(),
                message=f"健康检查异常: {error_type}",
                details={"error_type": error_type, "error_message": str(e)},
            )

            if save_history:
                if source_name not in self._health_history:
                    self._health_history[source_name] = deque(maxlen=self.MAX_HISTORY)
                self._health_history[source_name].append(result)

            return result

    async def check_all_sources(self, sources: list[DataSource]) -> dict[str, HealthCheckResult]:
        """
        并行检查所有数据源

        Args:
            sources: 数据源列表

        Returns:
            Dict[str, HealthCheckResult]: 数据源名称到检查结果的映射
        """
        results = {}

        async def check_with_source(source: DataSource) -> tuple[str, HealthCheckResult]:
            result = await self.check_source(source, save_history=False)
            return (source.name, result)

        tasks = [check_with_source(source) for source in sources]
        checked_results = await asyncio.gather(*tasks, return_exceptions=True)

        for item in checked_results:
            if isinstance(item, BaseException):
                continue

            source_name, result = item
            results[source_name] = result

        return results

    def get_source_health(self, source_name: str) -> HealthCheckResult | None:
        """获取数据源最近健康状态"""
        history = self._health_history.get(source_name)
        if history:
            return history[-1]
        return None

    def get_health_history(self, source_name: str, limit: int = 10) -> list[HealthCheckResult]:
        """获取数据源健康历史"""
        history: deque[HealthCheckResult] = self._health_history.get(source_name, deque())
        return list(history)[-limit:]

    def get_statistics(self) -> dict[str, Any]:
        """获取健康检查统计数据"""
        stats: dict[str, Any] = {"total_sources_checked": len(self._health_history), "sources": {}}

        for source_name, history in self._health_history.items():
            if not history:
                continue

            recent_results = [r for r in history if r.status == HealthStatus.HEALTHY]
            avg_response_time = sum(r.response_time_ms for r in history) / len(history)

            stats["sources"][source_name] = {
                "total_checks": len(history),
                "healthy_count": len(recent_results),
                "unhealthy_count": len(history) - len(recent_results),
                "avg_response_time_ms": avg_response_time,
                "current_status": history[-1].status.value,
                "last_check": history[-1].last_check.isoformat(),
            }

        return stats

    def get_unhealthy_sources(self) -> list[str]:
        """获取所有不健康的数据源名称"""
        unhealthy = []
        for source_name, history in self._health_history.items():
            if history and history[-1].status in (HealthStatus.UNHEALTHY, HealthStatus.DEGRADED):
                unhealthy.append(source_name)
        return unhealthy

    def get_healthy_sources(self) -> list[str]:
        """获取所有健康的数据源名称"""
        healthy = []
        for source_name, history in self._health_history.items():
            if history and history[-1].status == HealthStatus.HEALTHY:
                healthy.append(source_name)
        return healthy

    async def start_background_check(self, sources: list[DataSource]) -> None:
        """启动后台健康检查任务"""
        if self._running:
            return

        self._running = True

        async def periodic_check() -> None:
            while self._running:
                await asyncio.sleep(self.check_interval)
                await self.check_all_sources(sources)

        self._check_task = asyncio.create_task(periodic_check())

    def stop_background_check(self) -> None:
        """停止后台健康检查任务"""
        self._running = False
        if hasattr(self, "_check_task"):
            self._check_task.cancel()

    def reset(self) -> None:
        """重置所有健康检查状态"""
        self._health_history.clear()
        self._consecutive_failures.clear()
        self._running = False

    async def get_healthy_source(
        self, sources: list[DataSource], prefer_healthy: bool = True
    ) -> DataSource | None:
        """
        获取最健康的数据源

        Args:
            sources: 数据源列表
            prefer_healthy: 是否优先选择健康的数据源

        Returns:
            DataSource | None: 选中的数据源
        """
        if not sources:
            return None

        if not prefer_healthy:
            return sources[0]

        results = await self.check_all_sources(sources)

        healthy_sources = [
            s
            for s in sources
            if results.get(
                s.name,
                HealthCheckResult(
                    source_name=s.name,
                    status=HealthStatus.UNKNOWN,
                    response_time_ms=0,
                    error_count=0,
                    last_check=datetime.now(),
                ),
            ).status
            == HealthStatus.HEALTHY
        ]

        if healthy_sources:
            return min(
                healthy_sources,
                key=lambda s: (
                    results.get(
                        s.name,
                        HealthCheckResult(
                            source_name=s.name,
                            status=HealthStatus.HEALTHY,
                            response_time_ms=float("inf"),
                            error_count=0,
                            last_check=datetime.now(),
                        ),
                    ).response_time_ms
                ),
            )

        degraded_sources = [
            s
            for s in sources
            if results.get(
                s.name,
                HealthCheckResult(
                    source_name=s.name,
                    status=HealthStatus.UNKNOWN,
                    response_time_ms=0,
                    error_count=0,
                    last_check=datetime.now(),
                ),
            ).status
            == HealthStatus.DEGRADED
        ]

        if degraded_sources:
            return degraded_sources[0]

        return None

    def should_skip_source(self, source_name: str) -> bool:
        """判断是否应该跳过某个数据源"""
        result = self.get_source_health(source_name)
        if result is None:
            return False
        return result.status == HealthStatus.UNHEALTHY


# 导出
__all__ = ["FailoverManager", "HealthCheckResult", "HealthStatus"]
