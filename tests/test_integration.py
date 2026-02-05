# -*- coding: UTF-8 -*-
"""集成测试

测试完整的业务工作流程：
1. 基金列表完整工作流程
2. 通知系统工作流程
3. 数据导出完整流程
4. 缓存读写流程
5. 配置保存加载
"""

import csv
import os
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timedelta

from src.config.models import (
    Fund,
    Holding,
    AppConfig,
    FundList,
    Commodity,
    CommodityList,
    NotificationConfig,
    PriceAlert,
    AlertDirection,
    Theme,
    DataSource,
)
from src.gui.notifications import NotificationManager
from src.utils.export import export_funds_to_csv, export_portfolio_report
from src.datasources.cache import DataCache


class TestFundListWorkflow:
    """基金列表完整工作流程测试"""

    def test_fund_list_creation(self, fund_list, sample_funds, sample_holdings):
        """测试 FundList 创建"""
        assert len(fund_list.watchlist) == len(sample_funds)
        assert len(fund_list.holdings) == len(sample_holdings)

    def test_get_all_codes(self, fund_list):
        """测试获取所有基金代码"""
        codes = fund_list.get_all_codes()
        assert len(codes) == 5  # 3 unique from holdings + 2 unique from watchlist
        assert "000001" in codes
        assert "110011" in codes
        assert "161039" in codes

    def test_is_watching(self, fund_list):
        """测试检查是否在自选列表中"""
        assert fund_list.is_watching("000001") is True
        assert fund_list.is_watching("000002") is True
        assert fund_list.is_watching("NONEXISTENT") is False

    def test_get_holding(self, fund_list):
        """测试获取持仓信息"""
        holding = fund_list.get_holding("000001")
        assert holding is not None
        assert holding.shares == 1000.0
        assert holding.cost == 1.5
        assert holding.total_cost == 1500.0

        # 测试不存在的持仓
        assert fund_list.get_holding("NONEXISTENT") is None

    def test_fund_equality(self):
        """测试基金相等性"""
        fund1 = Fund(code="000001", name="华夏成长混合")
        fund2 = Fund(code="000001", name="华夏成长混合")
        fund3 = Fund(code="000002", name="华夏回报混合")

        assert fund1 == fund2
        assert fund1 != fund3
        assert hash(fund1) == hash(fund2)

    def test_holding_total_cost(self, sample_holdings):
        """测试持仓总成本计算"""
        holding = sample_holdings[0]
        assert holding.total_cost == 1500.0  # 1000.0 * 1.5

        holding2 = sample_holdings[2]
        assert holding2.total_cost == 2400.0  # 2000.0 * 1.2


class TestNotificationWorkflow:
    """通知系统完整工作流程测试"""

    def test_notification_manager_workflow(self, notification_config):
        """测试通知管理器完整工作流程"""
        manager = NotificationManager(notification_config)

        # 初始状态
        assert len(manager.get_all_alerts()) == 2
        assert len(manager.get_active_alerts()) == 2

        # 添加新预警
        new_alert = manager.add_alert(
            "161039", "富国中证新能源汽车指数", 1.0, AlertDirection.ABOVE.value
        )
        assert len(manager.get_all_alerts()) == 3
        assert len(manager.get_active_alerts()) == 3

        # 检查价格预警触发
        triggered = manager.check_price_alerts("000001", "华夏成长混合", 1.7)
        assert len(triggered) == 1
        assert len(manager.get_active_alerts()) == 2  # 一个已触发

        # 移除预警
        removed = manager.remove_alert("000002", 1.8)
        assert removed is True
        assert len(manager.get_all_alerts()) == 2

    def test_price_alert_edge_cases(self):
        """测试价格预警边界情况"""
        config = NotificationConfig()
        manager = NotificationManager(config)

        # 添加预警
        manager.add_alert("000001", "基金A", 1.5, AlertDirection.ABOVE.value)

        # 边界测试：等于目标价应该触发
        triggered = manager.check_price_alerts("000001", "基金A", 1.5)
        assert len(triggered) == 1

        # 已触发后不再触发
        triggered = manager.check_price_alerts("000001", "基金A", 1.6)
        assert len(triggered) == 0

        # 验证 alert.triggered 已被设为 True
        alerts = manager.get_all_alerts()
        assert alerts[0].triggered is True

    def test_notification_config_operations(self, notification_config):
        """测试通知配置操作"""
        # 添加预警
        alert = PriceAlert("161725", "招商中证白酒指数", 2.5, AlertDirection.BELOW.value)
        notification_config.add_alert(alert)
        assert len(notification_config.price_alerts) == 3

        # 获取基金的预警
        alerts = notification_config.get_alerts_for_fund("000001")
        assert len(alerts) == 1

        # 清除已触发预警
        notification_config.price_alerts[0].triggered = True
        count = notification_config.clear_triggered()
        assert count == 1
        assert len(notification_config.price_alerts) == 2


