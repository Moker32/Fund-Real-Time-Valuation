# -*- coding: UTF-8 -*-
"""GUI 模块回归测试

测试 GUI 应用的导入、初始化和基本功能。
确保 GUI 和数据库模块协同工作正常。
"""

import pytest
import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestGUIModuleImport:
    """GUI 模块导入测试"""

    def test_import_gui_module(self):
        """测试 GUI 模块可以正常导入"""
        from src.gui import FundGUIApp

        assert FundGUIApp is not None

    def test_import_main_module(self):
        """测试主应用模块可以正常导入"""
        from src.gui.main import (
            FundGUIApp,
            FundDisplayData,
        )

        assert FundGUIApp is not None
        assert FundDisplayData is not None

    def test_import_database_module(self):
        """测试数据库模块可以正常导入"""
        from src.db import DatabaseManager, ConfigDAO, FundHistoryDAO

        assert DatabaseManager is not None
        assert ConfigDAO is not None
        assert FundHistoryDAO is not None


class TestGUIAppInitialization:
    """GUI 应用初始化测试"""

    def test_gui_app_creation(self):
        """测试 GUI 应用可以正常创建实例"""
        from src.gui.main import FundGUIApp

        app = FundGUIApp()
        assert app is not None
        assert app.funds == []
        assert app.refresh_interval == 30

    def test_gui_app_has_required_attributes(self):
        """测试 GUI 应用具有必要的属性"""
        from src.gui.main import FundGUIApp

        app = FundGUIApp()

        # 检查数据管理器
        assert hasattr(app, "data_source_manager")
        assert hasattr(app, "db_manager")
        assert hasattr(app, "config_dao")

        # 检查数据列表
        assert hasattr(app, "funds")
        # news_list 在切换到新闻标签页时动态创建


class TestDataClasses:
    """数据类测试"""

    def test_fund_display_data_creation(self):
        """测试基金显示数据类创建"""
        from src.gui.main import FundDisplayData

        fund = FundDisplayData(
            code="161039",
            name="富国中证新能源汽车指数",
            net_value=1.2345,
            est_value=1.2456,
            change_pct=1.23,
            profit=156.78,
            hold_shares=1000.0,
            cost=1.15,
        )

        assert fund.code == "161039"
        assert fund.name == "富国中证新能源汽车指数"
        assert fund.net_value == 1.2345
        assert fund.change_pct == 1.23

    # CommodityDisplayData 和 NewsDisplayData 在 GUI 中使用 Column/List 实现
    # 不再需要单独的数据类
    """数据库集成测试"""

    def test_database_initialization_with_temp_path(self):
        """测试使用临时路径初始化数据库"""
        from src.db.database import DatabaseManager

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            db = DatabaseManager(db_path=temp_path)
            assert os.path.exists(temp_path)
            assert db.db_path == temp_path
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_config_dao_operations(self):
        """测试配置 DAO 基本操作"""
        from src.db.database import DatabaseManager, ConfigDAO

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            db = DatabaseManager(db_path=temp_path)
            dao = ConfigDAO(db)

            # 测试添加基金
            result = dao.add_fund("TEST001", "测试基金001")
            assert result is True

            # 测试获取基金
            fund = dao.get_fund("TEST001")
            assert fund is not None
            assert fund.code == "TEST001"
            assert fund.name == "测试基金001"

            # 测试删除基金
            result = dao.remove_fund("TEST001")
            assert result is True

            fund = dao.get_fund("TEST001")
            assert fund is None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_fund_history_operations(self):
        """测试基金历史数据操作"""
        from src.db.database import DatabaseManager, FundHistoryDAO

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            db = DatabaseManager(db_path=temp_path)
            history_dao = FundHistoryDAO(db)

            # 测试添加历史记录
            result = history_dao.add_history(
                fund_code="HIST001",
                fund_name="测试基金",
                date="2024-01-15",
                unit_net_value=1.2345,
                accumulated_net_value=1.5678,
                growth_rate=2.5,
            )
            assert result is True

            # 测试获取历史记录
            history = history_dao.get_history("HIST001", limit=10)
            assert len(history) >= 1
            assert history[0].fund_code == "HIST001"

            # 测试获取最新记录
            latest = history_dao.get_latest_record("HIST001")
            assert latest is not None
            assert latest.date == "2024-01-15"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_default_data_initialization(self):
        """测试默认数据初始化"""
        from src.db.database import DatabaseManager, ConfigDAO

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            db = DatabaseManager(db_path=temp_path)
            dao = ConfigDAO(db)

            # 初始化默认数据
            dao.init_default_funds()
            dao.init_default_commodities()

            # 验证默认基金
            fund = dao.get_fund("161039")
            assert fund is not None
            assert fund.name == "富国中证新能源汽车指数"

            # 验证默认商品
            commodity = dao.get_commodity("gold_cny")
            assert commodity is not None
            assert commodity.name == "Au99.99 (上海黄金)"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestDataSourceManager:
    """数据源管理器测试"""

    def test_data_source_manager_creation(self):
        """测试数据源管理器创建"""
        from src.datasources.manager import create_default_manager

        manager = create_default_manager()
        assert manager is not None
        # DataSourceManager 使用私有属性 _sources
        assert hasattr(manager, "_sources")
        assert hasattr(manager, "fetch")
        assert hasattr(manager, "fetch_batch")


