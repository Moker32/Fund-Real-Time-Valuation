"""
依赖注入模块
提供 FastAPI 应用所需的各种依赖项
"""

from typing import Optional

from src.datasources.manager import DataSourceManager, create_default_manager


# 全局数据源管理器实例
_data_source_manager: Optional[DataSourceManager] = None


def get_data_source_manager() -> DataSourceManager:
    """
    获取数据源管理器实例

    Returns:
        DataSourceManager: 数据源管理器实例
    """
    global _data_source_manager
    if _data_source_manager is None:
        _data_source_manager = create_default_manager()
    return _data_source_manager


def set_data_source_manager(manager: DataSourceManager):
    """
    设置数据源管理器实例（用于测试）

    Args:
        manager: 数据源管理器实例
    """
    global _data_source_manager
    _data_source_manager = manager


async def close_data_source_manager():
    """关闭数据源管理器"""
    global _data_source_manager
    if _data_source_manager is not None:
        await _data_source_manager.close_all()
        _data_source_manager = None


class DataSourceDependency:
    """数据源管理器依赖类"""

    def __init__(self, manager: Optional[DataSourceManager] = None):
        """
        初始化数据源依赖

        Args:
            manager: 可选的数据源管理器实例
        """
        self._manager = manager

    async def __call__(self) -> DataSourceManager:
        """
        获取数据源管理器

        Returns:
            DataSourceManager: 数据源管理器实例
        """
        if self._manager is not None:
            return self._manager
        return get_data_source_manager()
