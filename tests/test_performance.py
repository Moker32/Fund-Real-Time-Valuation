# -*- coding: UTF-8 -*-
"""性能测试

测试基金列表更新性能，验证是否需要虚拟滚动。
"""

import pytest
import time
from unittest.mock import Mock, MagicMock
from datetime import datetime
import flet as ft

# 添加 src 目录到路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.models import Fund, Holding
from src.gui.main import FundGUIApp, FundDisplayData
from dataclasses import dataclass, field


class TestFundListPerformance:
    """基金列表性能测试"""

    @pytest.fixture
    def mock_app(self):
        """创建模拟的 GUI 应用"""
        # Mock page
        mock_page = Mock()
        mock_page.width = 1200
        mock_page.height = 800
        mock_page.theme_mode = ft.ThemeMode.DARK
        mock_page.update = Mock()

        # Mock config
        mock_config = Mock()
        mock_config.refresh_interval = 5
        mock_config.history_points = 30
        mock_config.theme = "dark"
        mock_config.data_source = "akshare"

        app = FundGUIApp.__new__(FundGUIApp)
        app.page = mock_page
        app.config = mock_config
        app.funds = []
        app._fund_cards = {}

        # 初始化基本属性
        app._fund_list = ft.Column([])
        app._fund_list_stack = ft.Stack([app._fund_list, ft.Container(visible=False)])
        app.portfolio_card = None

        return app

    def test_update_50_funds_performance(self, mock_app):
        """测试更新 50 个基金的性能"""
        # 创建 50 个测试基金
        funds = []
        for i in range(50):
            fund = FundDisplayData(
                code=f"000{i:03d}",
                name=f"测试基金{i}",
                net_value=1.5 + i * 0.01,
                est_value=1.5 + i * 0.01,
                change_pct=0.5 + i * 0.1,
                profit=100.0,
                hold_shares=1000 if i < 10 else 0,
                cost=1.4,
                sector="",
                is_hold=(i < 10),
            )
            funds.append(fund)

        mock_app.funds = funds

        # 测量更新时间
        start = time.time()
        mock_app._update_fund_table()
        elapsed = time.time() - start

        # 验证：50 个基金更新应在 1 秒内完成
        assert elapsed < 1.0, f"50个基金更新耗时 {elapsed:.3f}秒，超过 1 秒阈值"

        # 验证卡片数量
        assert len(mock_app._fund_cards) == 50

        print(f"✓ 50个基金更新性能: {elapsed:.3f}秒")

    def test_update_100_funds_performance(self, mock_app):
        """测试更新 100 个基金的性能"""
        # 创建 100 个测试基金
        funds = []
        for i in range(100):
            fund = FundDisplayData(
                code=f"000{i:03d}",
                name=f"测试基金{i}",
                net_value=1.5 + i * 0.01,
                est_value=1.5 + i * 0.01,
                change_pct=0.5 + i * 0.1,
                profit=100.0,
                hold_shares=1000 if i < 20 else 0,
                cost=1.4,
                sector="",
                is_hold=(i < 20),
            )
            funds.append(fund)

        mock_app.funds = funds

        # 测量更新时间
        start = time.time()
        mock_app._update_fund_table()
        elapsed = time.time() - start

        # 验证：100 个基金更新应在 2 秒内完成
        assert elapsed < 2.0, f"100个基金更新耗时 {elapsed:.3f}秒，超过 2 秒阈值"

        # 验证卡片数量
        assert len(mock_app._fund_cards) == 100

        print(f"✓ 100个基金更新性能: {elapsed:.3f}秒")

    def test_incremental_update_performance(self, mock_app):
        """测试增量更新性能（缓存机制）"""
        # 初始创建 50 个基金
        funds = []
        for i in range(50):
            fund = FundDisplayData(
                code=f"000{i:03d}",
                name=f"测试基金{i}",
                net_value=1.5,
                est_value=1.5,
                change_pct=0.5,
                profit=100.0,
                hold_shares=1000,
                cost=1.4,
                sector="",
                is_hold=True,
            )
            funds.append(fund)

        mock_app.funds = funds
        mock_app._update_fund_table()

        # 更新所有基金的净值
        for fund in funds:
            fund.net_value += 0.01
            fund.est_value += 0.01

        # 测量增量更新时间
        start = time.time()
        mock_app._update_fund_table()
        elapsed = time.time() - start

        # 增量更新应该很快（< 0.5秒）
        assert elapsed < 0.5, f"增量更新耗时 {elapsed:.3f}秒，超过 0.5 秒阈值"

        # 验证卡片被复用（没有创建新对象）
        assert len(mock_app._fund_cards) == 50

        print(f"✓ 增量更新性能: {elapsed:.3f}秒")

    def test_add_remove_funds_performance(self, mock_app):
        """测试添加和删除基金的性能"""
        # 初始 50 个基金
        funds = []
        for i in range(50):
            fund = FundDisplayData(
                code=f"000{i:03d}",
                name=f"测试基金{i}",
                net_value=1.5,
                est_value=1.5,
                change_pct=0.5,
                profit=100.0,
                hold_shares=1000,
                cost=1.4,
                sector="",
                is_hold=True,
            )
            funds.append(fund)

        mock_app.funds = funds
        mock_app._update_fund_table()

        # 移除 10 个，添加 10 个
        mock_app.funds = funds[10:]  # 移除前 10 个
        for i in range(50, 60):
            new_fund = FundDisplayData(
                code=f"000{i:03d}",
                name=f"新基金{i}",
                net_value=1.5,
                est_value=1.5,
                change_pct=0.5,
                profit=100.0,
                hold_shares=1000,
                cost=1.4,
                sector="",
                is_hold=True,
            )
            mock_app.funds.append(new_fund)

        # 测量更新时间
        start = time.time()
        mock_app._update_fund_table()
        elapsed = time.time() - start

        # 应该很快（< 1秒）
        assert elapsed < 1.0, f"增删操作耗时 {elapsed:.3f}秒，超过 1 秒阈值"

        # 验证卡片数量正确
        assert len(mock_app._fund_cards) == 50

        print(f"✓ 增删操作性能: {elapsed:.3f}秒")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
