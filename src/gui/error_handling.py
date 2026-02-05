# -*- coding: UTF-8 -*-
"""错误处理工具模块

提供全局错误处理功能，包括错误对话框、错误记录和异常处理装饰器。
"""

import sys
import traceback
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import flet as ft

# 获取模块日志记录器
logger = logging.getLogger(__name__)
from flet import (
    AlertDialog,
    Column,
    Container,
    Divider,
    ElevatedButton,
    Icon,
    IconButton,
    Icons,
    Row,
    Text,
)

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from .components import AppColors


class ErrorSeverity(Enum):
    """错误严重级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# 错误级别对应的颜色
ERROR_COLORS = {
    ErrorSeverity.INFO: AppColors.ACCENT_BLUE,
    ErrorSeverity.WARNING: AppColors.ACCENT_ORANGE,
    ErrorSeverity.ERROR: AppColors.UP_RED,
    ErrorSeverity.CRITICAL: "#FF0000",  # 鲜红色
}

# 错误级别对应的图标
ERROR_ICONS = {
    ErrorSeverity.INFO: Icons.INFO,
    ErrorSeverity.WARNING: Icons.WARNING,
    ErrorSeverity.ERROR: Icons.ERROR,
    ErrorSeverity.CRITICAL: Icons.DANGEROUS,
}


@dataclass
class ErrorRecord:
    """错误记录"""

    message: str
    severity: ErrorSeverity
    timestamp: datetime = field(default_factory=datetime.now)
    details: str | None = None
    exception_type: str | None = None


class ErrorHandler:
    """全局错误处理器

    功能：
    - 记录错误和警告
    - 提供错误统计
    - 支持异常捕获装饰器
    - 自动清理旧错误
    """

    _shared_handler: Optional["ErrorHandler"] = None

    def __init__(self, max_recent_errors: int = 50):
        """初始化错误处理器

        Args:
            max_recent_errors: 最大保留的最近错误数量
        """
        self.max_recent_errors = max_recent_errors
        self.error_count = 0
        self.warning_count = 0
        self.recent_errors: list[ErrorRecord] = []

    @classmethod
    def get_shared(cls) -> "ErrorHandler":
        """获取共享的错误处理器实例"""
        if cls._shared_handler is None:
            cls._shared_handler = cls()
        return cls._shared_handler

    def record_error(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: str | None = None,
        exception: Exception | None = None,
    ) -> ErrorRecord:
        """记录一个错误

        Args:
            message: 错误信息
            severity: 错误级别
            details: 详细信息
            exception: 原始异常对象

        Returns:
            ErrorRecord: 错误记录对象
        """
        record = ErrorRecord(
            message=message,
            severity=severity,
            details=details,
            exception_type=type(exception).__name__ if exception else None,
            timestamp=datetime.now(),
        )

        self.recent_errors.append(record)

        # 更新计数
        if severity == ErrorSeverity.ERROR or severity == ErrorSeverity.CRITICAL:
            self.error_count += 1
        else:
            self.warning_count += 1

        # 清理超出限制的旧错误
        while len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors.pop(0)

        return record

    def record_warning(self, message: str, details: str | None = None) -> ErrorRecord:
        """记录一个警告

        Args:
            message: 警告信息
            details: 详细信息

        Returns:
            ErrorRecord: 警告记录对象
        """
        return self.record_error(
            message=message, severity=ErrorSeverity.WARNING, details=details
        )

    def get_stats(self) -> dict:
        """获取错误统计信息

        Returns:
            dict: 包含 error_count, warning_count, recent_errors 的字典
        """
        return {
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "recent_errors": [
                {
                    "message": r.message,
                    "severity": r.severity.value,
                    "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "details": r.details,
                }
                for r in self.recent_errors[-10:]  # 只返回最近10个
            ],
        }

    def clear_errors(self):
        """清除所有错误记录"""
        self.error_count = 0
        self.warning_count = 0
        self.recent_errors.clear()

    def exception_handler(
        self, default_return: Any = None, reraise: bool = False
    ) -> Callable:
        """异常处理装饰器

        Args:
            default_return: 捕获异常后返回的默认值
            reraise: 是否重新抛出异常

        Returns:
            Callable: 装饰器函数
        """

        def decorator(func: Callable) -> Callable:
            wrapper = func

            # 检查是否是异步函数
            import asyncio

            if asyncio.iscoroutinefunction(func):

                async def async_wrapper(*args, **kwargs) -> Any:
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        self.record_error(
                            message=str(e),
                            severity=ErrorSeverity.ERROR,
                            details=traceback.format_exc(),
                            exception=e,
                        )
                        if reraise:
                            raise
                        return default_return

                wrapper = async_wrapper
            else:

                def sync_wrapper(*args, **kwargs) -> Any:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        self.record_error(
                            message=str(e),
                            severity=ErrorSeverity.ERROR,
                            details=traceback.format_exc(),
                            exception=e,
                        )
                        if reraise:
                            raise
                        return default_return

                wrapper = sync_wrapper

            return wrapper

        return decorator


def show_error_dialog(
    page: ft.Page,
    message: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    title: str | None = None,
    details: str | None = None,
    on_dismiss: Callable | None = None,
) -> AlertDialog:
    """显示错误对话框

    Args:
        page: Flet 页面对象
        message: 错误信息
        severity: 错误级别
        title: 对话框标题（可选，默认根据 severity 自动生成）
        details: 详细信息（可选）
        on_dismiss: 关闭回调

    Returns:
        AlertDialog: 创建的对话框对象
    """
    # 确定标题
    if title is None:
        title_map = {
            ErrorSeverity.INFO: "提示信息",
            ErrorSeverity.WARNING: "警告",
            ErrorSeverity.ERROR: "错误",
            ErrorSeverity.CRITICAL: "严重错误",
        }
        title = title_map.get(severity, "错误")

    # 获取颜色和图标
    color = ERROR_COLORS.get(severity, AppColors.UP_RED)
    icon = ERROR_ICONS.get(severity, Icons.ERROR)

    # 构建内容
    content_controls = [
        Row(
            [
                Icon(icon, color=color, size=24),
                Text(title, size=18, weight=ft.FontWeight.BOLD, color=color),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        Container(height=10),
        Text(
            message,
            size=14,
            color=AppColors.TEXT_PRIMARY,
        ),
    ]

    # 添加详细信息（如果有）
    if details:
        content_controls.extend([
            Container(height=10),
            Divider(color=AppColors.DIVIDER),
            Container(height=10),
            Text(
                "详细信息:",
                size=12,
                color=AppColors.TEXT_SECONDARY,
            ),
            Container(
                content=Text(
                    details,
                    size=11,
                    color=AppColors.TEXT_SECONDARY,
                    selectable=True,
                ),
                bgcolor=AppColors.CARD_DARK,
                padding=8,
                border_radius=8,
            ),
        ])

    # 创建对话框
    dialog = AlertDialog(
        modal=True,
        title=Row(
            [
                Text(title, weight=ft.FontWeight.BOLD),
                Container(expand=True),
                IconButton(
                    icon=Icons.CLOSE,
                    icon_color=AppColors.TEXT_SECONDARY,
                    on_click=lambda e: _close_dialog(dialog, page, on_dismiss),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        content=Container(
            content=Column(
                controls=content_controls,
                spacing=0,
            ),
            width=max(400, int(page.width * 0.4)) if page else 400,
        ),
        actions=[
            ElevatedButton(
                "确定",
                on_click=lambda e: _close_dialog(dialog, page, on_dismiss),
                style=ft.ButtonStyle(
                    bgcolor=color,
                ),
            ),
        ],
    )

    # 添加到页面并显示
    page.overlay.append(dialog)
    dialog.open = True
    page.update()

    return dialog


def _close_dialog(
    dialog: AlertDialog,
    page: ft.Page,
    on_dismiss: Callable | None = None,
):
    """关闭对话框"""
    dialog.open = False
    page.update()

    # 调用关闭回调
    if on_dismiss:
        try:
            on_dismiss()
        except Exception as e:
            logger.warning(f"对话框关闭回调执行失败: {e}")


def show_network_error(
    page: ft.Page,
    operation: str = "网络请求",
    error_message: str | None = None,
) -> AlertDialog:
    """显示网络错误对话框

    Args:
        page: Flet 页面对象
        operation: 操作名称（如 "获取基金数据"）
        error_message: 错误信息（可选，默认显示通用信息）

    Returns:
        AlertDialog: 创建的对话框对象
    """
    message = error_message or f"{operation}失败，请检查网络连接后重试"

    return show_error_dialog(
        page=page,
        message=message,
        severity=ErrorSeverity.ERROR,
        title=f"{operation}失败",
    )


def show_data_error(
    page: ft.Page,
    data_type: str = "数据",
    error_message: str | None = None,
) -> AlertDialog:
    """显示数据错误对话框

    Args:
        page: Flet 页面对象
        data_type: 数据类型（如 "基金数据"）
        error_message: 错误信息（可选）

    Returns:
        AlertDialog: 创建的对话框对象
    """
    message = error_message or f"无法获取{data_type}，请稍后重试"

    return show_error_dialog(
        page=page,
        message=message,
        severity=ErrorSeverity.ERROR,
        title=f"{data_type}加载失败",
    )
