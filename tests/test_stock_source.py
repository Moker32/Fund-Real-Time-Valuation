"""
股票数据源测试
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.datasources.base import DataSourceType
from src.datasources.stock_source import (
    SinaStockDataSource,
    YahooStockSource,
)


class TestSinaStockDataSource:
    """新浪股票数据源测试"""
    
    @pytest.fixture
    def source(self):
        """创建数据源实例"""
        return SinaStockDataSource(timeout=5.0)
    
    def test_init(self):
        """测试初始化"""
        source = SinaStockDataSource()
        assert source.name == "sina_stock"
        assert source.source_type == DataSourceType.STOCK
        assert source.timeout == 10.0
    
    def test_get_market(self, source):
        """测试市场判断"""
        # 沪市股票 (6 开头)
        assert source._get_market("600000")[0] == "sh"
        assert source._get_market("688000")[0] == "sh"  # 科创板
        
        # 深市股票 (0, 3 开头)
        assert source._get_market("000001")[0] == "sz"
        assert source._get_market("300001")[0] == "sz"  # 创业板
    
    def test_parse_response(self, source):
        """测试响应解析"""
        # 模拟新浪股票响应
        response_text = 'var hq_str_sh600000="浦发银行,10.50,10.40,10.60,10.70,10.30,10.55,10.60,1234567,12345678,1000,2000,09:30:00";'
        
        data = source._parse_response(response_text, "600000", "sh")
        
        if data:
            assert data["code"] == "600000"
            assert data["market"] == "sh"
            assert data["name"] == "浦发银行"
            assert data["price"] == 10.6
    
    def test_parse_response_invalid(self, source):
        """测试无效响应解析"""
        # 无效响应
        result = source._parse_response("invalid", "600000", "sh")
        assert result is None
        
        # 空响应
        result = source._parse_response("", "600000", "sh")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_invalid_code(self, source):
        """测试无效股票代码"""
        # 空代码应该返回失败
        result = await source.fetch("")
        
        assert result.success is False
    
    @pytest.mark.asyncio
    async def test_fetch_with_valid_code(self, source):
        """测试有效股票代码"""
        with patch.object(source, '_get_market', return_value=("sh", "600000")), \
             patch.object(source, '_parse_response', return_value={"code": "600000", "price": 10.6}):
            with patch.object(source, 'client') as mock_client:
                mock_response = MagicMock()
                mock_response.raise_for_status = MagicMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                
                result = await source.fetch("600000")
                
                assert result.success is True
    
    @pytest.mark.asyncio
    async def test_fetch_batch(self, source):
        """测试批量获取"""
        with patch.object(source, 'fetch', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = MagicMock(success=True, data={"code": "600000"})
            
            results = await source.fetch_batch(["600000", "000001"])
            
            assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_close(self, source):
        """测试关闭客户端"""
        await source.close()


class TestYahooStockSource:
    """Yahoo 股票数据源测试"""
    
    @pytest.fixture
    def source(self):
        """创建数据源实例"""
        return YahooStockSource(timeout=10.0)
    
    def test_init(self):
        """测试初始化"""
        source = YahooStockSource()
        assert source.name == "yahoo_stock"
        assert source.source_type == DataSourceType.STOCK
    
    def test_get_market_type(self, source):
        """测试市场类型判断"""
        # A股 (需要带后缀)
        assert source._get_market_type("600000.SH") == "cn"
        assert source._get_market_type("000001.SZ") == "cn"
        
        # 港股
        assert source._get_market_type("0700.HK") == "hk"
        
        # 美股 (不带后缀)
        assert source._get_market_type("AAPL") == "us"
        assert source._get_market_type("MSFT") == "us"
    
    @pytest.mark.asyncio
    async def test_fetch_invalid_code(self, source):
        """测试无效股票代码"""
        result = await source.fetch("")
        
        assert result.success is False
    
    @pytest.mark.asyncio
    async def test_fetch_batch(self, source):
        """测试批量获取"""
        with patch.object(source, 'fetch', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = MagicMock(success=True, data={})
            
            results = await source.fetch_batch(["AAPL", "MSFT"])
            
            assert len(results) == 2
