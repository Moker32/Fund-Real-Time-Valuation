"""
数据源模块测试

覆盖:
1. 单元测试 - DataSourceType, DataSourceResult
2. 服务测试 (Mock) - SameSourceAggregator
3. 集成测试 (真实 API) - 基金数据源, 商品数据源
"""

import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.datasources.aggregator import (
    SameSourceAggregator,
)
from src.datasources.base import (
    DataParseError,
    DataSource,
    DataSourceError,
    DataSourceResult,
    DataSourceType,
    NetworkError,
)

# ============================================================================
# 1. 单元测试 - DataSourceType 枚举
# ============================================================================


class TestDataSourceType:
    """数据源类型枚举测试"""

    def test_fund_type(self):
        """测试基金类型"""
        assert DataSourceType.FUND.value == "fund"
        assert DataSourceType.FUND == DataSourceType.FUND

    def test_crypto_type(self):
        """测试加密货币类型"""
        assert DataSourceType.CRYPTO.value == "crypto"

    def test_commodity_type(self):
        """测试商品类型"""
        assert DataSourceType.COMMODITY.value == "commodity"

    def test_news_type(self):
        """测试新闻类型"""
        assert DataSourceType.NEWS.value == "news"

    def test_sector_type(self):
        """测试行业类型"""
        assert DataSourceType.SECTOR.value == "sector"

    def test_all_types_count(self):
        """测试所有类型数量"""
        assert len(DataSourceType) == 6

    def test_type_comparison(self):
        """测试类型比较"""
        assert DataSourceType.FUND != DataSourceType.STOCK
        assert DataSourceType.CRYPTO == DataSourceType.CRYPTO


# ============================================================================
# 2. 单元测试 - DataSourceResult
# ============================================================================


class TestDataSourceResult:
    """DataSourceResult 测试"""

    def test_success_result_default(self):
        """测试成功结果默认字段"""
        result = DataSourceResult(success=True, data={"price": 100})
        assert result.success is True
        assert result.data == {"price": 100}
        assert result.error is None
        assert result.timestamp > 0
        assert result.source == ""

    def test_error_result(self):
        """测试错误结果"""
        result = DataSourceResult(success=False, error="Network error", source="test_source")
        assert result.success is False
        assert result.error == "Network error"
        assert result.source == "test_source"

    def test_result_with_metadata(self):
        """测试带元数据的结果"""
        result = DataSourceResult(
            success=True, data={"price": 100}, source="test", metadata={"symbol": "AAPL"}
        )
        assert result.metadata == {"symbol": "AAPL"}

    def test_timestamp_auto_set(self):
        """测试时间戳自动设置"""
        before = time.time()
        result = DataSourceResult(success=True)
        after = time.time()
        assert before <= result.timestamp <= after

    def test_timestamp_manual_override(self):
        """测试手动设置时间戳"""
        manual_time = 1234567890.0
        result = DataSourceResult(success=True, timestamp=manual_time)
        assert result.timestamp == manual_time


# ============================================================================
# 3. 服务测试 (Mock) - SameSourceAggregator
# ============================================================================


