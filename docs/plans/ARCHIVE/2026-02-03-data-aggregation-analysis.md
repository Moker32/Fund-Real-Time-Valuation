# 基金实时估值 TUI 应用 - 数据聚合分析计划

**创建日期**: 2026-02-03
**目标**: 实现同源聚合与跨资产聚合分析

---

## 1. 数据聚合架构

### 1.1 同源聚合 (同类型多数据源)

```
┌─────────────────────────────────────────────────────┐
│                    DataSourceManager                 │
│                                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐             │
│  │ Source1 │  │ Source2 │  │ Source3 │             │
│  └────┬────┘  └────┬────┘  └────┬────┘             │
│       │            │            │                   │
│       └────────────┴────────────┘                   │
│                    │                                │
│              ┌─────▼─────┐                          │
│              │ Aggregator │                         │
│              │ (故障切换) │                         │
│              └─────┬─────┘                          │
│                    │                                │
│              ┌─────▼─────┐                          │
│              │  Result   │                          │
│              └───────────┘                          │
└─────────────────────────────────────────────────────┘
```

### 1.2 跨资产聚合 (组合分析)

```
┌─────────────────────────────────────────────────────┐
│              PortfolioAggregator                     │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐  │
│  │  Fund    │ │  Stock   │ │  Bond    │ │ Crypto│  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬───┘  │
│       │            │            │           │       │
│       └────────────┴────────────┴───────────┘       │
│                        │                            │
│              ┌─────────▼─────────┐                  │
│              │ PortfolioAnalyzer │                  │
│              │ - 组合收益        │                  │
│              │ - 资产配置        │                  │
│              │ - 风险指标        │                  │
│              └─────────┬─────────┘                  │
└────────────────────────┼────────────────────────────┘
                         │
              ┌─────────▼─────────┐
              │  PortfolioResult  │
              │ - total_value     │
              │ - total_profit    │
              │ - allocation      │
              │ - risk_metrics    │
              └───────────────────┘
```

---

## 2. 实现详情

### Task 1: 数据聚合器基类

**File**: `src/datasources/aggregator.py` (新建)

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from .base import DataSource, DataSourceResult


class DataAggregator(ABC):
    """数据聚合器基类"""

    def __init__(self, name: str):
        self.name = name
        self._sources: List[DataSource] = []
        self._primary_source: Optional[DataSource] = None

    def add_source(self, source: DataSource, is_primary: bool = False):
        """添加数据源"""
        self._sources.append(source)
        if is_primary or self._primary_source is None:
            self._primary_source = source

    @abstractmethod
    async def fetch(self, *args, **kwargs) -> DataSourceResult:
        """获取数据（聚合实现）"""
        pass

    def _get_best_source(self) -> DataSource:
        """获取最佳数据源（按优先级/健康度）"""
        # TODO: 实现智能选择逻辑
        return self._primary_source or self._sources[0]
```

---

### Task 2: 同源聚合器实现

**File**: `src/datasources/aggregator.py`

```python
class同源聚合器(DataAggregator):
    """同源数据聚合器 - 多数据源故障切换"""

    async def fetch(self, *args, **kwargs) -> DataSourceResult:
        """
        获取数据，尝试多个数据源

        策略:
        1. 优先使用主数据源
        2. 主数据源失败则切换到备用数据源
        3. 返回第一个成功的结果
        """
        errors = []

        # 优先主数据源
        if self._primary_source:
            try:
                result = await self._primary_source.fetch(*args, **kwargs)
                if result.success:
                    result.metadata = result.metadata or {}
                    result.metadata["source_used"] = self._primary_source.name
                    return result
                errors.append(f"{self._primary_source.name}: {result.error}")
            except Exception as e:
                errors.append(f"{self._primary_source.name}: {str(e)}")

        # 尝试备用数据源
        for source in self._sources:
            if source == self._primary_source:
                continue
            try:
                result = await source.fetch(*args, **kwargs)
                if result.success:
                    result.metadata = result.metadata or {}
                    result.metadata["source_used"] = source.name
                    result.metadata["fallback"] = True
                    return result
                errors.append(f"{source.name}: {result.error}")
            except Exception as e:
                errors.append(f"{source.name}: {str(e)}")

        return DataSourceResult(
            success=False,
            error=f"所有数据源均失败: {'; '.join(errors)}",
            timestamp=time.time(),
            source=self.name
        )
