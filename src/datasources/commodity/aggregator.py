"""商品数据聚合器及辅助函数"""

import asyncio
import logging
import time
from typing import Any

from src.db.commodity_repo import CommodityCategory

from ..base import DataSource, DataSourceResult
from .base import CommodityDataSource, CommoditySearchResult

logger = logging.getLogger(__name__)


class CommodityDataAggregator(CommodityDataSource):
    """商品数据聚合器 - 支持多数据源自动切换"""

    def __init__(self, timeout: float = 15.0):
        super().__init__(name="commodity_aggregator", timeout=timeout)
        self._sources: list[DataSource] = []
        self._primary_source: DataSource | None = None

    def add_source(self, source: DataSource, is_primary: bool = False):
        """添加数据源"""
        self._sources.append(source)
        if is_primary or self._primary_source is None:
            self._primary_source = source

    async def fetch(self, commodity_type: str = "gold") -> DataSourceResult:
        """获取商品数据，尝试多个数据源"""
        errors = []

        # 优先使用主数据源
        if self._primary_source:
            try:
                result = await self._primary_source.fetch(commodity_type)
                if result.success:
                    return result
                errors.append(f"{self._primary_source.name}: {result.error}")
            except Exception as e:
                logger.error(f"主数据源 {self._primary_source.name} 获取失败: {e}")
                errors.append(f"{self._primary_source.name}: {str(e)}")

        # 尝试其他数据源
        for source in self._sources:
            if source == self._primary_source:
                continue
            try:
                result = await source.fetch(commodity_type)
                if result.success:
                    return result
                errors.append(f"{source.name}: {result.error}")
            except Exception as e:
                logger.error(f"数据源 {source.name} 获取失败: {e}")
                errors.append(f"{source.name}: {str(e)}")

        logger.error(f"所有数据源均失败: {'; '.join(errors)}")
        return DataSourceResult(
            success=False,
            error=f"所有数据源均失败: {'; '.join(errors)}",
            timestamp=time.time(),
            source=self.name,
            metadata={"commodity_type": commodity_type, "errors": errors},
        )

    async def fetch_batch(self, commodity_types: list[str]) -> list[DataSourceResult]:
        """批量获取商品数据"""
        tasks = [self.fetch(ctype) for ctype in commodity_types]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"批量获取商品 {commodity_types[i]} 失败: {result}")
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"commodity_type": commodity_types[i]},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def get_status(self) -> dict[str, Any]:
        """获取聚合器状态"""
        status = super().get_status()
        status["source_count"] = len(self._sources)
        status["primary_source"] = self._primary_source.name if self._primary_source else None
        status["sources"] = [s.name for s in self._sources]
        return status

    async def close(self):
        """关闭所有数据源"""
        for source in self._sources:
            if hasattr(source, "close"):
                try:
                    await source.close()
                except Exception as e:
                    logger.warning(f"关闭数据源 {source.name} 失败: {e}")


# ============================================================
# 辅助函数
# ============================================================


def get_all_commodity_types() -> list[str]:
    """获取所有支持的商品类型"""
    return [
        # 贵金属
        "gold",
        "gold_cny",
        "gold_pax",
        "silver",
        # 能源
        "wti",
        "brent",
        "natural_gas",
        # 基本金属
        "copper",
        "aluminum",
        "zinc",
        "nickel",
        # 农产品
        "soybean",
        "corn",
        "wheat",
        "coffee",
        "sugar",
        # 加密货币
        "btc",
        "btc_futures",
        "eth",
        "eth_futures",
    ]


def get_commodities_by_category() -> dict[CommodityCategory, list[str]]:
    """获取按分类组织的商品类型"""
    return {
        CommodityCategory.PRECIOUS_METAL: ["gold", "gold_cny", "gold_pax", "silver"],
        CommodityCategory.ENERGY: ["wti", "brent", "natural_gas"],
        CommodityCategory.BASE_METAL: ["copper", "aluminum", "zinc", "nickel"],
        CommodityCategory.AGRICULTURE: ["soybean", "corn", "wheat", "coffee", "sugar"],
        CommodityCategory.CRYPTO: ["btc", "btc_futures", "eth", "eth_futures"],
    }


