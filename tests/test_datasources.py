"""
数据源模块测试

覆盖:
1. 单元测试 - DataSourceType, DataSourceResult
2. 服务测试 (Mock) - SinaStockDataSource, YahooStockSource, SameSourceAggregator
3. 集成测试 (真实 API) - 基金数据源, 商品数据源
"""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
from src.datasources.stock_source import (
    SinaStockDataSource,
    StockDataAggregator,
    YahooStockSource,
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

    def test_stock_type(self):
        """测试股票类型"""
        assert DataSourceType.STOCK.value == "stock"

    def test_bond_type(self):
        """测试债券类型"""
        assert DataSourceType.BOND.value == "bond"

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
        assert len(DataSourceType) == 7

    def test_type_comparison(self):
        """测试类型比较"""
        assert DataSourceType.STOCK != DataSourceType.BOND
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
# 3. 服务测试 (Mock) - SinaStockDataSource
# ============================================================================


class TestSinaStockDataSource:
    """新浪股票数据源测试"""

    @pytest.fixture
    def source(self):
        """创建测试实例"""
        s = SinaStockDataSource(timeout=5.0)
        yield s
        try:
            asyncio.run(s.close())
        except Exception:
            pass

    def test_init(self, source):
        """测试初始化"""
        assert source.name == "sina_stock"
        assert source.source_type == DataSourceType.STOCK
        assert source.timeout == 5.0

    def test_get_status(self, source):
        """测试状态获取"""
        status = source.get_status()
        assert status["name"] == "sina_stock"
        assert status["type"] == "stock"
        assert "supported_markets" in status

    def test_get_market_sh(self):
        """测试上海市场判断"""
        source = SinaStockDataSource()
        assert source._get_market("600000")[0] == "sh"
        assert source._get_market("688888")[0] == "sh"

    def test_get_market_sz(self):
        """测试深圳市场判断"""
        source = SinaStockDataSource()
        assert source._get_market("000001")[0] == "sz"
        assert source._get_market("300001")[0] == "sz"

    @pytest.mark.asyncio
    async def test_parse_response(self, source):
        """测试响应解析"""
        response_text = 'var hq_str_sh600000="浦发银行,9.25,9.24,9.30,9.31,9.20,9.25,9.26,152300,1410000,0,0,10:30:00";'
        data = source._parse_response(response_text, "600000", "sh")

        assert data is not None
        assert data["code"] == "600000"
        assert data["name"] == "浦发银行"
        assert data["price"] == 9.30
        assert data["open"] == 9.24
        assert data["pre_close"] == 9.25
        assert data["market"] == "sh"

    @pytest.mark.asyncio
    async def test_parse_invalid_response(self, source):
        """测试无效响应解析"""
        data = source._parse_response("invalid response", "600000", "sh")
        assert data is None

    @pytest.mark.asyncio
    async def test_parse_empty_response(self, source):
        """测试空响应解析"""
        data = source._parse_response("", "600000", "sh")
        assert data is None

    @pytest.mark.asyncio
    async def test_fetch_with_mock(self, source):
        """测试 Mock HTTP 响应"""
        mock_response = MagicMock()
        mock_response.text = 'var hq_str_sh600000="浦发银行,9.25,9.24,9.30,9.31,9.20,9.25,9.26,152300,1410000,0,0,10:30:00";'
        mock_response.raise_for_status = MagicMock()

        with patch.object(source.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await source.fetch("600000")

            assert result.success is True
            assert result.data["code"] == "600000"
            assert result.data["price"] == 9.30

    @pytest.mark.asyncio
    async def test_fetch_with_error(self, source):
        """测试 HTTP 错误响应"""
        import httpx

        with patch.object(source.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectTimeout("Connection timeout")
            result = await source.fetch("600000")

            assert result.success is False
            assert result.metadata["error_type"] == "ConnectTimeout"


# ============================================================================
# 5. 服务测试 (Mock) - YahooStockSource
# ============================================================================


class TestYahooStockSource:
    """Yahoo 股票数据源测试"""

    @pytest.fixture
    def source(self):
        """创建测试实例"""
        s = YahooStockSource(timeout=10.0)
        yield s

    def test_init(self, source):
        """测试初始化"""
        assert source.name == "yahoo_stock"
        assert source.source_type == DataSourceType.STOCK
        assert source.timeout == 10.0
        assert source._cache_timeout == 30.0

    def test_get_market_type_cn(self):
        """测试 A 股市场判断"""
        source = YahooStockSource()
        assert source._get_market_type("600000.SH") == "cn"
        assert source._get_market_type("000001.SZ") == "cn"

    def test_get_market_type_hk(self):
        """测试港股市场判断"""
        source = YahooStockSource()
        assert source._get_market_type("0700.HK") == "hk"

    def test_get_market_type_us(self):
        """测试美股市场判断"""
        source = YahooStockSource()
        assert source._get_market_type("AAPL") == "us"
        assert source._get_market_type("MSFT") == "us"

    def test_get_name(self, source):
        """测试名称获取"""
        info = {"shortName": "Apple Inc.", "longName": "Apple Inc."}
        assert source._get_name(info, "AAPL") == "Apple Inc."

        info = {"longName": "Microsoft Corporation"}
        assert source._get_name(info, "MSFT") == "Microsoft Corporation"

        info = {}
        assert source._get_name(info, "GOOGL") == "GOOGL"

    def test_cache_operations(self, source):
        """测试缓存操作"""
        assert source._is_cache_valid("test") is False

        source._cache["test"] = {"_cache_time": 0}
        assert source._is_cache_valid("test") is False

        source.clear_cache()
        assert len(source._cache) == 0

    @pytest.mark.asyncio
    async def test_fetch_with_mock(self, source):
        """测试 Mock yfinance 响应"""
        mock_info = {
            "currentPrice": 150.0,
            "regularMarketPrice": 150.0,
            "regularMarketOpen": 148.0,
            "regularMarketDayHigh": 152.0,
            "regularMarketDayLow": 147.0,
            "regularMarketChange": 2.0,
            "regularMarketChangePercent": 1.5,
            "regularMarketVolume": 1000000,
            "shortName": "Test Stock",
            "exchange": "NASDAQ",
            "currency": "USD",
        }

        with patch.dict("sys.modules", {"yfinance": MagicMock()}):
            import yfinance

            mock_yf_module = yfinance
            mock_ticker = MagicMock()
            mock_ticker.info = mock_info
            mock_yf_module.Ticker.return_value = mock_ticker

            result = await source.fetch("TEST")

            assert result.success is True
            assert result.data["price"] == 150.0
            assert result.data["name"] == "Test Stock"

    @pytest.mark.asyncio
    async def test_fetch_from_cache(self, source):
        """测试从缓存获取"""
        # 设置缓存
        source._cache["AAPL"] = {"symbol": "AAPL", "price": 150.0, "_cache_time": time.time()}

        result = await source.fetch("AAPL")

        assert result.success is True
        assert result.metadata["from_cache"] is True


# ============================================================================
# 6. 服务测试 (Mock) - SameSourceAggregator
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
# 8. 集成测试 - 数据源管理
# ============================================================================


class TestStockDataAggregator:
    """股票数据聚合器测试"""

    def test_add_source(self):
        """测试添加数据源"""
        agg = StockDataAggregator()
        source = MagicMock(spec=DataSource)
        source.name = "test"
        source.source_type = DataSourceType.STOCK

        agg.add_source(source, is_primary=True)

        assert agg._primary_source == source
        assert len(agg._sources) == 1

    @pytest.mark.asyncio
    async def test_aggregator_fetch(self):
        """测试聚合器获取"""
        agg = StockDataAggregator()
        sina = SinaStockDataSource(timeout=5.0)

        mock_response = MagicMock()
        mock_response.text = 'var hq_str_sh600000="浦发银行,9.25,9.24,9.30,9.31,9.20,9.25,9.26,152300,1410000,0,0,10:30:00";'
        mock_response.raise_for_status = MagicMock()

        with patch.object(sina.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            agg.add_source(sina, is_primary=True)

            result = await agg.fetch("600000")

            assert result.success is True
            assert result.data["code"] == "600000"

        await agg.close()


# ============================================================================
# 9. 集成测试 - 异常处理
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
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
