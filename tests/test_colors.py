"""
颜色和格式化工具测试
"""

from src.utils.colors import (
    ChangeColors,
    format_change_text,
    format_currency,
    format_number,
    format_profit_text,
    get_change_color,
)


class TestChangeColors:
    """涨跌颜色配置测试"""

    def test_colors_defined(self):
        """测试颜色已定义"""
        assert ChangeColors.POSITIVE == "#FF3B30"
        assert ChangeColors.NEGATIVE == "#34C759"
        assert ChangeColors.NEUTRAL == "#8E8E93"


class TestGetChangeColor:
    """涨跌颜色测试"""

    def test_positive_color(self):
        """测试上涨颜色"""
        assert get_change_color(1.5) == ChangeColors.POSITIVE
        assert get_change_color(0.01) == ChangeColors.POSITIVE

    def test_negative_color(self):
        """测试下跌颜色"""
        assert get_change_color(-1.5) == ChangeColors.NEGATIVE
        assert get_change_color(-0.01) == ChangeColors.NEGATIVE

    def test_neutral_color(self):
        """测试持平颜色"""
        assert get_change_color(0) == ChangeColors.NEUTRAL


class TestFormatChangeText:
    """涨跌幅格式化测试"""

    def test_positive_change(self):
        """测试正数格式化"""
        assert format_change_text(1.5) == "+1.50%"
        assert format_change_text(0.5) == "+0.50%"

    def test_negative_change(self):
        """测试负数格式化"""
        assert format_change_text(-1.5) == "-1.50%"

    def test_zero_change(self):
        """测试零格式化"""
        assert format_change_text(0) == "+0.00%"

    def test_custom_suffix(self):
        """测试自定义后缀"""
        assert format_change_text(1.5, "") == "+1.50"
        assert format_change_text(1.5, " %") == "+1.50 %"


class TestFormatProfitText:
    """盈亏格式化测试"""

    def test_positive_profit(self):
        """测试盈利格式化"""
        assert format_profit_text(100.5) == "+¥100.50"
        assert format_profit_text(0.5) == "+¥0.50"

    def test_negative_profit(self):
        """测试亏损格式化"""
        assert format_profit_text(-100.5) == "¥-100.50"

    def test_zero_profit(self):
        """测试零格式化"""
        assert format_profit_text(0) == "+¥0.00"

    def test_custom_prefix(self):
        """测试自定义前缀"""
        assert format_profit_text(100.5, "$") == "+$100.50"


class TestFormatNumber:
    """数字格式化测试"""

    def test_small_number(self):
        """测试小数字"""
        assert format_number(100) == "100.00"
        assert format_number(123.456) == "123.46"

    def test_large_number(self):
        """测试大数字"""
        assert format_number(15000) == "1.50万"
        assert format_number(100000) == "10.00万"

    def test_negative_number(self):
        """测试负数"""
        assert format_number(-100) == "-100.00"
        assert format_number(-15000) == "-1.50万"

    def test_custom_decimals(self):
        """测试自定义小数位"""
        assert format_number(123.456, 3) == "123.456"
        assert format_number(123.456, 0) == "123"


class TestFormatCurrency:
    """货币格式化测试"""

    def test_currency_format(self):
        """测试货币格式化"""
        assert format_currency(100) == "¥100.00"
        assert format_currency(1234.56) == "¥1,234.56"

    def test_custom_prefix(self):
        """测试自定义前缀"""
        assert format_currency(100, "$") == "$100.00"
