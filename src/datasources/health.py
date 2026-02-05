"""
数据源健康检查模块
提供健康状态管理、故障检测和自动切换功能
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .base import DataSource


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


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
            "details": self.details
        }


class DataSourceHealthChecker:
    """
    数据源健康检查器

    功能:
    - 定期检查数据源健康状态
    - 记录健康历史
    - 计算统计数据
    - 支持自动恢复检测
    """

    def __init__(
        self,
        check_interval: int = 60,
        timeout: float = 10.0,
        max_response_time_ms: float = 5000.0,
        consecutive_failure_threshold: int = 3
    ):
        """
        初始化健康检查器

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

        self.health_history: dict[str, list[HealthCheckResult]] = {}
        self._check_tasks: dict[str, asyncio.Task] = {}
        self._running = False
        self._consecutive_failures: dict[str, int] = {}

    async def check_source(self, source: DataSource, save_history: bool = True) -> HealthCheckResult:
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
            # 执行健康检查
            is_healthy = await asyncio.wait_for(
                source.health_check(),
                timeout=self.timeout
            )

            response_time_ms = (time.perf_counter() - start_time) * 1000

            # 判断健康状态
            if is_healthy:
                # 重置连续失败计数（健康时重置）
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
                    details={"response_time_threshold": self.max_response_time_ms}
                )
            else:
                self._consecutive_failures[source_name] = \
                    self._consecutive_failures.get(source_name, 0) + 1

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
                    message=message
                )

            # 保存到历史记录
            if save_history:
                if source_name not in self.health_history:
                    self.health_history[source_name] = []
                self.health_history[source_name].append(result)

                # 限制历史记录数量
                max_history = 100
                if len(self.health_history[source_name]) > max_history:
                    self.health_history[source_name] = self.health_history[source_name][-max_history:]

            return result

        except asyncio.TimeoutError:
            response_time_ms = (time.perf_counter() - start_time) * 1000
            self._consecutive_failures[source_name] = \
                self._consecutive_failures.get(source_name, 0) + 1

            result = HealthCheckResult(
                source_name=source_name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time_ms,
                error_count=self._consecutive_failures[source_name],
                last_check=datetime.now(),
                message=f"健康检查超时（>{self.timeout}s）"
            )

            # 保存到历史记录
            if save_history:
                if source_name not in self.health_history:
                    self.health_history[source_name] = []
                self.health_history[source_name].append(result)

            return result

        except Exception as e:
            response_time_ms = (time.perf_counter() - start_time) * 1000
            self._consecutive_failures[source_name] = \
                self._consecutive_failures.get(source_name, 0) + 1

            result = HealthCheckResult(
                source_name=source_name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time_ms,
                error_count=self._consecutive_failures[source_name],
                last_check=datetime.now(),
                message=f"健康检查异常: {str(e)}",
                details={"error_type": type(e).__name__}
            )

            # 保存到历史记录
            if save_history:
                if source_name not in self.health_history:
                    self.health_history[source_name] = []
                self.health_history[source_name].append(result)

            return result

    async def check_all_sources(
        self,
        sources: list[DataSource]
    ) -> dict[str, HealthCheckResult]:
        """
        并行检查所有数据源

        Args:
            sources: 数据源列表

        Returns:
            Dict[str, HealthCheckResult]: 数据源名称到检查结果的映射
        """
        results = {}

        # 并行执行检查（每个检查会自动保存到历史记录）
        async def check_with_source(source: DataSource) -> tuple[str, HealthCheckResult]:
            result = await self.check_source(source, save_history=False)  # 避免重复保存
            return (source.name, result)

        tasks = [check_with_source(source) for source in sources]
        checked_results = await asyncio.gather(*tasks, return_exceptions=True)

        for item in checked_results:
            if isinstance(item, Exception):
                # 如果出现异常，记录错误
                continue

            source_name, result = item
            results[source_name] = result

        return results

    def get_source_health(
        self,
        source_name: str
    ) -> HealthCheckResult | None:
        """
        获取数据源最近健康状态

        Args:
            source_name: 数据源名称

        Returns:
            HealthCheckResult: 最近一次检查结果，不存在返回 None
        """
        history = self.health_history.get(source_name)
        if history:
            return history[-1]
        return None

    def get_health_history(
        self,
        source_name: str,
        limit: int = 10
    ) -> list[HealthCheckResult]:
        """
        获取数据源健康历史

        Args:
            source_name: 数据源名称
            limit: 返回记录数量限制

        Returns:
            List[HealthCheckResult]: 健康检查历史列表
        """
        history = self.health_history.get(source_name, [])
        return history[-limit:]

    def get_statistics(self) -> dict[str, Any]:
        """
        获取健康检查统计数据

        Returns:
            Dict: 统计数据字典
        """
        stats = {
            "total_sources_checked": len(self.health_history),
            "sources": {}
        }

        for source_name, history in self.health_history.items():
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
                "last_check": history[-1].last_check.isoformat()
            }

        return stats

    def get_unhealthy_sources(self) -> list[str]:
        """
        获取所有不健康的数据源名称

        Returns:
            List[str]: 不健康的数据源名称列表
        """
        unhealthy = []
        for source_name, history in self.health_history.items():
            if history and history[-1].status in (
                HealthStatus.UNHEALTHY,
                HealthStatus.DEGRADED
            ):
                unhealthy.append(source_name)
        return unhealthy

    def get_healthy_sources(self) -> list[str]:
        """
        获取所有健康的数据源名称

        Returns:
            List[str]: 健康的数据源名称列表
        """
        healthy = []
        for source_name, history in self.health_history.items():
            if history and history[-1].status == HealthStatus.HEALTHY:
                healthy.append(source_name)
        return healthy

    async def start_background_check(
        self,
        sources: list[DataSource]
    ):
        """
        启动后台健康检查任务

        Args:
            sources: 要监控的数据源列表
        """
        if self._running:
            return

        self._running = True

        async def periodic_check():
            while self._running:
                await self.check_all_sources(sources)
                await asyncio.sleep(self.check_interval)

        self._check_task = asyncio.create_task(periodic_check())

    def stop_background_check(self):
        """停止后台健康检查任务"""
        self._running = False
        if hasattr(self, '_check_task'):
            self._check_task.cancel()
            try:
                # 在事件循环中等待任务取消
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self._check_task)
            except asyncio.CancelledError:
                pass

    def reset(self):
        """重置所有健康检查状态"""
        self.health_history.clear()
        self._consecutive_failures.clear()
        self._running = False


