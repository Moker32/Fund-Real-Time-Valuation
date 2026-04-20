"""大宗商品实时数据源 - akshare 国际期货 + Binance BTC

数据源：
- akshare futures_foreign_commodity_realtime() 获取 6 个国际商品实时行情
- Binance ticker 获取 BTC 实时行情

支持的商品（commodity_type → akshare symbol）：
- gold → GC (COMEX黄金)
- silver → SI (COMEX白银)
- platinum → XPT (伦敦铂金)
- wti → CL (NYMEX WTI原油)
- brent → OIL (布伦特原油)
- natural_gas → NG (NYMEX天然气)
- btc → BTCUSDT (Binance)
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from ..base import DataSourceResult
from .base import CommodityDataSource

logger = logging.getLogger(__name__)


class CommodityRealtimeSource(CommodityDataSource):
    """akshare 国际大宗商品实时行情 + Binance BTC"""

    # commodity_type → akshare futures_foreign_commodity_realtime symbol
    AKSHARE_SYMBOLS: dict[str, str] = {
        "gold": "GC",
        "silver": "SI",
        "platinum": "XPT",
        "wti": "CL",
        "brent": "OIL",
        "natural_gas": "NG",
    }

    AKSHARE_NAMES: dict[str, str] = {
        "gold": "黄金 (COMEX)",
        "silver": "白银 (COMEX)",
        "platinum": "铂金 (伦敦)",
        "wti": "WTI原油 (NYMEX)",
        "brent": "布伦特原油 (ICE)",
        "natural_gas": "天然气 (NYMEX)",
    }

    AKSHARE_EXCHANGES: dict[str, str] = {
        "gold": "COMEX",
        "silver": "COMEX",
        "platinum": "LBMA",
        "wti": "NYMEX",
        "brent": "ICE",
        "natural_gas": "NYMEX",
    }

    def __init__(self, timeout: float = 15.0):
        super().__init__(name="commodity_realtime", timeout=timeout)

    async def fetch(self, commodity_type: str = "gold") -> DataSourceResult:
        """获取单个商品实时数据"""
        # 检查内存缓存（30秒有效）
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

        # BTC 走 Binance
        if commodity_type == "btc":
            return await self._fetch_btc()

        # 其他 6 个商品走 akshare
        if commodity_type not in self.AKSHARE_SYMBOLS:
            logger.debug(f"[CommodityRealtime] 不支持的商品类型: {commodity_type}")
            return DataSourceResult(
                success=False,
                error=f"不支持的商品类型: {commodity_type}",
                timestamp=time.time(),
                source=self.name,
                metadata={"commodity_type": commodity_type},
            )

        try:
            return await self._fetch_akshare_realtime(commodity_type)
        except Exception as e:
            logger.error(f"[CommodityRealtime] 获取 {commodity_type} 数据失败: {e}")
            return self._handle_error(e, self.name)

    async def _fetch_akshare_realtime(self, commodity_type: str) -> DataSourceResult:
        """通过 akshare futures_foreign_commodity_realtime 获取实时行情"""
        symbol = self.AKSHARE_SYMBOLS[commodity_type]

        loop = asyncio.get_event_loop()

        async def _fetch() -> dict[str, Any]:
            import akshare as ak

            data = await loop.run_in_executor(
                None, lambda: ak.futures_foreign_commodity_realtime(symbol=symbol)
            )
            return data

        try:
            data = await self._fetch_with_retry(_fetch)

            # akshare 返回 DataFrame 或 dict，统一提取字段
            row = None
            if isinstance(data, dict):
                row = data
            elif hasattr(data, "iloc") and len(data) > 0:
                row = data.iloc[-1].to_dict()
            else:
                raise ValueError(f"无法解析 {symbol} 返回数据: {type(data)}")

            price = float(row.get("最新价", 0) or 0)
            change = float(row.get("涨跌额", 0) or 0)
            change_percent = float(row.get("涨跌幅", 0) or 0)
            prev_close = float(row.get("昨日结算价", 0) or 0) if row.get("昨日结算价") else None

            result_data = {
                "commodity": commodity_type,
                "symbol": symbol,
                "name": self.AKSHARE_NAMES.get(commodity_type, commodity_type),
                "price": price,
                "change": change,
                "change_percent": change_percent,
                "currency": "USD",
                "exchange": self.AKSHARE_EXCHANGES.get(commodity_type, "OTHER"),
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "high": float(row.get("最高价", 0) or 0) if row.get("最高价") else None,
                "low": float(row.get("最低价", 0) or 0) if row.get("最低价") else None,
                "open": float(row.get("开盘价", 0) or 0) if row.get("开盘价") else None,
                "prev_close": prev_close,
            }

            result_data["_cache_time"] = time.time()
            self._add_to_cache(commodity_type, result_data)
            await self._save_to_database(commodity_type, result_data, self.name)
            self._record_success()

            return DataSourceResult(
                success=True,
                data=result_data,
                timestamp=time.time(),
                source=self.name,
                metadata={"commodity_type": commodity_type, "source": "akshare"},
            )

        except ImportError:
            logger.error("akshare 未安装")
            return DataSourceResult(
                success=False,
                error="akshare 未安装",
                timestamp=time.time(),
                source=self.name,
                metadata={"commodity_type": commodity_type, "error_type": "ImportError"},
            )

    async def _fetch_btc(self) -> DataSourceResult:
        """从 Binance 获取 BTC 实时行情"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            response = await client.get(url, params={"symbol": "BTCUSDT"})
            response.raise_for_status()
            data = response.json()

        result_data = {
            "commodity": "btc",
            "symbol": "BTCUSDT",
            "name": "比特币 (Binance)",
            "price": float(data.get("lastPrice", 0)),
            "change": float(data.get("priceChange", 0)),
            "change_percent": float(data.get("priceChangePercent", 0)),
            "currency": "USDT",
            "exchange": "Binance",
            "high": float(data.get("highPrice", 0)),
            "low": float(data.get("lowPrice", 0)),
            "open": float(data.get("openPrice", 0)),
            "prev_close": float(data.get("prevClosePrice", 0)),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        cache_key = "btc"
        result_data["_cache_time"] = time.time()
        self._add_to_cache(cache_key, result_data)
        await self._save_to_database("btc", result_data, self.name)
        self._record_success()

        return DataSourceResult(
            success=True,
            data=result_data,
            timestamp=time.time(),
            source=self.name,
            metadata={"commodity_type": "btc", "source": "binance"},
        )

    async def fetch_batch(self, commodity_types: list[str]) -> list[DataSourceResult]:
        """批量获取商品数据"""

        async def fetch_one(ctype: str) -> DataSourceResult:
            return await self.fetch(ctype)

        tasks = [fetch_one(ctype) for ctype in commodity_types]
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

    async def fetch_all(self) -> DataSourceResult:
        """获取所有商品的实时数据（供推送循环使用）"""
        all_types = get_all_commodity_types()
        results = await self.fetch_batch(all_types)

        all_data = []
        for result in results:
            if result.success and result.data:
                all_data.append(result.data)

        if not all_data:
            return DataSourceResult(
                success=False,
                error="所有商品数据获取失败",
                timestamp=time.time(),
                source=self.name,
            )

        return DataSourceResult(
            success=True,
            data=all_data,
            timestamp=time.time(),
            source=self.name,
            metadata={"commodity_count": len(all_data), "from_cache": "memory"},
        )

    async def close(self):
        """关闭数据源"""
        pass
