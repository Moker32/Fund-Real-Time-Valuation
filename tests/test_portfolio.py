"""
投资组合模块测试
"""

from src.datasources.portfolio import (
    AssetType,
    PortfolioAllocation,
    PortfolioPosition,
    PortfolioResult,
)


class TestAssetType:
    """资产类型枚举测试"""

    def test_asset_types(self):
        """测试资产类型"""
        assert AssetType.FUND.value == "fund"
        assert AssetType.STOCK.value == "stock"
        assert AssetType.BOND.value == "bond"
        assert AssetType.COMMODITY.value == "commodity"
        assert AssetType.CRYPTO.value == "crypto"


class TestPortfolioPosition:
    """持仓测试"""

    def test_create_position(self):
        """测试创建持仓"""
        position = PortfolioPosition(
            symbol="000001",
            asset_type=AssetType.FUND,
            name="测试基金",
            quantity=1000,
            cost=1500.0,
            current_price=1.6,
        )
        assert position.symbol == "000001"
        assert position.quantity == 1000
        assert position.cost == 1500.0

    def test_current_value(self):
        """测试当前市值"""
        position = PortfolioPosition(
            symbol="000001",
            asset_type=AssetType.FUND,
            name="测试基金",
            quantity=1000,
            cost=1500.0,
            current_price=1.6,
        )
        assert position.current_value == 1600.0

    def test_profit_loss(self):
        """测试盈亏"""
        position = PortfolioPosition(
            symbol="000001",
            asset_type=AssetType.FUND,
            name="测试基金",
            quantity=1000,
            cost=1500.0,
            current_price=1.6,
        )
        assert position.profit_loss == 100.0  # 1600 - 1500

    def test_profit_loss_pct(self):
        """测试盈亏百分比"""
        position = PortfolioPosition(
            symbol="000001",
            asset_type=AssetType.FUND,
            name="测试基金",
            quantity=1000,
            cost=1500.0,
            current_price=1.65,
        )
        assert position.profit_loss_pct == 10.0  # (1650-1500)/1500 * 100

    def test_zero_cost(self):
        """测试零成本"""
        position = PortfolioPosition(
            symbol="000001",
            asset_type=AssetType.FUND,
            name="测试基金",
            quantity=1000,
            cost=0,
            current_price=1.6,
        )
        assert position.profit_loss_pct == 0.0


class TestPortfolioAllocation:
    """资产配置测试"""

    def test_create_allocation(self):
        """测试创建资产配置"""
        allocation = PortfolioAllocation(
            fund_weight=50.0,
            stock_weight=30.0,
            bond_weight=10.0,
            commodity_weight=5.0,
            crypto_weight=5.0,
        )
        assert allocation.fund_weight == 50.0
        assert allocation.stock_weight == 30.0
        assert allocation.bond_weight == 10.0


class TestPortfolioResult:
    """组合结果测试"""

    def test_create_result(self):
        """测试创建组合结果"""
        result = PortfolioResult(
            allocation=PortfolioAllocation(
                fund_weight=50.0,
                stock_weight=30.0,
                bond_weight=10.0,
                commodity_weight=5.0,
                crypto_weight=5.0,
            ),
        )
        assert result.allocation.fund_weight == 50.0
        assert result.total_value == 0.0
