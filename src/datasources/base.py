"""
数据源模块基类定义
提供抽象基类 DataSource，所有数据源需继承此类并实现抽象方法
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DataSourceErrorType(Enum):
    """统一的错误类型枚举"""

    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    PARSE_ERROR = "parse_error"
    AUTH_ERROR = "auth_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    DATA_NOT_FOUND = "data_not_found"
    UNKNOWN_ERROR = "unknown_error"


class DataSourceType(Enum):
    """数据源类型枚举"""

    FUND = "fund"
    COMMODITY = "commodity"
    NEWS = "news"
    SECTOR = "sector"
    STOCK = "stock"  # 股票行情（指数数据源复用此类型）
    CRYPTO = "crypto"  # 加密货币


class DataSourceError(Exception):
    """数据源基础异常类"""

    def __init__(self, message: str, source_type: DataSourceType, details: dict | None = None):
        self.message = message
        self.source_type = source_type
        self.details = details or {}
        super().__init__(self.message)


class NetworkError(DataSourceError):
    """网络异常"""

    pass


class DataParseError(DataSourceError):
    """数据解析异常"""

    pass


class DataSourceUnavailableError(DataSourceError):
    """数据源不可用"""

    pass


class TimeoutError(DataSourceError):
    """请求超时异常"""

    pass


@dataclass
class DataSourceResult:
    """数据源返回结果封装"""

    success: bool
    data: Any | None = None
    error: str | None = None
    timestamp: float = 0.0
    source: str = ""
    metadata: dict | None = None
    error_type: DataSourceErrorType | None = None
    retryable: bool = True

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    @classmethod
    def from_exception(cls, e: Exception, source: str, data: Any = None) -> "DataSourceResult":
        """
        从异常创建失败结果

        Args:
            e: 捕获的异常
            source: 数据源标识
            data: 可选的附加数据

        Returns:
            DataSourceResult: 包含错误信息的失败结果
        """
        error_type = cls._infer_error_type(e)
        retryable = error_type != DataSourceErrorType.AUTH_ERROR

        return cls(
            success=False,
            data=data,
            error=str(e),
            timestamp=time.time(),
            source=source,
            metadata={"error_type": type(e).__name__},
            error_type=error_type,
            retryable=retryable,
        )

    @staticmethod
    def _infer_error_type(e: Exception) -> DataSourceErrorType:
        """
        推断异常对应的错误类型

        Args:
            e: 捕获的异常

        Returns:
            DataSourceErrorType: 推断的错误类型
        """
        if isinstance(e, asyncio.TimeoutError):
            return DataSourceErrorType.TIMEOUT_ERROR
        elif isinstance(e, ConnectionError):
            return DataSourceErrorType.NETWORK_ERROR
        elif isinstance(e, json.JSONDecodeError):
            return DataSourceErrorType.PARSE_ERROR
        else:
            return DataSourceErrorType.UNKNOWN_ERROR


class DataSource(ABC):
    """数据源抽象基类"""

    def __init__(self, name: str, source_type: DataSourceType, timeout: float = 10.0):
        """
        初始化数据源

        Args:
            name: 数据源名称
            source_type: 数据源类型
            timeout: 请求超时时间(秒)
        """
        self.name = name
        self.source_type = source_type
        self.timeout = timeout
        self._last_error: DataSourceError | None = None
        self._request_count = 0
        self._error_count = 0
        self._cache: dict[str, Any] = {}

    @property
    def error_rate(self) -> float:
        """获取错误率"""
        if self._request_count == 0:
            return 0.0
        return self._error_count / self._request_count

    @abstractmethod
    async def fetch(self, *args: Any, **kwargs: Any) -> DataSourceResult:
        """
        获取数据（抽象方法，子类必须实现）

        Returns:
            DataSourceResult: 返回结果封装对象
        """
        pass

    async def close(self) -> None:
        """关闭数据源连接（子类可选实现）"""
        pass

    async def fetch_batch(self, keys: list[str]) -> list[DataSourceResult]:
        """
        批量获取数据（默认实现）

        Args:
            keys: 要获取的数据键列表

        Returns:
            List[DataSourceResult]: 返回结果列表
        """
        start_time = time.time()

        async def fetch_one(key: str) -> DataSourceResult:
            return await self.fetch(key)

        tasks = [fetch_one(key) for key in keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        success_count = 0
        fail_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"key": keys[i]},
                    )
                )
                fail_count += 1
            else:
                processed_results.append(result)
                if result.success:
                    success_count += 1
                else:
                    fail_count += 1

        duration_ms = (time.time() - start_time) * 1000
        logger.debug(
            "批量获取完成",
            extra={
                "data_source_name": self.name,
                "batch_size": len(keys),
                "success_count": success_count,
                "fail_count": fail_count,
                "duration_ms": round(duration_ms, 2),
            },
        )

        return processed_results

    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        检查缓存是否有效

        Args:
            cache_key: 缓存键

        Returns:
            bool: 缓存是否有效
        """
        if not hasattr(self, "_cache"):
            return False
        if self._cache_type == "list":
            if not self._cache:
                return False
            return (time.time() - self._cache_time) < self._cache_timeout
        else:
            if cache_key not in self._cache:
                return False
            cache_time = self._cache[cache_key].get("_cache_time", 0)
            return (time.time() - cache_time) < self._cache_timeout

    @property
    def _cache_type(self) -> str:
        """缓存类型: 'dict' 或 'list'"""
        return "dict"

    def clear_cache(self) -> None:
        """清空缓存"""
        if self._cache_type == "list":
            self._cache = []
            if hasattr(self, "_cache_time"):
                self._cache_time = 0.0
        else:
            self._cache.clear()

    def _handle_error(self, error: Exception, source: str) -> DataSourceResult:
        """
        处理错误并返回标准结果

        Args:
            error: 捕获的异常
            source: 数据源标识

        Returns:
            DataSourceResult: 包含错误信息的失败结果
        """
        self._request_count += 1
        self._error_count += 1

        if isinstance(error, DataSourceError):
            self._last_error = error
            logger.warning(
                "数据源错误",
                extra={
                    "source": source,
                    "data_source_name": self.name,
                    "error_type": error.source_type.value,
                    "error_message": error.message,
                    "details": error.details,
                    "error_count": self._error_count,
                    "error_rate": self.error_rate,
                },
            )
            return DataSourceResult(
                success=False,
                error=error.message,
                timestamp=time.time(),
                source=source,
                metadata={"source_type": error.source_type, "details": error.details},
            )

        self._last_error = DataSourceError(
            message=str(error),
            source_type=self.source_type,
            details={"original_error": type(error).__name__},
        )

        logger.error(
            "数据源请求异常",
            extra={
                "source": source,
                "data_source_name": self.name,
                "error": str(error),
                "error_type": type(error).__name__,
                "error_count": self._error_count,
                "error_rate": self.error_rate,
            },
            exc_info=True,
        )

        return DataSourceResult(
            success=False,
            error=str(error),
            timestamp=time.time(),
            source=source,
            metadata={"error_type": type(error).__name__},
        )

    def _record_success(self) -> DataSourceResult:
        """记录成功请求"""
        self._request_count += 1
        return DataSourceResult(success=True, timestamp=time.time(), source=self.name)

    def get_status(self) -> dict[str, Any]:
        """
        获取数据源状态

        Returns:
            Dict: 包含状态信息的字典
        """
        return {
            "name": self.name,
            "type": self.source_type.value,
            "timeout": self.timeout,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": self.error_rate,
            "last_error": str(self._last_error) if self._last_error else None,
        }

    async def health_check(self) -> bool:
        """
        健康检查（默认实现：尝试获取数据）

        Returns:
            bool: 健康状态
        """
        try:
            result = await self.fetch()
            return result.success
        except Exception:
            return False
