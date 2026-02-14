"""
统一数据请求/响应模型

为 DataGateway 提供统一的数据结构定义
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from src.datasources.base import DataSourceType


class RequestPriority(IntEnum):
    """请求优先级枚举"""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class ResponseStatus(IntEnum):
    """响应状态枚举"""

    SUCCESS = 0
    PARTIAL = 1  # 部分成功（批量请求时）
    FAILED = 2
    TIMEOUT = 3
    FALLBACK = 4  # 使用了降级


@dataclass
class DataRequest:
    """统一数据请求模型"""

    symbol: str  # 股票代码/基金代码/商品名称
    source_type: DataSourceType  # 数据源类型
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: RequestPriority = RequestPriority.NORMAL
    allow_fallback: bool = True  # 是否允许降级
    timeout: float = 10.0  # 超时时间(秒)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "symbol": self.symbol,
            "source_type": self.source_type.value,
            "priority": self.priority,
            "allow_fallback": self.allow_fallback,
            "timeout": self.timeout,
            "metadata": self.metadata,
        }


@dataclass
class DataResponse:
    """统一数据响应模型"""

    request_id: str
    success: bool
    data: Any = None
    error: str | None = None
    source: str = ""
    status: ResponseStatus = ResponseStatus.SUCCESS
    fallback_used: bool = False
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.success and self.status == ResponseStatus.SUCCESS:
            self.status = ResponseStatus.SUCCESS
        elif not self.success and self.status == ResponseStatus.SUCCESS:
            self.status = ResponseStatus.FAILED

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "source": self.source,
            "status": self.status,
            "fallback_used": self.fallback_used,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_result(
        cls,
        request: DataRequest,
        result: "DataSourceResult",
        latency_ms: float = 0.0,
    ) -> "DataResponse":
        """
        从 DataSourceResult 转换而来

        Args:
            request: 原始请求
            result: 数据源返回结果
            latency_ms: 请求延迟

        Returns:
            DataResponse 实例
        """
        if result.success:
            return cls(
                request_id=request.request_id,
                success=True,
                data=result.data,
                source=result.source,
                status=ResponseStatus.SUCCESS,
                latency_ms=latency_ms,
                timestamp=result.timestamp,
                metadata=result.metadata or {},
            )
        else:
            return cls(
                request_id=request.request_id,
                success=False,
                error=result.error,
                source=result.source,
                status=ResponseStatus.FAILED,
                latency_ms=latency_ms,
                timestamp=result.timestamp,
                metadata=result.metadata or {},
            )


@dataclass
class BatchDataRequest:
    """批量数据请求"""

    requests: list[DataRequest]
    parallel: bool = True  # 是否并行执行

    def __len__(self) -> int:
        return len(self.requests)


@dataclass
class BatchDataResponse:
    """批量数据响应"""

    request_id: str  # 批次请求ID
    responses: list[DataResponse]
    total_count: int
    success_count: int
    failed_count: int
    total_latency_ms: float

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "responses": [r.to_dict() for r in self.responses],
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "success_rate": self.success_rate,
            "total_latency_ms": self.total_latency_ms,
        }


# 为了向后兼容，导入 DataSourceResult
from src.datasources.base import DataSourceResult  # noqa: E402

__all__ = [
    "DataRequest",
    "DataResponse",
    "BatchDataRequest",
    "BatchDataResponse",
    "RequestPriority",
    "ResponseStatus",
    "DataSourceResult",
    "DataSourceType",
]