class HealthCheckInterceptor:
    """
    健康检查拦截器

    用于在数据请求前后进行健康检查，实现基于健康状态的故障切换
    """

    def __init__(self, checker: DataSourceHealthChecker):
        """
        初始化拦截器

        Args:
            checker: 健康检查器实例
        """
        self.checker = checker

    async def get_healthy_source(
        self,
        sources: list[DataSource],
        prefer_healthy: bool = True
    ) -> DataSource | None:
        """
        获取最健康的数据源

        Args:
            sources: 数据源列表
            prefer_healthy: 是否优先选择健康的数据源

        Returns:
            DataSource: 选中的数据源，无健康数据源返回 None
        """
        if not sources:
            return None

        if not prefer_healthy:
            return sources[0]

        # 检查所有数据源
        results = await self.checker.check_all_sources(sources)

        # 优先选择健康的数据源
        healthy_sources = [
            s for s in sources
            if results.get(s.name, HealthCheckResult(
                source_name=s.name,
                status=HealthStatus.UNKNOWN,
                response_time_ms=0,
                error_count=0,
                last_check=datetime.now()
            )).status == HealthStatus.HEALTHY
        ]

        if healthy_sources:
            # 返回响应时间最短的健康数据源
            return min(
                healthy_sources,
                key=lambda s: results.get(s.name, HealthCheckResult(
                    source_name=s.name,
                    status=HealthStatus.HEALTHY,
                    response_time_ms=float('inf'),
                    error_count=0,
                    last_check=datetime.now()
                )).response_time_ms
            )

        # 没有健康数据源，检查是否有降级的
        degraded_sources = [
            s for s in sources
            if results.get(s.name, HealthCheckResult(
                source_name=s.name,
                status=HealthStatus.UNKNOWN,
                response_time_ms=0,
                error_count=0,
                last_check=datetime.now()
            )).status == HealthStatus.DEGRADED
        ]

        if degraded_sources:
            return degraded_sources[0]

        return None

    def should_skip_source(self, source_name: str) -> bool:
        """
        判断是否应该跳过某个数据源

        Args:
            source_name: 数据源名称

        Returns:
            bool: True 表示应该跳过
        """
        result = self.checker.get_source_health(source_name)
        if result is None:
            return False
        return result.status == HealthStatus.UNHEALTHY


# 导出
__all__ = [
    "HealthStatus",
    "HealthCheckResult",
    "DataSourceHealthChecker",
    "HealthCheckInterceptor"
]
