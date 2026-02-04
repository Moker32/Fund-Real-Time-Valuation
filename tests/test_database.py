# -*- coding: UTF-8 -*-
"""数据库模块测试用例

使用 TDD 流程开发：
1. 先编写测试（预期失败）
2. 运行测试（验证失败）
3. 实现功能
4. 运行测试（验证通过）
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.database import (
    DatabaseManager,
    ConfigDAO,
    FundHistoryDAO,
    FundConfig,
    CommodityConfig,
)


@pytest.fixture
def temp_db_path():
    """创建临时数据库路径"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # 清理
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def db_manager(temp_db_path):
    """创建数据库管理器实例"""
    return DatabaseManager(db_path=temp_db_path)


@pytest.fixture
def config_dao(db_manager):
    """创建配置 DAO 实例"""
    return ConfigDAO(db_manager)


@pytest.fixture
def history_dao(db_manager):
    """创建历史数据 DAO 实例"""
    return FundHistoryDAO(db_manager)


class TestDatabaseManager:
    """DatabaseManager 测试类"""

    def test_database_initialization(self, db_manager):
        """测试数据库初始化"""
        assert os.path.exists(db_manager.db_path)

    def test_get_connection(self, db_manager):
        """测试获取数据库连接"""
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_vacuum(self, db_manager):
        """测试数据库清理"""
        # 添加一些数据
        dao = ConfigDAO(db_manager)
        dao.add_fund("TEST001", "测试基金")
        dao.add_fund("TEST002", "测试基金2")

        # 执行 vacuum
        db_manager.vacuum()
        # 不应抛出异常
        assert True

    def test_get_size(self, db_manager):
        """测试获取数据库大小"""
        size = db_manager.get_size()
        assert isinstance(size, int)
        assert size >= 0


class TestConfigDAO:
    """ConfigDAO 测试类"""

    def test_add_fund(self, config_dao):
        """测试添加基金"""
        result = config_dao.add_fund("TDD001", "测试基金001")
        assert result is True

    def test_add_duplicate_fund(self, config_dao):
        """测试添加重复基金（INSERT OR REPLACE 行为）"""
        config_dao.add_fund("TDD002", "测试基金002")
        # INSERT OR REPLACE 会更新现有记录，总是返回 True
        result = config_dao.add_fund("TDD002", "测试基金002-重名")
        assert result is True
        # 验证数据已被更新
        fund = config_dao.get_fund("TDD002")
        assert fund.name == "测试基金002-重名"

    def test_get_fund(self, config_dao):
        """测试获取单个基金"""
        config_dao.add_fund("TDD003", "测试基金003")
        fund = config_dao.get_fund("TDD003")

        assert fund is not None
        assert fund.code == "TDD003"
        assert fund.name == "测试基金003"
        assert fund.watchlist == True  # SQLite 返回整数 1
        assert fund.shares == 0.0

    def test_get_nonexistent_fund(self, config_dao):
        """测试获取不存在的基金"""
        fund = config_dao.get_fund("NOTEXIST")
        assert fund is None

    def test_get_watchlist(self, config_dao):
        """测试获取自选列表"""
        # 添加测试数据
        config_dao.add_fund("WATCH001", "自选基金1", watchlist=True)
        config_dao.add_fund("WATCH002", "自选基金2", watchlist=True)
        config_dao.add_fund("HOLD001", "持仓基金", watchlist=False, shares=100)

        watchlist = config_dao.get_watchlist()
        codes = [f.code for f in watchlist]

        assert "WATCH001" in codes
        assert "WATCH002" in codes
        assert "HOLD001" not in codes

    def test_get_holdings(self, config_dao):
        """测试获取持仓列表"""
        config_dao.add_fund("FUND001", "基金1", shares=0)
        config_dao.add_fund("FUND002", "基金2", shares=100)
        config_dao.add_fund("FUND003", "基金3", shares=200)

        holdings = config_dao.get_holdings()
        codes = [h.code for h in holdings]

        assert "FUND001" not in codes
        assert "FUND002" in codes
        assert "FUND003" in codes

    def test_update_fund(self, config_dao):
        """测试更新基金"""
        config_dao.add_fund("UPDATE001", "原名称")
        result = config_dao.update_fund("UPDATE001", name="新名称", shares=500)

        assert result is True
        fund = config_dao.get_fund("UPDATE001")
        assert fund.name == "新名称"
        assert fund.shares == 500

    def test_remove_fund(self, config_dao):
        """测试删除基金"""
        config_dao.add_fund("DELETE001", "待删除基金")
        result = config_dao.remove_fund("DELETE001")

        assert result is True
        assert config_dao.get_fund("DELETE001") is None

    def test_add_to_watchlist(self, config_dao):
        """测试添加到自选"""
        config_dao.add_fund("WATCHTEST", "测试", watchlist=False)
        result = config_dao.add_to_watchlist("WATCHTEST")

        assert result is True
        fund = config_dao.get_fund("WATCHTEST")
        assert fund.watchlist == True  # SQLite 返回整数 1

    def test_remove_from_watchlist(self, config_dao):
        """测试从自选移除"""
        config_dao.add_fund("WATCHTEST2", "测试", watchlist=True)
        result = config_dao.remove_from_watchlist("WATCHTEST2")

        assert result is True
        fund = config_dao.get_fund("WATCHTEST2")
        assert fund.watchlist == False  # SQLite 返回整数 0

    def test_add_commodity(self, config_dao):
        """测试添加商品"""
        result = config_dao.add_commodity("GOLD", "黄金", source="yfinance")
        assert result is True

    def test_get_commodities(self, config_dao):
        """测试获取商品列表"""
        config_dao.add_commodity("GOLD_CNY", "Au99.99", source="akshare")
        config_dao.add_commodity("SILVER", "白银", source="yfinance")

        commodities = config_dao.get_commodities()
        assert len(commodities) >= 2

    def test_update_commodity(self, config_dao):
        """测试更新商品"""
        config_dao.add_commodity("TEST_CMD", "测试商品")
        result = config_dao.update_commodity("TEST_CMD", name="新名称", enabled=False)

        assert result is True
        commodity = config_dao.get_commodity("TEST_CMD")
        assert commodity.name == "新名称"
        assert commodity.enabled == False  # SQLite 返回整数 0

    def test_init_default_funds(self, config_dao):
        """测试初始化默认基金"""
        config_dao.init_default_funds()

        # 检查默认基金是否存在
        fund = config_dao.get_fund("161039")
        assert fund is not None
        assert fund.name == "富国中证新能源汽车指数"

    def test_init_default_commodities(self, config_dao):
        """测试初始化默认商品"""
        config_dao.init_default_commodities()

        # 检查默认商品是否存在
        commodity = config_dao.get_commodity("gold_cny")
        assert commodity is not None
        assert commodity.name == "Au99.99 (上海黄金)"


