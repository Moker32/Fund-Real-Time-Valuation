"""
跨资产组合分析器模块

提供投资组合分析和风险管理功能:
- AssetType: 资产类型枚举
- PortfolioPosition: 持仓信息
- PortfolioAllocation: 资产配置比例
- PortfolioResult: 组合分析结果
- PortfolioAnalyzer: 组合分析器
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AssetType(Enum):
    """资产类型枚举"""
    FUND = "fund"
    STOCK = "stock"
    BOND = "bond"
    COMMODITY = "commodity"
    CRYPTO = "crypto"


@dataclass
class PortfolioPosition:
    """
    投资组合持仓

    Attributes:
        symbol: 资产代码/代码
        asset_type: 资产类型
        name: 资产名称
        quantity: 持有数量
        cost: 总成本
        current_price: 当前价格
        current_value: 当前市值 (只读，通过 quantity * current_price 计算)
    """
    symbol: str
    asset_type: AssetType
    name: str
    quantity: float
    cost: float
    current_price: float

    @property
    def current_value(self) -> float:
        """获取当前市值"""
        return self.quantity * self.current_price

    @property
    def profit_loss(self) -> float:
        """
        计算盈亏金额

        Returns:
            float: 盈亏金额（当前市值 - 总成本）
        """
        return self.current_value - self.cost

    @property
    def profit_loss_pct(self) -> float:
        """
        计算盈亏百分比

        Returns:
            float: 盈亏百分比
        """
        if self.cost == 0:
            return 0.0
        return (self.profit_loss / self.cost) * 100

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典

        Returns:
            Dict: 持仓信息字典
        """
        return {
            "symbol": self.symbol,
            "asset_type": self.asset_type.value,
            "name": self.name,
            "quantity": self.quantity,
            "cost": self.cost,
            "current_price": self.current_price,
            "current_value": self.current_value,
            "profit_loss": self.profit_loss,
            "profit_loss_pct": self.profit_loss_pct
        }


@dataclass
class PortfolioAllocation:
    """
    投资组合资产配置

    Attributes:
        fund_weight: 基金配置比例
        stock_weight: 股票配置比例
        bond_weight: 债券配置比例
        commodity_weight: 商品配置比例
        crypto_weight: 加密货币配置比例
    """
    fund_weight: float = 0.0
    stock_weight: float = 0.0
    bond_weight: float = 0.0
    commodity_weight: float = 0.0
    crypto_weight: float = 0.0

    def __post_init__(self):
        """验证配置比例"""
        weights = [
            self.fund_weight,
            self.stock_weight,
            self.bond_weight,
            self.commodity_weight,
            self.crypto_weight
        ]
        total = sum(weights)
        # 如果总和不等于100%，进行归一化
        if total != 0 and abs(total - 100.0) > 0.01:
            self.fund_weight = (self.fund_weight / total) * 100
            self.stock_weight = (self.stock_weight / total) * 100
            self.bond_weight = (self.bond_weight / total) * 100
            self.commodity_weight = (self.commodity_weight / total) * 100
            self.crypto_weight = (self.crypto_weight / total) * 100

    def to_dict(self) -> dict[str, float]:
        """
        转换为字典

        Returns:
            Dict: 配置比例字典
        """
        return {
            "fund": round(self.fund_weight, 2),
            "stock": round(self.stock_weight, 2),
            "bond": round(self.bond_weight, 2),
            "commodity": round(self.commodity_weight, 2),
            "crypto": round(self.crypto_weight, 2)
        }

    def to_percent_dict(self) -> dict[str, str]:
        """
        转换为百分比字符串字典

        Returns:
            Dict: 配置比例字符串字典
        """
        return {
            "fund": f"{self.fund_weight:.1f}%",
            "stock": f"{self.stock_weight:.1f}%",
            "bond": f"{self.bond_weight:.1f}%",
            "commodity": f"{self.commodity_weight:.1f}%",
            "crypto": f"{self.crypto_weight:.1f}%"
        }

    def get_diversification_score(self) -> float:
        """
        计算分散化得分

        分散化程度基于配置比例的均匀程度

        Returns:
            float: 分散化得分 (0-100)
        """
        weights = [
            self.fund_weight,
            self.stock_weight,
            self.bond_weight,
            self.commodity_weight,
            self.crypto_weight
        ]
        # 计算标准差
        mean = sum(weights) / len(weights)
        variance = sum((w - mean) ** 2 for w in weights) / len(weights)
        std_dev = math.sqrt(variance)

        # 将标准差转换为分散化得分 (标准差越小，得分越高)
        max_std = mean  # 理论最大标准差
        if max_std == 0:
            return 0.0

        score = (1 - (std_dev / max_std)) * 100
        return max(0.0, min(100.0, score))


