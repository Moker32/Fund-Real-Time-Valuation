"""
全球市场指数数据源模块
实现混合数据源策略：
- A股/港股/美股: 腾讯财经 (实时)
- 日经/欧洲: yfinance (有延迟)
"""

import asyncio
import re
import time
from datetime import datetime
from typing import Any

import httpx

from .base import DataSource, DataSourceResult, DataSourceType

# 腾讯财经代码映射 (A股、港股、美股)
TENCENT_CODES = {
    # A股 (s_ 前缀)
    "shanghai": "s_sh000001",
    "shenzhen": "s_sz399001",
    "shanghai50": "s_sh000016",
    "chi_next": "s_sz399006",
    "star50": "s_sh000688",
    "csi500": "s_sh000905",
    "csi1000": "s_sh000852",
    "hs300": "s_sh000300",
    "csiall": "s_sh000001",  # 暂用上证指数
    # 港股 (hk 前缀)
    "hang_seng": "hkHSI",
    # 美股 (us 前缀)
    "dow_jones": "usDJI",
    "nasdaq": "usIXIC",
    "sp500": "usINX",
}

# Yahoo Finance ticker 映射 (日经、欧洲)
YAHOO_TICKERS = {
    # 日经
    "nikkei225": "^N225",
    # 欧洲
    "dax": "^GDAXI",
    "ftse": "^FTSE",
    "cac40": "^FCHI",
}

# 合并所有 ticker 映射
INDEX_TICKERS = {**TENCENT_CODES, **YAHOO_TICKERS}


# 判断是否使用腾讯财经
def uses_tencent(index_type: str) -> bool:
    """判断是否使用腾讯财经数据源"""
    return index_type in TENCENT_CODES


# 指数区域分组
INDEX_REGIONS = {
    "shanghai": "china",
    "shenzhen": "china",
    "shanghai50": "china",
    "chi_next": "china",
    "star50": "china",
    "csi500": "china",
    "csi1000": "china",
    "hs300": "china",
    "csiall": "china",
    "hang_seng": "hk",
    "nikkei225": "asia",
    "dow_jones": "america",
    "nasdaq": "america",
    "sp500": "america",
    "dax": "europe",
    "ftse": "europe",
    "cac40": "europe",
}


# 指数中文名称
INDEX_NAMES = {
    "shanghai": "上证指数",
    "shenzhen": "深证成指",
    "shanghai50": "上证 50",
    "chi_next": "创业板指",
    "star50": "科创 50",
    "csi500": "中证 500",
    "csi1000": "中证 1000",
    "hs300": "沪深 300",
    "csiall": "中证全指",
    "hang_seng": "恒生指数",
    "nikkei225": "日经 225",
    "dow_jones": "道琼斯",
    "nasdaq": "纳斯达克",
    "sp500": "标普 500",
    "dax": "德国 DAX",
    "ftse": "富时 100",
    "cac40": "CAC 40",
}


# 各市场开盘时间段 (UTC 时间)
MARKET_HOURS = {
    # A股 (9:30-15:00 UTC+8)
    "shanghai": {"open": "01:30", "close": "08:00", "tz": "Asia/Shanghai"},
    "shenzhen": {"open": "01:30", "close": "08:00", "tz": "Asia/Shanghai"},
    "shanghai50": {"open": "01:30", "close": "08:00", "tz": "Asia/Shanghai"},
    "chi_next": {"open": "01:30", "close": "08:00", "tz": "Asia/Shanghai"},
    "star50": {"open": "01:30", "close": "08:00", "tz": "Asia/Shanghai"},
    "csi500": {"open": "01:30", "close": "08:00", "tz": "Asia/Shanghai"},
    "csi1000": {"open": "01:30", "close": "08:00", "tz": "Asia/Shanghai"},
    "hs300": {"open": "01:30", "close": "08:00", "tz": "Asia/Shanghai"},
    "csiall": {"open": "01:30", "close": "08:00", "tz": "Asia/Shanghai"},
    # 港股 (9:30-16:00 UTC+8)
    "hang_seng": {"open": "01:30", "close": "09:00", "tz": "Asia/Hong_Kong"},
    # 日经 (9:00-15:00 UTC+9)
    "nikkei225": {"open": "00:00", "close": "06:00", "tz": "Asia/Tokyo"},
    # 欧洲 (9:00-17:30 CET)
    "dax": {"open": "08:00", "close": "16:30", "tz": "Europe/Berlin"},
    "ftse": {"open": "08:00", "close": "16:30", "tz": "Europe/London"},
    "cac40": {"open": "08:00", "close": "16:30", "tz": "Europe/Paris"},
    # 美股 (9:30-16:00 EST)
    "dow_jones": {"open": "14:30", "close": "21:00", "tz": "America/New_York"},
    "nasdaq": {"open": "14:30", "close": "21:00", "tz": "America/New_York"},
    "sp500": {"open": "14:30", "close": "21:00", "tz": "America/New_York"},
}


