# -*- coding: UTF-8 -*-
"""API Models Tests

测试 API 数据模型
"""


from api.models import (
    CommodityListResponse,
    CommodityResponse,
    ErrorResponse,
    FundDetailResponse,
    FundEstimateResponse,
    FundListResponse,
    FundResponse,
)


class TestFundResponse:
    """基金响应模型测试"""

    def test_fund_response_creation(self):
        """测试基金响应创建"""
        fund = FundResponse(
            fund_code="000001",
            name="华夏成长混合",
            type="混合型",
            unit_net_value=1.5,
            net_value_date="2024-01-15",
            prev_net_value=1.48,
            prev_net_value_date="2024-01-12",
            estimated_net_value=1.52,
            estimated_growth_rate=2.7,
            estimate_time="2024-01-15 15:00",
            source="sina"
        )

        assert fund.code == "000001"
        assert fund.name == "华夏成长混合"
        assert fund.type == "混合型"
        assert fund.netValue == 1.5
        assert fund.prevNetValue == 1.48

    def test_fund_response_aliases(self):
        """测试字段别名"""
        fund = FundResponse(
            fund_code="000001",
            name="测试基金",
            unit_net_value=1.0
        )

        # 测试别名可以工作
        assert fund.code == "000001"
        assert fund.netValue == 1.0

    def test_fund_response_optional_fields(self):
        """测试可选字段"""
        fund = FundResponse(
            fund_code="000001",
            name="测试基金"
        )

        assert fund.type is None
        assert fund.netValue is None
        assert fund.estimateValue is None


class TestFundListResponse:
    """基金列表响应测试"""

    def test_fund_list_response(self):
        """测试基金列表响应"""
        response = FundListResponse(
            funds=[{"code": "000001"}, {"code": "000002"}],
            total=2,
            timestamp="2024-01-15T15:00:00"
        )

        assert len(response.funds) == 2
        assert response.total == 2


class TestFundDetailResponse:
    """基金详情响应测试"""

    def test_fund_detail_response(self):
        """测试基金详情响应"""
        fund = FundDetailResponse(
            fund_code="000001",
            name="华夏成长混合"
        )

        assert fund.code == "000001"
        assert isinstance(fund, FundResponse)


class TestFundEstimateResponse:
    """基金估值响应测试"""

    def test_fund_estimate_response(self):
        """测试基金估值响应"""
        fund = FundEstimateResponse(
            fund_code="000001",
            name="测试基金",
            estimated_net_value=1.5,
            estimated_growth_rate=2.5
        )

        assert fund.code == "000001"
        assert fund.estimateValue == 1.5


class TestCommodityResponse:
    """商品响应模型测试"""

    def test_commodity_response_creation(self):
        """测试商品响应创建"""
        commodity = CommodityResponse(
            symbol="AU9999",
            name="黄金",
            price=450.0,
            source="akshare"
        )

        assert commodity.symbol == "AU9999"
        assert commodity.name == "黄金"
        assert commodity.price == 450.0

    def test_commodity_response_optional(self):
        """测试可选字段"""
        commodity = CommodityResponse(
            symbol="AG9999",
            name="白银",
            price=5.0,
            source="akshare"
        )

        assert commodity.symbol == "AG9999"
        assert commodity.price == 5.0
        assert commodity.change is None


class TestCommodityListResponse:
    """商品列表响应测试"""

    def test_commodity_list_response(self):
        """测试商品列表响应"""
        response = CommodityListResponse(
            commodities=[{"symbol": "AU9999"}, {"symbol": "AG9999"}],
            timestamp="2024-01-15T15:00:00"
        )

        assert len(response.commodities) == 2
        assert response.timestamp == "2024-01-15T15:00:00"


class TestErrorResponse:
    """错误响应模型测试"""

    def test_error_response_creation(self):
        """测试错误响应创建"""
        error = ErrorResponse(
            error="Something went wrong",
            detail="Detailed error message"
        )

        assert error.error == "Something went wrong"
        assert error.detail == "Detailed error message"
        assert error.success is False
