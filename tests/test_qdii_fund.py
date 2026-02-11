# -*- coding: UTF-8 -*-
"""
QDII/FOF 基金核心功能单元测试

测试以下功能：
1. QDII/FOF 基金类型识别逻辑
2. _calculate_estimate_change 函数
3. _check_is_holding 函数
4. build_fund_response 函数
"""

import pytest
from unittest.mock import MagicMock, patch


class TestQdiiFofTypeRecognition:
    """测试 QDII/FOF 基金类型识别逻辑"""

    def test_qdii_type_from_name_with_parentheses(self):
        """测试 "(QDII)" 后缀识别"""
        from api.routes.funds import build_fund_response

        # 基金名称包含 "(QDII)"
        data = {
            "fund_code": "470888",
            "name": "华夏全球精选股票(QDII)",
            "type": "QDII",
            "unit_net_value": 1.5,
            "estimated_net_value": 1.52,
            "estimated_growth_rate": 1.33,
            "net_value_date": "2024-01-10",
            "estimate_time": "2024-01-10 15:00",
            "has_real_time_estimate": False,
        }

        response = build_fund_response(data, source="tiantian")

        assert response["type"] == "QDII"
        assert response["hasRealTimeEstimate"] is False

    def test_qdii_type_from_name_without_parentheses(self):
        """测试 "QDII" 后缀识别（无括号）"""
        from api.routes.funds import build_fund_response

        # 基金名称以 "QDII" 结尾
        data = {
            "fund_code": "000001",
            "name": "上投摩根全球新兴市场QDII",
            "type": "QDII",
            "unit_net_value": 1.2,
            "estimated_net_value": 1.18,
            "estimated_growth_rate": -1.67,
            "net_value_date": "2024-01-10",
            "estimate_time": "2024-01-10 15:00",
            "has_real_time_estimate": False,
        }

        response = build_fund_response(data, source="tiantian")

        assert response["type"] == "QDII"
        assert response["hasRealTimeEstimate"] is False

    def test_fof_type_from_name(self):
        """测试 FOF 类型识别"""
        from api.routes.funds import build_fund_response

        # 基金名称包含 FOF
        data = {
            "fund_code": "005217",
            "name": "交银施罗德安享稳健养老目标一年持有FOF",
            "type": "FOF",
            "unit_net_value": 1.08,
            "estimated_net_value": 1.09,
            "estimated_growth_rate": 0.93,
            "net_value_date": "2024-01-10",
            "estimate_time": "2024-01-10 15:00",
            "has_real_time_estimate": False,
        }

        response = build_fund_response(data, source="tiantian")

        assert response["type"] == "FOF"
        assert response["hasRealTimeEstimate"] is False

    def test_fof_type_from_name_with_parentheses(self):
        """测试 "(FOF)" 后缀识别"""
        from api.routes.funds import build_fund_response

        # 基金名称包含 "(FOF)"
        data = {
            "fund_code": "006289",
            "name": "中银添利稳健养老目标一年(FOF)",
            "type": "FOF",
            "unit_net_value": 1.05,
            "estimated_net_value": 1.06,
            "estimated_growth_rate": 0.95,
            "net_value_date": "2024-01-10",
            "estimate_time": "2024-01-10 15:00",
            "has_real_time_estimate": False,
        }

        response = build_fund_response(data, source="tiantian")

        assert response["type"] == "FOF"
        assert response["hasRealTimeEstimate"] is False


class TestHasRealTimeEstimate:
    """测试 hasRealTimeEstimate 字段"""

    def test_has_real_time_estimate_for_qdii(self):
        """测试 QDII 基金 hasRealTimeEstimate 为 False"""
        from api.routes.funds import build_fund_response

        data = {
            "fund_code": "470888",
            "name": "华夏全球精选股票(QDII)",
            "type": "QDII",
            "unit_net_value": 1.5,
            "has_real_time_estimate": False,
        }

        response = build_fund_response(data)

        assert response["hasRealTimeEstimate"] is False

    def test_has_real_time_estimate_for_normal(self):
        """测试普通基金 hasRealTimeEstimate 为 True"""
        from api.routes.funds import build_fund_response

        data = {
            "fund_code": "161039",
            "name": "富国中证新能源汽车指数",
            "type": "股票型",
            "unit_net_value": 2.0,
            "has_real_time_estimate": True,
        }

        response = build_fund_response(data)

        assert response["hasRealTimeEstimate"] is True

    def test_has_real_time_estimate_defaults_to_true(self):
        """测试 hasRealTimeEstimate 默认值为 True"""
        from api.routes.funds import build_fund_response

        data = {
            "fund_code": "161039",
            "name": "富国中证新能源汽车指数",
            "type": "股票型",
            "unit_net_value": 2.0,
            # 未指定 has_real_time_estimate
        }

        response = build_fund_response(data)

        assert response["hasRealTimeEstimate"] is True

    def test_has_real_time_estimate_for_fof(self):
        """FOF 基金 hasRealTimeEstimate 应为 False"""
        from api.routes.funds import build_fund_response

        data = {
            "fund_code": "005217",
            "name": "交银施罗德安享稳健养老目标一年持有FOF",
            "type": "FOF",
            "has_real_time_estimate": False,
        }
        response = build_fund_response(data)
        assert response["hasRealTimeEstimate"] is False


