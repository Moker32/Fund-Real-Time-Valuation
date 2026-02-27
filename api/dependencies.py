"""
依赖注入模块
提供 FastAPI 应用所需的各种依赖项
"""

from src.config import get_config_manager as get_config_manager_func
from src.config.manager import ConfigManager
from src.datasources.manager import DataSourceManager, create_default_manager

# 全局数据源管理器实例
_data_source_manager: DataSourceManager | None = None


def get_data_source_manager() -> DataSourceManager:
    """
    获取数据源管理器实例（单例）

    Returns:
        DataSourceManager: 数据源管理器实例
    """
    global _data_source_manager
    if _data_source_manager is None:
        _data_source_manager = create_default_manager()
    return _data_source_manager


def set_data_source_manager(manager: DataSourceManager) -> None:
    """
    设置数据源管理器实例（用于测试）

    Args:
        manager: 数据源管理器实例
    """
    global _data_source_manager
    _data_source_manager = manager


async def close_data_source_manager() -> None:
    """关闭数据源管理器"""
    global _data_source_manager
    if _data_source_manager is not None:
        await _data_source_manager.close_all()
        _data_source_manager = None


def DataSourceDependency() -> DataSourceManager:
    """
    FastAPI 依赖：获取数据源管理器

    Returns:
        DataSourceManager: 数据源管理器实例

    Usage:
        @app.get("/items")
        async def read_items(manager: DataSourceManager = Depends(DataSourceDependency)):
            ...
    """
    return get_data_source_manager()


def ConfigManagerDependency() -> ConfigManager:
    """
    FastAPI 依赖：获取配置管理器

    Returns:
        ConfigManager: 配置管理器实例

    Usage:
        @app.get("/funds")
        async def get_funds(config: ConfigManager = Depends(ConfigManagerDependency)):
            ...
    """
    return get_config_manager_func()
