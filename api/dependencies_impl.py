"""
依赖注入实现模块
包含依赖项的具体实现
"""

import uuid
from contextvars import ContextVar
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Header

from src.config import get_config_manager as get_config_manager_func
from src.config.manager import ConfigManager
from src.datasources.manager import DataSourceManager, create_default_manager

if TYPE_CHECKING:
    from src.datasources.index_source import HybridIndexSource
    from src.datasources.trading_calendar_source import TradingCalendarSource
    from src.db.database import DatabaseManager

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


# ==================== 交易日历数据源依赖 ====================


_trading_calendar_source: "TradingCalendarSource | None" = None


def get_trading_calendar_source() -> "TradingCalendarSource":
    """
    获取交易日历数据源实例（单例）

    Returns:
        TradingCalendarSource: 交易日历数据源实例
    """
    global _trading_calendar_source
    if _trading_calendar_source is None:
        from src.datasources.trading_calendar_source import TradingCalendarSource

        _trading_calendar_source = TradingCalendarSource()
    return _trading_calendar_source


def set_trading_calendar_source(source: "TradingCalendarSource") -> None:
    """
    设置交易日历数据源实例（用于测试）

    Args:
        source: 交易日历数据源实例
    """
    global _trading_calendar_source
    _trading_calendar_source = source


class TradingCalendarDependency:
    """
    FastAPI 依赖类：获取交易日历数据源

    Usage:
        @app.get("/items")
        async def read_items(calendar: TradingCalendarSource = Depends(TradingCalendarDependency())):
            ...
    """

    def __call__(self) -> "TradingCalendarSource":
        """获取交易日历数据源实例"""
        return get_trading_calendar_source()


# ==================== 指数历史数据源依赖 ====================


_index_history_source: "HybridIndexSource | None" = None


def get_index_history_source() -> "HybridIndexSource":
    """
    获取指数历史数据源实例（单例）

    Returns:
        HybridIndexSource: 指数历史数据源实例
    """
    global _index_history_source
    if _index_history_source is None:
        from src.datasources.index_source import HybridIndexSource

        _index_history_source = HybridIndexSource()
    return _index_history_source


def set_index_history_source(source: "HybridIndexSource") -> None:
    """
    设置指数历史数据源实例（用于测试）

    Args:
        source: 指数历史数据源实例
    """
    global _index_history_source
    _index_history_source = source


class IndexHistoryDependency:
    """
    FastAPI 依赖类：获取指数历史数据源

    Usage:
        @app.get("/indices/history")
        async def get_history(source: HybridIndexSource = Depends(IndexHistoryDependency())):
            ...
    """

    def __call__(self) -> "HybridIndexSource":
        """获取指数历史数据源实例"""
        return get_index_history_source()


# ==================== 指数分时数据源依赖 ====================


_index_intraday_source: "HybridIndexSource | None" = None


def get_index_intraday_source() -> "HybridIndexSource":
    """
    获取指数分时数据源实例（单例）

    Returns:
        HybridIndexSource: 指数分时数据源实例
    """
    global _index_intraday_source
    if _index_intraday_source is None:
        from src.datasources.index_source import HybridIndexSource

        _index_intraday_source = HybridIndexSource()
    return _index_intraday_source


def set_index_intraday_source(source: "HybridIndexSource") -> None:
    """
    设置指数分时数据源实例（用于测试）

    Args:
        source: 指数分时数据源实例
    """
    global _index_intraday_source
    _index_intraday_source = source


class IndexIntradayDependency:
    """
    FastAPI 依赖类：获取指数分时数据源

    Usage:
        @app.get("/indices/intraday")
        async def get_intraday(source: HybridIndexSource = Depends(IndexIntradayDependency())):
            ...
    """

    def __call__(self) -> "HybridIndexSource":
        """获取指数分时数据源实例"""
        return get_index_intraday_source()


# ==================== 数据库管理器依赖 ====================


_db_source: "DatabaseManager | None" = None


def get_database_source() -> "DatabaseManager":
    """
    获取数据库管理器实例（单例）

    Returns:
        DatabaseManager: 数据库管理器实例
    """
    global _db_source
    if _db_source is None:
        from src.db.database import DatabaseManager

        _db_source = DatabaseManager()
    return _db_source


def set_database_source(source: "DatabaseManager") -> None:
    """
    设置数据库管理器实例（用于测试）

    Args:
        source: 数据库管理器实例
    """
    global _db_source
    _db_source = source


class DatabaseDependency:
    """
    FastAPI 依赖类：获取数据库管理器

    Usage:
        @app.get("/holidays")
        async def get_holidays(db: DatabaseManager = Depends(DatabaseDependency())):
            ...
    """

    def __call__(self) -> "DatabaseManager":
        """获取数据库管理器实例"""
        return get_database_source()
