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
    """获取所有支持的商品类型（7个核心商品）"""
    return [
        # 贵金属
        "gold",
        "silver",
        "platinum",
        # 能源
        "wti",
        "brent",
        "natural_gas",
        # 加密货币
        "btc",
    ]


def get_commodities_by_category() -> dict[CommodityCategory, list[str]]:
    """获取按分类组织的商品类型"""
    return {
        CommodityCategory.PRECIOUS_METAL: ["gold", "silver", "platinum"],
        CommodityCategory.ENERGY: ["wti", "brent", "natural_gas"],
        CommodityCategory.CRYPTO: ["btc"],
    }


# 搜索商品配置映射（7个核心商品）
SEARCHABLE_COMMODITIES: dict[str, dict[str, str]] = {
    # 贵金属
    "GC": {
        "name": "黄金 (COMEX)",
        "category": "precious_metal",
        "exchange": "COMEX",
        "currency": "USD",
    },
    "SI": {
        "name": "白银 (COMEX)",
        "category": "precious_metal",
        "exchange": "COMEX",
        "currency": "USD",
    },
    "XPT": {
        "name": "铂金 (伦敦)",
        "category": "precious_metal",
        "exchange": "LBMA",
        "currency": "USD",
    },
    # 能源
    "CL": {
        "name": "WTI原油 (NYMEX)",
        "category": "energy",
        "exchange": "NYMEX",
        "currency": "USD",
    },
    "OIL": {
        "name": "布伦特原油 (ICE)",
        "category": "energy",
        "exchange": "ICE",
        "currency": "USD",
    },
    "NG": {
        "name": "天然气 (NYMEX)",
        "category": "energy",
        "exchange": "NYMEX",
        "currency": "USD",
    },
    # 加密货币
    "BTCUSDT": {
        "name": "比特币 (Binance)",
        "category": "crypto",
        "exchange": "Binance",
        "currency": "USDT",
    },
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