```

---

### Task 3: 跨资产组合分析器

**File**: `src/datasources/portfolio.py` (新建)

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class AssetType(Enum):
    """资产类型"""
    FUND = "fund"
    STOCK = "stock"
    BOND = "bond"
    COMMODITY = "commodity"
    CRYPTO = "crypto"


@dataclass
class PortfolioPosition:
    """组合持仓"""
    symbol: str           # 代码
    asset_type: AssetType  # 资产类型
    name: str             # 名称
    quantity: float       # 数量
    cost: float           # 成本
    current_price: float  # 当前价
    current_value: float  # 市值

    @property
    def profit_loss(self) -> float:
        return self.current_value - self.cost

    @property
    def profit_loss_pct(self) -> float:
        if self.cost == 0:
            return 0.0
        return (self.profit_loss / self.cost) * 100


@dataclass
class PortfolioAllocation:
    """资产配置"""
    fund_weight: float = 0.0
    stock_weight: float = 0.0
    bond_weight: float = 0.0
    commodity_weight: float = 0.0
    crypto_weight: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "基金": self.fund_weight,
            "股票": self.stock_weight,
            "债券": self.bond_weight,
            "商品": self.commodity_weight,
            "加密货币": self.crypto_weight,
        }


@dataclass
class PortfolioResult:
    """组合分析结果"""
    total_value: float = 0.0
    total_cost: float = 0.0
    total_profit: float = 0.0
    profit_pct: float = 0.0
    positions: List[PortfolioPosition] = field(default_factory=list)
    allocation: PortfolioAllocation = field(default_factory=PortfolioAllocation)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_value": self.total_value,
            "total_cost": self.total_cost,
            "total_profit": self.total_profit,
            "profit_pct": self.profit_pct,
            "positions": [
                {
                    "symbol": p.symbol,
                    "name": p.name,
                    "value": p.current_value,
                    "profit": p.profit_loss,
                    "profit_pct": p.profit_loss_pct,
                }
                for p in self.positions
            ],
            "allocation": self.allocation.to_dict(),
        }


class PortfolioAnalyzer:
    """组合分析器"""

    def __init__(self):
        self.positions: List[PortfolioPosition] = []

    def add_position(
        self,
        symbol: str,
        asset_type: AssetType,
        name: str,
        quantity: float,
        cost: float,
        current_price: float
    ):
        """添加持仓"""
        current_value = quantity * current_price
        position = PortfolioPosition(
            symbol=symbol,
            asset_type=asset_type,
            name=name,
            quantity=quantity,
            cost=cost,
            current_price=current_price,
            current_value=current_value
        )
        self.positions.append(position)

    def analyze(self) -> PortfolioResult:
        """分析组合"""
        total_value = sum(p.current_value for p in self.positions)
        total_cost = sum(p.cost for p in self.positions)
        total_profit = total_value - total_cost

        profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0.0

        # 计算资产配置
        allocation = self._calculate_allocation()

        return PortfolioResult(
            total_value=total_value,
            total_cost=total_cost,
            total_profit=total_profit,
            profit_pct=profit_pct,
            positions=self.positions,
            allocation=allocation,
        )

    def _calculate_allocation(self) -> PortfolioAllocation:
        """计算资产配置权重"""
        if not self.positions:
            return PortfolioAllocation()

        total = sum(p.current_value for p in self.positions)

        allocation = PortfolioAllocation()
        for position in self.positions:
            weight = position.current_value / total * 100
            if position.asset_type == AssetType.FUND:
                allocation.fund_weight += weight
            elif position.asset_type == AssetType.STOCK:
                allocation.stock_weight += weight
            elif position.asset_type == AssetType.BOND:
                allocation.bond_weight += weight
            elif position.asset_type == AssetType.COMMODITY:
                allocation.commodity_weight += weight
            elif position.asset_type == AssetType.CRYPTO:
                allocation.crypto_weight += weight

        return allocation

    def get_risk_metrics(self) -> Dict[str, float]:
        """获取风险指标（简化版）"""
        if len(self.positions) < 2:
            return {"diversification": 0.0, "max_position_pct": 100.0}

        values = [p.current_value for p in self.positions]
        total = sum(values)

        # 最大持仓占比
        max_pct = max(values) / total * 100 if total > 0 else 0.0

        # 简单分散度 (赫芬达尔指数倒数归一化)
        hhi = sum((v / total * 100) ** 2 for v in values if total > 0)
        diversification = min(100.0, (10000 / hhi - 1) / 99 * 100) if hhi > 0 else 0.0

        return {
            "diversification": round(diversification, 2),
            "max_position_pct": round(max_pct, 2),
            "position_count": len(self.positions),
        }
```

---

### Task 4: 组合聚合器

**File**: `src/datasources/portfolio.py`