class TestUIComponents:
    """UI 组件测试"""

    def test_main_function_exists(self):
        """测试主入口函数存在"""
        from src.gui.main import main

        assert callable(main)

    def test_add_fund_dialog_class(self):
        """测试添加基金对话框类存在"""
        from src.gui.main import AddFundDialog

        assert AddFundDialog is not None

    def test_holding_dialog_class(self):
        """测试持仓设置对话框类存在"""
        from src.gui.main import HoldingDialog

        assert HoldingDialog is not None

    def test_delete_confirm_dialog_class(self):
        """测试删除确认对话框类存在"""
        from src.gui.main import DeleteConfirmDialog

        assert DeleteConfirmDialog is not None

    def test_fund_display_data_with_holding(self):
        """测试带持仓信息的基金数据"""
        from src.gui.main import FundDisplayData

        fund = FundDisplayData(
            code="TEST001",
            name="测试基金",
            net_value=1.5000,
            est_value=1.5200,
            change_pct=1.33,
            profit=100.0,
            hold_shares=1000.0,
            cost=1.4000,
        )

        assert fund.code == "TEST001"
        assert fund.hold_shares == 1000.0
        assert fund.cost == 1.4000
        # 验证持仓盈亏计算（使用近似值比较）
        expected_profit = (fund.net_value - fund.cost) * fund.hold_shares
        assert abs(fund.profit - expected_profit) < 0.01

    def test_fund_display_data_without_holding(self):
        """测试不带持仓信息的基金数据"""
        from src.gui.main import FundDisplayData

        fund = FundDisplayData(
            code="TEST002",
            name="测试基金2",
            net_value=1.0000,
            est_value=1.0100,
            change_pct=1.0,
            profit=0.0,
            hold_shares=0.0,
            cost=0.0,
        )

        assert fund.code == "TEST002"
        assert fund.hold_shares == 0.0
        assert fund.cost == 0.0
        assert fund.profit == 0.0


