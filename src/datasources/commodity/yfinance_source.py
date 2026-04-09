"""yfinance 商品数据源 - 国际商品期货 + 加密货币"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from ..base import DataSourceResult
from .base import MAX_CACHE_SIZE, CommodityDataSource

logger = logging.getLogger(__name__)


class YFinanceCommoditySource(CommodityDataSource):
    """yfinance 商品数据源"""

    # 并发控制：最多 3 个并发请求
    _semaphore: asyncio.Semaphore | None = None

    # 商品 ticker 映射（yfinance 不支持上海黄金交易所 SG=f）
    COMMODITY_TICKERS = {
        # 贵金属
        "gold": "GC=F",  # COMEX 黄金期货
        "gold_pax": "PAXG-USD",  # Pax Gold (数字黄金)
        "silver": "SI=F",  # 国际白银
        "platinum": "PT=F",  # 铂金
        "palladium": "PA=F",  # 钯金
        # 能源
        "wti": "CL=F",  # WTI 原油
        "brent": "BZ=F",  # 布伦特原油
        "natural_gas": "NG=F",  # 天然气
        # 基本金属
        "copper": "HG=F",  # 铜
        "aluminum": "ALI=F",  # 铝 (LME Aluminum Futures)
        "zinc": "ZN=F",  # 锌
        # 农产品
        "soybean": "ZS=F",  # 大豆
        "corn": "ZC=F",  # 玉米
        "wheat": "ZW=F",  # 小麦
        "coffee": "KC=F",  # 咖啡
        "sugar": "SB=F",  # 白糖
        # 加密货币
        "btc": "BTC-USD",  # 比特币现货
        "btc_futures": "BTC=F",  # 比特币期货
        "eth": "ETH-USD",  # 以太坊现货
        "eth_futures": "ETH=F",  # 以太坊期货
    }

    # yfinance 调用超时时间（秒）
    YFINANCE_TIMEOUT = 10.0

    def __init__(self, timeout: float = 15.0):
        super().__init__(name="yfinance_commodity", timeout=timeout)
        # 加密货币 ticker 映射 (使用 Binance)
        self._crypto_tickers = {
            "btc": "BTCUSDT",
            "eth": "ETHUSDT",
        }

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        """获取并发控制信号量（懒加载）"""
        if cls._semaphore is None:
            cls._semaphore = asyncio.Semaphore(3)
        return cls._semaphore

    async def _fetch_yfinance_info(self, ticker: str) -> dict[str, Any]:
        """
        使用 run_in_executor 获取 yfinance 数据，带超时控制和重试机制

        Args:
            ticker: yfinance ticker 符号

        Returns:
            dict: yfinance info 字典

        Raises:
            asyncio.TimeoutError: 超时
            Exception: 其他错误
        """
        import yfinance as yf

        loop = asyncio.get_event_loop()

        async def _fetch() -> dict[str, Any]:
            async with self._get_semaphore():
                ticker_obj = yf.Ticker(ticker)
                info = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: ticker_obj.info),
                    timeout=self.YFINANCE_TIMEOUT,
                )
                return info

        try:
            return await self._fetch_with_retry(_fetch)
        except asyncio.TimeoutError:
            logger.warning(f"[YFinance] 获取 {ticker} 超时 ({self.YFINANCE_TIMEOUT}s)")
            raise

    async def fetch(self, commodity_type: str = "gold") -> DataSourceResult:
        """
        获取商品数据

        Args:
            commodity_type: 商品类型 (gold, wti, brent, silver, natural_gas)

        Returns:
            DataSourceResult: 商品数据结果
        """
        # 加密货币使用 Binance (实时 ~100ms)
        if commodity_type in self._crypto_tickers:
            return await self._fetch_from_binance(commodity_type)

        # 检查内存缓存（优先检查内存缓存，更快）
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
                    # 移除内部字段
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

        try:
            ticker = self.COMMODITY_TICKERS.get(commodity_type)
            if not ticker:
                logger.debug(f"[YFinance] 不支持的商品类型: {commodity_type}")
                return DataSourceResult(
                    success=False,
                    error=f"不支持的商品类型: {commodity_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"commodity_type": commodity_type},
                )

            logger.debug(f"[YFinance] fetching {commodity_type} -> ticker={ticker}")

            info = await self._fetch_yfinance_info(ticker)

            if not info or info.get("symbol") is None:
                logger.debug(f"[YFinance] ticker {ticker} 返回空数据或 404")

            price = info.get("currentPrice", info.get("regularMarketPrice"))
            change = info.get("regularMarketChange", info.get("change", 0))
            change_percent = info.get("regularMarketChangePercent", info.get("changePercent", 0))

            if price is None:
                return DataSourceResult(
                    success=False,
                    error="无法获取价格数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"commodity_type": commodity_type},
                )

            # 转换时间戳为 UTC ISO 格式
            market_time = info.get("regularMarketTime")
            if market_time:
                try:
                    utc_dt = datetime.fromtimestamp(market_time, timezone.utc)
                    timestamp_str = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                except (ValueError, TypeError, OSError) as e:
                    logger.warning(f"转换时间戳失败: {e}")
                    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            day_high = info.get("dayHigh")
            day_low = info.get("dayLow")
            market_open = info.get("regularMarketOpen")
            prev_close = info.get("regularMarketPreviousClose")

            data = {
                "commodity": commodity_type,
                "symbol": ticker,
                "name": self.get_name(commodity_type),
                "price": float(price),
                "change": float(change) if change else 0.0,
                "change_percent": float(change_percent) if change_percent else 0.0,
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange", ""),
                "timestamp": timestamp_str,
                "high": float(day_high) if day_high else None,
                "low": float(day_low) if day_low else None,
                "open": float(market_open) if market_open else None,
                "prev_close": float(prev_close) if prev_close else None,
            }

            # 更新LRU缓存
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

        except ImportError:
            logger.error("yfinance 未安装")
            return DataSourceResult(
                success=False,
                error="yfinance 未安装，请运行: pip install yfinance",
                timestamp=time.time(),
                source=self.name,
                metadata={"commodity_type": commodity_type, "error_type": "ImportError"},
            )
        except Exception as e:
            logger.error(f"[YFinance] 获取 {commodity_type} 数据失败: {e}")
            return self._handle_error(e, self.name)

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

    def get_name(self, commodity_type: str) -> str:
        """获取商品名称"""
        names = {
            "gold": "黄金 (COMEX)",
            "gold_cny": "沪金",
            "gold_pax": "Pax Gold",
            "wti": "WTI原油",
            "brent": "布伦特原油",
            "silver": "白银",
            "natural_gas": "天然气",
            "platinum": "铂金",
            "palladium": "钯金",
            "copper": "铜",
            "aluminum": "铝",
            "zinc": "锌",
            "nickel": "镍",
            "soybean": "大豆",
            "corn": "玉米",
            "wheat": "小麦",
            "coffee": "咖啡",
            "sugar": "白糖",
            "btc": "比特币",
            "btc_futures": "比特币期货",
            "eth": "以太坊",
            "eth_futures": "以太坊期货",
        }
        return names.get(commodity_type, commodity_type)

    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache:
            return False
        cache_time = self._cache[cache_key].get("_cache_time", 0)
        return (time.time() - cache_time) < self._cache_timeout

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.info(f"[{self.name}] 缓存已清空")

    async def fetch_by_ticker(self, ticker: str) -> DataSourceResult:
        """根据任意 ticker 获取商品数据"""
        # 检查是否是 Binance 加密货币 ticker (如 BTCUSDT, ETHUSDT)
        for commodity_type, symbol in self._crypto_tickers.items():
            if symbol == ticker:
                return await self._fetch_from_binance(commodity_type)

        try:
            # 使用异步方法获取数据（带超时控制和并发控制）
            info = await self._fetch_yfinance_info(ticker)

            price = info.get("currentPrice", info.get("regularMarketPrice"))
            change = info.get("regularMarketChange", info.get("change", 0))
            change_percent = info.get("regularMarketChangePercent", info.get("changePercent", 0))

            if price is None:
                return DataSourceResult(
                    success=False,
                    error=f"无法获取 {ticker} 的价格数据",
                    timestamp=time.time(),
                    source=self.name,
                )

            day_high = info.get("dayHigh")
            day_low = info.get("dayLow")
            market_open = info.get("regularMarketOpen")
            prev_close = info.get("regularMarketPreviousClose")

            market_time = info.get("regularMarketTime")
            if market_time:
                try:
                    utc_dt = datetime.fromtimestamp(market_time, timezone.utc)
                    timestamp_str = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                except (ValueError, TypeError, OSError) as e:
                    logger.warning(f"转换时间戳失败: {e}")
                    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            data = {
                "commodity": ticker.lower(),
                "symbol": ticker,
                "name": info.get("shortName", info.get("longName", ticker)),
                "price": float(price),
                "change": float(change) if change else 0.0,
                "change_percent": float(change_percent) if change_percent else 0.0,
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange", ""),
                "timestamp": timestamp_str,
                "high": float(day_high) if day_high else None,
                "low": float(day_low) if day_low else None,
                "open": float(market_open) if market_open else None,
                "prev_close": float(prev_close) if prev_close else None,
            }

            self._record_success()
            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
            )

        except Exception as e:
            logger.error(f"[YFinance] 获取 ticker {ticker} 数据失败: {e}")
            return self._handle_error(e, self.name)

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态（含缓存信息）"""
        status = super().get_status()
        status["cache_size"] = len(self._cache)
        status["cache_max_size"] = MAX_CACHE_SIZE
        status["cache_timeout"] = self._cache_timeout
        status["supported_commodities"] = list(self.COMMODITY_TICKERS.keys())
        # 标记预留商品
        reserved = ["platinum", "palladium", "copper", "aluminum", "zinc", "nickel"]
        status["reserved_commodities"] = reserved
        return status

    async def close(self):
        """关闭数据源（yfinance 不需要显式关闭）"""
        pass

    async def _fetch_from_binance(self, commodity_type: str) -> DataSourceResult:
        """从 Binance 获取加密货币数据"""

        symbol = self._crypto_tickers.get(commodity_type)
        if not symbol:
            return DataSourceResult(
                success=False,
                error=f"不支持的加密货币: {commodity_type}",
                timestamp=time.time(),
                source=self.name,
            )

        async def _fetch() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://api.binance.com/api/v3/ticker/24hr"
                response = await client.get(url, params={"symbol": symbol})
                response.raise_for_status()
                return response.json()

        try:
            data = await self._fetch_with_retry(_fetch)

            crypto_names = {
                "btc": "比特币",
                "eth": "以太坊",
            }

            result_data = {
                "commodity": commodity_type,
                "symbol": symbol,
                "name": crypto_names.get(commodity_type, commodity_type),
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

            cache_key = commodity_type
            result_data["_cache_time"] = time.time()
            self._add_to_cache(cache_key, result_data)

            await self._save_to_database(commodity_type, result_data, self.name)

            self._record_success()
            return DataSourceResult(
                success=True,
                data=result_data,
                timestamp=time.time(),
                source=self.name,
                metadata={"commodity_type": commodity_type, "source": "binance"},
            )

        except Exception as e:
            logger.error(f"[Binance] 获取 {commodity_type} 数据失败: {e}")
            return self._handle_error(e, self.name)
