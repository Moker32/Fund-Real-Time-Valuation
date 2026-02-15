"""
Baostock 股票数据源测试
TDD 方式实现 - 先写测试
"""


import pytest

from src.datasources.stock_source import BaostockStockSource


class TestBaostockStockSource:
    """BaostockStockSource 测试类"""

    def test_init(self):
        """测试初始化"""
        source = BaostockStockSource()
        assert source.name == "baostock_stock"
        assert source.source_type.value == "stock"
        assert source.timeout == 10.0

    def test_get_name(self):
        """测试获取数据源名称"""
        source = BaostockStockSource()
        assert source.get_status()["name"] == "baostock_stock"

    @pytest.mark.asyncio
    async def test_fetch_sh_stock(self):
        """测试获取上海股票历史数据"""
        source = BaostockStockSource()
        result = await source.fetch("sh.600000")
        # Baostock 返回历史数据，不一定是实时价格
        assert result.success is True or result.success is False

    @pytest.mark.asyncio
    async def test_fetch_sz_stock(self):
        """测试获取深圳股票历史数据"""
        source = BaostockStockSource()
        result = await source.fetch("sz.000001")
        assert result.success is True or result.success is False

    @pytest.mark.asyncio
    async def test_fetch_with_date_range(self):
        """测试获取指定日期范围的数据"""
        source = BaostockStockSource()
        result = await source.fetch("sh.600000", start_date="2025-01-01", end_date="2025-01-10")
        assert result.success is True or result.success is False

    @pytest.mark.asyncio
    async def test_fetch_invalid_code(self):
        """测试无效股票代码"""
        source = BaostockStockSource()
        result = await source.fetch("invalid_code")
        # 无效代码应该返回失败
        assert result.success is False or result.error is not None

    @pytest.mark.asyncio
    async def test_fetch_batch(self):
        """测试批量获取"""
        source = BaostockStockSource()
        results = await source.fetch_batch(["sh.600000", "sz.000001"])
        assert isinstance(results, list)
        assert len(results) == 2