class TestCalculateEstimateChange:
    """测试 _calculate_estimate_change 函数"""

    def test_calculate_estimate_change_normal(self):
        """正常情况 - 计算估算涨跌额"""
        from api.routes.funds import _calculate_estimate_change

        # 正常情况：单位净值 1.5，估算净值 1.52，涨跌额应该是 0.02
        result = _calculate_estimate_change(unit_net=1.5, estimate_net=1.52)

        assert result == 0.02

    def test_calculate_estimate_change_negative(self):
        """计算负向涨跌额"""
        from api.routes.funds import _calculate_estimate_change

        # 单位净值 1.5，估算净值 1.48，涨跌额应该是 -0.02
        result = _calculate_estimate_change(unit_net=1.5, estimate_net=1.48)

        assert result == -0.02

    def test_calculate_estimate_change_zero_division(self):
        """单位净值为 0 时应返回 None"""
        from api.routes.funds import _calculate_estimate_change

        # 单位净值为 0
        result = _calculate_estimate_change(unit_net=0.0, estimate_net=1.52)

        assert result is None

    def test_calculate_estimate_change_none_unit_net(self):
        """单位净值为 None 时应返回 None"""
        from api.routes.funds import _calculate_estimate_change

        result = _calculate_estimate_change(unit_net=None, estimate_net=1.52)

        assert result is None

    def test_calculate_estimate_change_none_estimate_net(self):
        """估算净值为 None 时应返回 None"""
        from api.routes.funds import _calculate_estimate_change

        result = _calculate_estimate_change(unit_net=1.5, estimate_net=None)

        assert result is None

    def test_calculate_estimate_change_both_none(self):
        """两个参数都为 None 时应返回 None"""
        from api.routes.funds import _calculate_estimate_change

        result = _calculate_estimate_change(unit_net=None, estimate_net=None)

        assert result is None

    def test_calculate_estimate_change_rounding(self):
        """测试四舍五入"""
        from api.routes.funds import _calculate_estimate_change

        # 结果应该四舍五入到 4 位小数
        result = _calculate_estimate_change(unit_net=1.123456, estimate_net=1.654321)

        assert result == round(1.654321 - 1.123456, 4)

    def test_calculate_estimate_change_extreme_values(self):
        """测试极端值场景"""
        from api.routes.funds import _calculate_estimate_change

        # 大数计算
        result = _calculate_estimate_change(unit_net=1000000.0, estimate_net=1000000.1234)
        assert result == 0.1234

        # 极小数值
        result = _calculate_estimate_change(unit_net=0.0001, estimate_net=0.0002)
        assert result == 0.0001


class TestCheckIsHolding:
    """测试 _check_is_holding 函数"""

    @patch("api.routes.funds.ConfigManager")
    def test_check_is_holding_with_holding(self, mock_config_manager):
        """持仓中 - 应返回 True"""
        from api.routes.funds import _check_is_holding

        # 模拟持仓数据
        mock_fund_list = MagicMock()
        mock_fund_list.holdings = [
            MagicMock(code="000001"),
            MagicMock(code="000002"),
            MagicMock(code="161039"),
        ]
        mock_config_manager.return_value.load_funds.return_value = mock_fund_list

        result = _check_is_holding("000001")

        assert result is True

    @patch("api.routes.funds.ConfigManager")
    def test_check_is_holding_without_holding(self, mock_config_manager):
        """未持仓 - 应返回 False"""
        from api.routes.funds import _check_is_holding

        # 模拟持仓数据
        mock_fund_list = MagicMock()
        mock_fund_list.holdings = [
            MagicMock(code="000001"),
            MagicMock(code="000002"),
        ]
        mock_config_manager.return_value.load_funds.return_value = mock_fund_list

        result = _check_is_holding("999999")

        assert result is False

    @patch("api.routes.funds.ConfigManager")
    def test_check_is_holding_empty_holdings(self, mock_config_manager):
        """空持仓列表 - 应返回 False"""
        from api.routes.funds import _check_is_holding

        # 模拟空持仓
        mock_fund_list = MagicMock()
        mock_fund_list.holdings = []
        mock_config_manager.return_value.load_funds.return_value = mock_fund_list

        result = _check_is_holding("000001")

        assert result is False

    @patch("api.routes.funds.ConfigManager")
    def test_check_is_holding_exception(self, mock_config_manager):
        """加载失败时返回 False"""
        from api.routes.funds import _check_is_holding

        # 模拟加载异常
        mock_config_manager.return_value.load_funds.side_effect = Exception("Config error")

        result = _check_is_holding("000001")

        assert result is False


