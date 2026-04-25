"""
涨跌幅计算逻辑测试
测试 estimateChange 和 estimateChangePercent 的计算正确性
"""

import pytest

from api.routes.funds.funds_data import _calculate_estimate_change


class TestCalculateEstimateChange:
    """测试 _calculate_estimate_change 函数"""

    def test_normal_case(self):
        """正常情况：估算净值 > 单位净值，返回正数"""
        unit_net = 1.2233
        estimate_net = 1.2304
        result = _calculate_estimate_change(unit_net, estimate_net)
        assert result == pytest.approx(0.0071, rel=1e-4)

    def test_negative_change(self):
        """估算净值 < 单位净值，返回负数"""
        unit_net = 1.2306
        estimate_net = 1.2200
        result = _calculate_estimate_change(unit_net, estimate_net)
        assert result == pytest.approx(-0.0106, rel=1e-4)

    def test_no_change(self):
        """估算净值 == 单位净值，返回 0"""
        unit_net = 1.5000
        estimate_net = 1.5000
        result = _calculate_estimate_change(unit_net, estimate_net)
        assert result == 0.0

    def test_unit_net_none(self):
        """单位净值为 None，返回 None"""
        result = _calculate_estimate_change(None, 1.5000)
        assert result is None

    def test_estimate_net_none(self):
        """估算净值为 None，返回 None"""
        result = _calculate_estimate_change(1.5000, None)
        assert result is None

    def test_both_none(self):
        """两个都为 None，返回 None"""
        result = _calculate_estimate_change(None, None)
        assert result is None

    def test_unit_net_zero(self):
        """单位净值为 0，减法运算仍然有效"""
        result = _calculate_estimate_change(0, 1.5000)
        assert result == 1.5000

    def test_small_change(self):
        """小幅度变化"""
        unit_net = 1.0000
        estimate_net = 1.0001
        result = _calculate_estimate_change(unit_net, estimate_net)
        assert result == pytest.approx(0.0001, rel=1e-4)

    def test_large_change(self):
        """大幅度变化（涨跌停）"""
        unit_net = 1.0000
        estimate_net = 1.1000  # 10% 涨幅
        result = _calculate_estimate_change(unit_net, estimate_net)
        assert result == pytest.approx(0.1000, rel=1e-4)

    def test_rounding(self):
        """测试四舍五入到 4 位小数"""
        unit_net = 1.12345678
        estimate_net = 1.12345679
        result = _calculate_estimate_change(unit_net, estimate_net)
        # 差值约为 0.00000001，应被 round 到 0.0000
        assert result == 0.0


class TestEstimateChangePercentConsistency:
    """测试 estimateChangePercent 与 estimateChange 的一致性"""

    def test_change_percent_matches_change_value(self):
        """
        验证：estimateChangePercent = (estimateChange / netValue) * 100
        这个测试验证数据源返回的 estimateChangePercent 与计算值一致
        """
        # 这是一个示例，actual data validation 应该在 API 层面进行
        # 这里我们验证计算逻辑
        unit_net = 1.2233
        estimate_net = 1.2304
        estimate_change = _calculate_estimate_change(unit_net, estimate_net)

        # 验证涨跌幅计算公式
        expected_percent = (estimate_change / unit_net) * 100
        actual_percent = (estimate_net - unit_net) / unit_net * 100

        assert expected_percent == pytest.approx(actual_percent, rel=1e-6)


class TestValidateEstimateChangePercent:
    """测试 _validate_estimate_change_percent 函数"""

    def test_valid_percent_returns_unchanged(self):
        """提供的增长率与计算值一致，返回原值"""
        from api.routes.funds.funds_data import _validate_estimate_change_percent

        unit_net = 1.2233
        estimate_net = 1.2304
        provided_percent = 0.5838  # 接近计算值

        result = _validate_estimate_change_percent(
            unit_net, estimate_net, provided_percent, "023521"
        )
        assert result == pytest.approx(0.5838, rel=1e-4)

    def test_invalid_percent_is_corrected(self):
        """提供的增长率与计算值不一致，返回修正值"""
        from api.routes.funds.funds_data import _validate_estimate_change_percent

        unit_net = 1.2233
        estimate_net = 1.2304
        provided_percent = 99.0  # 错误值

        result = _validate_estimate_change_percent(
            unit_net, estimate_net, provided_percent, "023521"
        )
        # 计算值应该是 0.5838...
        expected = (estimate_net - unit_net) / unit_net * 100
        assert result == pytest.approx(expected, rel=1e-4)

    def test_none_values_return_provided(self):
        """当输入为 None 时，返回提供的值（不做校验）"""
        from api.routes.funds.funds_data import _validate_estimate_change_percent

        assert _validate_estimate_change_percent(None, 1.5, 5.0, "023521") == 5.0
        assert _validate_estimate_change_percent(1.5, None, 5.0, "023521") == 5.0
        assert _validate_estimate_change_percent(1.5, 1.5, None, "023521") is None

    def test_zero_unit_net_returns_provided(self):
        """当 unit_net 为 0 时，避免除零错误"""
        from api.routes.funds.funds_data import _validate_estimate_change_percent

        result = _validate_estimate_change_percent(0, 1.5, 5.0, "023521")
        assert result == 5.0
