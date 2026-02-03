"""
数据源模块基类定义
提供抽象基类 DataSource，所有数据源需继承此类并实现抽象方法
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum
import time


class DataSourceType(Enum):
    """数据源类型枚举"""
    FUND = "fund"
    COMMODITY = "commodity"
    NEWS = "news"
    SECTOR = "sector"


class DataSourceError(Exception):
    """数据源基础异常类"""

    def __init__(self, message: str, source_type: DataSourceType, details: Optional[Dict] = None):
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


@dataclass
class DataSourceResult:
    """数据源返回结果封装"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: float = 0.0
    source: str = ""
    metadata: Optional[Dict] = None

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


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
        self._last_error: Optional[DataSourceError] = None
        self._request_count = 0
        self._error_count = 0

    @property
    def error_rate(self) -> float:
        """获取错误率"""
        if self._request_count == 0:
            return 0.0
        return self._error_count / self._request_count

    @abstractmethod
    async def fetch(self, *args, **kwargs) -> DataSourceResult:
        """
        获取数据（抽象方法，子类必须实现）

        Returns:
            DataSourceResult: 返回结果封装对象
        """
        pass

    @abstractmethod
    async def fetch_batch(self, *args, **kwargs) -> List[DataSourceResult]:
        """
        批量获取数据（抽象方法，子类可选实现）

        Returns:
            List[DataSourceResult]: 返回结果列表
        """
        pass

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
            return DataSourceResult(
                success=False,
                error=error.message,
                timestamp=time.time(),
                source=source,
                metadata={"source_type": error.source_type, "details": error.details}
            )

        self._last_error = DataSourceError(
            message=str(error),
            source_type=self.source_type,
            details={"original_error": type(error).__name__}
        )

        return DataSourceResult(
            success=False,
            error=str(error),
            timestamp=time.time(),
            source=source,
            metadata={"error_type": type(error).__name__}
        )

    def _record_success(self) -> DataSourceResult:
        """记录成功请求"""
        self._request_count += 1
        return DataSourceResult(success=True, timestamp=time.time(), source=self.name)

    def get_status(self) -> Dict[str, Any]:
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
            "last_error": str(self._last_error) if self._last_error else None
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
