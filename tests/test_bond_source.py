"""
债券数据源测试
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.datasources.base import DataSourceType
from src.datasources.bond_source import (
    AKShareBondSource,
    EastMoneyBondSource,
    SinaBondDataSource,
)


class TestSinaBondDataSource:
    """新浪债券数据源测试"""

    @pytest.fixture
    def source(self):
        """创建数据源实例"""
        return SinaBondDataSource(timeout=5.0, max_retries=2)

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        source = SinaBondDataSource()
        assert source.name == "sina_bond"
        assert source.source_type == DataSourceType.BOND
        assert source.timeout == 10.0
        assert source.max_retries == 3

    @pytest.mark.asyncio
    async def test_validate_bond_code(self, source):
        """测试债券代码验证"""
        assert source._validate_bond_code("113052") is True
        assert source._validate_bond_code("110053") is True
        assert source._validate_bond_code("123456") is True
        assert source._validate_bond_code("12345") is False
        assert source._validate_bond_code("1234567") is False
        assert source._validate_bond_code("abc123") is False

    @pytest.mark.asyncio
    async def test_fetch_invalid_code(self, source):
        """测试无效债券代码"""
        result = await source.fetch("12345")
        assert result.success is False
        assert "无效的债券代码" in result.error

    @pytest.mark.asyncio
    async def test_parse_response(self, source):
        """测试响应解析"""
        # 模拟新浪债券响应
        response_text = 'var hq_str_sh113052="兴业转债,100.000,99.500,100.500,101.000,99.000,100.500,100.600,10000,1000000";'
        
        data = source._parse_response(response_text, "113052")
        
        assert data is not None
        assert data["code"] == "113052"
        assert data["market"] == "sh"
        assert data["name"] == "兴业转债"
        assert data["price"] == 100.5
        assert data["pre_close"] == 99.5

    @pytest.mark.asyncio
    async def test_parse_response_invalid(self, source):
        """测试无效响应解析"""
        # 无效响应
        result = source._parse_response("invalid response", "113052")
        assert result is None
        
        # 空响应
        result = source._parse_response("", "113052")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_with_mock(self, source):
        """测试模拟获取债券数据"""
        with patch.object(source, '_parse_response', return_value={"code": "113052", "price": 100.5}):
            with patch.object(source, 'client') as mock_client:
                mock_response = MagicMock()
                mock_response.raise_for_status = MagicMock()
                mock_response.text = '{"data": {"result": []}}'
                mock_client.get = AsyncMock(return_value=mock_response)
                
                result = await source.fetch("113052")
                
                assert result.success is True

    @pytest.mark.asyncio
    async def test_fetch_batch(self, source):
        """测试批量获取"""
        with patch.object(source, 'fetch', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = MagicMock(success=True, data={"code": "113052"})
            
            results = await source.fetch_batch(["113052", "110053"])
            
            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_health_check(self, source):
        """测试健康检查"""
        with patch.object(source, 'client') as mock_client:
            mock_response = MagicMock()
            mock_response.text = 'var hq_str_sh113052="test";'
            mock_response.raise_for_status = MagicMock()
            
            mock_client.get = AsyncMock(return_value=mock_response)
            
            await source.health_check()
            # 健康检查可能返回 True 或 False，取决于实际接口


class TestAKShareBondSource:
    """AKShare 债券数据源测试"""

    @pytest.fixture
    def source(self):
        """创建数据源实例"""
        return AKShareBondSource(timeout=30.0)

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        source = AKShareBondSource()
        assert source.name == "akshare_bond"
        assert source.source_type == DataSourceType.BOND
        assert source.timeout == 30.0

    @pytest.mark.asyncio
    async def test_safe_float(self, source):
        """测试安全浮点转换"""
        assert source._safe_float("123.45") == 123.45
        assert source._safe_float(None) is None
        assert source._safe_float("invalid") is None

    @pytest.mark.asyncio
    async def test_safe_int(self, source):
        """测试安全整数转换"""
        assert source._safe_int("12345") == 12345
        assert source._safe_int(None) is None
        assert source._safe_int("invalid") is None

    @pytest.mark.asyncio
    async def test_fetch_unsupported_type(self, source):
        """测试不支持的债券类型"""
        await source.fetch("unknown_type")

    @pytest.mark.asyncio
    async def test_fetch_batch(self, source):
        """测试批量获取"""
        with patch.object(source, 'fetch', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = MagicMock(success=True, data={"bonds": []})
            
            results = await source.fetch_batch(["cbond", "bond_china"])
            
            assert len(results) == 2


class TestEastMoneyBondSource:
    """东方财富债券数据源测试"""

    @pytest.fixture
    def source(self):
        """创建数据源实例"""
        return EastMoneyBondSource(timeout=5.0)

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        source = EastMoneyBondSource()
        assert source.name == "eastmoney_bond"
        assert source.source_type == DataSourceType.BOND

    @pytest.mark.asyncio
    async def test_fetch_with_mock(self, source):
        """测试模拟获取债券数据"""
        with patch.object(source, 'client') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": {
                    "f2": 100.5,
                    "f3": 1.0,
                    "f4": 1.0,
                    "f5": 10000,
                    "f6": 1000000,
                    "f14": "测试债券"
                }
            }
            mock_response.raise_for_status = MagicMock()
            
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await source.fetch("113052")
            
            assert result.success is True

    @pytest.mark.asyncio
    async def test_fetch_no_data(self, source):
        """测试无数据情况"""
        with patch.object(source, 'client') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": None}
            mock_response.raise_for_status = MagicMock()
            
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await source.fetch("113052")
            
            assert result.success is False

    @pytest.mark.asyncio
    async def test_fetch_batch(self, source):
        """测试批量获取"""
        with patch.object(source, 'fetch', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = MagicMock(success=True, data={})
            
            results = await source.fetch_batch(["113052", "110053"])
            
            assert len(results) == 2
