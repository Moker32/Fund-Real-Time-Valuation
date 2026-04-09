"""AKShare 国内商品数据源 - 上海黄金交易所"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from ..base import DataSourceResult
from .base import CommodityDataSource

logger = logging.getLogger(__name__)


class AKShareCommoditySource(CommodityDataSource):
    """AKShare 国内商品数据源 - 用于国内黄金"""

    def __init__(self, timeout: float = 15.0):
        super().__init__(name="akshare_commodity", timeout=timeout)
        self._cache_timeout = 10.0  # 缓存10秒，商品价格实时性要求高

    async def fetch(self, commodity_type: str = "gold_cny") -> DataSourceResult:
        """获取国内商品数据"""
        # 检查数据库缓存
        if self._db_dao:
            try:
                db_record = self._db_dao.get_latest(commodity_type)
                if db_record and not self._db_dao.is_expired(commodity_type):
                    data = db_record.to_dict()
                    data.pop("id", None)
                    data.pop("created_at", None)
                    return DataSourceResult(
                        success=True,
                        data=data,
                        timestamp=datetime.fromisoformat(
                            data.get("timestamp", "").replace("Z", "+00:00")
                        ).timestamp()
                        if data.get("timestamp")
                        else time.time(),
                        source=self.name,
                        metadata={"commodity_type": commodity_type, "from_cache": "database"},
                    )
            except Exception as e:
                logger.warning(f"查询数据库缓存失败: {e}")

        # 检查内存缓存
        cache_key = commodity_type
        cached_data = self._get_from_cache(cache_key)
        if cached_data and self._is_cache_valid(cache_key):
            return DataSourceResult(
                success=True,
                data=cached_data,
                timestamp=cached_data.get("_cache_time", time.time()),
                source=self.name,
                metadata={"commodity_type": commodity_type, "from_cache": "memory"},
            )

        try:
            import akshare as ak  # noqa: F401  # 动态导入检查可用性

            if commodity_type == "gold_cny":
                data = await self._fetch_gold_cny()
            else:
                logger.debug(f"[AKShare] 不支持的商品类型: {commodity_type}，仅支持 gold_cny")
                return DataSourceResult(
                    success=False,
                    error=f"不支持的商品类型: {commodity_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"commodity_type": commodity_type},
                )

            if data:
                data["_cache_time"] = time.time()
                self._add_to_cache(cache_key, data)
                # 异步保存到数据库
                await self._save_to_database(commodity_type, data, self.name)
                self._record_success()
                return DataSourceResult(
                    success=True,
                    data=data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"commodity_type": commodity_type},
                )

            logger.error(f"[AKShare] 获取 {commodity_type} 数据为空")
            return DataSourceResult(
                success=False,
                error="获取商品数据为空",
                timestamp=time.time(),
                source=self.name,
                metadata={"commodity_type": commodity_type},
            )

        except ImportError:
            logger.error("AKShare 未安装")
            return DataSourceResult(
                success=False,
                error="AKShare 未安装",
                timestamp=time.time(),
                source=self.name,
                metadata={"commodity_type": commodity_type},
            )
        except Exception as e:
            logger.error(f"[AKShare] 获取 {commodity_type} 数据失败: {e}")
            return self._handle_error(e, self.name)

    async def _fetch_gold_cny(self) -> dict[str, Any] | None:
        """获取上海黄金交易所 Au99.99 实时行情数据"""
        import akshare as ak

        async def _fetch_realtime() -> dict[str, Any] | None:
            """获取实时行情"""
            # 优先使用实时行情接口
            df = ak.spot_quotations_sge()
            if df is not None and not df.empty:
                au_df = df[df["品种"] == "Au99.99"]
                if not au_df.empty:
                    latest = au_df.iloc[-1]
                    price = float(latest.get("现价", 0) or 0)

                    # 获取当日开盘价（第一条数据）
                    open_price = float(au_df.iloc[0].get("现价", 0)) if len(au_df) > 0 else None
                    # 获取当日最高最低
                    high_price = au_df["现价"].astype(float).max()
                    low_price = au_df["现价"].astype(float).min()

                    # 获取昨日收盘价（从历史接口）
                    prev_close = None
                    try:
                        hist_df = ak.spot_hist_sge(symbol="Au99.99")
                        if hist_df is not None and len(hist_df) >= 2:
                            prev_close = float(hist_df.iloc[-2].get("close", 0) or 0)
                    except Exception as e:
                        logger.warning(f"获取 Au99.99 历史数据失败: {e}")

                    # 计算涨跌幅
                    change = None
                    change_percent = None
                    if prev_close and prev_close > 0:
                        change = round(price - prev_close, 2)
                        change_percent = round((change / prev_close) * 100, 2)

                    return {
                        "commodity": "gold_cny",
                        "symbol": "Au99.99",
                        "name": "Au99.99 (上海黄金)",
                        "price": price,
                        "change": change,
                        "change_percent": change_percent,
                        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "high": high_price if high_price > 0 else None,
                        "low": low_price if low_price > 0 else None,
                        "open": open_price if open_price and open_price > 0 else None,
                        "prev_close": prev_close,
                        "currency": "CNY",
                        "exchange": "SGE",
                    }
            return None

        async def _fetch_history() -> dict[str, Any] | None:
            """获取历史数据作为备用"""
            df = ak.spot_hist_sge(symbol="Au99.99")
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                trade_date = latest.get("date", "")
                price = float(latest.get("close", 0) or 0)
                open_price = float(latest.get("open", 0) or 0)
                high = float(latest.get("high", 0) or 0)
                low = float(latest.get("low", 0) or 0)
                prev_close = None
                if len(df) >= 2:
                    prev_close = float(df.iloc[-2].get("close", 0) or 0)

                change = None
                change_percent = None
                if prev_close and prev_close > 0:
                    change = round(price - prev_close, 2)
                    change_percent = round((change / prev_close) * 100, 2)

                return {
                    "commodity": "gold_cny",
                    "symbol": "Au99.99",
                    "name": "Au99.99 (上海黄金)",
                    "price": price,
                    "change": change,
                    "change_percent": change_percent,
                    "timestamp": f"{trade_date}T00:00:00Z",
                    "high": high if high > 0 else None,
                    "low": low if low > 0 else None,
                    "open": open_price if open_price > 0 else None,
                    "prev_close": prev_close,
                    "currency": "CNY",
                    "exchange": "SGE",
                }
            return None

        try:
            # 尝试获取实时数据
            result = await _fetch_realtime()
            if result:
                return result
        except Exception as e:
            logger.warning(f"获取沪金实时数据失败，尝试备用接口: {e}")

        # 备用：使用历史数据接口
        try:
            result = await _fetch_history()
            if result:
                return result
        except Exception as e:
            logger.error(f"备用接口也失败: {e}")

        return None

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

    def _is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self._cache:
            return False
        cache_time = self._cache[cache_key].get("_cache_time", 0)
        return (time.time() - cache_time) < self._cache_timeout

    def clear_cache(self):
        self._cache.clear()
        logger.info(f"[{self.name}] 缓存已清空")

    async def close(self):
        """关闭数据源"""
        pass
