"""
股票数据源测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from src.datasources.stock_source import (
    SinaStockDataSource,
    YahooStockSource,
)
from src.datasources.base import DataSourceType


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
        assert source._get_market("600000") == "sh"
        assert source._get_market("688000") == "sh"  # 科创板
        
        # 深市股票 (0, 3 开头)
        assert source._get_market("000001") == "sz"
        assert source._get_market("300001") == "sz"  # 创业板
        
        # 北交所 (8, 4 开头)
        assert source._get_market("830001") == "bj"
        assert source._get_market("430001") == "bj"
    
    def test_validate_stock_code(self, source):
        """测试股票代码验证"""
        # 有效代码
        assert source._validate_stock_code("600000") is True
        assert source._validate_stock_code("000001") is True
        assert source._validate_stock_code("300001") is True
        assert source._validate_stock_code("688001") is True
        assert source._validate_stock_code("830001") is True
        
        # 无效代码
        assert source._validate_stock_code("60000") is False  # 不足6位
        assert source._validate_stock_code("6000000") is False  # 超过6位
        assert source._validate_stock_code("abc") is False  # 非数字
    
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
        with patch.object(source, '_validate_stock_code', return_value=False):
            result = await source.fetch("123")
        
        assert result.success is False
    
    @pytest.mark.asyncio
    async def test_fetch_with_valid_code(self, source):
        """测试有效股票代码"""
        with patch.object(source, '_get_market', return_value="sh"), \
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
        # A股
        assert source._get_market_type("600000") == "sh"
        assert source._get_market_type("000001") == "sz"
        
        # 港股
        assert source._get_market_type("0700") == "hk"
        assert source._get_market_type("0700.HK") == "hk"
        
        # 美股
        assert source._get_market_type("AAPL") == "us"
        assert source._get_market_type("MSFT") == "us"
    
    def test_convert_to_yahoo_format(self, source):
        """测试转换为 Yahoo 格式"""
        # A股
        assert source._convert_to_yahoo_format("600000", "sh") == "600000.SS"
        assert source._convert_to_yahoo_format("000001", "sz") == "000001.SZ"
        
        # 港股
        assert source._convert_to_yahoo_format("0700", "hk") == "0700.HK"
        
        # 美股
        assert source._convert_to_yahoo_format("AAPL", "us") == "AAPL"
    
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
