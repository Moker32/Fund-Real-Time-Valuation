"""
商品数据源测试
测试 YFinance 和 AKShare 商品数据源
"""

import pytest
import asyncio
from src.datasources.commodity_source import (
    YFinanceCommoditySource,
    AKShareCommoditySource,
)


class TestYFinanceCommoditySource:
    """YFinance 商品数据源测试"""

    @pytest.fixture
    def source(self):
        """创建数据源实例"""
        return YFinanceCommoditySource()

    @pytest.mark.asyncio
    async def test_commodity_tickers(self, source):
        """测试商品 ticker 配置"""
        # 验证核心商品 ticker 存在
        assert "gold" in source.COMMODITY_TICKERS
        assert "wti" in source.COMMODITY_TICKERS
        assert "brent" in source.COMMODITY_TICKERS
        assert "silver" in source.COMMODITY_TICKERS

    @pytest.mark.asyncio
    async def test_reserved_commodities(self, source):
        """测试预留商品 ticker"""
        # 验证贵金属预留
        assert "platinum" in source.COMMODITY_TICKERS  # 铂金 PT=F
        assert "palladium" in source.COMMODITY_TICKERS  # 钯金 PA=F

        # 验证基本金属预留
        assert "copper" in source.COMMODITY_TICKERS  # 铜 HG=F
        assert "aluminum" in source.COMMODITY_TICKERS  # 铝 AL=f
        assert "zinc" in source.COMMODITY_TICKERS  # 锌 ZN=f
        assert "nickel" in source.COMMODITY_TICKERS  # 镍 NI=f

    @pytest.mark.asyncio
    async def test_commodity_names(self, source):
        """测试商品名称映射"""
        assert source._get_name("gold") == "黄金 (COMEX)"
        assert source._get_name("wti") == "WTI原油"
        assert source._get_name("platinum") == "铂金"
        assert source._get_name("palladium") == "钯金"
        assert source._get_name("copper") == "铜"
        assert source._get_name("aluminum") == "铝"

    @pytest.mark.asyncio
    async def test_get_status(self, source):
        """测试状态获取"""
        status = source.get_status()

        assert status["name"] == "yfinance_commodity"
        assert status["type"] == "commodity"
        assert "supported_commodities" in status
        assert "reserved_commodities" in status
        # 验证预留商品在列表中
        reserved = status.get("reserved_commodities", [])
        assert "platinum" in reserved
        assert "copper" in reserved

    @pytest.mark.asyncio
    async def test_fetch_gold(self, source):
        """测试获取黄金数据"""
        result = await source.fetch("gold")

        # 由于是真实API调用，结果可能是成功或失败
        assert result.source == "yfinance_commodity"
        # 如果成功应该有数据
        if result.success:
            assert result.data is not None
            assert "price" in result.data
        else:
            # 失败时应该有错误信息
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_fetch_invalid_type(self, source):
        """测试获取不支持的商品类型"""
        result = await source.fetch("invalid_commodity")

        assert result.success is False
        assert "不支持" in result.error


class TestAKShareCommoditySource:
    """AKShare 商品数据源测试"""

    @pytest.fixture
    def source(self):
        """创建数据源实例"""
        return AKShareCommoditySource()

    @pytest.mark.asyncio
    async def test_fetch_gold_cny(self, source):
        """测试获取国内黄金"""
        result = await source.fetch("gold_cny")

        assert result.source == "akshare_commodity"
        # 如果 akshare 安装正确，应该能获取数据
        if result.success:
            assert result.data is not None
            assert result.data.get("commodity") == "gold_cny"
        else:
            # 如果失败，可能是 akshare 未安装、网络问题或 SSL 错误
            assert "akshare" in result.error.lower() or "失败" in result.error or "SSL" in result.error or "Connection" in result.error

    @pytest.mark.asyncio
    async def test_invalid_commodity_type(self, source):
        """测试不支持的商品类型"""
        result = await source.fetch("invalid_type")

        assert result.success is False
        assert "不支持" in result.error


class TestCommodityTickerMapping:
    """商品 ticker 映射测试"""

    def test_ticker_values(self):
        """验证 ticker 值正确性"""
        tickers = YFinanceCommoditySource.COMMODITY_TICKERS

        # 核心商品
        assert tickers["gold"] == "GC=F"
        assert tickers["wti"] == "CL=F"
        assert tickers["brent"] == "BZ=F"
        assert tickers["silver"] == "SI=F"

        # 贵金属 (预留)
        assert tickers["platinum"] == "PT=F"
        assert tickers["palladium"] == "PA=F"

        # 基本金属 (预留)
        assert tickers["copper"] == "HG=F"
        assert tickers["aluminum"] == "AL=f"
        assert tickers["zinc"] == "ZN=f"
        assert tickers["nickel"] == "NI=f"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
