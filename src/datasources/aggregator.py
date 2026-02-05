"""
数据聚合器模块

提供多数据源聚合功能:
- DataAggregator: 抽象基类，管理多个数据源
- SameSourceAggregator: 同源数据聚合器，支持故障切换
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .base import DataSource, DataSourceResult


@dataclass
class AggregatorSourceInfo:
    """聚合器中的数据源信息"""
    source: DataSource
    is_primary: bool = False
    weight: float = 1.0  # 负载均衡权重


class DataAggregator(ABC):
    """
    数据聚合器抽象基类

    管理多个数据源，提供统一的聚合获取接口
    """

    def __init__(self, name: str = "DataAggregator"):
        """
        初始化数据聚合器

        Args:
            name: 聚合器名称
        """
        self.name = name
        self._sources: list[AggregatorSourceInfo] = []
        self._request_count = 0
        self._success_count = 0
        self._failover_count = 0

    def add_source(self, source: DataSource, is_primary: bool = False, weight: float = 1.0):
        """
        添加数据源到聚合器

        Args:
            source: 数据源实例
            is_primary: 是否为主要数据源
            weight: 负载均衡权重
        """
        self._sources.append(AggregatorSourceInfo(
            source=source,
            is_primary=is_primary,
            weight=weight
        ))

    def remove_source(self, source_name: str) -> bool:
        """
        从聚合器移除数据源

        Args:
            source_name: 数据源名称

        Returns:
            bool: 是否成功移除
        """
        for i, info in enumerate(self._sources):
            if info.source.name == source_name:
                self._sources.pop(i)
                return True
        return False

    def get_sources(self) -> list[DataSource]:
        """
        获取所有数据源

        Returns:
            List[DataSource]: 数据源列表
        """
        return [info.source for info in self._sources]

    def get_primary_source(self) -> DataSource | None:
        """
        获取主数据源

        Returns:
            Optional[DataSource]: 主数据源实例
        """
        for info in self._sources:
            if info.is_primary:
                return info.source
        return self._sources[0].source if self._sources else None

    @abstractmethod
    async def fetch(self, *args, **kwargs) -> DataSourceResult:
        """
        获取数据（抽象方法，子类必须实现）

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            DataSourceResult: 聚合后的结果
        """
        pass

    @abstractmethod
    async def fetch_all(self, *args, **kwargs) -> list[DataSourceResult]:
        """
        获取所有数据源的数据

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            List[DataSourceResult]: 所有数据源的结果列表
        """
        pass

    def get_statistics(self) -> dict[str, Any]:
        """
        获取聚合器统计信息

        Returns:
            Dict: 统计信息字典
        """
        return {
            "name": self.name,
            "source_count": len(self._sources),
            "primary_source": self.get_primary_source().name if self.get_primary_source() else None,
            "request_count": self._request_count,
            "success_count": self._success_count,
            "failover_count": self._failover_count,
            "success_rate": self._success_count / self._request_count if self._request_count > 0 else 0.0,
            "sources": [
                {
                    "name": info.source.name,
                    "is_primary": info.is_primary,
                    "weight": info.weight,
                    "status": info.source.get_status()
                }
                for info in self._sources
            ]
        }


class SameSourceAggregator(DataAggregator):
    """
    同源数据聚合器 - 多数据源故障切换

    优先使用主数据源，主数据源失败时切换到备用数据源
    """

    def __init__(self, name: str = "SameSourceAggregator"):
        """
        初始化同源数据聚合器

        Args:
            name: 聚合器名称
        """
        super().__init__(name)
        self._last_successful_source: str | None = None

    async def fetch(self, *args, **kwargs) -> DataSourceResult:
        """
        获取数据（故障切换策略）

        策略:
        1. 优先使用主数据源
        2. 主数据源失败则切换到备用数据源
        3. 返回第一个成功的结果

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            DataSourceResult: 第一个成功的结果
        """
        if not self._sources:
            return DataSourceResult(
                success=False,
                error="聚合器中没有数据源",
                timestamp=time.time(),
                source=self.name
            )

        self._request_count += 1
        errors: list[str] = []

        # 1. 优先尝试主数据源
        primary_source = self.get_primary_source()
        if primary_source:
            try:
                result = await primary_source.fetch(*args, **kwargs)
                if result.success:
                    self._success_count += 1
                    self._last_successful_source = primary_source.name
                    return result
                errors.append(f"{primary_source.name}: {result.error}")
            except Exception as e:
                errors.append(f"{primary_source.name}: {str(e)}")

        # 2. 主数据源失败，切换到备用数据源
        for info in self._sources:
            source = info.source
            # 跳过主数据源（已尝试过）和上一次成功的源
            if source.name == primary_source.name:
                continue
            if source.name == self._last_successful_source:
                continue

            try:
                result = await source.fetch(*args, **kwargs)
                if result.success:
                    self._success_count += 1
                    self._failover_count += 1
                    self._last_successful_source = source.name
                    return result
                errors.append(f"{source.name}: {result.error}")
            except Exception as e:
                errors.append(f"{source.name}: {str(e)}")

        # 3. 所有数据源都失败
        return DataSourceResult(
            success=False,
            error=f"所有数据源均失败: {'; '.join(errors)}",
            timestamp=time.time(),
            source=self.name,
            metadata={"failover_count": self._failover_count, "errors": errors}
        )

    async def fetch_all(self, *args, **kwargs) -> list[DataSourceResult]:
        """
        获取所有数据源的数据

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            List[DataSourceResult]: 所有数据源的结果列表
        """
        if not self._sources:
            return [
                DataSourceResult(
                    success=False,
                    error="聚合器中没有数据源",
                    timestamp=time.time(),
                    source=self.name
                )
            ]

        results: list[DataSourceResult] = []
        for info in self._sources:
            try:
                result = await info.source.fetch(*args, **kwargs)
                results.append(result)
            except Exception as e:
                results.append(DataSourceResult(
                    success=False,
                    error=str(e),
                    timestamp=time.time(),
                    source=info.source.name
                ))
        return results


class LoadBalancedAggregator(DataAggregator):
    """
    负载均衡数据聚合器

    根据权重在多个数据源之间分配请求
    """

    def __init__(self, name: str = "LoadBalancedAggregator"):
        """
        初始化负载均衡聚合器

        Args:
            name: 聚合器名称
        """
        super().__init__(name)
        self._current_index = 0
        self._source_usage: dict[str, int] = {}

    def add_source(self, source: DataSource, is_primary: bool = False, weight: float = 1.0):
        """
        添加数据源到聚合器

        Args:
            source: 数据源实例
            is_primary: 是否为主要数据源
            weight: 负载均衡权重
        """
        super().add_source(source, is_primary, weight)
        self._source_usage[source.name] = 0

    async def fetch(self, *args, **kwargs) -> DataSourceResult:
        """
        获取数据（负载均衡策略）

        根据权重选择数据源，优先选择使用次数最少的数据源

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            DataSourceResult: 选择的数据源结果
        """
        if not self._sources:
            return DataSourceResult(
                success=False,
                error="聚合器中没有数据源",
                timestamp=time.time(),
                source=self.name
            )

        self._request_count += 1

        # 按使用次数排序，选择使用次数最少的数据源
        sorted_sources = sorted(
            self._sources,
            key=lambda x: self._source_usage.get(x.source.name, 0)
        )

        for info in sorted_sources:
            source = info.source
            try:
                result = await source.fetch(*args, **kwargs)
                self._source_usage[source.name] += 1

                if result.success:
                    self._success_count += 1
                    return result
            except Exception:
                self._source_usage[source.name] += 1

        return DataSourceResult(
            success=False,
            error="所有数据源均失败",
            timestamp=time.time(),
            source=self.name
        )

    async def fetch_all(self, *args, **kwargs) -> list[DataSourceResult]:
        """
        获取所有数据源的数据

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            List[DataSourceResult]: 所有数据源的结果列表
        """
        if not self._sources:
            return [
                DataSourceResult(
                    success=False,
                    error="聚合器中没有数据源",
                    timestamp=time.time(),
                    source=self.name
                )
            ]

        results: list[DataSourceResult] = []
        for info in self._sources:
            try:
                result = await info.source.fetch(*args, **kwargs)
                results.append(result)
            except Exception as e:
                results.append(DataSourceResult(
                    success=False,
                    error=str(e),
                    timestamp=time.time(),
                    source=info.source.name
                ))
        return results

    def get_statistics(self) -> dict[str, Any]:
        """
        获取聚合器统计信息

        Returns:
            Dict: 统计信息字典，包含负载均衡统计
        """
        stats = super().get_statistics()
        stats["source_usage"] = self._source_usage
        return stats


# 导出
__all__ = [
    "DataAggregator",
    "SameSourceAggregator",
    "LoadBalancedAggregator",
    "AggregatorSourceInfo"
]
