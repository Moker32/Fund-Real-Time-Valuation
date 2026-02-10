"""
加密货币数据源模块
实现从 Binance 和 CoinGecko 获取加密货币数据
"""

import asyncio
import time
from typing import Any

import httpx

from .base import (
    DataSource,
    DataSourceResult,
    DataSourceType,
)


class BinanceCryptoSource(DataSource):
    """Binance API 加密货币数据源"""

    def __init__(self, timeout: float = 10.0):
        """
        初始化 Binance 加密货币数据源

        Args:
            timeout: 请求超时时间(秒)
        """
        super().__init__(
            name="binance_crypto",
            source_type=DataSourceType.CRYPTO,
            timeout=timeout
        )
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
        )
        # 常用交易对
        self.common_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]

    async def fetch(self, symbol: str = "BTCUSDT") -> DataSourceResult:
        """获取加密货币行情

        Args:
            symbol: 交易对 (如: BTCUSDT, ETHUSDT)

        Returns:
            DataSourceResult: 加密货币数据结果
        """
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            params = {"symbol": symbol.upper()}

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            result_data = {
                "symbol": data.get("symbol"),
                "price": float(data.get("lastPrice", 0)),
                "change": float(data.get("priceChange", 0)),
                "change_pct": float(data.get("priceChangePercent", 0)),
                "high": float(data.get("highPrice", 0)),
                "low": float(data.get("lowPrice", 0)),
                "volume": float(data.get("volume", 0)),
                "quote_volume": float(data.get("quoteVolume", 0)),
            }

            self._record_success()
            return DataSourceResult(
                success=True,
                data=result_data,
                timestamp=time.time(),
                source=self.name,
                metadata={"symbol": symbol}
            )
        except httpx.ConnectTimeout:
            return DataSourceResult(
                success=False,
                error="连接超时，请检查网络连接或代理设置",
                timestamp=time.time(),
                source=self.name,
                metadata={"symbol": symbol, "error_type": "ConnectTimeout"}
            )
        except httpx.HTTPStatusError as e:
            return DataSourceResult(
                success=False,
                error=f"HTTP 错误: {e.response.status_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"symbol": symbol, "error_type": "HTTPStatusError"}
            )
        except Exception as e:
            error_msg = str(e)
            if "Connect" in error_msg:
                return DataSourceResult(
                    success=False,
                    error="网络连接失败，请检查网络连接",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"symbol": symbol, "error_type": "ConnectionError"}
                )
            return self._handle_error(e, self.name)

    async def fetch_batch(self, symbols: list[str]) -> list[DataSourceResult]:
        """批量获取加密货币数据

        Args:
            symbols: 交易对列表

        Returns:
            List[DataSourceResult]: 数据源结果列表
        """
        async def fetch_one(sym: str) -> DataSourceResult:
            return await self.fetch(sym)

        tasks = [fetch_one(sym) for sym in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"symbol": symbols[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["common_symbols"] = self.common_symbols
        return status

    async def health_check(self) -> bool:
        """
        健康检查 - Binance API

        Returns:
            bool: 健康状态
        """
        try:
            url = "https://api.binance.com/api/v3/ping"
            response = await self.client.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.status_code == 200
        except Exception:
            return False


class CoinGeckoCryptoSource(DataSource):
    """CoinGecko API 加密货币数据源"""

    # 常用币种 ID 映射
    COIN_IDS = {
        "bitcoin": "BTC",
        "ethereum": "ETH",
        "solana": "SOL",
        "binancecoin": "BNB",
        "ripple": "XRP",
        "cardano": "ADA",
        "dogecoin": "DOGE",
        "polkadot": "DOT",
        "polygon": "MATIC",
        "chainlink": "LINK",
    }

    def __init__(self, timeout: float = 15.0):
        """
        初始化 CoinGecko 加密货币数据源

        Args:
            timeout: 请求超时时间(秒)
        """
        super().__init__(
            name="coingecko_crypto",
            source_type=DataSourceType.CRYPTO,
            timeout=timeout
        )
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            }
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timeout = 60.0  # 缓存60秒

    async def fetch(self, coin_id: str = "bitcoin") -> DataSourceResult:
        """获取加密货币数据

        Args:
            coin_id: 币种 ID (如: bitcoin, ethereum, solana)

        Returns:
            DataSourceResult: 加密货币数据结果
        """
        # 检查缓存
        cache_key = coin_id.lower()
        if self._is_cache_valid(cache_key):
            return DataSourceResult(
                success=True,
                data=self._cache[cache_key],
                timestamp=self._cache[cache_key].get("_cache_time", time.time()),
                source=self.name,
                metadata={"coin_id": coin_id, "from_cache": True}
            )

        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id.lower(),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
                "include_24hr_vol": "true"
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            coin_data = data.get(coin_id.lower(), {})
            if not coin_data:
                return DataSourceResult(
                    success=False,
                    error=f"未找到币种: {coin_id}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"coin_id": coin_id}
                )

            symbol = self.COIN_IDS.get(coin_id.lower(), coin_id.upper())
            result_data = {
                "id": coin_id,
                "symbol": symbol,
                "name": self._get_name(coin_id),
                "current_price": coin_data.get("usd"),
                "price_change_24h": coin_data.get("usd_24h_change", 0),
                "market_cap": coin_data.get("usd_market_cap"),
                "volume_24h": coin_data.get("usd_24h_vol"),
            }

            # 缓存数据
            result_data["_cache_time"] = time.time()
            self._cache[cache_key] = result_data

            self._record_success()
            return DataSourceResult(
                success=True,
                data=result_data,
                timestamp=time.time(),
                source=self.name,
                metadata={"coin_id": coin_id}
            )
        except httpx.ConnectTimeout:
            return DataSourceResult(
                success=False,
                error="连接超时，请检查网络连接或代理设置",
                timestamp=time.time(),
                source=self.name,
                metadata={"coin_id": coin_id, "error_type": "ConnectTimeout"}
            )
        except httpx.HTTPStatusError as e:
            return DataSourceResult(
                success=False,
                error=f"HTTP 错误: {e.response.status_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"coin_id": coin_id, "error_type": "HTTPStatusError"}
            )
        except Exception as e:
            error_msg = str(e)
            if "Connect" in error_msg:
                return DataSourceResult(
                    success=False,
                    error="网络连接失败，请检查网络连接",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"coin_id": coin_id, "error_type": "ConnectionError"}
                )
            return self._handle_error(e, self.name)

    async def fetch_batch(self, coin_ids: list[str]) -> list[DataSourceResult]:
        """批量获取加密货币数据

        Args:
            coin_ids: 币种 ID 列表

        Returns:
            List[DataSourceResult]: 数据源结果列表
        """
        async def fetch_one(coin_id: str) -> DataSourceResult:
            return await self.fetch(coin_id)

        tasks = [fetch_one(coin_id) for coin_id in coin_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"coin_id": coin_ids[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def _get_name(self, coin_id: str) -> str:
        """获取币种显示名称"""
        names = {
            "bitcoin": "Bitcoin",
            "ethereum": "Ethereum",
            "solana": "Solana",
            "binancecoin": "Binance Coin",
            "ripple": "XRP",
            "cardano": "Cardano",
            "dogecoin": "Dogecoin",
            "polkadot": "Polkadot",
            "polygon": "Polygon",
            "chainlink": "Chainlink",
        }
        return names.get(coin_id.lower(), coin_id.capitalize())

    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache:
            return False
        cache_time = self._cache[cache_key].get("_cache_time", 0)
        return (time.time() - cache_time) < self._cache_timeout

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["cache_size"] = len(self._cache)
        status["cache_timeout"] = self._cache_timeout
        status["supported_coins"] = list(self.COIN_IDS.keys())
        return status

    async def health_check(self) -> bool:
        """
        健康检查 - CoinGecko API

        Returns:
            bool: 健康状态
        """
        try:
            url = "https://api.coingecko.com/api/v3/ping"
            response = await self.client.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data.get("gecko_says", "") == "To the Moon!"
        except Exception:
            return False


class CryptoAggregator(DataSource):
    """加密货币数据聚合器 - 支持多数据源自动切换"""

    def __init__(self, timeout: float = 15.0):
        """
        初始化加密货币数据聚合器

        Args:
            timeout: 请求超时时间(秒)
        """
        super().__init__(
            name="crypto_aggregator",
            source_type=DataSourceType.CRYPTO,
            timeout=timeout
        )
        self._sources: list[DataSource] = []
        self._primary_source: DataSource | None = None

    def add_source(self, source: DataSource, is_primary: bool = False):
        """添加数据源

        Args:
            source: 数据源实例
            is_primary: 是否作为主数据源
        """
        self._sources.append(source)
        if is_primary or self._primary_source is None:
            self._primary_source = source

    async def fetch(self, symbol: str = "BTCUSDT") -> DataSourceResult:
        """获取加密货币数据，尝试多个数据源

        Args:
            symbol: 交易对或币种 ID
        """
        errors = []

        # 优先使用主数据源
        if self._primary_source:
            try:
                result = await self._primary_source.fetch(symbol)
                if result.success:
                    return result
                errors.append(f"{self._primary_source.name}: {result.error}")
            except Exception as e:
                errors.append(f"{self._primary_source.name}: {str(e)}")

        # 尝试其他数据源
        for source in self._sources:
            if source == self._primary_source:
                continue
            try:
                result = await source.fetch(symbol)
                if result.success:
                    return result
                errors.append(f"{source.name}: {result.error}")
            except Exception as e:
                errors.append(f"{source.name}: {str(e)}")

        return DataSourceResult(
            success=False,
            error=f"所有数据源均失败: {'; '.join(errors)}",
            timestamp=time.time(),
            source=self.name,
            metadata={"symbol": symbol, "errors": errors}
        )

    async def fetch_batch(self, symbols: list[str]) -> list[DataSourceResult]:
        """批量获取加密货币数据"""
        tasks = [self.fetch(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"symbol": symbols[i]}
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
            if hasattr(source, 'close'):
                try:
                    await source.close()
                except Exception:
                    pass


__all__ = ["BinanceCryptoSource", "CoinGeckoCryptoSource", "CryptoAggregator"]
