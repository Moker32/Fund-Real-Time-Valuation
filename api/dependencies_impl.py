"""
依赖注入实现模块
包含依赖项的具体实现
"""

import uuid
from contextvars import ContextVar
from typing import Annotated

from fastapi import Depends, Header
from src.config import get_config_manager as get_config_manager_func
from src.config.manager import ConfigManager
from src.datasources.manager import DataSourceManager, create_default_manager

# 全局数据源管理器实例
_data_source_manager: DataSourceManager | None = None

# 请求ID上下文变量
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """获取当前请求的request_id"""
    return _request_id_ctx.get()


def set_request_id(request_id: str) -> None:
    """设置当前请求的request_id"""
    _request_id_ctx.set(request_id)


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


class DataSourceDependency:
    """
    FastAPI 依赖类：获取数据源管理器

    使用类而非函数可以更好地支持类型提示和扩展

    Attributes:
        _instance: 缓存的实例（如果需要每个请求新实例可移除）

    Usage:
        @app.get("/items")
        async def read_items(manager: DataSourceManager = Depends(DataSourceDependency)):
            ...
    """

    def __call__(self) -> DataSourceManager:
        """获取数据源管理器实例"""
        return get_data_source_manager()


class CloseDataSourceManager:
    """FastAPI 依赖类：关闭数据源管理器"""

    async def __call__(self) -> None:
        """关闭数据源管理器"""
        await close_data_source_manager()


class ConfigManagerDependency:
    """FastAPI 依赖类：获取配置管理器"""

    def __call__(self) -> ConfigManager:
        """获取配置管理器实例"""
        return get_config_manager_func()


# 为向后兼容保留别名
DataSourceDependencyCallable = DataSourceDependency
ConfigManagerDependencyCallable = ConfigManagerDependency


class RequestIdDependency:
    """
    FastAPI 依赖类：获取或生成请求ID

    从 X-Request-ID header 提取，如果不存在则生成新的UUID

    Usage:
        @app.get("/items")
        async def read_items(request_id: str = Depends(RequestIdDependency())):
            logger.info("Processing request", extra={"request_id": request_id})
    """

    def __call__(self, x_request_id: str | None = Header(None)) -> str:
        """获取请求ID"""
        if x_request_id:
            request_id = x_request_id
        else:
            request_id = str(uuid.uuid4())
        set_request_id(request_id)
        return request_id


# 预定义类型别名，方便使用
RequestId = Annotated[str, Depends(RequestIdDependency())]
