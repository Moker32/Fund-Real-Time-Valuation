"""
全球市场指数数据源模块
实现从 yfinance 获取全球主要市场指数数据
- A股: 上证指数、深证成指、上证50、创业板指、科创50、中证500、中证1000、沪深300、中证全指
- 港股: 恒生指数
- 亚太: 日经225
- 美股: 道琼斯、纳斯达克、标普500
- 欧洲: 德国DAX、英国富时100、法国CAC40
"""

import asyncio
import time
from datetime import datetime
from typing import Any

from .base import DataSource, DataSourceResult, DataSourceType

# 全球指数 ticker 映射 (使用 Yahoo Finance 格式)
INDEX_TICKERS = {
    # A股 (使用 SSE/SZSE 代码)
    "shanghai": "000001.SS",     # 上证指数
    "shenzhen": "399001.SZ",      # 深证成指
    "shanghai50": "000016.SS",    # 上证 50
    "chi_next": "399006.SZ",      # 创业板指
    "star50": "000688.SS",        # 科创 50
    "csi500": "000905.SS",        # 中证 500
    "csi1000": "000852.SS",       # 中证 1000
    "hs300": "000300.SS",         # 沪深 300
    "csiall": "000985.SS",        # 中证全指
    # 港股
    "hang_seng": "^HSI",
    # 亚太
    "nikkei225": "^N225",
    # 美股
    "dow_jones": "^DJI",
    "nasdaq": "^IXIC",
    "sp500": "^GSPC",
    # 欧洲
    "dax": "^GDAXI",
    "ftse": "^FTSE",
    "cac40": "^FCHI",
}


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
