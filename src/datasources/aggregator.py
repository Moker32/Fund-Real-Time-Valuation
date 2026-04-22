"""
数据聚合器模块

提供多数据源聚合功能:
- DataAggregator: 抽象基类，管理多个数据源
- SameSourceAggregator: 同源数据聚合器，支持故障切换
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TypedDict

from .base import DataSource, DataSourceResult


@dataclass
class AggregatorSourceInfo:
    """聚合器中的数据源信息"""

    source: DataSource
    is_primary: bool = False
    weight: float = 1.0  # 负载均衡权重


class AggregatorStatisticsSource(TypedDict):
    """聚合器统计中单个数据源信息"""

    name: str
    is_primary: bool
    weight: float
    status: dict[str, Any]


class AggregatorStatistics(TypedDict):
    """聚合器统计信息"""

    name: str
    source_count: int
    primary_source: str | None
    request_count: int
    success_count: int
    failover_count: int
    success_rate: float
    sources: list[AggregatorStatisticsSource]


class LoadBalancedAggregatorStatistics(AggregatorStatistics, total=False):
    """负载均衡聚合器统计信息（包含额外负载均衡统计）"""

    source_usage: dict[str, int]


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

    def add_source(self, source: DataSource, is_primary: bool = False, weight: float = 1.0) -> None:
        """
        添加数据源到聚合器

        Args:
            source: 数据源实例
            is_primary: 是否为主要数据源
            weight: 负载均衡权重
        """
        self._sources.append(
            AggregatorSourceInfo(source=source, is_primary=is_primary, weight=weight)
        )

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
    async def fetch(self, *args: Any, **kwargs: Any) -> DataSourceResult:
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
    async def fetch_all(self, *args: Any, **kwargs: Any) -> list[DataSourceResult]:
        """
        获取所有数据源的数据

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            List[DataSourceResult]: 所有数据源的结果列表
        """
        pass

    def get_statistics(self) -> AggregatorStatistics:
        """
        获取聚合器统计信息

        Returns:
            AggregatorStatistics: 统计信息字典
        """
        return {
            "name": self.name,
            "source_count": len(self._sources),
            "primary_source": self.get_primary_source().name if self.get_primary_source() else None,
            "request_count": self._request_count,
            "success_count": self._success_count,
            "failover_count": self._failover_count,
            "success_rate": self._success_count / self._request_count
            if self._request_count > 0
            else 0.0,
            "sources": [
                {
                    "name": info.source.name,
                    "is_primary": info.is_primary,
                    "weight": info.weight,
                    "status": info.source.get_status(),
                }
                for info in self._sources
            ],
        }


# 导出
__all__ = [
    "DataAggregator",
    "AggregatorSourceInfo",
]