@dataclass
class PortfolioResult:
    """
    投资组合分析结果

    Attributes:
        total_value: 组合总市值
        total_cost: 组合总成本
        total_profit: 总盈亏
        profit_pct: 盈亏百分比
        positions: 持仓列表
        allocation: 资产配置
    """
    total_value: float = 0.0
    total_cost: float = 0.0
    total_profit: float = 0.0
    profit_pct: float = 0.0
    positions: list[PortfolioPosition] = field(default_factory=list)
    allocation: PortfolioAllocation = field(default_factory=PortfolioAllocation)

    def __post_init__(self):
        """计算汇总指标"""
        self.total_value = sum(p.current_value for p in self.positions)
        self.total_cost = sum(p.cost for p in self.positions)
        self.total_profit = self.total_value - self.total_cost
        if self.total_cost > 0:
            self.profit_pct = (self.total_profit / self.total_cost) * 100

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典

        Returns:
            Dict: 分析结果字典
        """
        return {
            "total_value": round(self.total_value, 2),
            "total_cost": round(self.total_cost, 2),
            "total_profit": round(self.total_profit, 2),
            "profit_pct": round(self.profit_pct, 2),
            "positions": [p.to_dict() for p in self.positions],
            "allocation": self.allocation.to_dict(),
            "diversification_score": self.allocation.get_diversification_score()
        }

    def get_summary(self) -> dict[str, Any]:
        """
        获取摘要信息

        Returns:
            Dict: 摘要信息字典
        """
        profitable_count = sum(1 for p in self.positions if p.profit_loss > 0)
        losing_count = sum(1 for p in self.positions if p.profit_loss < 0)

        return {
            "total_value": round(self.total_value, 2),
            "total_cost": round(self.total_cost, 2),
            "total_profit": round(self.total_profit, 2),
            "profit_pct": round(self.profit_pct, 2),
            "position_count": len(self.positions),
            "profitable_positions": profitable_count,
            "losing_positions": losing_count,
            "allocation": self.allocation.to_percent_dict(),
            "diversification_score": round(self.allocation.get_diversification_score(), 1)
        }


class PortfolioAnalyzer:
    """
    投资组合分析器

    提供组合构建、分析和风险管理功能
    """

    def __init__(self):
        """初始化分析器"""
        self.positions: list[PortfolioPosition] = []

    def add_position(
        self,
        symbol: str,
        asset_type: AssetType,
        name: str,
        quantity: float,
        cost: float,
        current_price: float
    ) -> PortfolioPosition:
        """
        添加持仓

        Args:
            symbol: 资产代码
            asset_type: 资产类型
            name: 资产名称
            quantity: 持有数量
            cost: 总成本
            current_price: 当前价格

        Returns:
            PortfolioPosition: 创建的持仓对象
        """
        position = PortfolioPosition(
            symbol=symbol,
            asset_type=asset_type,
            name=name,
            quantity=quantity,
            cost=cost,
            current_price=current_price
        )
        self.positions.append(position)
        return position

    def remove_position(self, symbol: str) -> bool:
        """
        移除持仓

        Args:
            symbol: 资产代码

        Returns:
            bool: 是否成功移除
        """
        for i, position in enumerate(self.positions):
            if position.symbol == symbol:
                self.positions.pop(i)
                return True
        return False

    def get_position(self, symbol: str) -> PortfolioPosition | None:
        """
        获取持仓

        Args:
            symbol: 资产代码

        Returns:
            Optional[PortfolioPosition]: 持仓对象
        """
        for position in self.positions:
            if position.symbol == symbol:
                return position
        return None

    def update_price(self, symbol: str, new_price: float) -> bool:
        """
        更新持仓价格

        Args:
            symbol: 资产代码
            new_price: 新价格

        Returns:
            bool: 是否成功更新
        """
        position = self.get_position(symbol)
        if position:
            position.current_price = new_price
            return True
        return False

    def analyze(self) -> PortfolioResult:
        """
        分析投资组合

        Returns:
            PortfolioResult: 分析结果
        """
        allocation = self._calculate_allocation()

        return PortfolioResult(
            total_value=sum(p.current_value for p in self.positions),
            total_cost=sum(p.cost for p in self.positions),
            total_profit=sum(p.profit_loss for p in self.positions),
            profit_pct=(sum(p.profit_loss for p in self.positions) /
                       sum(p.cost for p in self.positions) * 100) if sum(p.cost for p in self.positions) > 0 else 0,
            positions=self.positions.copy(),
            allocation=allocation
        )

    def _calculate_allocation(self) -> PortfolioAllocation:
        """
        计算资产配置比例

        Returns:
            PortfolioAllocation: 资产配置对象
        """
        total_value = sum(p.current_value for p in self.positions)
        if total_value == 0:
            return PortfolioAllocation()

        weights = {
            AssetType.FUND: 0.0,
            AssetType.STOCK: 0.0,
            AssetType.BOND: 0.0,
            AssetType.COMMODITY: 0.0,
            AssetType.CRYPTO: 0.0
        }

        for position in self.positions:
            weights[position.asset_type] += position.current_value

        return PortfolioAllocation(
            fund_weight=(weights[AssetType.FUND] / total_value) * 100,
            stock_weight=(weights[AssetType.STOCK] / total_value) * 100,
            bond_weight=(weights[AssetType.BOND] / total_value) * 100,
            commodity_weight=(weights[AssetType.COMMODITY] / total_value) * 100,
            crypto_weight=(weights[AssetType.CRYPTO] / total_value) * 100
        )

    def get_risk_metrics(self) -> dict[str, float]:
        """
        获取风险指标

        Returns:
            Dict: 风险指标字典
        """
        if not self.positions:
            return {
                "total_value": 0.0,
                "total_cost": 0.0,
                "total_profit": 0.0,
                "profit_pct": 0.0,
                "position_count": 0,
                "diversification_score": 0.0,
                "volatility": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0
            }

        positions = self.positions

        # 计算总市值
        total_value = sum(p.current_value for p in positions)
        total_cost = sum(p.cost for p in positions)
        total_profit = total_value - total_cost
        profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0

        # 计算盈亏标准差（波动率）
        returns = []
        for p in positions:
            if p.cost > 0:
                ret = (p.current_value - p.cost) / p.cost
                returns.append(ret)

        volatility = 0.0
        if len(returns) > 1:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            volatility = math.sqrt(variance) * 100  # 转换为百分比

        # 获取分散化得分
        allocation = self._calculate_allocation()
        diversification_score = allocation.get_diversification_score()

        # 简化的最大回撤（基于单日最大亏损）
        max_drawdown = 0.0
        for p in positions:
            if p.cost > 0:
                drawdown = min(0, (p.current_value - p.cost) / p.cost * 100)
                max_drawdown = min(max_drawdown, drawdown)

        # 简化的夏普比率（假设无风险利率为3%）
        risk_free_rate = 0.03
        sharpe_ratio = 0.0
        if volatility > 0 and returns:
            portfolio_return = total_profit / total_cost if total_cost > 0 else 0
            sharpe_ratio = (portfolio_return - risk_free_rate) / volatility * 100

        return {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_profit": round(total_profit, 2),
            "profit_pct": round(profit_pct, 2),
            "position_count": len(positions),
            "diversification_score": round(diversification_score, 1),
            "volatility": round(volatility, 2),
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe_ratio, 2)
        }

    def get_performance_by_type(self) -> dict[str, dict[str, float]]:
        """
        获取各类型资产的表现

        Returns:
            Dict: 各类型资产表现字典
        """
        performance: dict[str, dict[str, float]] = {}

        for asset_type in AssetType:
            type_positions = [p for p in self.positions if p.asset_type == asset_type]
            if not type_positions:
                continue

            total_value = sum(p.current_value for p in type_positions)
            total_cost = sum(p.cost for p in type_positions)
            total_profit = total_value - total_cost
            profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0

            performance[asset_type.value] = {
                "total_value": round(total_value, 2),
                "total_cost": round(total_cost, 2),
                "total_profit": round(total_profit, 2),
                "profit_pct": round(profit_pct, 2),
                "position_count": len(type_positions)
            }

        return performance

    def get_top_performers(self, n: int = 5) -> list[PortfolioPosition]:
        """
        获取表现最好的持仓

        Args:
            n: 返回数量

        Returns:
            List[PortfolioPosition]: 表现最好的持仓列表
        """
        sorted_positions = sorted(
            self.positions,
            key=lambda p: p.profit_loss_pct,
            reverse=True
        )
        return sorted_positions[:n]

    def get_worst_performers(self, n: int = 5) -> list[PortfolioPosition]:
        """
        获取表现最差的持仓

        Args:
            n: 返回数量

        Returns:
            List[PortfolioPosition]: 表现最差的持仓列表
        """
        sorted_positions = sorted(
            self.positions,
            key=lambda p: p.profit_loss_pct
        )
        return sorted_positions[:n]

    def clear(self):
        """清空所有持仓"""
        self.positions.clear()


# 导出
__all__ = [
    "AssetType",
    "PortfolioPosition",
    "PortfolioAllocation",
    "PortfolioResult",
    "PortfolioAnalyzer"
]