class IndexDataSource(DataSource):
    """全球指数数据源基类"""

    def __init__(self, name: str, timeout: float = 30.0):
        """
        初始化指数数据源

        Args:
            name: 数据源名称
            timeout: 请求超时时间(秒)
        """
        super().__init__(
            name=name,
            source_type=DataSourceType.STOCK,  # 复用 STOCK 类型
            timeout=timeout
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timeout = 60.0  # 缓存60秒

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
        """关闭数据源"""
        pass


class YahooIndexSource(IndexDataSource):
    """Yahoo Finance 全球指数数据源"""

    def __init__(self, timeout: float = 30.0):
        super().__init__(
            name="yfinance_index",
            timeout=timeout
        )

    async def fetch(self, index_type: str) -> DataSourceResult:
        """
        获取单个指数数据

        Args:
            index_type: 指数类型 (如 shanghai, nasdaq, dax 等)

        Returns:
            DataSourceResult: 指数数据结果
        """
        cache_key = index_type
        if self._is_cache_valid(cache_key):
            return DataSourceResult(
                success=True,
                data=self._cache[cache_key],
                timestamp=self._cache[cache_key].get("_cache_time", time.time()),
                source=self.name,
                metadata={"index_type": index_type, "from_cache": True}
            )

        try:
            import yfinance as yf

            ticker = INDEX_TICKERS.get(index_type)
            if not ticker:
                return DataSourceResult(
                    success=False,
                    error=f"不支持的指数类型: {index_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type}
                )

            # 获取数据
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            price = info.get('currentPrice', info.get('regularMarketPrice'))
            change = info.get('regularMarketChange', info.get('change', 0))
            change_percent = info.get('regularMarketChangePercent', info.get('changePercent', 0))

            if price is None:
                return DataSourceResult(
                    success=False,
                    error="无法获取价格数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type}
                )

            # 转换时间戳为可读格式
            market_time = info.get('regularMarketTime')
            if market_time:
                try:
                    time_str = datetime.fromtimestamp(market_time).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError, OSError):
                    time_str = str(market_time)
            else:
                time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            data = {
                "index": index_type,
                "symbol": ticker,
                "name": INDEX_NAMES.get(index_type, index_type),
                "price": float(price),
                "change": float(change) if change else 0.0,
                "change_percent": float(change_percent) if change_percent else 0.0,
                "currency": info.get('currency', 'USD'),
                "exchange": info.get('exchange', ''),
                "time": time_str,
                "high": info.get('regularMarketDayHigh'),
                "low": info.get('regularMarketDayLow'),
                "open": info.get('regularMarketOpen'),
                "prev_close": info.get('regularMarketPreviousClose'),
                "region": INDEX_REGIONS.get(index_type, 'unknown'),
                "market_hours": MARKET_HOURS.get(index_type, {}),
            }

            # 缓存数据
            data["_cache_time"] = time.time()
            self._cache[cache_key] = data

            self._record_success()
            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type}
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="yfinance 未安装，请运行: pip install yfinance",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type, "error_type": "ImportError"}
            )
        except Exception as e:
            return self._handle_error(e, self.name)

    async def fetch_batch(self, index_types: list[str]) -> list[DataSourceResult]:
        """批量获取指数数据"""
        async def fetch_one(itype: str) -> DataSourceResult:
            return await self.fetch(itype)

        tasks = [fetch_one(itype) for itype in index_types]
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
                        metadata={"index_type": index_types[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["cache_size"] = len(self._cache)
        status["cache_timeout"] = self._cache_timeout
        status["supported_indices"] = list(INDEX_TICKERS.keys())
        return status


class TencentIndexSource(IndexDataSource):
    """腾讯财经指数数据源 (A股、港股、美股 - 实时)"""

    def __init__(self, timeout: float = 10.0):
        super().__init__(
            name="tencent_index",
            timeout=timeout
        )
        self.base_url = "https://qt.gtimg.cn/q"

    async def fetch(self, index_type: str) -> DataSourceResult:
        """
        获取单个指数数据

        Args:
            index_type: 指数类型 (如 shanghai, hang_seng, dow_jones 等)

        Returns:
            DataSourceResult: 指数数据结果
        """
        cache_key = f"tencent_{index_type}"
        if self._is_cache_valid(cache_key):
            return DataSourceResult(
                success=True,
                data=self._cache[cache_key],
                timestamp=self._cache[cache_key].get("_cache_time", time.time()),
                source=self.name,
                metadata={"index_type": index_type, "from_cache": True}
            )

        try:
            tencent_code = TENCENT_CODES.get(index_type)
            if not tencent_code:
                return DataSourceResult(
                    success=False,
                    error=f"腾讯财经不支持的指数类型: {index_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type}
                )

            url = f"{self.base_url}={tencent_code}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                text = response.text.strip()

            if "none_match" in text or not text:
                return DataSourceResult(
                    success=False,
                    error=f"未找到指数数据: {index_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type}
                )

            # 解析数据
            # 格式: v_usDJI="200~道琼斯~.DJI~49451.98~50121.40~...";
            match = re.search(r'="([^"]+)"', text)
            if not match:
                return DataSourceResult(
                    success=False,
                    error="解析腾讯财经数据失败",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type}
                )

            parts = match.group(1).split("~")

            # 判断市场类型
            is_us = tencent_code.startswith("us")
            is_hk = tencent_code.startswith("hk")

            if is_us:
                # 美股格式
                price = float(parts[3]) if parts[3] else 0.0
                change = float(parts[32]) if len(parts) > 32 and parts[32] else 0.0
                # 涨跌幅计算
                if price > 0 and change != 0:
                    change_percent = (change / (price - change)) * 100
                else:
                    change_percent = 0.0
                currency = "USD"
                exchange = "US"
            elif is_hk:
                # 港股格式: 3=当前价, 4=昨日收盘
                price = float(parts[3]) if parts[3] else 0.0
                prev_close = float(parts[4]) if parts[4] else 0.0
                change = price - prev_close  # 直接计算涨跌
                if price > 0 and prev_close > 0:
                    change_percent = (change / prev_close) * 100
                else:
                    change_percent = 0.0
                currency = "HKD"
                exchange = "HKEX"
            else:
                # A股格式
                price = float(parts[3]) if parts[3] else 0.0
                change = float(parts[4]) if parts[4] else 0.0
                change_percent = float(parts[5]) if parts[5] else 0.0
                currency = "CNY"
                exchange = "SSE" if tencent_code.startswith("s_sh") else "SZSE"

            # 获取当前时间作为数据时间
            time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            data = {
                "index": index_type,
                "symbol": tencent_code,
                "name": INDEX_NAMES.get(index_type, index_type),
                "price": price,
                "change": change,
                "change_percent": change_percent,
                "currency": currency,
                "exchange": exchange,
                "time": time_str,
                "high": None,  # 腾讯财经不提供这些字段
                "low": None,
                "open": None,
                "prev_close": None,
                "region": INDEX_REGIONS.get(index_type, "unknown"),
                "market_hours": MARKET_HOURS.get(index_type, {}),
            }

            # 缓存数据
            data["_cache_time"] = time.time()
            self._cache[cache_key] = data

            self._record_success()
            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type}
            )

        except httpx.HTTPError as e:
            return self._handle_error(e, self.name)
        except Exception as e:
            return self._handle_error(e, self.name)

    async def fetch_batch(self, index_types: list[str]) -> list[DataSourceResult]:
        """批量获取指数数据"""
        async def fetch_one(itype: str) -> DataSourceResult:
            return await self.fetch(itype)

        tasks = [fetch_one(itype) for itype in index_types]
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
                        metadata={"index_type": index_types[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["cache_size"] = len(self._cache)
        status["cache_timeout"] = self._cache_timeout
        status["data_sources"] = {
            "tencent": "A股/港股/美股 (实时)",
            "yahoo": "日经/欧洲 (延迟)"
        }
        return status


class HybridIndexSource(IndexDataSource):
    """混合指数数据源
    根据指数类型自动选择最佳数据源:
    - A股/港股/美股 -> 腾讯财经 (实时)
    - 日经/欧洲 -> yfinance (有延迟)
    """

    def __init__(self, timeout: float = 30.0):
        super().__init__(
            name="hybrid_index",
            timeout=timeout
        )
        self._tencent = TencentIndexSource(timeout=10.0)
        self._yahoo = YahooIndexSource(timeout=timeout)

    async def fetch(self, index_type: str) -> DataSourceResult:
        """获取指数数据，自动选择数据源"""
        # 根据指数类型选择数据源
        if uses_tencent(index_type):
            return await self._tencent.fetch(index_type)
        else:
            return await self._yahoo.fetch(index_type)

    async def fetch_batch(self, index_types: list[str]) -> list[DataSourceResult]:
        """批量获取指数数据"""
        async def fetch_one(itype: str) -> DataSourceResult:
            return await self.fetch(itype)

        tasks = [fetch_one(itype) for itype in index_types]
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
                        metadata={"index_type": index_types[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def clear_cache(self):
        """清空所有缓存"""
        super().clear_cache()
        self._tencent.clear_cache()
        self._yahoo.clear_cache()

    async def close(self):
        """关闭数据源"""
        await self._tencent.close()
        await self._yahoo.close()

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["tencent_status"] = self._tencent.get_status()
        status["yahoo_status"] = self._yahoo.get_status()
        return status
