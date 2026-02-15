"""
日志缓冲区模块

提供内存日志缓冲和 API 端点，用于实时查看后端日志。
"""

import logging
import threading
from collections import deque
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel


class LogEntry(BaseModel):
    """日志条目"""

    timestamp: datetime
    level: str
    logger: str
    message: str
    extra: dict | None = None


class LogBuffer(logging.Handler):
    """
    自定义日志 Handler，将日志存储到内存缓冲区
    """

    # 类级别的缓冲区，所有实例共享
    _buffer: ClassVar[deque[LogEntry]] = deque(maxlen=1000)
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, level: int = logging.DEBUG):
        super().__init__(level)
        self.formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created),
                level=logging.getLevelName(record.levelno),
                logger=record.name,
                message=msg,
            )
            with self._lock:
                self._buffer.append(entry)
        except Exception:
            self.handleError(record)

    @classmethod
    def get_logs(
        cls,
        level: str | None = None,
        limit: int = 100,
        logger: str | None = None,
    ) -> list[LogEntry]:
        """
        获取日志条目

        Args:
            level: 日志级别过滤 (DEBUG, INFO, WARNING, ERROR)
            limit: 返回数量限制
            logger: 日志器名称过滤

        Returns:
            日志条目列表
        """
        with cls._lock:
            logs = list(cls._buffer)

        # 过滤
        if level:
            logs = [log for log in logs if log.level == level.upper()]
        if logger:
            logs = [log for log in logs if logger.lower() in log.logger.lower()]

        # 返回最新的
        return logs[-limit:]

    @classmethod
    def clear(cls):
        """清空日志缓冲区"""
        with cls._lock:
            cls._buffer.clear()


# 创建全局日志缓冲区实例
_log_buffer = LogBuffer()


def get_log_buffer() -> LogBuffer:
    """获取日志缓冲区实例"""
    return _log_buffer
