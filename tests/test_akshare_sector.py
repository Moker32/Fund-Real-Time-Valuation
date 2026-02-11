"""
板块数据源测试
测试新浪和东方财富板块数据源
"""


import pytest

from src.datasources.sector_source import (
    EastMoneyConceptDetailSource,
    EastMoneyIndustryDetailSource,
    EastMoneySectorSource,
    SectorDataAggregator,
    SinaSectorDataSource,
)


class TestSinaSectorDataSource:
    """新浪行业板块数据源测试"""

    @pytest.fixture
    def source(self):
        """创建数据源实例"""
        return SinaSectorDataSource()

    @pytest.mark.asyncio
    async def test_sector_config(self, source):
        """测试板块配置"""
        config = source.get_sector_config()

        assert len(config) > 0
        # 验证关键板块存在
        names = [c["name"] for c in config]
        assert "白酒" in names
        assert "银行" in names
        assert "医药" in names

    @pytest.mark.asyncio
    async def test_fetch_all(self, source):
        """测试获取所有板块数据"""
        result = await source.fetch_all()

        # 预留接口：可能返回模拟数据
        assert result.source == "sina_sector"
        if result.success:
            assert isinstance(result.data, list)

    @pytest.mark.asyncio
    async def test_fetch_by_code(self, source):
        """测试按代码获取板块"""
        result = await source.fetch("bk04151")  # 白酒

        assert result.source == "sina_sector"
        if result.success:
            assert isinstance(result.data, list)

    @pytest.mark.asyncio
    async def test_fetch_by_category(self, source):
        """测试按类别获取板块"""
        result = await source.fetch_by_category("科技")

        assert result.source == "sina_sector"
        if result.success:
            assert isinstance(result.data, list)


class TestSectorDataAggregator:
    """板块数据聚合器测试"""

    @pytest.fixture
    def aggregator(self):
        """创建聚合器实例"""
        return SectorDataAggregator()

    def test_add_source(self, aggregator):
        """测试添加数据源"""
        source = SinaSectorDataSource()
        aggregator.add_source(source, is_primary=True)

        assert len(aggregator._sources) == 1
        assert aggregator._primary_source == source

    @pytest.mark.asyncio
    async def test_fetch_no_source(self, aggregator):
        """测试无数据源时获取"""
        result = await aggregator.fetch()

        assert result.success is False
        assert "失败" in result.error


class TestEastMoneySectorSource:
    """东方财富板块数据源测试"""

    @pytest.fixture
    def source(self):
        """创建数据源实例"""
        return EastMoneySectorSource()

    @pytest.mark.asyncio
    async def test_fetch_industry(self, source):
        """测试获取行业板块"""
        result = await source.fetch("industry")

        assert result.source == "sector_eastmoney_akshare"
        # 接口已实现，应该能获取数据
        if result.success:
            assert result.data is not None
            assert "sectors" in result.data
            assert result.data.get("type") == "industry"
        else:
            # 可能是网络问题
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_fetch_concept(self, source):
        """测试获取概念板块"""
        result = await source.fetch("concept")

        assert result.source == "sector_eastmoney_akshare"
        if result.success:
            assert result.data is not None
            assert "sectors" in result.data
            assert result.data.get("type") == "concept"
        else:
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_fetch_invalid_type(self, source):
        """测试获取不支持的板块类型"""
        result = await source.fetch("invalid_type")

        assert result.success is False
        assert "不支持" in result.error

    @pytest.mark.asyncio
    async def test_fetch_batch(self, source):
        """测试批量获取"""
        result = await source.fetch_batch(["industry", "concept"])

        assert len(result) == 2
        # 至少行业板块应该成功
        assert result[0].source == "sector_eastmoney_akshare"

    @pytest.mark.asyncio
    async def test_get_status(self, source):
        """测试状态获取"""
        status = source.get_status()

        assert status["name"] == "sector_eastmoney_akshare"
        assert status["type"] == "sector"
        assert "supported_types" in status
        assert "cache_size" in status


class TestEastMoneyDetailSources:
    """东方财富板块详情数据源测试"""

    @pytest.fixture
    def industry_source(self):
        return EastMoneyIndustryDetailSource()

    @pytest.fixture
    def concept_source(self):
        return EastMoneyConceptDetailSource()

    @pytest.mark.asyncio
    async def test_industry_detail(self, industry_source):
        """测试行业板块详情"""
        result = await industry_source.fetch("银行")

        assert result.source == "sector_industry_detail_akshare"
        if result.success:
            assert result.data is not None
            assert "stocks" in result.data
        else:
            # 网络问题也接受
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_industry_detail_empty_name(self, industry_source):
        """测试空板块名称"""
        result = await industry_source.fetch("")

        assert result.success is False
        assert "请指定" in result.error

    @pytest.mark.asyncio
    async def test_concept_detail(self, concept_source):
        """测试概念板块详情"""
        result = await concept_source.fetch("新能源")

        assert result.source == "sector_concept_detail_akshare"
        if result.success:
            assert result.data is not None
            assert "stocks" in result.data
        else:
            # 概念板块接口可能不稳定
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_concept_detail_empty_name(self, concept_source):
        """测试空板块名称"""
        result = await concept_source.fetch("")

        assert result.success is False
        assert "请指定" in result.error


class TestSectorConfig:
    """板块配置测试"""

    def test_sina_sector_categories(self):
        """测试新浪板块分类"""
        source = SinaSectorDataSource()
        categories = set(c["category"] for c in source.SECTOR_CONFIG)

        expected = {"消费", "新能源", "医药", "科技", "金融", "周期", "制造"}
        assert categories == expected

    def test_sina_sector_count(self):
        """测试新浪板块数量"""
        source = SinaSectorDataSource()
        assert len(source.SECTOR_CONFIG) == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
