# -*- coding: UTF-8 -*-
"""通知系统测试"""


from src.gui.notifications import NotificationManager

from src.config.models import (
    AlertDirection,
    NotificationConfig,
    PriceAlert,
)


class TestPriceAlert:
    """价格预警模型测试"""

    def test_alert_creation(self):
        """测试预警创建"""
        alert = PriceAlert(
            fund_code="000001",
            fund_name="测试基金",
            target_price=1.5,
            direction=AlertDirection.ABOVE.value,
        )
        assert alert.fund_code == "000001"
        assert alert.fund_name == "测试基金"
        assert alert.target_price == 1.5
        assert alert.direction == AlertDirection.ABOVE.value
        assert alert.triggered is False

    def test_alert_check_above(self):
        """测试高于目标价预警检查"""
        alert = PriceAlert(
            fund_code="000001",
            fund_name="测试基金",
            target_price=1.5,
            direction=AlertDirection.ABOVE.value,
        )
        # 低于目标价，不触发
        assert alert.check(1.4) is False
        # 等于目标价，触发
        assert alert.check(1.5) is True
        # 高于目标价，但已触发，不再触发
        alert.triggered = False  # 重置
        assert alert.check(1.6) is True

    def test_alert_check_below(self):
        """测试低于目标价预警检查"""
        alert = PriceAlert(
            fund_code="000001",
            fund_name="测试基金",
            target_price=1.5,
            direction=AlertDirection.BELOW.value,
        )
        # 高于目标价，不触发
        assert alert.check(1.6) is False
        # 等于目标价，触发
        assert alert.check(1.5) is True


class TestNotificationConfig:
    """通知配置测试"""

    def test_config_defaults(self):
        """测试默认配置"""
        config = NotificationConfig()
        assert config.enabled is True
        assert config.daily_summary is False
        assert config.alert_sound is False
        assert len(config.price_alerts) == 0

    def test_add_alert(self):
        """测试添加预警"""
        config = NotificationConfig()
        alert = PriceAlert(
            fund_code="000001",
            fund_name="测试基金",
            target_price=1.5,
        )
        config.add_alert(alert)
        assert len(config.price_alerts) == 1

    def test_remove_alert(self):
        """测试移除预警"""
        config = NotificationConfig()
        alert = PriceAlert(
            fund_code="000001",
            fund_name="测试基金",
            target_price=1.5,
        )
        config.add_alert(alert)
        assert config.remove_alert("000001", 1.5) is True
        assert len(config.price_alerts) == 0

    def test_get_alerts_for_fund(self):
        """测试获取基金预警"""
        config = NotificationConfig()
        config.add_alert(PriceAlert("000001", "基金A", 1.5))
        config.add_alert(PriceAlert("000002", "基金B", 2.0))
        config.add_alert(PriceAlert("000001", "基金A", 1.6))

        alerts = config.get_alerts_for_fund("000001")
        assert len(alerts) == 2

    def test_clear_triggered(self):
        """测试清除已触发预警"""
        config = NotificationConfig()
        alert1 = PriceAlert("000001", "基金A", 1.5, triggered=False)
        alert2 = PriceAlert("000002", "基金B", 2.0, triggered=True)
        config.add_alert(alert1)
        config.add_alert(alert2)

        count = config.clear_triggered()
        assert count == 1
        assert len(config.price_alerts) == 1


class TestNotificationManager:
    """通知管理器测试"""

    def test_manager_creation(self):
        """测试管理器创建"""
        config = NotificationConfig()
        manager = NotificationManager(config)
        assert manager.config is config

    def test_add_alert(self):
        """测试通过管理器添加预警"""
        config = NotificationConfig()
        manager = NotificationManager(config)

        alert = manager.add_alert("000001", "测试基金", 1.5, AlertDirection.ABOVE.value)
        assert alert.fund_code == "000001"
        assert len(manager.get_all_alerts()) == 1

    def test_check_price_alerts(self):
        """测试价格预警检查"""
        config = NotificationConfig()
        manager = NotificationManager(config)
        manager.add_alert("000001", "测试基金", 1.5, AlertDirection.ABOVE.value)

        # 低于目标价，不触发
        triggered = manager.check_price_alerts("000001", "测试基金", 1.4)
        assert len(triggered) == 0

        # 高于目标价，触发
        triggered = manager.check_price_alerts("000001", "测试基金", 1.6)
        assert len(triggered) == 1
        assert triggered[0].fund_code == "000001"

        # 已触发，不再触发
        triggered = manager.check_price_alerts("000001", "测试基金", 1.7)
        assert len(triggered) == 0

    def test_get_active_alerts(self):
        """测试获取未触发预警"""
        config = NotificationConfig()
        manager = NotificationManager(config)
        manager.add_alert("000001", "基金A", 1.5, AlertDirection.ABOVE.value)
        manager.add_alert("000002", "基金B", 2.0, AlertDirection.BELOW.value)

        # 触发一个预警
        manager.check_price_alerts("000001", "基金A", 1.6)

        active = manager.get_active_alerts()
        assert len(active) == 1
        assert active[0].fund_code == "000002"

    def test_batch_alert_check(self):
        """测试批量检查预警"""
        config = NotificationConfig()
        manager = NotificationManager(config)

        # 添加多个预警
        manager.add_alert("000001", "基金A", 1.5, AlertDirection.ABOVE.value)
        manager.add_alert("000002", "基金B", 2.0, AlertDirection.BELOW.value)
        manager.add_alert("000003", "基金C", 3.0, AlertDirection.ABOVE.value)

        # 模拟价格数据
        prices = {
            "000001": 1.6,  # 触发
            "000002": 2.1,  # 不触发 (需要低于2.0)
            "000003": 3.5,  # 触发
        }

        triggered_all = []
        for fund_code, fund_name, price in [
            ("000001", "基金A", prices["000001"]),
            ("000002", "基金B", prices["000002"]),
            ("000003", "基金C", prices["000003"]),
        ]:
            triggered = manager.check_price_alerts(fund_code, fund_name, price)
            triggered_all.extend(triggered)

        # 应该触发2个预警
        assert len(triggered_all) == 2
        assert len(manager.get_active_alerts()) == 1

    def test_alert_not_trigger_repeatedly(self):
        """测试已触发不重复触发"""
        config = NotificationConfig()
        manager = NotificationManager(config)

        alert = manager.add_alert("000001", "基金A", 1.5, AlertDirection.ABOVE.value)

        # 第一次触发
        triggered1 = manager.check_price_alerts("000001", "基金A", 1.6)
        assert len(triggered1) == 1
        assert alert.triggered is True

        # 再次检查，不应该再次触发
        triggered2 = manager.check_price_alerts("000001", "基金A", 1.7)
        assert len(triggered2) == 0

        # 再次触发，仍然不触发
        triggered3 = manager.check_price_alerts("000001", "基金A", 1.8)
        assert len(triggered3) == 0

        # 确认只有1个预警被标记为已触发
        all_alerts = manager.get_all_alerts()
        assert len([a for a in all_alerts if a.triggered]) == 1
