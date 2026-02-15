"""
配置模块测试
"""

from src.config.models import (
    AlertDirection,
    AppConfig,
    Commodity,
    CommodityList,
    Fund,
    FundList,
    Holding,
    NotificationConfig,
    PriceAlert,
)


class TestAppConfig:
    """应用配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = AppConfig()
        assert config.refresh_interval == 30
        assert config.theme == "dark"
        assert config.default_fund_source == "sina"
        assert config.max_history_points == 100
        assert config.enable_auto_refresh is True

    def test_custom_config(self):
        """测试自定义配置"""
        config = AppConfig(
            refresh_interval=60,
            theme="light",
            max_history_points=200,
        )
        assert config.refresh_interval == 60
        assert config.theme == "light"
        assert config.max_history_points == 200


class TestFundList:
    """基金列表测试"""

    def test_fund_list_with_funds(self):
        """测试基金列表"""
        funds = [
            Fund(code="000001", name="华夏成长"),
            Fund(code="000002", name="华夏回报"),
        ]
        holdings = [
            Holding(code="000001", name="华夏成长", shares=1000, cost=1.5),
        ]
        fund_list = FundList(watchlist=funds, holdings=holdings)
        
        assert len(fund_list.watchlist) == 2
        assert len(fund_list.holdings) == 1
        assert fund_list.is_watching("000001")
        assert not fund_list.is_watching("999999")
        assert fund_list.is_holding("000001")
        assert not fund_list.is_holding("000002")

    def test_get_all_codes(self):
        """测试获取所有基金代码"""
        funds = [Fund(code="000001", name="基金1")]
        holdings = [Holding(code="000002", name="基金2", shares=100, cost=1.0)]
        fund_list = FundList(watchlist=funds, holdings=holdings)
        
        codes = fund_list.get_all_codes()
        assert "000001" in codes
        assert "000002" in codes

    def test_get_holding(self):
        """测试获取持仓"""
        holdings = [Holding(code="000001", name="基金1", shares=100, cost=1.5)]
        fund_list = FundList(holdings=holdings)
        
        holding = fund_list.get_holding("000001")
        assert holding is not None
        assert holding.shares == 100
        
        non_existent = fund_list.get_holding("999999")
        assert non_existent is None


class TestCommodityList:
    """商品列表测试"""

    def test_commodity_list(self):
        """测试商品列表"""
        commodities = [
            Commodity(symbol="AU9999", name="黄金", source="akshare"),
            Commodity(symbol="AG9999", name="白银", source="akshare"),
        ]
        commodity_list = CommodityList(commodities=commodities)
        
        assert len(commodity_list.commodities) == 2
        assert commodity_list.get_by_symbol("AU9999") is not None
        assert commodity_list.get_by_symbol("AU9999").name == "黄金"
        assert commodity_list.get_by_source("akshare") == commodities


class TestPriceAlert:
    """价格预警测试"""

    def test_price_alert_above(self):
        """测试高于目标价预警"""
        alert = PriceAlert(
            fund_code="000001",
            fund_name="测试基金",
            target_price=1.5,
            direction=AlertDirection.ABOVE.value,
        )
        
        # 低于目标价，不触发
        assert not alert.check(1.4)
        # 高于目标价，触发
        assert alert.check(1.6)
        # 已触发后不再触发（需要手动设置 triggered）
        alert.triggered = True
        assert not alert.check(1.7)

    def test_price_alert_below(self):
        """测试低于目标价预警"""
        alert = PriceAlert(
            fund_code="000001",
            fund_name="测试基金",
            target_price=1.5,
            direction=AlertDirection.BELOW.value,
        )
        
        # 高于目标价，不触发
        assert not alert.check(1.6)
        # 低于目标价，触发
        assert alert.check(1.4)


class TestNotificationConfig:
    """通知配置测试"""

    def test_add_remove_alert(self):
        """测试添加和移除预警"""
        config = NotificationConfig()
        
        alert1 = PriceAlert(
            fund_code="000001",
            fund_name="基金1",
            target_price=1.5,
        )
        alert2 = PriceAlert(
            fund_code="000002",
            fund_name="基金2",
            target_price=2.0,
        )
        
        config.add_alert(alert1)
        config.add_alert(alert2)
        
        assert len(config.price_alerts) == 2
        
        # 移除
        result = config.remove_alert("000001", 1.5)
        assert result is True
        assert len(config.price_alerts) == 1

    def test_get_alerts_for_fund(self):
        """测试获取基金的预警"""
        config = NotificationConfig()
        
        alert1 = PriceAlert(fund_code="000001", fund_name="基金1", target_price=1.5)
        alert2 = PriceAlert(fund_code="000001", fund_name="基金1", target_price=1.8)
        alert3 = PriceAlert(fund_code="000002", fund_name="基金2", target_price=2.0)
        
        config.add_alert(alert1)
        config.add_alert(alert2)
        config.add_alert(alert3)
        
        alerts_000001 = config.get_alerts_for_fund("000001")
        assert len(alerts_000001) == 2
        
        alerts_000002 = config.get_alerts_for_fund("000002")
        assert len(alerts_000002) == 1
