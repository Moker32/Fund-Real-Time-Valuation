"""
加密货币数据源测试
"""

import asyncio
import sys
from pathlib import Path

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.datasources.base import DataSourceResult, DataSourceType
from src.datasources.crypto_source import (
    BinanceCryptoSource,
    CoinGeckoCryptoSource,
    CryptoAggregator,
)


class TestBinanceCryptoSource:
    """BinanceCryptoSource 测试类"""

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
    async def test_fetch_invalid_symbol(self, source):
        """测试无效交易对"""
        result = await source.fetch("INVALID")
        assert result.success is False
        assert result.source == "binance_crypto"


class TestCoinGeckoCryptoSource:
    """CoinGeckoCryptoSource 测试类"""

    @pytest.fixture
    def source(self):
        """创建测试实例"""
        s = CoinGeckoCryptoSource(timeout=10.0)
        yield s
        asyncio.get_event_loop().run_until_complete(s.close())

    def test_init(self, source):
        """测试初始化"""
        assert source.name == "coingecko_crypto"
        assert source.source_type == DataSourceType.CRYPTO
        assert source.timeout == 10.0
        assert "bitcoin" in source.COIN_IDS

    def test_get_status(self, source):
        """测试状态获取"""
        status = source.get_status()
        assert status["name"] == "coingecko_crypto"
        assert status["type"] == "crypto"
        assert "cache_size" in status
        assert "supported_coins" in status

    def test_get_name(self, source):
        """测试名称获取"""
        assert source._get_name("bitcoin") == "Bitcoin"
        assert source._get_name("ethereum") == "Ethereum"
        assert source._get_name("unknown") == "Unknown"

    def test_cache_operations(self, source):
        """测试缓存操作"""
        # 测试缓存有效性检查
        assert source._is_cache_valid("test") is False

        # 添加缓存数据
        source._cache["test"] = {
            "_cache_time": 0,  # 过期
        }
        assert source._is_cache_valid("test") is False

        # 清除缓存
        source.clear_cache()
        assert len(source._cache) == 0

    @pytest.mark.asyncio
    async def test_fetch_invalid_coin(self, source):
        """测试无效币种"""
        result = await source.fetch("invalid_coin_xyz")
        assert result.success is False
        assert "未找到币种" in result.error


class TestCryptoAggregator:
    """CryptoAggregator 测试类"""

    @pytest.fixture
    def aggregator(self):
        """创建测试聚合器"""
        agg = CryptoAggregator(timeout=15.0)
        binance = BinanceCryptoSource(timeout=5.0)
        coingecko = CoinGeckoCryptoSource(timeout=10.0)
        agg.add_source(binance, is_primary=True)
        agg.add_source(coingecko)
        yield agg
        asyncio.get_event_loop().run_until_complete(agg.close())

    def test_init(self, aggregator):
        """测试初始化"""
        assert aggregator.name == "crypto_aggregator"
        assert aggregator.source_type == DataSourceType.CRYPTO
        assert len(aggregator._sources) == 2

    def test_add_source(self):
        """测试添加数据源"""
        agg = CryptoAggregator()
        source1 = BinanceCryptoSource()
        source2 = CoinGeckoCryptoSource()

        agg.add_source(source1, is_primary=False)
        agg.add_source(source2, is_primary=True)

        assert agg._primary_source == source2
        assert len(agg._sources) == 2

    def test_get_status(self, aggregator):
        """测试状态获取"""
        status = aggregator.get_status()
        assert status["source_count"] == 2
        assert status["primary_source"] == "binance_crypto"
        assert len(status["sources"]) == 2


class TestDataSourceResult:
    """DataSourceResult 测试类"""

    def test_success_result(self):
        """测试成功结果"""
        result = DataSourceResult(
            success=True,
            data={"price": 100},
            source="test"
        )
        assert result.success is True
        assert result.data["price"] == 100
        assert result.timestamp > 0

    def test_error_result(self):
        """测试错误结果"""
        result = DataSourceResult(
            success=False,
            error="Test error",
            source="test"
        )
        assert result.success is False
        assert result.error == "Test error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
