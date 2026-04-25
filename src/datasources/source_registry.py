"""
数据源注册表模块
负责数据源的注册、发现和生命周期管理
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from .base import DataSource, DataSourceType

logger = logging.getLogger(__name__)


@dataclass
class DataSourceConfig:
    """数据源配置"""

    source_class: type[DataSource]
    name: str
    source_type: DataSourceType
    enabled: bool = True
    priority: int = 0
    config: dict[str, Any] = field(default_factory=dict)


class SourceRegistry:
    """
    数据源注册表

    负责：
    - 数据源注册和注销
    - 数据源发现和查询
    - 按类型组织数据源
    """

    def __init__(self) -> None:
        self._sources: dict[str, DataSource] = {}
        self._source_configs: dict[str, DataSourceConfig] = {}
        self._type_sources: dict[DataSourceType, list[str]] = {
            DataSourceType.FUND: [],
            DataSourceType.COMMODITY: [],
            DataSourceType.NEWS: [],
            DataSourceType.SECTOR: [],
            DataSourceType.STOCK: [],
        }

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

    def get(self, source_name: str) -> DataSource | None:
        """
        获取指定数据源

        Args:
            source_name: 数据源名称

        Returns:
            DataSource | None: 数据源实例，不存在返回 None
        """
        return self._sources.get(source_name)

    def get_by_type(self, source_type: DataSourceType) -> list[DataSource]:
        """
        按类型获取数据源列表

        Args:
            source_type: 数据源类型

        Returns:
            List[DataSource]: 数据源列表
        """
        return [self._sources[name] for name in self._type_sources[source_type]]

    def get_by_type_ids(self, source_type: DataSourceType) -> list[str]:
        """
        按类型获取数据源 ID 列表

        Args:
            source_type: 数据源类型

        Returns:
            List[str]: 数据源 ID 列表
        """
        return list(self._type_sources[source_type])

    def all_sources(self) -> dict[str, DataSource]:
        """
        获取所有数据源

        Returns:
            Dict[str, DataSource]: 数据源名称到实例的映射
        """
        return dict(self._sources)

    def all_configs(self) -> dict[str, DataSourceConfig]:
        """
        获取所有数据源配置

        Returns:
            Dict[str, DataSourceConfig]: 数据源名称到配置的映射
        """
        return dict(self._source_configs)

    def get_config(self, source_name: str) -> DataSourceConfig | None:
        """
        获取数据源配置

        Args:
            source_name: 数据源名称

        Returns:
            DataSourceConfig | None: 数据源配置
        """
        return self._source_configs.get(source_name)

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

    def set_enabled(self, source_name: str, enabled: bool) -> None:
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

    def set_priority(self, source_name: str, priority: int) -> None:
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


# 导出
__all__ = ["SourceRegistry", "DataSourceConfig"]