# 搜索商品配置映射（用于自定义关注商品搜索）
SEARCHABLE_COMMODITIES: dict[str, dict[str, str]] = {
    # 贵金属
    "GC=F": {
        "name": "黄金 (COMEX)",
        "category": "precious_metal",
        "exchange": "CME",
        "currency": "USD",
    },
    "Au99.99": {
        "name": "上海黄金 (Au99.99)",
        "category": "precious_metal",
        "exchange": "SGE",
        "currency": "CNY",
    },
    "SI=F": {"name": "白银", "category": "precious_metal", "exchange": "CME", "currency": "USD"},
    "PT=F": {"name": "铂金", "category": "precious_metal", "exchange": "NYMEX", "currency": "USD"},
    "PA=F": {"name": "钯金", "category": "precious_metal", "exchange": "NYMEX", "currency": "USD"},
    # 能源
    "CL=F": {"name": "WTI 原油", "category": "energy", "exchange": "NYMEX", "currency": "USD"},
    "BZ=F": {"name": "布伦特原油", "category": "energy", "exchange": "ICE", "currency": "USD"},
    "NG=F": {"name": "天然气", "category": "energy", "exchange": "NYMEX", "currency": "USD"},
    "HO=F": {"name": "燃油", "category": "energy", "exchange": "NYMEX", "currency": "USD"},
    "RB=F": {"name": "汽油", "category": "energy", "exchange": "NYMEX", "currency": "USD"},
    # 基本金属
    "HG=F": {"name": "铜", "category": "base_metal", "exchange": "CME", "currency": "USD"},
    "ALU": {"name": "铝", "category": "base_metal", "exchange": "LME", "currency": "USD"},
    "ZN=F": {"name": "锌", "category": "base_metal", "exchange": "LME", "currency": "USD"},
    "NI=F": {"name": "镍", "category": "base_metal", "exchange": "LME", "currency": "USD"},
    "PB=F": {"name": "铅", "category": "base_metal", "exchange": "LME", "currency": "USD"},
    "SN=F": {"name": "锡", "category": "base_metal", "exchange": "LME", "currency": "USD"},
    # 农产品
    "ZS=F": {"name": "大豆", "category": "agriculture", "exchange": "CBOT", "currency": "USD"},
    "ZC=F": {"name": "玉米", "category": "agriculture", "exchange": "CBOT", "currency": "USD"},
    "ZW=F": {"name": "小麦", "category": "agriculture", "exchange": "CBOT", "currency": "USD"},
    "KC=F": {"name": "咖啡", "category": "agriculture", "exchange": "ICE", "currency": "USD"},
    "SB=F": {"name": "白糖", "category": "agriculture", "exchange": "ICE", "currency": "USD"},
    "CC=F": {"name": "可可", "category": "agriculture", "exchange": "ICE", "currency": "USD"},
    "CT=F": {"name": "棉花", "category": "agriculture", "exchange": "ICE", "currency": "USD"},
    "LE=F": {"name": "活牛", "category": "agriculture", "exchange": "CME", "currency": "USD"},
    "HE=F": {"name": "瘦肉猪", "category": "agriculture", "exchange": "CME", "currency": "USD"},
    "ZR=F": {"name": "糙米", "category": "agriculture", "exchange": "CBOT", "currency": "USD"},
    "OJ=F": {"name": "橙汁", "category": "agriculture", "exchange": "ICE", "currency": "USD"},
    # 加密货币现货
    "BTC-USD": {"name": "比特币", "category": "crypto", "exchange": "Spot", "currency": "USD"},
    "ETH-USD": {"name": "以太坊", "category": "crypto", "exchange": "Spot", "currency": "USD"},
    # 加密货币期货
    "BTC=F": {"name": "比特币期货", "category": "crypto", "exchange": "CME", "currency": "USD"},
    "ETH=F": {"name": "以太坊期货", "category": "crypto", "exchange": "CME", "currency": "USD"},
}


def identify_category(symbol: str) -> str:
    """
    识别商品分类

    Args:
        symbol: 商品代码

    Returns:
        str: 分类名称
    """
    clean_symbol = symbol.upper().strip()
    if clean_symbol in SEARCHABLE_COMMODITIES:
        return SEARCHABLE_COMMODITIES[clean_symbol]["category"]
    return "other"


def search_commodities(query: str) -> list[CommoditySearchResult]:
    """
    搜索可关注的大宗商品

    支持按代码或名称模糊搜索，返回匹配的 yfinance 可期货商品。

    Args:
        query: 搜索关键词（代码或名称）

    Returns:
        list[CommoditySearchResult]: 搜索结果列表
    """
    if not query or len(query.strip()) < 1:
        return []

    query_lower = query.lower().strip()
    results: list[CommoditySearchResult] = []

    for symbol, info in SEARCHABLE_COMMODITIES.items():
        # 检查代码是否匹配
        if query_lower in symbol.lower():
            results.append(
                {
                    "symbol": symbol,
                    "name": info["name"],
                    "exchange": info["exchange"],
                    "currency": info["currency"],
                    "category": info["category"],
                }
            )
            continue

        # 检查名称是否匹配
        if query_lower in info["name"].lower():
            results.append(
                {
                    "symbol": symbol,
                    "name": info["name"],
                    "exchange": info["exchange"],
                    "currency": info["currency"],
                    "category": info["category"],
                }
            )

    return results


def get_all_available_commodities() -> list[CommoditySearchResult]:
    """
    获取所有可关注的大宗商品列表

    Returns:
        list[CommoditySearchResult]: 所有可用商品列表
    """
    results: list[CommoditySearchResult] = []
    for symbol, info in SEARCHABLE_COMMODITIES.items():
        results.append(
            {
                "symbol": symbol,
                "name": info["name"],
                "exchange": info["exchange"],
                "currency": info["currency"],
                "category": info["category"],
            }
        )
    return results
