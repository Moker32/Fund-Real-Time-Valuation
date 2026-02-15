"""
大宗商品配置测试
"""


import pytest

from src.config.commodities_config import (
    CATEGORY_MAPPING,
    CommoditiesConfig,
    WatchedCommodityDict,
)


class TestCommoditiesConfig:
    """商品配置测试"""

    def test_identify_precious_metals(self):
        """测试贵金属分类"""
        assert CommoditiesConfig.identify_category("GC=F") == "precious_metal"
        assert CommoditiesConfig.identify_category("SI=F") == "precious_metal"

    def test_identify_energy(self):
        """测试能源分类"""
        assert CommoditiesConfig.identify_category("CL=F") == "energy"
        assert CommoditiesConfig.identify_category("BZ=F") == "energy"

    def test_identify_base_metals(self):
        """测试基本金属分类"""
        assert CommoditiesConfig.identify_category("HG=F") == "base_metal"
        assert CommoditiesConfig.identify_category("AL=F") == "base_metal"

    def test_identify_agriculture(self):
        """测试农产品分类"""
        assert CommoditiesConfig.identify_category("ZS=F") == "agriculture"
        assert CommoditiesConfig.identify_category("ZC=F") == "agriculture"

    def test_identify_crypto(self):
        """测试加密货币分类"""
        assert CommoditiesConfig.identify_category("BTC=F") == "crypto"
        assert CommoditiesConfig.identify_category("ETH=F") == "crypto"

    def test_identify_unknown(self):
        """测试未知分类"""
        assert CommoditiesConfig.identify_category("UNKNOWN") == "other"
        assert CommoditiesConfig.identify_category("") == "other"


class TestWatchedCommodityDict:
    """关注商品数据结构测试"""

    def test_create_watched_commodity(self):
        """测试创建关注商品"""
        commodity: WatchedCommodityDict = {
            "symbol": "GC=F",
            "name": "黄金",
            "category": "precious_metal",
            "added_at": "2024-01-01T00:00:00Z",
        }
        assert commodity["symbol"] == "GC=F"
        assert commodity["category"] == "precious_metal"


class TestCategoryMapping:
    """分类映射测试"""

    def test_category_mapping_not_empty(self):
        """测试分类映射不为空"""
        assert len(CATEGORY_MAPPING) > 0

    def test_gold_mapping(self):
        """测试黄金映射"""
        assert CATEGORY_MAPPING.get("GC=F") == "precious_metal"

    def test_oil_mapping(self):
        """测试原油映射"""
        assert CATEGORY_MAPPING.get("CL=F") == "energy"


class TestCommoditiesConfigInstance:
    """商品配置实例测试"""

    @pytest.fixture
    def config(self, tmp_path):
        return CommoditiesConfig(config_dir=str(tmp_path))

    def test_get_watched_commodities_empty(self, config):
        """测试获取空关注列表"""
        commodities = config.get_watched_commodities()
        assert commodities == []

    def test_add_watched_commodity(self, config):
        """测试添加关注商品"""
        result, msg = config.add_watched_commodity("GC=F", "黄金")
        assert result is True

    def test_is_watching(self, config):
        """测试是否在关注列表"""
        config.add_watched_commodity("GC=F", "黄金")
        assert config.is_watching("GC=F") is True
        assert config.is_watching("CL=F") is False

    def test_remove_watched_commodity(self, config):
        """测试移除关注商品"""
        config.add_watched_commodity("GC=F", "黄金")
        result, msg = config.remove_watched_commodity("GC=F")
        assert result is True
        assert config.is_watching("GC=F") is False

    def test_get_watched_by_category(self, config):
        """测试按分类获取"""
        config.add_watched_commodity("GC=F", "黄金")
        config.add_watched_commodity("CL=F", "原油")
        
        precious = config.get_watched_by_category("precious_metal")
        assert len(precious) == 1
        assert precious[0]["symbol"] == "GC=F"

    def test_get_watched_count(self, config):
        """测试获取关注数量"""
        assert config.get_watched_count() == 0
        config.add_watched_commodity("GC=F", "黄金")
        assert config.get_watched_count() == 1