```python
class PortfolioAggregator:
    """
    组合数据聚合器

    功能:
    - 整合多资产类型数据
    - 计算组合价值和收益
    - 分析资产配置
    """

    def __init__(self, data_source_manager: DataSourceManager):
        self.manager = data_source_manager
        self.analyzer = PortfolioAnalyzer()

    async def fetch_portfolio(
        self,
        positions: List[Dict[str, Any]]
    ) -> PortfolioResult:
        """
        获取组合数据

        Args:
            positions: 持仓列表
                [
                    {"symbol": "161039", "type": "fund", "quantity": 10000, "cost": 1.5},
                    {"symbol": "AAPL", "type": "stock", "quantity": 10, "cost": 150.0},
                    ...
                ]

        Returns:
            PortfolioResult: 组合分析结果
        """
        # 获取所有持仓的实时价格
        for pos in positions:
            price = await self._fetch_price(pos["symbol"], pos["type"])
            if price:
                self.analyzer.add_position(
                    symbol=pos["symbol"],
                    asset_type=AssetType(pos["type"]),
                    name=pos.get("name", pos["symbol"]),
                    quantity=pos["quantity"],
                    cost=pos["cost"] * pos["quantity"],  # 总成本
                    current_price=price,
                )

        return self.analyzer.analyze()

    async def _fetch_price(self, symbol: str, asset_type: str) -> Optional[float]:
        """获取单个资产价格"""
        from .base import DataSourceType

        type_mapping = {
            "fund": DataSourceType.FUND,
            "stock": DataSourceType.STOCK,
            "bond": DataSourceType.BOND,
            "commodity": DataSourceType.COMMODITY,
            "crypto": DataSourceType.CRYPTO,
        }

        source_type = type_mapping.get(asset_type)
        if not source_type:
            return None

        result = await self.manager.fetch(source_type, symbol)
        if result.success:
            return result.data.get("price") or result.data.get("current_price")

        return None
```

---

### Task 5: 更新模块导出

**File**: `src/datasources/__init__.py`

```python
from .aggregator import DataAggregator, SameSourceAggregator
from .portfolio import (
    PortfolioAnalyzer,
    PortfolioAggregator,
    PortfolioResult,
    PortfolioPosition,
    PortfolioAllocation,
    AssetType,
)

__all__ = [
    # 聚合器
    "DataAggregator",
    "SameSourceAggregator",
    # 组合分析
    "PortfolioAnalyzer",
    "PortfolioAggregator",
    "PortfolioResult",
    "PortfolioPosition",
    "PortfolioAllocation",
    "AssetType",
]
```

---

## 3. 测试验证

**File**: `tests/test_aggregation.py`

```python
import pytest
from src.datasources.portfolio import PortfolioAnalyzer, PortfolioResult


class TestPortfolioAnalyzer:
    """组合分析器测试"""

    def test_single_position(self):
        """单持仓分析"""
        analyzer = PortfolioAnalyzer()
        analyzer.add_position(
            symbol="161039",
            asset_type=AssetType.FUND,
            name="测试基金",
            quantity=10000,
            cost=15000.0,  # 总成本
            current_price=1.6,
        )

        result = analyzer.analyze()

        assert result.total_value == 16000.0
        assert result.total_profit == 1000.0
        assert result.profit_pct == pytest.approx(6.67, rel=0.01)

    def test_multiple_positions(self):
        """多持仓分析"""
        analyzer = PortfolioAnalyzer()
        analyzer.add_position("161039", AssetType.FUND, "基金1", 10000, 15000.0, 1.6)
        analyzer.add_position("600000", AssetType.STOCK, "浦发银行", 1000, 8000.0, 9.5)

        result = analyzer.analyzer.analyze()

        assert result.total_value == 16000.0 + 9500.0  # 25500.0
        assert len(result.positions) == 2
        assert result.allocation.fund_weight > 0
        assert result.allocation.stock_weight > 0

    def test_allocation_calculation(self):
        """资产配置计算"""
        analyzer = PortfolioAnalyzer()
        analyzer.add_position("F1", AssetType.FUND, "基金", 10000, 10000.0, 1.0)
        analyzer.add_position("S1", AssetType.STOCK, "股票", 1000, 5000.0, 10.0)

        result = analyzer.analyze()

        # 基金 10000 / 20000 = 50%
        # 股票 10000 / 20000 = 50%
        assert result.allocation.fund_weight == 50.0
        assert result.allocation.stock_weight == 50.0
```

---

## 4. 时间估算

| Task | 复杂度 | 预估时间 |
|------|--------|----------|
| Task 1: 聚合器基类 | 低 | 30min |
| Task 2: 同源聚合器 | 中 | 1.5h |
| Task 3: 组合分析器 | 中 | 2h |
| Task 4: 组合聚合器 | 中 | 1.5h |
| Task 5: 模块导出 | 低 | 15min |

**总计**: ~6h