class TestFundChart:
    """基金图表测试 - 分时图/K线图"""

    def test_fund_chart_dialog_class_exists(self):
        """测试基金图表对话框类存在"""
        from src.gui.chart import FundChartDialog

        assert FundChartDialog is not None

    def test_fund_history_data_class_exists(self):
        """测试基金历史数据类存在"""
        from src.gui.chart import FundHistoryData

        assert FundHistoryData is not None

    def test_fund_history_data_creation(self):
        """测试基金历史数据创建"""
        from src.gui.chart import FundHistoryData

        history = FundHistoryData(
            fund_code="TEST001",
            fund_name="测试基金",
            dates=["2024-01-01", "2024-01-02", "2024-01-03"],
            open_values=[1.0, 1.01, 1.02],
            close_values=[1.01, 1.02, 1.03],
            high_values=[1.02, 1.03, 1.04],
            low_values=[0.99, 1.00, 1.01],
            volumes=[1000, 1500, 2000],
        )

        assert history.fund_code == "TEST001"
        assert history.fund_name == "测试基金"
        assert len(history.dates) == 3
        assert len(history.close_values) == 3

    def test_fund_chart_generation(self):
        """测试基金图表生成"""
        from src.gui.chart import FundHistoryData
        import matplotlib

        matplotlib.use("Agg")  # 使用非交互式后端
        import matplotlib.pyplot as plt

        history = FundHistoryData(
            fund_code="TEST001",
            fund_name="测试基金",
            dates=[
                "2024-01-01",
                "2024-01-02",
                "2024-01-03",
                "2024-01-04",
                "2024-01-05",
            ],
            open_values=[1.0, 1.01, 1.02, 1.015, 1.03],
            close_values=[1.01, 1.02, 1.015, 1.03, 1.04],
            high_values=[1.02, 1.03, 1.025, 1.035, 1.05],
            low_values=[0.99, 1.00, 1.01, 1.01, 1.02],
            volumes=[1000, 1500, 1200, 1800, 2000],
        )

        # 生成图表
        fig = FundHistoryData.generate_candlestick_chart(history)
        assert fig is not None
        assert isinstance(fig, matplotlib.figure.Figure)

        # 清理
        plt.close(fig)

    def test_fund_chart_with_ma_lines(self):
        """测试带均线的基金图表"""
        from src.gui.chart import FundHistoryData
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # 创建足够长的历史数据用于计算均线
        dates = [f"2024-01-{i + 1:02d}" for i in range(30)]
        close_values = [1.0 + i * 0.01 + (i % 5) * 0.005 for i in range(30)]

        history = FundHistoryData(
            fund_code="TEST002",
            fund_name="测试基金2",
            dates=dates,
            open_values=close_values,
            close_values=close_values,
            high_values=[v * 1.01 for v in close_values],
            low_values=[v * 0.99 for v in close_values],
            volumes=[1000] * 30,
        )

        # 生成带均线的图表
        fig = FundHistoryData.generate_candlestick_chart(
            history, show_ma=True, ma_periods=[5, 10, 20]
        )
        assert fig is not None
        plt.close(fig)


