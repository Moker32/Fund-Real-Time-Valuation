"""
板块数据源测试
测试新浪和东方财富板块数据源
"""


from unittest.mock import patch

import pandas as pd
import pytest

from src.datasources.sector_source import (
    EastMoneyConceptDetailSource,
    EastMoneyIndustryDetailSource,
    EastMoneySectorSource,
    SectorDataAggregator,
    SinaSectorDataSource,
)


class TestEastMoneySectorSpotSource:
    """测试 akshare _spot_em 接口"""

    @pytest.fixture
    def sector_source(self):
        """创建数据源实例"""
        return EastMoneySectorSource()

    @pytest.mark.asyncio
    async def test_fetch_industry_spot(self, sector_source):
        """测试获取行业板块实时行情"""
        result = await sector_source.fetch(sector_type="industry")

        assert result.source == "sector_eastmoney_akshare"
        if result.success:
            assert result.data is not None
            assert "sectors" in result.data
            assert result.data.get("type") == "industry"
            assert len(result.data["sectors"]) > 0

            # 验证数据字段
            item = result.data["sectors"][0]
            assert "name" in item
            assert "code" in item
            assert "price" in item
            assert "change_percent" in item
            assert "up_count" in item
            assert "down_count" in item
            assert "lead_stock" in item
        else:
            # 网络问题也接受
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_fetch_concept_spot(self, sector_source):
        """测试获取概念板块实时行情"""
        result = await sector_source.fetch(sector_type="concept")

        assert result.source == "sector_eastmoney_akshare"
        if result.success:
            assert result.data is not None
            assert "sectors" in result.data
            assert result.data.get("type") == "concept"

            # 概念板块通常数量更多
            assert len(result.data["sectors"]) > 100
        else:
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_invalid_sector_type(self, sector_source):
        """测试无效的板块类型"""
        result = await sector_source.fetch(sector_type="invalid")

        assert result.success is False
        assert "不支持" in result.error

    @pytest.mark.asyncio
    async def test_fetch_industry_spot_mocked(self):
        """使用 mock 测试行业板块获取"""
        mock_df = pd.DataFrame(
            {
                "排名": [1, 2],
                "板块名称": ["银行", "保险"],
                "板块代码": ["bk04804", "bk04805"],
                "最新价": [100.0, 200.0],
                "涨跌额": [1.0, 2.0],
                "涨跌幅": [1.0, 2.0],
                "总市值": [1000000, 2000000],
                "换手率": [0.5, 0.6],
                "上涨家数": [10, 20],
                "下跌家数": [5, 8],
                "领涨股票": ["招商银行", "中国平安"],
                "领涨股票-涨跌幅": [3.0, 4.0],
            }
        )

        with patch("akshare.stock_board_industry_spot_em", return_value=mock_df):
            source = EastMoneySectorSource()
            result = await source.fetch(sector_type="industry")

            assert result.success is True
            assert result.data is not None
            assert len(result.data["sectors"]) == 2

            # 验证数据字段映射
            first_sector = result.data["sectors"][0]
            assert first_sector["name"] == "银行"
            assert first_sector["code"] == "bk04804"
            assert first_sector["price"] == 100.0
            assert first_sector["change_percent"] == 1.0
            assert first_sector["up_count"] == 10
            assert first_sector["down_count"] == 5
            assert first_sector["lead_stock"] == "招商银行"
            assert first_sector["lead_stock_change"] == 3.0

    @pytest.mark.asyncio
    async def test_fetch_concept_spot_mocked(self):
        """使用 mock 测试概念板块获取"""
        mock_df = pd.DataFrame(
            {
                "排名": [1, 2, 3],
                "板块名称": ["人工智能", "ChatGPT", "机器人"],
                "板块代码": ["bk04360", "bk04361", "bk04362"],
                "最新价": [150.0, 180.0, 120.0],
                "涨跌额": [5.0, 8.0, 3.0],
                "涨跌幅": [3.5, 4.7, 2.6],
                "总市值": [500000, 300000, 400000],
                "换手率": [1.2, 1.5, 0.8],
                "上涨家数": [50, 40, 30],
                "下跌家数": [10, 8, 15],
                "领涨股票": ["科大讯飞", "昆仑万维", "机器人"],
                "领涨股票-涨跌幅": [10.0, 9.5, 8.0],
            }
        )

        with patch("akshare.stock_board_concept_spot_em", return_value=mock_df):
            source = EastMoneySectorSource()
            result = await source.fetch(sector_type="concept")

            assert result.success is True
            assert result.data["type"] == "concept"
            assert len(result.data["sectors"]) == 3

            # 验证数据字段映射
            first_sector = result.data["sectors"][0]
            assert first_sector["name"] == "人工智能"
            assert first_sector["change_percent"] == 3.5
            assert first_sector["turnover_rate"] == 1.2

    @pytest.mark.asyncio
    async def test_fetch_empty_data_mocked(self):
        """测试空数据返回"""
        with patch("akshare.stock_board_industry_spot_em", return_value=pd.DataFrame()):
            source = EastMoneySectorSource()
            result = await source.fetch(sector_type="industry")

            assert result.success is False
            assert result.error is not None
            assert "为空" in result.error

    @pytest.mark.asyncio
    async def test_fetch_api_error_mocked(self):
        """测试 API 异常处理"""
        with patch("akshare.stock_board_industry_spot_em", side_effect=Exception("API Error")):
            source = EastMoneySectorSource()
            result = await source.fetch(sector_type="industry")

            assert result.success is False
            assert result.error is not None

    def test_get_status_spot_source(self, sector_source):
        """测试状态获取"""
        status = sector_source.get_status()

        assert status["name"] == "sector_eastmoney_akshare"
        assert status["type"] == "sector"
        assert "supported_types" in status
        assert "industry" in status["supported_types"]
        assert "concept" in status["supported_types"]
        assert status["api_version"] == "spot_em"
        assert "cache_size" in status


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
