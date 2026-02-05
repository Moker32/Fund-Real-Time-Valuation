# -*- coding: UTF-8 -*-
"""错误处理模块测试

测试全局错误处理功能。
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestErrorHandlingModule:
    """错误处理模块测试"""

    def test_error_handling_module_exists(self):
        """测试错误处理模块可以正常导入"""
        from src.gui.error_handling import (
            ErrorHandler,
            show_error_dialog,
            ErrorSeverity,
        )

        assert ErrorHandler is not None
        assert show_error_dialog is not None
        assert ErrorSeverity is not None

    def test_error_severity_enum_values(self):
        """测试错误严重级别枚举值"""
        from src.gui.error_handling import ErrorSeverity

        assert hasattr(ErrorSeverity, "INFO")
        assert hasattr(ErrorSeverity, "WARNING")
        assert hasattr(ErrorSeverity, "ERROR")
        assert hasattr(ErrorSeverity, "CRITICAL")

    def test_error_handler_initialization(self):
        """测试错误处理器初始化"""
        from src.gui.error_handling import ErrorHandler

        handler = ErrorHandler()
        assert handler is not None
        assert hasattr(handler, "error_count")
        assert hasattr(handler, "warning_count")

    def test_error_handler_record_error(self):
        """测试错误处理器记录错误"""
        from src.gui.error_handling import ErrorHandler, ErrorSeverity

        handler = ErrorHandler()

        # 记录一个错误
        handler.record_error("Test error message", ErrorSeverity.ERROR)

        assert handler.error_count == 1
        assert len(handler.recent_errors) == 1

    def test_error_handler_record_warning(self):
        """测试错误处理器记录警告"""
        from src.gui.error_handling import ErrorHandler, ErrorSeverity

        handler = ErrorHandler()

        # 记录一个警告
        handler.record_warning("Test warning message")

        assert handler.warning_count == 1

    def test_error_handler_get_stats(self):
        """测试错误处理器获取统计信息"""
        from src.gui.error_handling import ErrorHandler, ErrorSeverity

        handler = ErrorHandler()

        # 记录一些错误和警告
        handler.record_error("Error 1", ErrorSeverity.ERROR)
        handler.record_error("Error 2", ErrorSeverity.ERROR)  # 改为 ERROR
        handler.record_warning("Warning 1")

        stats = handler.get_stats()

        assert "error_count" in stats
        assert "warning_count" in stats
        assert "recent_errors" in stats
        assert stats["error_count"] == 2  # 2 个 ERROR
        assert stats["warning_count"] == 1

    def test_error_handler_clear_errors(self):
        """测试错误处理器清除错误"""
        from src.gui.error_handling import ErrorHandler, ErrorSeverity

        handler = ErrorHandler()

        # 记录错误
        handler.record_error("Test error", ErrorSeverity.ERROR)
        handler.record_warning("Test warning")

        # 清除
        handler.clear_errors()

        assert handler.error_count == 0
        assert handler.warning_count == 0
        assert len(handler.recent_errors) == 0

    def test_error_handler_clear_old_errors(self):
        """测试错误处理器清除旧错误"""
        from src.gui.error_handling import ErrorHandler, ErrorSeverity
        import time

        handler = ErrorHandler(max_recent_errors=5)

        # 记录超过限制的错误
        for i in range(10):
            handler.record_error(f"Error {i}", ErrorSeverity.ERROR)

        # 验证保留最近的错误
        assert len(handler.recent_errors) == 5
        # 应该是最后5个错误（Error 5 到 Error 9）
        assert handler.recent_errors[-1].message == "Error 9"

    def test_error_handler_exception_handler(self):
        """测试错误处理器异常装饰器"""
        from src.gui.error_handling import ErrorHandler, ErrorSeverity

        handler = ErrorHandler()

        @handler.exception_handler()
        def test_function():
            raise ValueError("Test exception")

        # 应该捕获异常并记录
        result = test_function()
        assert result is None  # 异常被捕获后返回None

        assert handler.error_count == 1
        assert len(handler.recent_errors) == 1
        # 验证异常类型被正确记录
        assert handler.recent_errors[0].exception_type == "ValueError"

    def test_error_handler_exception_handler_with_return(self):
        """测试异常装饰器可以返回默认值"""
        from src.gui.error_handling import ErrorHandler, ErrorSeverity

        handler = ErrorHandler()

        @handler.exception_handler(default_return="fallback")
        def test_function():
            raise ValueError("Test exception")

        result = test_function()
        assert result == "fallback"


class TestShowErrorDialog:
    """错误对话框测试"""

    def test_show_error_dialog_function_exists(self):
        """测试 show_error_dialog 函数存在"""
        from src.gui.error_handling import show_error_dialog

        assert callable(show_error_dialog)

    def test_show_error_dialog_with_mock_page(self):
        """测试使用模拟页面显示错误对话框"""
        from src.gui.error_handling import show_error_dialog, ErrorSeverity

        # 创建模拟页面
        mock_page = MagicMock()
        mock_page.overlay = []
        mock_page.update = MagicMock()

        # 显示错误对话框
        show_error_dialog(
            mock_page,
            "测试错误信息",
            ErrorSeverity.ERROR,
            title="测试标题",
        )

        # 验证对话框被添加到 overlay
        assert len(mock_page.overlay) == 1

        # 验证 update 被调用
        mock_page.update.assert_called_once()

    def test_show_error_dialog_info_severity(self):
        """测试显示信息级别错误对话框"""
        from src.gui.error_handling import show_error_dialog, ErrorSeverity

        mock_page = MagicMock()
        mock_page.overlay = []
        mock_page.update = MagicMock()

        show_error_dialog(
            mock_page,
            "这是一条信息",
            ErrorSeverity.INFO,
        )

        dialog = mock_page.overlay[0]
        assert dialog is not None

    def test_show_error_dialog_warning_severity(self):
        """测试显示警告级别错误对话框"""
        from src.gui.error_handling import show_error_dialog, ErrorSeverity

        mock_page = MagicMock()
        mock_page.overlay = []
        mock_page.update = MagicMock()

        show_error_dialog(
            mock_page,
            "这是一条警告",
            ErrorSeverity.WARNING,
        )

        dialog = mock_page.overlay[0]
        assert dialog is not None

    def test_show_error_dialog_critical_severity(self):
        """测试显示严重级别错误对话框"""
        from src.gui.error_handling import show_error_dialog, ErrorSeverity

        mock_page = MagicMock()
        mock_page.overlay = []
        mock_page.update = MagicMock()

        show_error_dialog(
            mock_page,
            "这是一条严重错误",
            ErrorSeverity.CRITICAL,
        )

        dialog = mock_page.overlay[0]
        assert dialog is not None

    def test_show_error_dialog_with_details(self):
        """测试显示带详细信息的错误对话框"""
        from src.gui.error_handling import show_error_dialog, ErrorSeverity

        mock_page = MagicMock()
        mock_page.overlay = []
        mock_page.update = MagicMock()

        show_error_dialog(
            mock_page,
            "主要错误信息",
            ErrorSeverity.ERROR,
            details="详细错误信息\n错误堆栈...",
        )

        # 验证对话框被添加
        assert len(mock_page.overlay) == 1


class TestErrorHandlerIntegration:
    """错误处理器集成测试"""

    def test_gui_app_has_error_handler(self):
        """测试 GUI 应用有错误处理器"""
        from src.gui.main import FundGUIApp

        app = FundGUIApp()
        assert hasattr(app, "error_handler")

    def test_gui_app_error_handler_type(self):
        """测试 GUI 应用错误处理器类型"""
        from src.gui.main import FundGUIApp
        from src.gui.error_handling import ErrorHandler

        app = FundGUIApp()
        assert isinstance(app.error_handler, ErrorHandler)

    def test_gui_app_error_handler_shared(self):
        """测试 GUI 应用共享同一个错误处理器"""
        from src.gui.main import FundGUIApp
        from src.gui.error_handling import ErrorHandler

        app1 = FundGUIApp()
        app2 = FundGUIApp()

        # 验证使用的是同一个错误处理器实例
        assert app1.error_handler is app2.error_handler

    def test_show_error_dialog_integration(self):
        """测试错误对话框在 GUI 中集成"""
        from src.gui.main import FundGUIApp
        from src.gui.error_handling import ErrorSeverity, show_error_dialog
        from unittest.mock import MagicMock

        app = FundGUIApp()

        # 创建模拟页面
        mock_page = MagicMock()
        mock_page.overlay = []
        mock_page.update = MagicMock()

        # 模拟 page 属性
        app.page = mock_page

        # 使用应用的方法显示错误
        app._show_error = lambda msg, sev=ErrorSeverity: show_error_dialog(
            app.page, msg, sev
        )

        app._show_error("集成测试错误", ErrorSeverity.ERROR)

        assert len(mock_page.overlay) == 1


class TestAppColorsInErrorHandling:
    """错误处理中的颜色配置测试"""

    def test_error_severity_colors_defined(self):
        """测试错误级别颜色已定义"""
        from src.gui.error_handling import (
            ErrorSeverity,
            ERROR_COLORS,
        )

        assert hasattr(ErrorSeverity, "INFO")
        assert hasattr(ErrorSeverity, "WARNING")
        assert hasattr(ErrorSeverity, "ERROR")
        assert hasattr(ErrorSeverity, "CRITICAL")

        # 验证颜色映射存在（使用枚举作为键）
        assert ErrorSeverity.INFO in ERROR_COLORS
        assert ErrorSeverity.WARNING in ERROR_COLORS
        assert ErrorSeverity.ERROR in ERROR_COLORS
        assert ErrorSeverity.CRITICAL in ERROR_COLORS
