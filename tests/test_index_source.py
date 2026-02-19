"""
全球市场指数数据源测试

测试:
1. TencentIndexSource - 腾讯财经指数
2. YahooIndexSource - Yahoo Finance 指数
3. HybridIndexSource - 全球指数聚合
"""

from unittest.mock import AsyncMock

import pytest

from src.datasources.base import DataSourceType
from src.datasources.index_source import (
    INDEX_REGIONS,
    INDEX_TICKERS,
    HybridIndexSource,
    TencentIndexSource,
    YahooIndexSource,
    uses_tencent,
)


class TestIndexSourceConstants:
    """测试指数源常量"""

    def test_index_tickers_not_empty(self):
        """测试指数代码映射不为空"""
        assert len(INDEX_TICKERS) > 0

    def test_uses_tencent(self):
        """测试腾讯财经判断"""
        # A股使用腾讯
        assert uses_tencent("shanghai") is True
        assert uses_tencent("shenzhen") is True
        assert uses_tencent("hs300") is True
        
        # 港股使用腾讯
        assert uses_tencent("hang_seng") is True
        
        # 美股使用腾讯
        assert uses_tencent("dow_jones") is True
        assert uses_tencent("nasdaq") is True
        
        # 日经使用 Yahoo
        assert uses_tencent("nikkei225") is False
        
        # 欧洲使用 Yahoo
        assert uses_tencent("dax") is False
        assert uses_tencent("ftse") is False

    def test_index_regions(self):
        """测试指数区域映射"""
        assert INDEX_REGIONS["shanghai"] == "china"
        assert INDEX_REGIONS["hang_seng"] == "hk"
        assert INDEX_REGIONS["dow_jones"] == "america"
        assert INDEX_REGIONS["nikkei225"] == "asia"
        assert INDEX_REGIONS["dax"] == "europe"


class TestTencentIndexSource:
    """测试腾讯财经指数数据源"""

    def test_init(self):
        """测试初始化"""
        ds = TencentIndexSource(timeout=10.0)
        
        assert ds.name == "tencent_index"
        assert ds.source_type == DataSourceType.STOCK  # 复用 STOCK 类型
        assert ds.timeout == 10.0

    def test_init_default_timeout(self):
        """测试默认超时时间"""
        ds = TencentIndexSource()
        assert ds.timeout == 10.0


class TestYahooIndexSource:
    """测试 Yahoo Finance 指数数据源"""

    def test_init(self):
        """测试初始化"""
        ds = YahooIndexSource(timeout=15.0)
        
        assert ds.name == "yfinance_index"
        assert ds.source_type == DataSourceType.STOCK  # 复用 STOCK 类型
        assert ds.timeout == 15.0

    def test_init_default_timeout(self):
        """测试默认超时时间"""
        ds = YahooIndexSource()
        assert ds.timeout == 30.0


class TestHybridIndexSource:
    """测试混合指数数据源"""

    def test_init(self):
        """测试初始化"""
        ds = HybridIndexSource()
        
        assert ds.name == "hybrid_index"
        assert ds.source_type == DataSourceType.STOCK  # 复用 STOCK 类型
        assert ds._tencent is not None
        assert ds._yahoo is not None

    @pytest.mark.asyncio
    async def test_fetch_tencent_index(self):
        """测试获取腾讯指数"""
        ds = HybridIndexSource()
        
        # Mock 腾讯数据源
        from src.datasources.base import DataSourceResult
        
        mock_result = DataSourceResult(
            success=True,
            data=[{"name": "shanghai", "price": 3500}],
            timestamp=1000.0,
            source="tencent"
        )
        ds._tencent.fetch = AsyncMock(return_value=mock_result)
        
        result = await ds.fetch("shanghai")
        
        assert result.success is True

    @pytest.mark.asyncio
    async def test_fetch_yahoo_index(self):
        """测试获取 Yahoo 指数"""
        ds = HybridIndexSource()
        
        from src.datasources.base import DataSourceResult
        
        mock_result = DataSourceResult(
            success=True,
            data=[{"name": "nikkei225", "price": 35000}],
            timestamp=1000.0,
            source="yahoo"
        )
        ds._yahoo.fetch = AsyncMock(return_value=mock_result)
        
        result = await ds.fetch("nikkei225")
        
        assert result.success is True

    @pytest.mark.asyncio
    async def test_fetch_batch(self):
        """测试批量获取"""
        ds = HybridIndexSource()
        
        from src.datasources.base import DataSourceResult
        
        mock_result = DataSourceResult(
            success=True,
            data=[{}],
            timestamp=1000.0,
            source="test"
        )
        ds._tencent.fetch = AsyncMock(return_value=mock_result)
        
        results = await ds.fetch_batch(["shanghai", "shenzhen"])
        
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_close(self):
        """测试关闭"""
        ds = HybridIndexSource()
        
        # 应该不会抛出异常
        await ds.close()
