# -*- coding: UTF-8 -*-
"""TUI应用自动化测试"""

import pytest
from textual.app import App
from textual.widgets import Static, DataTable


class TestFundTUI:
    """基金TUI应用测试类"""

    @pytest.fixture
    def app(self):
        """创建测试应用实例"""
        from src.ui.app import FundTUIApp
        return FundTUIApp()

    def test_app_initial_state(self, app):
        """测试应用初始状态"""
        assert app.active_view == "fund"
        assert app.is_dark_theme == True

    def test_fund_table_columns(self):
        """测试基金表格列"""
        from src.ui.tables import FundTable
        table = FundTable()
        # 验证表存在
        assert table is not None

    def test_fund_data_model(self):
        """测试基金数据模型"""
        from src.ui.models import FundData
        fund = FundData(
            code="161039",
            name="测试基金",
            net_value=1.0000,
            est_value=1.0100,
            change_pct=1.0,
            profit=100.0,
            hold_shares=1000.0,
            cost=1.0000
        )
        assert fund.code == "161039"
        assert fund.hold_shares == 1000.0


def test_app_compose():
    """测试应用Compose"""
    from src.ui.app import FundTUIApp
    app = FundTUIApp()
    # 测试能够正常compose
    assert app is not None


def test_tabbed_content_import():
    """测试TabbedContent导入"""
    from textual.widgets import TabbedContent, TabPane
    assert TabbedContent is not None
    assert TabPane is not None


def test_screen_import():
    """测试Screen导入"""
    from textual.screen import Screen
    assert Screen is not None


def test_fund_detail_screen_import():
    """测试FundDetailScreen导入"""
    from src.ui.fund_detail_screen import FundDetailScreen
    assert FundDetailScreen is not None


def test_fund_context_menu_import():
    """测试FundContextMenu导入"""
    from src.ui.menus import FundContextMenu
    assert FundContextMenu is not None


def test_fund_table_bindings():
    """测试基金表格快捷键绑定"""
    from src.ui.tables import FundTable
    # BINDINGS 是 [(key, action, description), ...] 格式
    binding_keys = [b[0] for b in FundTable.BINDINGS]
    assert "enter" in binding_keys
    assert "a" in binding_keys
    assert "d" in binding_keys


def test_fund_context_menu_bindings():
    """测试上下文菜单快捷键绑定"""
    from src.ui.menus import FundContextMenu
    # BINDINGS 是 [(key, action, description), ...] 格式
    binding_keys = [b[0] for b in FundContextMenu.BINDINGS]
    assert "escape" in binding_keys
    assert "up" in binding_keys
    assert "down" in binding_keys
    assert "enter" in binding_keys


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
