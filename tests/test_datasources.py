"""
数据源模块测试

覆盖:
1. 单元测试 - DataSourceType, DataSourceResult, PortfolioAnalyzer
2. 服务测试 (Mock) - SinaStockDataSource, YahooStockSource, BinanceCryptoSource, SameSourceAggregator
3. 集成测试 (真实 API) - 基金数据源, 商品数据源
"""

import pytest
import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.datasources.base import (
    DataSourceType,
    DataSourceResult,
    DataSource,
    DataSourceError,
    NetworkError,
    DataParseError,
)
from src.datasources.portfolio import (
    PortfolioAnalyzer,
    AssetType,
    PortfolioPosition,
    PortfolioAllocation,
    PortfolioResult,
)
from src.datasources.stock_source import (
    SinaStockDataSource,
    YahooStockSource,
    StockDataAggregator,
)
from src.datasources.crypto_source import (
    BinanceCryptoSource,
    CoinGeckoCryptoSource,
)
from src.datasources.aggregator import (
    DataAggregator,
    SameSourceAggregator,
    LoadBalancedAggregator,
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
        result = DataSourceResult(
            success=False,
            error="Network error",
            source="test_source"
        )
        assert result.success is False
        assert result.error == "Network error"
        assert result.source == "test_source"

    def test_result_with_metadata(self):
        """测试带元数据的结果"""
        result = DataSourceResult(
            success=True,
            data={"price": 100},
            source="test",
            metadata={"symbol": "AAPL"}
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
# 3. 单元测试 - PortfolioAnalyzer
# ============================================================================

class TestPortfolioAnalyzer:
    """组合分析器测试"""

    def test_empty_analyzer(self):
        """测试空分析器"""
        analyzer = PortfolioAnalyzer()
        assert len(analyzer.positions) == 0
        result = analyzer.analyze()
        assert result.total_value == 0.0
        assert result.total_cost == 0.0
        assert result.total_profit == 0.0

    def test_single_position_profit(self):
        """单持仓盈利测试"""
        analyzer = PortfolioAnalyzer()
        analyzer.add_position(
            symbol="161039",
            asset_type=AssetType.FUND,
            name="测试基金",
            quantity=10000,
            cost=15000.0,
            current_price=1.6
        )
        result = analyzer.analyze()
        # 市值 = 10000 * 1.6 = 16000
        assert result.total_value == 16000.0
        # 盈亏 = 16000 - 15000 = 1000
        assert result.total_profit == 1000.0

    def test_single_position_loss(self):
        """单持仓亏损测试"""
        analyzer = PortfolioAnalyzer()
        analyzer.add_position(
            symbol="161039",
            asset_type=AssetType.FUND,
            name="亏损基金",
            quantity=1000,
            cost=2000.0,
            current_price=1.5
        )
        result = analyzer.analyze()
        # 市值 = 1000 * 1.5 = 1500
        assert result.total_value == 1500.0
        # 盈亏 = 1500 - 2000 = -500
        assert result.total_profit == -500.0

    def test_allocation_calculation(self):
        """资产配置计算测试"""
        analyzer = PortfolioAnalyzer()
        # 基金: 10000 * 1.0 = 10000
        # 股票: 1000 * 10.0 = 10000
        # 总市值: 20000
        # 基金配置 = 10000 / 20000 * 100 = 50%
        # 股票配置 = 10000 / 20000 * 100 = 50%
        analyzer.add_position("F1", AssetType.FUND, "基金1", 10000, 10000.0, 1.0)
        analyzer.add_position("S1", AssetType.STOCK, "股票1", 1000, 5000.0, 10.0)

        result = analyzer.analyze()
        assert result.allocation.fund_weight == pytest.approx(50.0, rel=0.01)
        assert result.allocation.stock_weight == pytest.approx(50.0, rel=0.01)

    def test_multi_asset_allocation(self):
        """多资产配置测试"""
        analyzer = PortfolioAnalyzer()
        # 添加各类型资产
        analyzer.add_position("F1", AssetType.FUND, "基金", 1000, 10000.0, 10.0)
        analyzer.add_position("S1", AssetType.STOCK, "股票", 500, 10000.0, 20.0)
        analyzer.add_position("B1", AssetType.BOND, "债券", 2000, 10000.0, 5.0)
        analyzer.add_position("C1", AssetType.COMMODITY, "商品", 100, 10000.0, 100.0)

        result = analyzer.analyze()
        total_value = 40000.0  # 10000 + 10000 + 10000 + 10000
        assert result.allocation.fund_weight == pytest.approx(25.0, rel=0.01)
        assert result.allocation.stock_weight == pytest.approx(25.0, rel=0.01)
        assert result.allocation.bond_weight == pytest.approx(25.0, rel=0.01)
        assert result.allocation.commodity_weight == pytest.approx(25.0, rel=0.01)

    def test_remove_position(self):
        """测试移除持仓"""
        analyzer = PortfolioAnalyzer()
        analyzer.add_position("F1", AssetType.FUND, "基金1", 1000, 1000.0, 1.0)
        analyzer.add_position("F2", AssetType.FUND, "基金2", 2000, 2000.0, 2.0)

        assert len(analyzer.positions) == 2

        removed = analyzer.remove_position("F1")
        assert removed is True
        assert len(analyzer.positions) == 1
        assert analyzer.get_position("F1") is None

    def test_remove_nonexistent_position(self):
        """测试移除不存在的持仓"""
        analyzer = PortfolioAnalyzer()
        result = analyzer.remove_position("NOTEXIST")
        assert result is False

    def test_update_price(self):
        """测试更新价格"""
        analyzer = PortfolioAnalyzer()
        analyzer.add_position("F1", AssetType.FUND, "基金", 1000, 1000.0, 1.0)

        assert analyzer.get_position("F1").current_price == 1.0

        updated = analyzer.update_price("F1", 1.5)
        assert updated is True
        assert analyzer.get_position("F1").current_price == 1.5

        result = analyzer.analyze()
        assert result.total_value == 1500.0

    def test_update_nonexistent_price(self):
        """测试更新不存在的持仓价格"""
        analyzer = PortfolioAnalyzer()
        result = analyzer.update_price("NOTEXIST", 1.5)
        assert result is False

    def test_get_position(self):
        """测试获取持仓"""
        analyzer = PortfolioAnalyzer()
        analyzer.add_position("F1", AssetType.FUND, "基金1", 1000, 1000.0, 1.0)
        analyzer.add_position("F2", AssetType.FUND, "基金2", 2000, 2000.0, 2.0)

        pos = analyzer.get_position("F1")
        assert pos is not None
        assert pos.symbol == "F1"
        assert pos.name == "基金1"

    def test_get_top_performers(self):
        """测试获取表现最好的持仓"""
        analyzer = PortfolioAnalyzer()
        analyzer.add_position("F1", AssetType.FUND, "盈利基金", 1000, 1000.0, 2.0)  # +100%
        analyzer.add_position("F2", AssetType.FUND, "亏损基金", 1000, 1000.0, 0.5)  # -50%
        analyzer.add_position("F3", AssetType.FUND, "持平基金", 1000, 1000.0, 1.0)  # 0%

        top = analyzer.get_top_performers(2)
        assert len(top) == 2
        assert top[0].symbol == "F1"  # 最高盈利
        assert top[1].symbol == "F3"  # 次高（持平）

    def test_get_worst_performers(self):
        """测试获取表现最差的持仓"""
        analyzer = PortfolioAnalyzer()
        analyzer.add_position("F1", AssetType.FUND, "盈利基金", 1000, 1000.0, 2.0)
        analyzer.add_position("F2", AssetType.FUND, "亏损基金", 1000, 1000.0, 0.5)
        analyzer.add_position("F3", AssetType.FUND, "持平基金", 1000, 1000.0, 1.0)

        worst = analyzer.get_worst_performers(2)
        assert len(worst) == 2
        assert worst[0].symbol == "F2"  # 最大亏损
        assert worst[1].symbol == "F3"  # 次差（持平）

    def test_clear_positions(self):
        """测试清空所有持仓"""
        analyzer = PortfolioAnalyzer()
        analyzer.add_position("F1", AssetType.FUND, "基金1", 1000, 1000.0, 1.0)
        analyzer.add_position("F2", AssetType.FUND, "基金2", 2000, 2000.0, 2.0)

        assert len(analyzer.positions) == 2

        analyzer.clear()
        assert len(analyzer.positions) == 0

    def test_get_risk_metrics(self):
        """测试获取风险指标"""
        analyzer = PortfolioAnalyzer()
        analyzer.add_position("F1", AssetType.FUND, "基金1", 1000, 1000.0, 1.5)

        metrics = analyzer.get_risk_metrics()
        assert metrics["total_value"] == 1500.0
        assert metrics["total_cost"] == 1000.0
        assert metrics["total_profit"] == 500.0
        assert metrics["position_count"] == 1

    def test_get_performance_by_type(self):
        """测试按类型获取表现"""
        analyzer = PortfolioAnalyzer()
        analyzer.add_position("F1", AssetType.FUND, "基金1", 1000, 1000.0, 1.2)
        analyzer.add_position("F2", AssetType.FUND, "基金2", 2000, 2000.0, 1.1)
        analyzer.add_position("S1", AssetType.STOCK, "股票1", 500, 5000.0, 12.0)

        performance = analyzer.get_performance_by_type()

        assert "fund" in performance
        assert "stock" in performance
        assert performance["fund"]["total_value"] == 3400.0  # 1200 + 2200
        assert performance["fund"]["position_count"] == 2


class TestPortfolioPosition:
    """持仓测试"""

    def test_current_value(self):
        """测试当前市值计算"""
        position = PortfolioPosition(
            symbol="F1",
            asset_type=AssetType.FUND,
            name="基金",
            quantity=1000,
            cost=1000.0,
            current_price=1.5
        )
        assert position.current_value == 1500.0

    def test_profit_loss(self):
        """测试盈亏计算"""
        position = PortfolioPosition(
            symbol="F1",
            asset_type=AssetType.FUND,
            name="基金",
            quantity=1000,
            cost=1000.0,
            current_price=1.5
        )
        assert position.profit_loss == 500.0
        assert position.profit_loss_pct == 50.0

    def test_loss_profit_loss_pct(self):
        """测试亏损时盈亏百分比"""
        position = PortfolioPosition(
            symbol="F1",
            asset_type=AssetType.FUND,
            name="基金",
            quantity=1000,
            cost=1000.0,
            current_price=0.8
        )
        assert position.profit_loss == -200.0
        assert position.profit_loss_pct == -20.0

    def test_zero_cost_profit_loss_pct(self):
        """测试零成本时盈亏百分比"""
        position = PortfolioPosition(
            symbol="F1",
            asset_type=AssetType.FUND,
            name="基金",
            quantity=1000,
            cost=0.0,
            current_price=1.0
        )
        assert position.profit_loss_pct == 0.0

    def test_to_dict(self):
        """测试转换为字典"""
        position = PortfolioPosition(
            symbol="F1",
            asset_type=AssetType.FUND,
            name="基金",
            quantity=1000,
            cost=1000.0,
            current_price=1.5
        )
        data = position.to_dict()
        assert data["symbol"] == "F1"
        assert data["asset_type"] == "fund"
        assert data["quantity"] == 1000
        assert data["current_value"] == 1500.0
        assert data["profit_loss"] == 500.0


class TestPortfolioAllocation:
    """资产配置测试"""

    def test_default_allocation(self):
        """测试默认配置"""
        alloc = PortfolioAllocation()
        assert alloc.fund_weight == 0.0
        assert alloc.stock_weight == 0.0

    def test_allocation_normalization(self):
        """测试配置归一化"""
        # 总和不为100%时应该自动归一化
        alloc = PortfolioAllocation(fund_weight=30, stock_weight=30)
        assert alloc.fund_weight == 50.0
        assert alloc.stock_weight == 50.0

    def test_diversification_score(self):
        """测试分散化得分"""
        # 均匀分布（每个权重相等）
        alloc = PortfolioAllocation(
            fund_weight=20,
            stock_weight=20,
            bond_weight=20,
            commodity_weight=20,
            crypto_weight=20
        )
        score = alloc.get_diversification_score()
        # 均匀分布时标准差为0，得分应该为100
        assert score == 100.0

    def test_concentrated_allocation(self):
        """测试集中配置"""
        alloc = PortfolioAllocation(
            fund_weight=90,
            stock_weight=10,
            bond_weight=0,
            commodity_weight=0,
            crypto_weight=0
        )
        score = alloc.get_diversification_score()
        assert score < 30  # 集中配置得分低


# ============================================================================
# 4. 服务测试 (Mock) - SinaStockDataSource
# ============================================================================

class TestSinaStockDataSource:
    """新浪股票数据源测试"""

    @pytest.fixture
    def source(self):
        """创建测试实例"""
        s = SinaStockDataSource(timeout=5.0)
        yield s
        asyncio.get_event_loop().run_until_complete(s.close())

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
        assert source._get_market("600000") == "sh"
        assert source._get_market("688888") == "sh"

    def test_get_market_sz(self):
        """测试深圳市场判断"""
        source = SinaStockDataSource()
        assert source._get_market("000001") == "sz"
        assert source._get_market("300001") == "sz"

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

        with patch.object(source.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await source.fetch("600000")

            assert result.success is True
            assert result.data["code"] == "600000"
            assert result.data["price"] == 9.30

    @pytest.mark.asyncio
    async def test_fetch_with_error(self, source):
        """测试 HTTP 错误响应"""
        import httpx

        with patch.object(source.client, 'get', new_callable=AsyncMock) as mock_get:
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
            'currentPrice': 150.0,
            'regularMarketPrice': 150.0,
            'regularMarketOpen': 148.0,
            'regularMarketDayHigh': 152.0,
            'regularMarketDayLow': 147.0,
            'regularMarketChange': 2.0,
            'regularMarketChangePercent': 1.5,
            'regularMarketVolume': 1000000,
            'shortName': 'Test Stock',
            'exchange': 'NASDAQ',
            'currency': 'USD'
        }

        with patch.dict('sys.modules', {'yfinance': MagicMock()}):
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
        source._cache["AAPL"] = {
            "symbol": "AAPL",
            "price": 150.0,
            "_cache_time": time.time()
        }

        result = await source.fetch("AAPL")

        assert result.success is True
        assert result.metadata["from_cache"] is True


# ============================================================================
# 6. 服务测试 (Mock) - BinanceCryptoSource
# ============================================================================

class TestBinanceCryptoSource:
    """Binance 加密货币数据源测试"""

    @pytest.fixture
    def source(self):
        """创建测试实例"""
        s = BinanceCryptoSource(timeout=5.0)
        yield s
        asyncio.get_event_loop().run_until_complete(s.close())

    def test_init(self, source):
        """测试初始化"""
        assert source.name == "binance_crypto"
        assert source.source_type == DataSourceType.CRYPTO
        assert source.timeout == 5.0
        assert "BTCUSDT" in source.common_symbols

    def test_get_status(self, source):
        """测试状态获取"""
        status = source.get_status()
        assert status["name"] == "binance_crypto"
        assert status["type"] == "crypto"
        assert "common_symbols" in status

    @pytest.mark.asyncio
    async def test_fetch_with_mock(self, source):
        """测试 Mock HTTP 响应"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "symbol": "BTCUSDT",
            "lastPrice": "50000.00",
            "priceChange": "500.00",
            "priceChangePercent": "1.00",
            "highPrice": "51000.00",
            "lowPrice": "49000.00",
            "volume": "1000.00",
            "quoteVolume": "50000000.00"
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(source.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await source.fetch("BTCUSDT")

            assert result.success is True
            assert result.data["symbol"] == "BTCUSDT"
            assert result.data["price"] == 50000.0

    @pytest.mark.asyncio
    async def test_fetch_batch_with_mock(self, source):
        """测试批量获取"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "symbol": "BTCUSDT",
            "lastPrice": "50000.00",
            "priceChange": "500.00",
            "priceChangePercent": "1.00",
            "highPrice": "51000.00",
            "lowPrice": "49000.00",
            "volume": "1000.00",
            "quoteVolume": "50000000.00"
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(source.client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            results = await source.fetch_batch(["BTCUSDT", "ETHUSDT"])

            assert len(results) == 2
            assert results[0].success is True


# ============================================================================
# 7. 服务测试 (Mock) - SameSourceAggregator
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
        primary.fetch = AsyncMock(return_value=DataSourceResult(
            success=True,
            data={"price": 100},
            source="primary"
        ))

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
        primary.fetch = AsyncMock(return_value=DataSourceResult(
            success=False,
            error="Primary failed",
            source="primary"
        ))

        secondary = MagicMock(spec=DataSource)
        secondary.name = "secondary"
        secondary.source_type = DataSourceType.STOCK
        secondary.fetch = AsyncMock(return_value=DataSourceResult(
            success=True,
            data={"price": 200},
            source="secondary"
        ))

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
        source1.fetch = AsyncMock(return_value=DataSourceResult(
            success=False,
            error="Failed",
            source="source1"
        ))

        source2 = MagicMock(spec=DataSource)
        source2.name = "source2"
        source2.source_type = DataSourceType.STOCK
        source2.fetch = AsyncMock(return_value=DataSourceResult(
            success=False,
            error="Failed",
            source="source2"
        ))

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

        with patch.object(sina.client, 'get', new_callable=AsyncMock) as mock_get:
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
            message="Test error",
            source_type=DataSourceType.STOCK,
            details={"key": "value"}
        )
        assert error.message == "Test error"
        assert error.source_type == DataSourceType.STOCK
        assert error.details["key"] == "value"

    def test_network_error(self):
        """测试网络异常"""
        error = NetworkError(
            message="Connection failed",
            source_type=DataSourceType.STOCK
        )
        assert isinstance(error, DataSourceError)
        assert "Connection failed" in error.message

    def test_data_parse_error(self):
        """测试数据解析异常"""
        error = DataParseError(
            message="Parse failed",
            source_type=DataSourceType.STOCK
        )
        assert isinstance(error, DataSourceError)


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
