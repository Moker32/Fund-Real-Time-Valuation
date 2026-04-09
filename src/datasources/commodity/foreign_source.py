"""AKShare 外盘期货数据源 - 伦敦金属交易所、纽约商品交易所等"""

import asyncio
import logging
import time

from ..base import DataSourceResult
from .base import CommodityDataSource

logger = logging.getLogger(__name__)


# 外盘期货 ticker 映射
FOREIGN_FUTURES_TICKERS: dict[str, str] = {
    "AHD": "aluminum_lme",
    "NID": "nickel_lme",
    "CAD": "copper_lme",
    "ZSD": "zinc_lme",
    "PBD": "lead_lme",
    "SND": "tin_lme",
    "XAU": "gold_london",
    "XAG": "silver_london",
    "XPT": "platinum_london",
    "XPD": "palladium_london",
    "GC": "gold_nymex",
    "SI": "silver_nymex",
    "CL": "wti_nymex",
    "NG": "natural_gas_nymex",
    "HG": "copper_comex",
    "S": "soybean_cbot",
    "W": "wheat_cbot",
    "C": "corn_cbot",
    "BO": "soybean_oil_cbot",
    "SM": "soybean_meal_cbot",
    "CT": "cotton_nybot",
    "RS": "sugar_nybot",
    "OIL": "brent_ice",
    "BTC": "bitcoin_cme",
    "LHC": "lean_hogs_cme",
    "FCPO": "crude_palm_oil",
    "TRB": "rubber_tocom",
    "EUA": "carbon_emissions",
}

# 反向映射: commodity_type -> AKShare symbol
FOREIGN_FUTURES_REVERSE: dict[str, str] = {v: k for k, v in FOREIGN_FUTURES_TICKERS.items()}

FOREIGN_FUTURES_NAMES: dict[str, str] = {
    "aluminum_lme": "LME铝",
    "nickel_lme": "LME镍",
    "copper_lme": "LME铜",
    "zinc_lme": "LME锌",
    "lead_lme": "LME铅",
    "tin_lme": "LME锡",
    "gold_london": "伦敦金",
    "silver_london": "伦敦银",
    "platinum_london": "伦敦铂金",
    "palladium_london": "伦敦钯金",
    "gold_nymex": "COMEX黄金",
    "silver_nymex": "COMEX白银",
    "wti_nymex": "NYMEX原油",
    "natural_gas_nymex": "NYMEX天然气",
    "copper_comex": "COMEX铜",
    "soybean_cbot": "CBOT黄豆",
    "wheat_cbot": "CBOT小麦",
    "corn_cbot": "CBOT玉米",
    "soybean_oil_cbot": "CBOT黄豆油",
    "soybean_meal_cbot": "CBOT黄豆粉",
    "cotton_nybot": "NYBOT棉花",
    "sugar_nybot": "NYBOT原糖",
    "brent_ice": "布伦特原油",
    "bitcoin_cme": "CME比特币",
    "lean_hogs_cme": "CME瘦肉猪",
    "crude_palm_oil": "马棕油",
    "rubber_tocom": "日本橡胶",
    "carbon_emissions": "欧洲碳排放",
}


class AKShareForeignFuturesSource(CommodityDataSource):
    """AKShare 外盘期货数据源 - 伦敦金属交易所、纽约商品交易所等"""

    def __init__(self, timeout: float = 15.0):
        super().__init__(name="akshare_foreign_futures", timeout=timeout)
        self._cache_timeout = 30.0  # 缓存30秒

    async def fetch(self, commodity_type: str = "gold_london") -> DataSourceResult:
        cached_data = self._get_from_cache(commodity_type)
        if cached_data and self._is_cache_valid(commodity_type):
            return DataSourceResult(
                success=True,
                data=cached_data,
                timestamp=cached_data.get("_cache_time", time.time()),
                source=self.name,
                metadata={"commodity_type": commodity_type, "from_cache": "memory"},
            )

        try:
            import akshare as ak

            akshare_symbol = FOREIGN_FUTURES_REVERSE.get(commodity_type)
            if not akshare_symbol:
                logger.debug(f"[AKShare Foreign] 不支持的商品类型: {commodity_type}")
                return DataSourceResult(
                    success=False,
                    error=f"不支持的商品类型: {commodity_type}",
                    timestamp=time.time(),
                    source=self.name,
                )

            df = ak.futures_foreign_hist(symbol=akshare_symbol)
            if df is None or df.empty:
                logger.warning(f"[AKShare Foreign] 无法获取 {commodity_type} 数据")
                return DataSourceResult(
                    success=False,
                    error=f"无法获取 {commodity_type} 数据",
                    timestamp=time.time(),
                    source=self.name,
                )

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) >= 2 else latest

            price = float(latest.get("close", 0) or 0)
            prev_price = float(prev.get("close", 0) or 0)
            change = price - prev_price if prev_price else None
            change_percent = (change / prev_price * 100) if prev_price and change else None

            exchange_map = {
                "aluminum_lme": "LME",
                "nickel_lme": "LME",
                "copper_lme": "LME",
                "zinc_lme": "LME",
                "lead_lme": "LME",
                "tin_lme": "LME",
                "gold_london": "LBMA",
                "silver_london": "LBMA",
                "platinum_london": "LBMA",
                "palladium_london": "LBMA",
                "gold_nymex": "COMEX",
                "silver_nymex": "COMEX",
                "wti_nymex": "NYMEX",
                "natural_gas_nymex": "NYMEX",
                "copper_comex": "COMEX",
                "soybean_cbot": "CBOT",
                "wheat_cbot": "CBOT",
                "corn_cbot": "CBOT",
                "soybean_oil_cbot": "CBOT",
                "soybean_meal_cbot": "CBOT",
                "cotton_nybot": "NYBOT",
                "sugar_nybot": "NYBOT",
                "brent_ice": "ICE",
                "bitcoin_cme": "CME",
                "lean_hogs_cme": "CME",
                "crude_palm_oil": "BMD",
                "rubber_tocom": "TOCOM",
                "carbon_emissions": "ICE",
            }

            data = {
                "commodity": commodity_type,
                "symbol": akshare_symbol,
                "name": FOREIGN_FUTURES_NAMES.get(commodity_type, commodity_type),
                "price": price,
                "change": round(change, 2) if change else None,
                "change_percent": round(change_percent, 2) if change_percent else None,
                "timestamp": f"{latest.get('date')}T00:00:00Z",
                "high": float(latest.get("high", 0)) if latest.get("high") else None,
                "low": float(latest.get("low", 0)) if latest.get("low") else None,
                "open": float(latest.get("open", 0)) if latest.get("open") else None,
                "prev_close": prev_price if prev_price else None,
                "currency": "CNY",
                "exchange": exchange_map.get(commodity_type, "OTHER"),
            }
            data["_cache_time"] = time.time()
            self._add_to_cache(commodity_type, data)

            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
            )

        except Exception as e:
            logger.error(f"[AKShare Foreign] 获取 {commodity_type} 数据失败: {e}")
            return self._handle_error(e, self.name)

    async def fetch_batch(self, commodity_types: list[str]) -> list[DataSourceResult]:
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

    async def close(self):
        pass