class TestExportWorkflow:
    """数据导出完整流程测试"""

    def test_export_workflow(self, tmp_path, sample_funds, sample_holdings):
        """测试完整导出流程"""
        # 导出基金列表
        funds_csv = tmp_path / "funds.csv"
        result1 = export_funds_to_csv(sample_funds, str(funds_csv))
        assert result1 is True
        assert funds_csv.exists()

        # 导出持仓报告
        portfolio_csv = tmp_path / "portfolio.csv"
        result2 = export_portfolio_report(sample_holdings, str(portfolio_csv))
        assert result2 is True
        assert portfolio_csv.exists()

        # 验证基金 CSV 内容
        with open(funds_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == len(sample_funds)
            assert rows[0]["code"] == "000001"

        # 验证持仓 CSV 内容
        with open(portfolio_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == len(sample_holdings)

    def test_export_with_dict_data(self, tmp_path):
        """测试导出字典格式数据"""
        # 测试使用字典格式导出
        funds_dict = [
            {"code": "DICT001", "name": "字典测试基金1"},
            {"code": "DICT002", "name": "字典测试基金2"},
        ]

        filepath = tmp_path / "dict_funds.csv"
        result = export_funds_to_csv(funds_dict, str(filepath))

        assert result is True
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]["code"] == "DICT001"

    def test_export_mixed_data_types(self, tmp_path):
        """测试混合数据类型导出"""
        # 混合 Fund 对象和字典
        mixed_data = [
            Fund(code="FUND001", name="对象基金"),
            {"code": "DICT001", "name": "字典基金"},
        ]

        filepath = tmp_path / "mixed.csv"
        result = export_funds_to_csv(mixed_data, str(filepath))

        assert result is True

    def test_export_creates_parent_dir(self, tmp_path):
        """测试导出时自动创建父目录"""
        nested_path = tmp_path / "nested" / "deep" / "funds.csv"
        assert not nested_path.parent.exists()

        funds = [Fund(code="000001", name="测试基金")]
        result = export_funds_to_csv(funds, str(nested_path))

        assert result is True
        assert nested_path.exists()


class TestCacheWorkflow:
    """缓存读写流程测试"""

    def test_cache_full_workflow(self, tmp_path):
        """测试完整缓存工作流程"""
        cache = DataCache(cache_dir=tmp_path)

        # 1. 设置缓存
        cache.set("key1", "value1", ttl_seconds=300)
        cache.set("key2", {"data": "value2"}, ttl_seconds=300)
        cache.set("key3", [1, 2, 3], ttl_seconds=300)

        # 2. 读取缓存
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == {"data": "value2"}
        assert cache.get("key3") == [1, 2, 3]

        # 3. 更新缓存
        cache.set("key1", "new_value")
        assert cache.get("key1") == "new_value"

        # 4. 清除单个缓存
        cache.clear("key1")
        assert cache.get("key1") is None
        assert cache.get("key2") == {"data": "value2"}

        # 5. 清除所有缓存
        cache.clear()
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cache_expiration_workflow(self, tmp_path):
        """测试缓存过期流程"""
        cache = DataCache(cache_dir=tmp_path)

        # 设置短期缓存
        cache.set("short_lived", "value", ttl_seconds=1)
        assert cache.get("short_lived") == "value"

        # 设置长期缓存
        cache.set("long_lived", "value", ttl_seconds=300)
        assert cache.get("long_lived") == "value"

        # 短期缓存过期后
        import time
        time.sleep(1.5)
        assert cache.get("short_lived") is None
        assert cache.get("long_lived") == "value"

    def test_cache_stats_and_cleanup(self, tmp_path):
        """测试缓存统计和清理"""
        cache = DataCache(cache_dir=tmp_path)

        # 设置一些缓存
        cache.set("valid1", "value1", ttl_seconds=300)
        cache.set("valid2", "value2", ttl_seconds=300)
        cache.set("expired1", "value3", ttl_seconds=1)

        # 等待过期
        import time
        time.sleep(1.5)

        # 清理过期缓存
        cleaned = cache.cleanup_expired()
        assert cleaned >= 1

        # 获取统计信息
        stats = cache.get_stats()
        assert stats["total_files"] >= 0
        assert stats["expired_files"] == 0  # 已清理

    def test_cache_persistence(self, tmp_path):
        """测试缓存持久化"""
        cache_dir = tmp_path / "persistent"

        # 创建缓存
        cache1 = DataCache(cache_dir=cache_dir)
        cache1.set("persistent_key", "persistent_value", ttl_seconds=300)

        # 模拟应用重启 - 创建新的缓存实例
        cache2 = DataCache(cache_dir=cache_dir)
        result = cache2.get("persistent_key")

        assert result == "persistent_value"


class TestConfigSaveLoad:
    """配置保存加载测试"""

    def test_app_config_creation(self, app_config):
        """测试应用配置创建"""
        assert app_config.refresh_interval == 30
        assert app_config.theme == "dark"
        assert app_config.default_fund_source == "sina"
        assert app_config.enable_auto_refresh is True

    def test_app_config_modification(self, app_config):
        """测试应用配置修改"""
        # 修改配置
        app_config.refresh_interval = 60
        app_config.theme = "light"
        app_config.enable_auto_refresh = False

        assert app_config.refresh_interval == 60
        assert app_config.theme == "light"
        assert app_config.enable_auto_refresh is False

    def test_fund_list_integration(self, fund_list):
        """测试基金列表集成"""
        # 获取所有代码
        all_codes = fund_list.get_all_codes()

        # 过滤自选基金
        watchlist_codes = [f.code for f in fund_list.watchlist]

        # 验证数据完整性
        for code in watchlist_codes:
            assert fund_list.is_watching(code) is True

        # 验证持仓计算
        for holding in fund_list.holdings:
            assert holding.total_cost >= 0

    def test_commodity_list_operations(self, sample_commodities):
        """测试商品列表操作"""
        commodity_list = CommodityList(commodities=sample_commodities)

        # 获取单个商品
        gold = commodity_list.get_by_symbol("AU9999")
        assert gold is not None
        assert gold.name == "黄金"

        # 获取数据源过滤
        akshare_commodities = commodity_list.get_by_source("akshare")
        assert len(akshare_commodities) == 2  # AU9999, AG9999

    def test_theme_enum(self):
        """测试主题枚举"""
        assert Theme.LIGHT.value == "light"
        assert Theme.DARK.value == "dark"

    def test_data_source_enum(self):
        """测试数据源枚举"""
        assert DataSource.SINA.value == "sina"
        assert DataSource.EASTMONEY.value == "eastmoney"
        assert DataSource.AKSHARE.value == "akshare"


class TestIntegrationScenarios:
    """集成场景测试"""

    def test_fund_price_alert_export_flow(self, sample_funds, sample_holdings, notification_config, tmp_path):
        """测试基金-预警-导出完整流程"""
        # 1. 创建基金和持仓
        fund_list = FundList(watchlist=sample_funds, holdings=sample_holdings)

        # 2. 设置价格预警
        manager = NotificationManager(notification_config)

        # 3. 模拟价格检查
        for holding in sample_holdings:
            # 假设当前价格是成本价的 1.1 倍
            current_price = holding.cost * 1.1
            manager.check_price_alerts(holding.code, holding.name, current_price)

        # 4. 导出持仓报告
        portfolio_csv = tmp_path / "portfolio_with_alerts.csv"
        result = export_portfolio_report(sample_holdings, str(portfolio_csv))

        assert result is True
        assert portfolio_csv.exists()

        # 5. 验证导出内容包含所有基金
        with open(portfolio_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == len(sample_holdings)

    def test_cache_with_fund_data(self, tmp_path, sample_funds):
        """测试使用基金数据的缓存流程"""
        cache = DataCache(cache_dir=tmp_path)

        # 缓存基金数据
        fund_data = {
            "funds": [
                {"code": f.code, "name": f.name}
                for f in sample_funds
            ],
            "timestamp": datetime.now().isoformat(),
        }

        cache.set("fund_data", fund_data, ttl_seconds=300)

        # 模拟从缓存读取
        cached = cache.get("fund_data")
        assert cached is not None
        assert len(cached["funds"]) == len(sample_funds)

        # 验证基金代码存在
        cached_codes = [f["code"] for f in cached["funds"]]
        for fund in sample_funds:
            assert fund.code in cached_codes

    def test_notification_with_cache(self, notification_config, tmp_path):
        """测试带缓存的通知流程"""
        cache = DataCache(cache_dir=tmp_path)
        manager = NotificationManager(notification_config)

        # 缓存预警配置
        alerts_data = {
            "alerts": [
                {
                    "fund_code": alert.fund_code,
                    "fund_name": alert.fund_name,
                    "target_price": alert.target_price,
                    "direction": alert.direction,
                }
                for alert in manager.get_all_alerts()
            ],
            "enabled": manager.config.enabled,
        }

        cache.set("notification_config", alerts_data, ttl_seconds=300)

        # 验证缓存
        cached = cache.get("notification_config")
        assert cached is not None
        assert len(cached["alerts"]) == len(manager.get_all_alerts())
        assert cached["enabled"] is True
