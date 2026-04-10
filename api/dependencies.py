"""
依赖注入模块
提供 FastAPI 应用所需的各种依赖项

注意：此模块使用应用级单例模式，通过 lifespan 进行初始化。
这种设计保证了：
1. 数据源管理器在应用生命周期内只初始化一次
2. 所有请求共享同一个管理器实例，提高性能
3. 便于测试时通过 set_data_source_manager 替换为 mock 对象
"""

from src.config import get_config_manager as get_config_manager_from_config
from src.config.manager import ConfigManager
from src.datasources.manager import DataSourceManager, create_default_manager

from .dependencies_impl import (
    CloseDataSourceManager,
    ConfigManagerDependency,
    ConfigManagerDependencyCallable,
    DataSourceDependency,
    RequestIdDependency,
    close_data_source_manager,
    get_data_source_manager,
    get_request_id,
    set_data_source_manager,
)

# 重新导出配置管理器函数
get_config_manager = get_config_manager_from_config

__all__ = [
    "DataSourceManager",
    "create_default_manager",
    "ConfigManager",
    "get_config_manager",
    "get_data_source_manager",
    "set_data_source_manager",
    "close_data_source_manager",
    "DataSourceDependency",
    "CloseDataSourceManager",
    "ConfigManagerDependency",
    "ConfigManagerDependencyCallable",
    "RequestIdDependency",
    "get_request_id",
]
