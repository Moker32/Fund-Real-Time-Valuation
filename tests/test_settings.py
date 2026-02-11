# -*- coding: UTF-8 -*-
"""设置功能测试"""


from src.config.models import AppConfig, Theme


class TestAppConfig:
    """应用配置测试"""

    def test_config_defaults(self):
        """测试默认配置"""
        config = AppConfig()
        assert config.refresh_interval == 30
        assert config.theme == Theme.DARK.value
        assert config.enable_auto_refresh is True
        assert config.show_profit_loss is True
        assert config.max_history_points == 100

    def test_config_custom(self):
        """测试自定义配置"""
        config = AppConfig(
            refresh_interval=60,
            theme=Theme.LIGHT.value,
            enable_auto_refresh=False,
            show_profit_loss=False,
            max_history_points=200,
        )
        assert config.refresh_interval == 60
        assert config.theme == Theme.LIGHT.value
        assert config.enable_auto_refresh is False
        assert config.show_profit_loss is False
        assert config.max_history_points == 200


class TestConfigValidation:
    """配置验证测试"""

    def test_refresh_interval_bounds(self):
        """测试刷新间隔边界"""
        # 最小值
        config = AppConfig(refresh_interval=10)
        assert config.refresh_interval == 10

        # 最大值
        config = AppConfig(refresh_interval=300)
        assert config.refresh_interval == 300

    def test_history_points_bounds(self):
        """测试历史数据点数边界"""
        # 最小值
        config = AppConfig(max_history_points=50)
        assert config.max_history_points == 50

        # 最大值
        config = AppConfig(max_history_points=500)
        assert config.max_history_points == 500

    def test_theme_values(self):
        """测试主题值"""
        assert Theme.DARK.value == "dark"
        assert Theme.LIGHT.value == "light"