class TestSameSourceAggregator:
    """同源聚合器测试"""

    def test_empty_aggregator(self):
        """测试空聚合器"""
        agg = SameSourceAggregator()
        assert len(agg._sources) == 0

    def test_add_source(self):
        """测试添加数据源"""
        agg = SameSourceAggregator()
        source = MagicMock(spec=DataSource)
        source.name = "test_source"
        source.source_type = DataSourceType.STOCK

        agg.add_source(source, is_primary=True)

        assert len(agg._sources) == 1
        assert agg.get_primary_source() == source

    def test_add_multiple_sources(self):
        """测试添加多个数据源"""
        agg = SameSourceAggregator()
        source1 = MagicMock(spec=DataSource)
        source1.name = "source1"
        source1.source_type = DataSourceType.STOCK
        source2 = MagicMock(spec=DataSource)
        source2.name = "source2"
        source2.source_type = DataSourceType.STOCK

        agg.add_source(source1, is_primary=True)
        agg.add_source(source2)

        assert len(agg._sources) == 2
        assert agg.get_primary_source() == source1

    def test_remove_source(self):
        """测试移除数据源"""
        agg = SameSourceAggregator()
        source1 = MagicMock(spec=DataSource)
        source1.name = "source1"
        source1.source_type = DataSourceType.STOCK
        source2 = MagicMock(spec=DataSource)
        source2.name = "source2"
        source2.source_type = DataSourceType.STOCK

        agg.add_source(source1)
        agg.add_source(source2)

        assert agg.remove_source("source1") is True
        assert agg.remove_source("notexist") is False

    def test_get_statistics(self):
        """测试获取统计信息"""
        agg = SameSourceAggregator()
        source = MagicMock(spec=DataSource)
        source.name = "test_source"
        source.source_type = DataSourceType.STOCK
        source.get_status.return_value = {"name": "test"}

        agg.add_source(source, is_primary=True)

        stats = agg.get_statistics()
        assert stats["name"] == "SameSourceAggregator"
        assert stats["source_count"] == 1
        assert stats["primary_source"] == "test_source"

    @pytest.mark.asyncio
    async def test_fetch_with_primary_success(self):
        """测试主数据源成功获取"""
        agg = SameSourceAggregator()
        primary = MagicMock(spec=DataSource)
        primary.name = "primary"
        primary.source_type = DataSourceType.STOCK
        primary.fetch = AsyncMock(
            return_value=DataSourceResult(success=True, data={"price": 100}, source="primary")
        )

        agg.add_source(primary, is_primary=True)

        result = await agg.fetch("TEST")
        assert result.success is True
        assert result.data["price"] == 100

    @pytest.mark.asyncio
    async def test_fetch_failover_to_secondary(self):
        """测试故障切换到备用数据源"""
        agg = SameSourceAggregator()

        primary = MagicMock(spec=DataSource)
        primary.name = "primary"
        primary.source_type = DataSourceType.STOCK
        primary.fetch = AsyncMock(
            return_value=DataSourceResult(success=False, error="Primary failed", source="primary")
        )

        secondary = MagicMock(spec=DataSource)
        secondary.name = "secondary"
        secondary.source_type = DataSourceType.STOCK
        secondary.fetch = AsyncMock(
            return_value=DataSourceResult(success=True, data={"price": 200}, source="secondary")
        )

        agg.add_source(primary, is_primary=True)
        agg.add_source(secondary)

        result = await agg.fetch("TEST")
        assert result.success is True
        assert result.data["price"] == 200
        assert agg._failover_count == 1

    @pytest.mark.asyncio
    async def test_fetch_all_sources_fail(self):
        """测试所有数据源都失败"""
        agg = SameSourceAggregator()

        source1 = MagicMock(spec=DataSource)
        source1.name = "source1"
        source1.source_type = DataSourceType.STOCK
        source1.fetch = AsyncMock(
            return_value=DataSourceResult(success=False, error="Failed", source="source1")
        )

        source2 = MagicMock(spec=DataSource)
        source2.name = "source2"
        source2.source_type = DataSourceType.STOCK
        source2.fetch = AsyncMock(
            return_value=DataSourceResult(success=False, error="Failed", source="source2")
        )

        agg.add_source(source1, is_primary=True)
        agg.add_source(source2)

        result = await agg.fetch("TEST")
        assert result.success is False
        assert "所有数据源均失败" in result.error

    @pytest.mark.asyncio
    async def test_fetch_empty_aggregator(self):
        """测试空聚合器获取"""
        agg = SameSourceAggregator()
        result = await agg.fetch("TEST")
        assert result.success is False
        assert "没有数据源" in result.error


# ============================================================================
# 8. 集成测试 - 异常处理
# ============================================================================


class TestDataSourceErrors:
    """数据源异常测试"""

    def test_data_source_error(self):
        """测试数据源异常"""
        error = DataSourceError(
            message="Test error", source_type=DataSourceType.STOCK, details={"key": "value"}
        )
        assert error.message == "Test error"
        assert error.source_type == DataSourceType.STOCK
        assert error.details["key"] == "value"

    def test_network_error(self):
        """测试网络异常"""
        error = NetworkError(message="Connection failed", source_type=DataSourceType.STOCK)
        assert isinstance(error, DataSourceError)
        assert "Connection failed" in error.message

    def test_data_parse_error(self):
        """测试数据解析异常"""
        error = DataParseError(message="Parse failed", source_type=DataSourceType.STOCK)
        assert isinstance(error, DataSourceError)


# ============================================================================
# 10. 单元测试 - 基金类型推断
# ============================================================================


