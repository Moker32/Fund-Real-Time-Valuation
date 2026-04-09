"""
QDII 基金实时估值引擎

基于 QDII 基金跟踪的海外指数实时涨跌幅，加权计算 QDII 基金的估算净值。

工作原理：
1. 从 qdii_index_map 获取基金跟踪的指数列表及权重
2. 通过 HybridIndexSource 获取各指数实时涨跌幅
3. 加权计算估算涨跌幅：Σ(权重_i × 指数涨跌幅_i) / 100
4. 估算净值 = prev_net_value × (1 + estimated_change_percent / 100)
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.datasources.base import DataSourceResult
from src.datasources.index_source import HybridIndexSource
from src.datasources.qdii_index_map import get_qdii_tracking_indices
from src.datasources.trading_calendar_source import (
    Market,
    TradingCalendarSource,
)

logger = logging.getLogger(__name__)


@dataclass
class QdiiEstimateResult:
    """QDII 估值结果"""

    success: bool
    fund_code: str = ""
    estimated_net_value: float | None = None
    estimated_change_percent: float | None = None
    estimated_change: float | None = None
    prev_net_value: float | None = None
    estimate_time: str | None = None
    market_status: str | None = None
    underlying_indices: list[dict] = field(default_factory=list)
    index_contributions: list[dict] = field(default_factory=list)
    error: str | None = None
    source: str = "qdii_estimator"


class QdiiEstimator:
    def __init__(self):
        self._index_source = HybridIndexSource()
        self._calendar = TradingCalendarSource()
        self._index_cache: dict[str, tuple[float, DataSourceResult]] = {}
        self._cache_ttl = 30.0

    async def estimate(
        self,
        fund_code: str,
        prev_net_value: float | None = None,
    ) -> QdiiEstimateResult:
        """
        估算 QDII 基金实时净值

        Args:
            fund_code: 基金代码
            prev_net_value: 上一交易日净值（用于计算估算净值）

        Returns:
            QdiiEstimateResult: 估值结果
        """
        tracking_indices = get_qdii_tracking_indices(fund_code)
        if not tracking_indices:
            return QdiiEstimateResult(
                success=False,
                fund_code=fund_code,
                error=f"基金 {fund_code} 无跟踪指数映射，无法估算",
            )

        primary_market = self._get_primary_market(tracking_indices)
        market_status = self._get_market_trading_status(primary_market)

        if market_status in ("closed", "non_trading_day"):
            return QdiiEstimateResult(
                success=True,
                fund_code=fund_code,
                estimated_net_value=prev_net_value,
                estimated_change_percent=0.0,
                estimated_change=0.0,
                prev_net_value=prev_net_value,
                estimate_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                market_status=market_status,
                underlying_indices=tracking_indices,
            )

        index_results = await self._fetch_index_data(tracking_indices)

        failed_indices = [idx for idx, result in index_results.items() if not result.success]
        if failed_indices:
            logger.warning(f"QDII 估值部分指数获取失败: {fund_code}, 失败: {failed_indices}")
            if len(failed_indices) == len(tracking_indices):
                return QdiiEstimateResult(
                    success=False,
                    fund_code=fund_code,
                    error=f"所有跟踪指数数据获取失败: {', '.join(failed_indices)}",
                )

        total_weight = 0.0
        weighted_change = 0.0
        index_contributions = []

        for idx_info in tracking_indices:
            index_type = idx_info["index_type"]
            weight = idx_info.get("weight", 0.0)
            index_name = idx_info.get("name", index_type)

            result = index_results.get(index_type)
            if result and result.success and result.data:
                change_pct = result.data.get("change_percent", 0.0)
                contribution = weight * change_pct / 100.0
                weighted_change += contribution
                total_weight += weight

                index_contributions.append(
                    {
                        "index_type": index_type,
                        "index_name": index_name,
                        "weight": weight,
                        "change_percent": change_pct,
                        "contribution": round(contribution, 4),
                    }
                )
            else:
                index_contributions.append(
                    {
                        "index_type": index_type,
                        "index_name": index_name,
                        "weight": weight,
                        "change_percent": None,
                        "contribution": 0.0,
                    }
                )

        if total_weight > 0:
            estimated_change_percent = weighted_change / total_weight * 100
        else:
            estimated_change_percent = 0.0

        estimated_net_value = None
        estimated_change = None
        if prev_net_value is not None:
            estimated_change = prev_net_value * estimated_change_percent / 100
            estimated_net_value = prev_net_value + estimated_change

        estimate_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        return QdiiEstimateResult(
            success=True,
            fund_code=fund_code,
            estimated_net_value=round(estimated_net_value, 4) if estimated_net_value else None,
            estimated_change_percent=round(estimated_change_percent, 4),
            estimated_change=round(estimated_change, 4) if estimated_change else None,
            prev_net_value=prev_net_value,
            estimate_time=estimate_time,
            market_status=market_status,
            underlying_indices=tracking_indices,
            index_contributions=index_contributions,
        )

    async def _fetch_index_data(self, tracking_indices: list[dict]) -> dict[str, DataSourceResult]:
        """
        获取所有跟踪指数的实时数据（带缓存）

        Args:
            tracking_indices: 跟踪指数列表

        Returns:
            dict: index_type -> DataSourceResult
        """
        now = time.time()
        results: dict[str, DataSourceResult] = {}

        to_fetch = []
        for idx_info in tracking_indices:
            index_type = idx_info["index_type"]

            if index_type in self._index_cache:
                cached_time, cached_result = self._index_cache[index_type]
                if now - cached_time < self._cache_ttl:
                    results[index_type] = cached_result
                    continue

            to_fetch.append(index_type)

        if to_fetch:
            try:
                batch_results = await self._index_source.fetch_batch(to_fetch)
                for index_type, result in zip(to_fetch, batch_results):
                    results[index_type] = result
                    self._index_cache[index_type] = (now, result)
            except Exception as e:
                logger.error(f"批量获取指数数据失败: {e}")
                for index_type in to_fetch:
                    results[index_type] = DataSourceResult(
                        success=False,
                        error=str(e),
                        timestamp=now,
                        source="qdii_estimator",
                    )

        return results

    def _get_primary_market(self, tracking_indices: list[dict]) -> str:
        sorted_indices = sorted(tracking_indices, key=lambda x: x.get("weight", 0), reverse=True)
        if not sorted_indices:
            return "unknown"

        primary_index = sorted_indices[0]["index_type"]
        market_map = {
            "sp500": "usa",
            "nasdaq": "usa",
            "dow_jones": "usa",
            "hang_seng": "hk",
            "hang_seng_tech": "hk",
            "dax": "germany",
            "ftse": "uk",
            "cac40": "france",
            "nikkei225": "japan",
        }
        return market_map.get(primary_index, "unknown")

    def _get_market_trading_status(self, market: str) -> str:
        market_enum_map = {
            "usa": Market.USA,
            "hk": Market.HONG_KONG,
            "germany": Market.GERMANY,
            "uk": Market.UK,
            "france": Market.FRANCE,
            "japan": Market.JAPAN,
        }
        market_enum = market_enum_map.get(market)
        if market_enum is None:
            return "unknown"

        try:
            status = self._calendar.is_within_trading_hours(market_enum)
            return status.get("status", "unknown")
        except Exception as e:
            logger.warning(f"获取市场交易状态失败: {market} - {e}")
            return "unknown"

    def clear_cache(self) -> None:
        self._index_cache.clear()