class TestBuildFundResponse:
    """测试 build_fund_response 函数"""

    def test_build_fund_response_with_qdii(self):
        """QDII 基金测试"""
        from api.routes.funds import build_fund_response

        data = {
            "fund_code": "470888",
            "name": "华夏全球精选股票(QDII)",
            "type": "QDII",
            "unit_net_value": 1.5,
            "net_value_date": "2024-01-10",
            "prev_net_value": 1.48,
            "prev_net_value_date": "2024-01-09",
            "estimated_net_value": 1.52,
            "estimated_growth_rate": 2.67,
            "estimate_time": "2024-01-10 15:00",
            "has_real_time_estimate": False,
        }

        response = build_fund_response(data, source="tiantian", is_holding=True)

        assert response["code"] == "470888"
        assert response["name"] == "华夏全球精选股票(QDII)"
        assert response["type"] == "QDII"
        assert response["netValue"] == 1.5
        assert response["estimateValue"] == 1.52
        assert response["estimateChange"] == 0.02
        assert response["estimateChangePercent"] == 2.67
        assert response["source"] == "tiantian"
        assert response["isHolding"] is True
        assert response["hasRealTimeEstimate"] is False

    def test_build_fund_response_with_normal(self):
        """普通基金测试"""
        from api.routes.funds import build_fund_response

        data = {
            "fund_code": "161039",
            "name": "富国中证新能源汽车指数",
            "type": "股票型",
            "unit_net_value": 2.0,
            "net_value_date": "2024-01-10",
            "estimated_net_value": 2.05,
            "estimated_growth_rate": 2.5,
            "estimate_time": "2024-01-10 15:00",
            "has_real_time_estimate": True,
        }

        response = build_fund_response(data, source="eastmoney", is_holding=False)

        assert response["code"] == "161039"
        assert response["name"] == "富国中证新能源汽车指数"
        assert response["type"] == "股票型"
        assert response["netValue"] == 2.0
        assert response["estimateValue"] == 2.05
        assert response["estimateChange"] == 0.05
        assert response["source"] == "eastmoney"
        assert response["isHolding"] is False
        assert response["hasRealTimeEstimate"] is True

    def test_build_fund_response_with_fof(self):
        """FOF 基金测试"""
        from api.routes.funds import build_fund_response

        data = {
            "fund_code": "005217",
            "name": "交银施罗德安享稳健养老目标一年持有FOF",
            "type": "FOF",
            "unit_net_value": 1.08,
            "net_value_date": "2024-01-10",
            "estimated_net_value": 1.08,
            "estimated_growth_rate": 0.0,
            "estimate_time": "2024-01-10 15:00",
            "has_real_time_estimate": False,
        }

        response = build_fund_response(data, source="tiantian")

        assert response["type"] == "FOF"
        assert response["hasRealTimeEstimate"] is False
        assert response["estimateChange"] == 0.0

    def test_build_fund_response_missing_fields(self):
        """测试缺失字段的处理"""
        from api.routes.funds import build_fund_response

        data = {
            "fund_code": "161039",
            "name": "富国中证新能源汽车指数",
            # 其他字段缺失
        }

        response = build_fund_response(data)

        assert response["code"] == "161039"
        assert response["name"] == "富国中证新能源汽车指数"
        assert response["type"] is None
        assert response["netValue"] is None
        assert response["estimateValue"] is None
        assert response["estimateChange"] is None
        assert response["hasRealTimeEstimate"] is True  # 默认值

    def test_build_fund_response_with_etf_link(self):
        """ETF-联接基金测试"""
        from api.routes.funds import build_fund_response

        data = {
            "fund_code": "510500",
            "name": "华夏上证50ETF联接",
            "type": "ETF-联接",
            "unit_net_value": 1.5,
            "net_value_date": "2024-01-10",
            "estimated_net_value": 1.52,
            "estimated_growth_rate": 1.33,
            "estimate_time": "2024-01-10 15:00",
            "has_real_time_estimate": False,
        }

        response = build_fund_response(data)

        assert response["type"] == "ETF-联接"
        assert response["hasRealTimeEstimate"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