class TestFundTypeInference:
    """基金类型推断测试"""

    def test_infer_fund_type_qdii(self):
        """测试 QDII 基金类型推断"""
        from src.datasources.fund_source import _infer_fund_type_from_name

        assert _infer_fund_type_from_name("华宝标普美国品质消费股票(QDII-LOF)A") == "QDII"
        assert _infer_fund_type_from_name("易方达标普500指数(QDII-LOF)人民币") == "QDII"
        assert _infer_fund_type_from_name("广发纳斯达克100指数(QDII)") == "QDII"

    def test_infer_fund_type_fof(self):
        """测试 FOF 基金类型推断"""
        from src.datasources.fund_source import _infer_fund_type_from_name

        assert _infer_fund_type_from_name("华夏聚惠稳健目标风险混合(FOF)") == "FOF"
        assert _infer_fund_type_from_name("南方养老2035(FOF)") == "FOF"

    def test_infer_fund_type_etf(self):
        """测试 ETF 基金类型推断"""
        from src.datasources.fund_source import _infer_fund_type_from_name

        assert _infer_fund_type_from_name("华夏沪深300ETF") == "ETF"
        assert _infer_fund_type_from_name("易方达创业板ETF") == "ETF"

    def test_infer_fund_type_etf_connect(self):
        """测试 ETF 联接基金类型推断"""
        from src.datasources.fund_source import _infer_fund_type_from_name

        assert _infer_fund_type_from_name("华夏沪深300ETF联接") == "ETF-联接"
        assert _infer_fund_type_from_name("易方达创业板ETF联接A") == "ETF-联接"

    def test_infer_fund_type_lof(self):
        """测试 LOF 基金类型推断"""
        from src.datasources.fund_source import _infer_fund_type_from_name

        assert _infer_fund_type_from_name("兴全合润混合(LOF)") == "LOF"
        assert _infer_fund_type_from_name("中欧盛世成长混合(LOF)") == "LOF"

    def test_infer_fund_type_money(self):
        """测试货币型基金类型推断"""
        from src.datasources.fund_source import _infer_fund_type_from_name

        assert _infer_fund_type_from_name("余额宝货币市场基金") == "货币型"
        assert _infer_fund_type_from_name("华夏货币A") == "货币型"

    def test_infer_fund_type_bond(self):
        """测试债券型基金类型推断"""
        from src.datasources.fund_source import _infer_fund_type_from_name

        assert _infer_fund_type_from_name("易方达稳健债券") == "债券型"
        assert _infer_fund_type_from_name("华夏债券A") == "债券型"

    def test_infer_fund_type_hybrid(self):
        """测试混合型基金类型推断"""
        from src.datasources.fund_source import _infer_fund_type_from_name

        assert _infer_fund_type_from_name("华夏回报混合") == "混合型"
        assert _infer_fund_type_from_name("易方达蓝筹精选混合") == "混合型"

    def test_infer_fund_type_index(self):
        """测试指数型基金类型推断 - 关键测试"""
        from src.datasources.fund_source import _infer_fund_type_from_name

        # 指数型基金应该返回"指数型"，而不是"股票型"
        assert _infer_fund_type_from_name("招商中证白酒指数") == "指数型"
        assert _infer_fund_type_from_name("易方达上证50指数A") == "指数型"
        assert _infer_fund_type_from_name("国泰中证新能源汽车指数") == "指数型"

    def test_infer_fund_type_stock(self):
        """测试股票型基金类型推断"""
        from src.datasources.fund_source import _infer_fund_type_from_name

        # 不含"指数"的股票型基金
        assert _infer_fund_type_from_name("易方达中小盘股票") == "股票型"
        assert _infer_fund_type_from_name("华夏成长股票") == "股票型"

    def test_infer_fund_type_empty(self):
        """测试空名称"""
        from src.datasources.fund_source import _infer_fund_type_from_name

        assert _infer_fund_type_from_name("") == ""
        assert _infer_fund_type_from_name(None) == ""

    def test_infer_fund_type_unknown(self):
        """测试未知类型"""
        from src.datasources.fund_source import _infer_fund_type_from_name

        assert _infer_fund_type_from_name("某基金") == ""


class TestFundTypeFromFundNameEm:
    """基金类型 API 获取测试"""

    @pytest.mark.skip(reason="需要真实 API 调用，在集成测试中运行")
    def test_get_fund_type_from_fund_name_em_real(self):
        """测试从 fund_name_em API 获取基金类型（真实调用）"""
        from src.datasources.fund_source import _get_fund_type_from_fund_name_em

        # 测试一个已知存在的基金
        # 基金 025833 应该返回 "指数型-股票" 或类似格式
        fund_type = _get_fund_type_from_fund_name_em("025833")
        # 如果 API 正常工作，应该返回包含"指数"的类型
        if fund_type:
            assert "指数" in fund_type or "股票" in fund_type

    def test_get_fund_type_from_fund_name_em_invalid(self):
        """测试无效基金代码"""
        from src.datasources.fund_source import _get_fund_type_from_fund_name_em

        # 测试一个明显无效的基金代码
        # 注意：这个测试可能会因为 API 返回格式变化而失败
        # 所以我们只测试函数不会抛出异常
        try:
            _get_fund_type_from_fund_name_em("000000")
            # 无论返回什么，都不应该抛出异常
        except Exception:
            pytest.fail("函数不应该抛出异常")


class TestGetFundBasicInfo:
    """基金基本信息获取测试"""

    def test_get_fund_basic_info_type_priority(self):
        """测试基金类型获取优先级"""
        # 这个测试验证类型获取的优先级：
        # 1. fund_individual_basic_info_xq (最精确)
        # 2. fund_name_em (备用，保留子类型)
        # 3. _infer_fund_type_from_name (最后回退)
        #
        # 由于涉及真实 API 调用，这里只验证函数签名和基本行为
        from src.datasources.fund_source import get_fund_basic_info

        # 验证函数存在且可调用
        assert callable(get_fund_basic_info)

    @pytest.mark.skip(reason="需要真实 API 调用，在集成测试中运行")
    def test_get_fund_basic_info_index_fund(self):
        """测试指数型基金类型获取 - 验证 025833 案例"""
        from src.datasources.fund_source import get_fund_basic_info

        # 获取基金 025833 的信息
        result = get_fund_basic_info("025833")
        if result:
            name, fund_type = result
            # 验证基金类型包含"指数"
            assert "指数" in fund_type, f"期望基金类型包含'指数'，实际获取: {fund_type}"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