class TestFundDetail:
    """基金详情页测试"""

    def test_fund_detail_dialog_class_exists(self):
        """测试基金详情对话框类存在"""
        from src.gui.detail import FundDetailDialog

        assert FundDetailDialog is not None

    def test_fund_detail_dialog_creation(self):
        """测试基金详情对话框创建"""
        from src.gui.detail import FundDetailDialog
        from src.gui.main import FundDisplayData

        # 创建模拟的app和fund数据
        class MockApp:
            pass

        fund = FundDisplayData(
            code="TEST001",
            name="测试基金",
            net_value=1.5000,
            est_value=1.5200,
            change_pct=1.33,
            profit=100.0,
            hold_shares=1000.0,
            cost=1.4000,
        )

        app = MockApp()
        dialog = FundDetailDialog(app, fund)

        assert dialog.fund_code == "TEST001"
        assert dialog.fund_name == "测试基金"
        assert dialog.fund.net_value == 1.5000
        assert dialog.fund.profit == 100.0

    def test_fund_detail_statistics_calculation(self):
        """测试基金详情统计计算"""
        from src.gui.detail import FundDetailDialog
        from src.gui.main import FundDisplayData

        class MockApp:
            pass

        fund = FundDisplayData(
            code="TEST001",
            name="测试基金",
            net_value=1.5000,
            est_value=1.5200,
            change_pct=1.33,
            profit=100.0,
            hold_shares=1000.0,
            cost=1.4000,
        )

        app = MockApp()
        dialog = FundDetailDialog(app, fund)

        # 验证统计信息计算
        assert dialog._get_profit_rate() == pytest.approx(
            7.14, abs=0.01
        )  # (1.5-1.4)/1.4 * 100

    def test_fund_detail_with_no_holding(self):
        """测试无持仓的基金详情"""
        from src.gui.detail import FundDetailDialog
        from src.gui.main import FundDisplayData

        class MockApp:
            pass

        fund = FundDisplayData(
            code="TEST002",
            name="无持仓测试基金",
            net_value=1.0000,
            est_value=1.0100,
            change_pct=1.0,
            profit=0.0,
            hold_shares=0.0,
            cost=0.0,
        )

        app = MockApp()
        dialog = FundDetailDialog(app, fund)

        assert dialog.fund.hold_shares == 0.0
        assert dialog.fund.cost == 0.0
        assert dialog._get_profit_rate() == 0.0

    def test_fund_chart_with_ma_lines(self):
        """测试带均线的基金图表"""
        from src.gui.chart import FundHistoryData
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # 创建足够长的历史数据用于计算均线
        dates = [f"2024-01-{i + 1:02d}" for i in range(30)]
        close_values = [1.0 + i * 0.01 + (i % 5) * 0.005 for i in range(30)]

        history = FundHistoryData(
            fund_code="TEST002",
            fund_name="测试基金2",
            dates=dates,
            open_values=close_values,
            close_values=close_values,
            high_values=[v * 1.01 for v in close_values],
            low_values=[v * 0.99 for v in close_values],
            volumes=[1000] * 30,
        )

        # 生成带均线的图表
        fig = FundHistoryData.generate_candlestick_chart(
            history, show_ma=True, ma_periods=[5, 10, 20]
        )
        assert fig is not None
        plt.close(fig)

    # SettingsDialog 在 GUI 中暂时未实现
    # def test_settings_dialog_class(self):
    #     """测试设置对话框类存在"""
    #     from src.gui.main import SettingsDialog
    #     assert SettingsDialog is not None