class TestFundHistoryDAO:
    """FundHistoryDAO 测试类"""

    def test_add_history(self, history_dao):
        """测试添加历史记录"""
        result = history_dao.add_history(
            fund_code="HIST001",
            fund_name="测试基金",
            date="2024-01-15",
            unit_net_value=1.2345,
            accumulated_net_value=1.5678,
            estimated_value=1.2400,
            growth_rate=1.5,
        )
        assert result is True

    def test_add_history_batch(self, history_dao):
        """测试批量添加历史记录"""
        from src.db.database import FundHistoryRecord

        records = [
            FundHistoryRecord(
                fund_code="BATCH001",
                fund_name="批量测试",
                date="2024-01-10",
                unit_net_value=1.0,
                accumulated_net_value=1.0,
                fetched_at="2024-01-10T10:00:00",
            ),
            FundHistoryRecord(
                fund_code="BATCH001",
                fund_name="批量测试",
                date="2024-01-11",
                unit_net_value=1.01,
                accumulated_net_value=1.01,
                fetched_at="2024-01-11T10:00:00",
            ),
        ]

        count = history_dao.add_history_batch(records)
        assert count == 2

    def test_get_history(self, history_dao):
        """测试获取历史记录"""
        # 先添加数据
        history_dao.add_history(
            fund_code="GETHIST001",
            fund_name="获取测试",
            date="2024-02-01",
            unit_net_value=1.5,
        )

        history = history_dao.get_history("GETHIST001", limit=10)

        assert len(history) >= 1
        record = history[0]
        assert record.fund_code == "GETHIST001"
        assert record.date == "2024-02-01"

    def test_get_history_with_limit(self, history_dao):
        """测试获取历史记录（限制数量）"""
        # 添加多条记录
        for i in range(5):
            history_dao.add_history(
                fund_code="LIMIT001",
                fund_name="限制测试",
                date=f"2024-01-{10 + i:02d}",
                unit_net_value=1.0 + i * 0.01,
            )

        history = history_dao.get_history("LIMIT001", limit=3)
        assert len(history) == 3

    def test_get_history_date_filter(self, history_dao):
        """测试获取历史记录（日期过滤）"""
        # 添加数据
        history_dao.add_history(
            fund_code="DATE001",
            fund_name="日期过滤测试",
            date="2024-06-15",
            unit_net_value=1.5,
        )

        history = history_dao.get_history(
            "DATE001", start_date="2024-06-01", end_date="2024-06-30"
        )

        assert len(history) == 1
        assert history[0].date == "2024-06-15"

    def test_get_latest_record(self, history_dao):
        """测试获取最新记录"""
        # 添加多条记录
        dates = ["2024-03-01", "2024-03-05", "2024-03-10"]
        for date in dates:
            history_dao.add_history(
                fund_code="LATEST001",
                fund_name="最新测试",
                date=date,
                unit_net_value=1.0,
            )

        latest = history_dao.get_latest_record("LATEST001")
        assert latest is not None
        assert latest.date == "2024-03-10"

    def test_get_history_summary(self, history_dao):
        """测试获取历史统计摘要"""
        # 添加测试数据
        for i in range(5):
            history_dao.add_history(
                fund_code="SUMMARY001",
                fund_name="统计测试",
                date=f"2024-01-{10 + i:02d}",
                unit_net_value=1.0 + i * 0.1,
            )

        summary = history_dao.get_history_summary("SUMMARY001")

        assert summary["total_records"] == 5
        assert summary["min_value"] == 1.0
        assert summary["max_value"] == 1.4


class TestFundConfig:
    """FundConfig 数据类测试"""

    def test_fund_config_creation(self):
        """测试基金配置创建"""
        fund = FundConfig(
            code="FUND001", name="测试基金", watchlist=True, shares=1000, cost=1.5
        )

        assert fund.code == "FUND001"
        assert fund.name == "测试基金"
        assert fund.watchlist is True
        assert fund.shares == 1000
        assert fund.cost == 1.5


class TestCommodityConfig:
    """CommodityConfig 数据类测试"""

    def test_commodity_config_creation(self):
        """测试商品配置创建"""
        commodity = CommodityConfig(
            symbol="GOLD", name="黄金", source="yfinance", enabled=True
        )

        assert commodity.symbol == "GOLD"
        assert commodity.name == "黄金"
        assert commodity.source == "yfinance"
        assert commodity.enabled is True
