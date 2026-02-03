"""
数据模型模块
定义基金、持仓、商品等核心数据模型
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Theme(str, Enum):
    """主题枚举"""
    LIGHT = "light"
    DARK = "dark"


class DataSource(str, Enum):
    """数据源标识"""
    # 基金数据源
    SINA = "sina"          # 新浪财经
    EASTMONEY = "eastmoney"  # 东方财富
    # 商品数据源
    ALPHA_VANTAGE = "alpha_vantage"
    AKSHARE = "akshare"
    # 新闻数据源
    SINA_NEWS = "sina_news"
    EASTMONEY_NEWS = "eastmoney_news"


@dataclass
class Fund:
    """基金基础模型"""
    code: str              # 基金代码
    name: str              # 基金名称

    def __hash__(self):
        return hash(self.code)

    def __eq__(self, other):
        if isinstance(other, Fund):
            return self.code == other.code
        return False


@dataclass
class Holding(Fund):
    """持仓模型"""
    shares: float = 0.0    # 持有份额
    cost: float = 0.0      # 成本价

    @property
    def total_cost(self) -> float:
        """计算总成本"""
        return self.shares * self.cost


@dataclass
class Commodity:
    """商品模型"""
    symbol: str            # 商品代码/符号
    name: str              # 商品名称
    source: str = DataSource.AKSHARE.value  # 数据源标识

    def __hash__(self):
        return hash(self.symbol)

    def __eq__(self, other):
        if isinstance(other, Commodity):
            return self.symbol == other.symbol
        return False


@dataclass
class AppConfig:
    """应用主配置"""
    refresh_interval: int = 30          # 刷新频率（秒）
    theme: str = Theme.DARK.value       # 主题
    default_fund_source: str = DataSource.SINA.value  # 默认基金数据源
    max_history_points: int = 100       # 历史数据最大点数
    enable_auto_refresh: bool = True    # 是否启用自动刷新
    show_profit_loss: bool = True       # 是否显示盈亏


@dataclass
class FundList:
    """基金列表容器"""
    watchlist: list[Fund] = field(default_factory=list)
    holdings: list[Holding] = field(default_factory=list)

    def get_all_codes(self) -> list[str]:
        """获取所有基金代码"""
        codes = [f.code for f in self.watchlist]
        codes.extend(h.code for h in self.holdings)
        return list(set(codes))

    def is_watching(self, code: str) -> bool:
        """检查是否在自选列表中"""
        return any(f.code == code for f in self.watchlist)

    def get_holding(self, code: str) -> Optional[Holding]:
        """获取持仓信息"""
        for h in self.holdings:
            if h.code == code:
                return h
        return None


@dataclass
class CommodityList:
    """商品列表容器"""
    commodities: list[Commodity] = field(default_factory=list)

    def get_by_symbol(self, symbol: str) -> Optional[Commodity]:
        """根据代码获取商品"""
        for c in self.commodities:
            if c.symbol == symbol:
                return c
        return None

    def get_by_source(self, source: str) -> list[Commodity]:
        """根据数据源获取商品列表"""
        return [c for c in self.commodities if c.source == source]