class TestRegressionTests:
    """回归测试"""

    def test_full_workflow_simulation(self):
        """测试完整工作流程模拟"""
        from src.db.database import DatabaseManager, ConfigDAO, FundHistoryDAO

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            # 1. 初始化数据库
            db = DatabaseManager(db_path=temp_path)
            config_dao = ConfigDAO(db)
            history_dao = FundHistoryDAO(db)

            # 2. 添加基金到自选
            config_dao.add_fund("REGRESS001", "回归测试基金1")
            config_dao.add_fund("REGRESS002", "回归测试基金2")
            config_dao.add_fund("REGRESS003", "回归测试基金3")

            # 3. 设置持仓
            config_dao.update_fund("REGRESS001", shares=1000, cost=1.0)
            config_dao.update_fund("REGRESS002", shares=500, cost=1.5)

            # 4. 验证自选列表
            watchlist = config_dao.get_watchlist()
            codes = [f.code for f in watchlist]
            assert "REGRESS001" in codes
            assert "REGRESS002" in codes
            assert "REGRESS003" in codes

            # 5. 验证持仓列表
            holdings = config_dao.get_holdings()
            holding_codes = [h.code for h in holdings]
            assert "REGRESS001" in holding_codes
            assert "REGRESS002" in holding_codes
            assert "REGRESS003" not in holding_codes

            # 6. 添加历史数据
            for date in ["2024-01-01", "2024-01-02", "2024-01-03"]:
                history_dao.add_history(
                    fund_code="REGRESS001",
                    fund_name="回归测试基金1",
                    date=date,
                    unit_net_value=1.0 + (int(date[-2:]) * 0.01),
                )

            # 7. 验证历史数据
            history = history_dao.get_history("REGRESS001", limit=10)
            assert len(history) == 3

            # 8. 获取统计摘要
            summary = history_dao.get_history_summary("REGRESS001")
            assert summary["total_records"] == 3
            assert "min_value" in summary
            assert "max_value" in summary

            # 9. 清理测试数据
            config_dao.remove_fund("REGRESS001")
            config_dao.remove_fund("REGRESS002")
            config_dao.remove_fund("REGRESS003")

            # 10. 验证清理成功
            assert config_dao.get_fund("REGRESS001") is None
            assert config_dao.get_fund("REGRESS002") is None
            assert config_dao.get_fund("REGRESS003") is None

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_database_and_gui_compatibility(self):
        """测试数据库和 GUI 模块兼容性"""
        from src.gui.main import FundDisplayData
        from src.db.database import FundConfig

        # 测试数据类可以互相转换（模拟）
        fund_display = FundDisplayData(
            code="COMPAT001",
            name="兼容性测试基金",
            net_value=1.5,
            est_value=1.52,
            change_pct=1.33,
            profit=100.0,
            hold_shares=100,
            cost=1.4,
        )

        fund_config = FundConfig(
            code="COMPAT001", name="兼容性测试基金", watchlist=1, shares=100, cost=1.4
        )

        # 验证数据可以正确传递
        assert fund_display.code == fund_config.code
        assert fund_display.name == fund_config.name
        assert fund_display.hold_shares == fund_config.shares
        assert fund_display.cost == fund_config.cost

    def test_multiple_operations_atomicity(self):
        """测试多次操作的原子性"""
        from src.db.database import DatabaseManager, ConfigDAO

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            db = DatabaseManager(db_path=temp_path)
            dao = ConfigDAO(db)

            # 批量操作测试
            operations = [
                ("ATOM001", "原子操作基金1"),
                ("ATOM002", "原子操作基金2"),
                ("ATOM003", "原子操作基金3"),
            ]

            for code, name in operations:
                dao.add_fund(code, name)

            # 验证所有操作成功
            for code, name in operations:
                fund = dao.get_fund(code)
                assert fund is not None
                assert fund.name == name

            # 清理
            for code, _ in operations:
                dao.remove_fund(code)

            # 验证清理成功
            for code, _ in operations:
                assert dao.get_fund(code) is None

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestConfigurationPersistence:
    """配置持久化测试"""

    def test_config_persistence_across_sessions(self):
        """测试配置跨会话持久化"""
        from src.db.database import DatabaseManager, ConfigDAO

        # 第一个"会话" - 写入配置
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            session1_path = f.name

        try:
            db1 = DatabaseManager(db_path=session1_path)
            dao1 = ConfigDAO(db1)
            dao1.add_fund("SESSION001", "会话测试基金")
            dao1.add_commodity("GOLD_CNY", "Au99.99")
        finally:
            pass  # 不删除，让下一个会话使用

        # 第二个"会话" - 读取配置
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            pass  # 使用不同的临时文件

        db2 = DatabaseManager(db_path=session1_path)  # 使用同一个路径
        dao2 = ConfigDAO(db2)

        # 验证配置持久化
        fund = dao2.get_fund("SESSION001")
        assert fund is not None
        assert fund.name == "会话测试基金"

        commodity = dao2.get_commodity("GOLD_CNY")
        assert commodity is not None
        assert commodity.name == "Au99.99"

        # 清理
        if os.path.exists(session1_path):
            os.unlink(session1_path)

    def test_history_data_pagination(self):
        """测试历史数据分页"""
        from src.db.database import DatabaseManager, FundHistoryDAO

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            db = DatabaseManager(db_path=temp_path)
            history_dao = FundHistoryDAO(db)

            # 添加20条历史记录
            for i in range(20):
                history_dao.add_history(
                    fund_code="PAGE001",
                    fund_name="分页测试",
                    date=f"2024-01-{i + 1:02d}",
                    unit_net_value=1.0 + i * 0.01,
                )

            # 测试分页获取
            page1 = history_dao.get_history("PAGE001", limit=10)
            assert len(page1) == 10

            page2 = history_dao.get_history(
                "PAGE001", limit=10, start_date="2024-01-11"
            )
            assert len(page2) == 10

            # 测试获取所有
            all_history = history_dao.get_history("PAGE001", limit=100)
            assert len(all_history) == 20

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
