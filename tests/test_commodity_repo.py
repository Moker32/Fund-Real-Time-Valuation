"""
商品缓存仓库测试
"""


from src.db.commodity_repo import (
    CATEGORY_NAMES,
    COMMODITY_CATEGORY_MAP,
    COMMODITY_NAMES,
    CommodityCacheRecord,
    CommodityCategory,
    get_category_info,
    get_commodity_info,
)


class TestCommodityCategory:
    """商品分类枚举测试"""
    
    def test_category_values(self):
        """测试分类值"""
        assert CommodityCategory.PRECIOUS_METAL.value == "precious_metal"
        assert CommodityCategory.ENERGY.value == "energy"
        assert CommodityCategory.BASE_METAL.value == "base_metal"
        assert CommodityCategory.AGRICULTURE.value == "agriculture"
        assert CommodityCategory.CRYPTO.value == "crypto"
    
    def test_category_names(self):
        """测试分类名称映射"""
        assert CATEGORY_NAMES[CommodityCategory.PRECIOUS_METAL] == "贵金属"
        assert CATEGORY_NAMES[CommodityCategory.ENERGY] == "能源化工"
        assert CATEGORY_NAMES[CommodityCategory.BASE_METAL] == "基本金属"
        assert CATEGORY_NAMES[CommodityCategory.AGRICULTURE] == "农产品"
        assert CATEGORY_NAMES[CommodityCategory.CRYPTO] == "加密货币"


class TestCommodityCategoryMap:
    """商品分类映射测试"""
    
    def test_gold_mapping(self):
        """测试黄金映射"""
        assert COMMODITY_CATEGORY_MAP["gold"] == CommodityCategory.PRECIOUS_METAL
        assert COMMODITY_CATEGORY_MAP["gold_cny"] == CommodityCategory.PRECIOUS_METAL
    
    def test_energy_mapping(self):
        """测试能源映射"""
        assert COMMODITY_CATEGORY_MAP["wti"] == CommodityCategory.ENERGY
        assert COMMODITY_CATEGORY_MAP["brent"] == CommodityCategory.ENERGY
    
    def test_base_metal_mapping(self):
        """测试基本金属映射"""
        assert COMMODITY_CATEGORY_MAP["copper"] == CommodityCategory.BASE_METAL
        assert COMMODITY_CATEGORY_MAP["aluminum"] == CommodityCategory.BASE_METAL
    
    def test_agriculture_mapping(self):
        """测试农产品映射"""
        assert COMMODITY_CATEGORY_MAP["soybean"] == CommodityCategory.AGRICULTURE
        assert COMMODITY_CATEGORY_MAP["corn"] == CommodityCategory.AGRICULTURE
    
    def test_crypto_mapping(self):
        """测试加密货币映射"""
        assert COMMODITY_CATEGORY_MAP["btc"] == CommodityCategory.CRYPTO
        assert COMMODITY_CATEGORY_MAP["eth"] == CommodityCategory.CRYPTO


class TestCommodityNames:
    """商品名称测试"""
    
    def test_precious_metals(self):
        """测试贵金属名称"""
        assert COMMODITY_NAMES["gold"] == "黄金 (COMEX)"
        assert COMMODITY_NAMES["gold_cny"] == "沪金 Au99.99"
        assert COMMODITY_NAMES["silver"] == "国际白银"
    
    def test_energy(self):
        """测试能源名称"""
        assert COMMODITY_NAMES["wti"] == "WTI原油"
        assert COMMODITY_NAMES["brent"] == "布伦特原油"
    
    def test_base_metals(self):
        """测试基本金属名称"""
        assert COMMODITY_NAMES["copper"] == "铜"
        assert COMMODITY_NAMES["aluminum"] == "铝"
    
    def test_agriculture(self):
        """测试农产品名称"""
        assert COMMODITY_NAMES["soybean"] == "大豆"
        assert COMMODITY_NAMES["corn"] == "玉米"
    
    def test_crypto(self):
        """测试加密货币名称"""
        assert COMMODITY_NAMES["btc"] == "比特币"
        assert COMMODITY_NAMES["eth"] == "以太坊"


class TestCommodityCacheRecord:
    """商品缓存记录测试"""
    
    def test_record_creation(self):
        """测试记录创建"""
        record = CommodityCacheRecord(
            commodity_type="gold",
            symbol="GC=F",
            name="黄金",
            price=1800.5,
            change=10.2,
            change_percent=0.57,
        )
        
        assert record.commodity_type == "gold"
        assert record.symbol == "GC=F"
        assert record.name == "黄金"
        assert record.price == 1800.5
    
    def test_record_to_dict(self):
        """测试记录转字典"""
        record = CommodityCacheRecord(
            commodity_type="gold",
            symbol="GC=F",
            name="黄金",
            price=1800.5,
            change=10.2,
            change_percent=0.57,
        )
        
        data = record.to_dict()
        
        assert data["commodity_type"] == "gold"
        assert data["price"] == 1800.5
    
    def test_record_default_values(self):
        """测试默认值"""
        record = CommodityCacheRecord()
        
        assert record.price == 0.0
        assert record.change == 0.0
        assert record.change_percent == 0.0


class TestGetCategoryInfo:
    """获取分类信息测试"""
    
    def test_precious_metal_info(self):
        """测试贵金属分类信息"""
        info = get_category_info(CommodityCategory.PRECIOUS_METAL)
        
        assert "name" in info
        assert "id" in info
        assert info["name"] == "贵金属"
    
    def test_energy_info(self):
        """测试能源分类信息"""
        info = get_category_info(CommodityCategory.ENERGY)
        
        assert info["name"] == "能源化工"
    
    def test_base_metal_info(self):
        """测试基本金属分类信息"""
        info = get_category_info(CommodityCategory.BASE_METAL)
        
        assert info["name"] == "基本金属"


class TestGetCommodityInfo:
    """获取商品信息测试"""
    
    def test_gold_info(self):
        """测试黄金信息"""
        info = get_commodity_info("gold")
        
        assert "name" in info
        assert "category" in info
        assert info["name"] == "黄金 (COMEX)"
    
    def test_wti_info(self):
        """测试 WTI 原油信息"""
        info = get_commodity_info("wti")
        
        assert info["name"] == "WTI原油"
    
    def test_unknown_commodity(self):
        """测试未知商品"""
        info = get_commodity_info("unknown")
        
        # 未知商品返回原始名称
        assert info["name"] == "unknown"
