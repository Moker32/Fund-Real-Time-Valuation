"""
全球市场指数数据源模块
实现混合数据源策略：
- A股/港股/美股: 腾讯财经 (实时)
- 日经/欧洲: yfinance (有延迟)
- AKShare 实时接口: 带优化配置的备用数据源
"""

import asyncio
import logging
import re
import time
from datetime import datetime
from typing import Any

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

from .akshare_config import (
    DEFAULT_RATE_LIMIT,
    MAX_RETRIES,
    call_akshare_with_retry,
)
from .base import DataSource, DataSourceResult, DataSourceType

# 腾讯财经代码映射 (A股、港股、美股)
TENCENT_CODES = {
    # A股 (无 s_ 前缀才能获取完整盘口数据)
    "shanghai": "sh000001",
    "shenzhen": "sz399001",
    "shanghai50": "sh000016",
    "chi_next": "sz399006",
    "star50": "sh000688",
    "csi500": "sh000905",
    "csi1000": "sh000852",
    "hs300": "sh000300",
    "csiall": "sh000985",  # 中证全指
    # 港股 (hk 前缀)
    "hang_seng": "hkHSI",
    "hang_seng_tech": "hkHSTECH",  # 恒生科技
    # 美股 (us 前缀，腾讯财经格式)
    # 注意：腾讯财经支持道琼斯、纳斯达克和标普500
    "dow_jones": "usDJI",
    "nasdaq": "usIXIC",
    "sp500": "usINX",  # 腾讯财经代码是 usINX 不是 usGSPC
}

# Yahoo Finance ticker 映射 (只包含有历史数据的指数)
YAHOO_TICKERS = {
    # 日经
    "nikkei225": "^N225",
    # 欧洲
    "dax": "^GDAXI",
    "ftse": "^FTSE",
    "cac40": "^FCHI",
    # 港股
    "hang_seng": "^HSI",
    "hang_seng_tech": "HSTECH.HK",
    # 美股 (作为腾讯财经的回退)
    "dow_jones": "^DJI",
    "nasdaq": "^IXIC",
    "sp500": "^GSPC",
}

# 合并所有 ticker 映射
INDEX_TICKERS = {**TENCENT_CODES, **YAHOO_TICKERS}


# AKShare A股指数代码映射 (用于历史数据)
AKSHARE_INDEX_CODES = {
    "shanghai": "sh000001",      # 上证指数
    "shenzhen": "sz399001",      # 深证成指
    "shanghai50": "sh000016",    # 上证50
    "chi_next": "sz399006",      # 创业板指
    "star50": "sh000688",        # 科创50
    "csi500": "sh000905",        # 中证500
    "csi1000": "sh000852",       # 中证1000
    "hs300": "sh000300",         # 沪深300
    "csiall": "sh000985",        # 中证全指
}

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
    "hang_seng_tech": "hk",
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
    "hang_seng_tech": "恒生科技",
    "nikkei225": "日经 225",
    "dow_jones": "道琼斯",
    "nasdaq": "纳斯达克",
    "sp500": "标普 500",
    "dax": "德国 DAX",
    "ftse": "富时 100",
    "cac40": "CAC 40",
}


# A股市场配置 (共享)
A_SHARE_MARKET_HOURS = {
    "open": "01:30",
    "close": "08:00",
    "tz": "Asia/Shanghai",
    "lunch_start": "03:30",
    "lunch_end": "05:00",
}

# A股指数列表
A_SHARE_INDICES = [
    "shanghai",
    "shenzhen",
    "shanghai50",
    "chi_next",
    "star50",
    "csi500",
    "csi1000",
    "hs300",
    "csiall",
]

# 港股市场配置 (无午休)
HK_MARKET_HOURS = {
    "open": "01:30",
    "close": "08:00",
    "tz": "Asia/Hong_Kong",
}

# 港股指数列表
HK_INDICES = ["hang_seng", "hang_seng_tech"]

# 美股市场配置
US_MARKET_HOURS = {
    "open": "14:30",
    "close": "21:00",
    "tz": "America/New_York",
}

# 美股指数列表
US_INDICES = ["dow_jones", "nasdaq", "sp500"]


# 各市场开盘时间段 (UTC 时间)
# lunch_start/lunch_end 为午休时间段（本地时间），可选
MARKET_HOURS: dict[str, dict[str, str]] = {
    # A股 (9:30-11:30, 13:00-15:00 UTC+8) - 使用字典推导式生成
    **{idx: A_SHARE_MARKET_HOURS.copy() for idx in A_SHARE_INDICES},
    # 港股 (9:30-16:00 UTC+8, 无午休)
    **{idx: HK_MARKET_HOURS.copy() for idx in HK_INDICES},
    # 日经 (9:00-15:00 UTC+9, 无午休)
    "nikkei225": {"open": "00:00", "close": "06:00", "tz": "Asia/Tokyo"},
    # 欧洲 (9:00-17:30 CET, 无午休)
    "dax": {"open": "08:00", "close": "16:30", "tz": "Europe/Berlin"},
    "ftse": {"open": "08:00", "close": "16:30", "tz": "Europe/London"},
    "cac40": {"open": "08:00", "close": "16:30", "tz": "Europe/Paris"},
    # 美股 (9:30-16:00 EST, 无午休)
    **{idx: US_MARKET_HOURS.copy() for idx in US_INDICES},
}


class IndexDataSource(DataSource):
    """全球指数数据源基类

    由于实时数据不需要缓存，该类移除了缓存逻辑。
    如果未来需要缓存，可以在子类中实现。
    """

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
            timeout=timeout,
        )

    async def close(self) -> None:
        """关闭数据源"""
        pass

    async def fetch_history(self, index_type: str, period: str = "1y") -> DataSourceResult:
        """
        获取指数历史数据

        Args:
            index_type: 指数类型
            period: 时间周期 (1d, 5d, 1w, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)

        Returns:
            DataSourceResult: 包含历史数据的结果
        """
        raise NotImplementedError("子类必须实现 fetch_history 方法")

    async def fetch_batch(self, index_types: list[str]) -> list[DataSourceResult]:
        """批量获取指数数据的通用实现

        Args:
            index_types: 指数类型列表

        Returns:
            结果列表，与输入顺序一致
        """

        async def fetch_one(itype: str) -> DataSourceResult:
            return await self.fetch(itype)

        tasks = [fetch_one(itype) for itype in index_types]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results: list[DataSourceResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"index_type": index_types[i]},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results


class YahooIndexSource(IndexDataSource):
    """Yahoo Finance 全球指数数据源"""

    # 并发控制：最多 3 个并发请求
    _semaphore: asyncio.Semaphore | None = None

    # yfinance 调用超时时间（秒）
    YFINANCE_TIMEOUT = 10.0

    def __init__(self, timeout: float = 10.0):
        super().__init__(name="yfinance_index", timeout=timeout)

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        """获取并发控制信号量（懒加载）"""
        if cls._semaphore is None:
            cls._semaphore = asyncio.Semaphore(3)
        return cls._semaphore

    async def _fetch_yfinance_info(self, ticker: str) -> dict[str, Any]:
        """
        使用 run_in_executor 获取 yfinance 数据，带超时控制

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

        async with self._get_semaphore():
            try:
                ticker_obj = yf.Ticker(ticker)
                info = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: ticker_obj.info),
                    timeout=self.YFINANCE_TIMEOUT,
                )
                return info
            except asyncio.TimeoutError:
                logger.warning(f"[YFinance Index] 获取 {ticker} 超时 ({self.YFINANCE_TIMEOUT}s)")
                raise

    async def fetch(self, index_type: str) -> DataSourceResult:
        """
        获取单个指数数据

        Args:
            index_type: 指数类型 (如 shanghai, nasdaq, dax 等)

        Returns:
            DataSourceResult: 指数数据结果
        """
        try:
            ticker = INDEX_TICKERS.get(index_type)
            if not ticker:
                return DataSourceResult(
                    success=False,
                    error=f"不支持的指数类型: {index_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            # 使用异步方法获取数据（带超时控制和并发控制）
            info = await self._fetch_yfinance_info(ticker)

            price = info.get("currentPrice", info.get("regularMarketPrice"))
            change = info.get("regularMarketChange", info.get("change", 0))
            change_percent = info.get("regularMarketChangePercent", info.get("changePercent", 0))

            if price is None:
                return DataSourceResult(
                    success=False,
                    error="无法获取价格数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            # 转换时间戳为可读格式
            market_time = info.get("regularMarketTime")
            data_timestamp: str | None = None
            if market_time:
                try:
                    time_str = datetime.fromtimestamp(market_time).strftime("%Y-%m-%d %H:%M:%S")
                    data_timestamp = datetime.utcfromtimestamp(market_time).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                except (ValueError, TypeError, OSError):
                    time_str = str(market_time)
            else:
                time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            data = {
                "index": index_type,
                "symbol": ticker,
                "name": INDEX_NAMES.get(index_type, index_type),
                "price": float(price),
                "change": float(change) if change else 0.0,
                "change_percent": float(change_percent) if change_percent else 0.0,
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange", ""),
                "time": time_str,
                "data_timestamp": data_timestamp,
                "high": info.get("regularMarketDayHigh"),
                "low": info.get("regularMarketDayLow"),
                "open": info.get("regularMarketOpen"),
                "prev_close": info.get("regularMarketPreviousClose"),
                "region": INDEX_REGIONS.get(index_type, "unknown"),
                "market_hours": MARKET_HOURS.get(index_type, {}),
            }

            self._record_success()
            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="yfinance 未安装，请运行: pip install yfinance",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type, "error_type": "ImportError"},
            )
        except Exception as e:
            return self._handle_error(e, self.name)

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["supported_indices"] = list(INDEX_TICKERS.keys())
        return status

    async def fetch_history(self, index_type: str, period: str = "1y") -> DataSourceResult:
        """获取指数历史数据"""
        try:
            ticker = INDEX_TICKERS.get(index_type)
            if not ticker:
                return DataSourceResult(
                    success=False,
                    error=f"不支持的指数类型: {index_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            import yfinance as yf

            loop = asyncio.get_event_loop()

            async with self._get_semaphore():
                try:
                    ticker_obj = yf.Ticker(ticker)
                    hist = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: ticker_obj.history(period=period)),
                        timeout=self.YFINANCE_TIMEOUT * 2,
                    )

                    if hist is None or hist.empty:
                        return DataSourceResult(
                            success=False,
                            error="无法获取历史数据",
                            timestamp=time.time(),
                            source=self.name,
                            metadata={"index_type": index_type, "period": period},
                        )

                    data = []
                    for idx, row in hist.iterrows():
                        data.append(
                            {
                                "time": idx.strftime("%Y-%m-%d"),
                                "open": float(row["Open"]) if pd.notna(row["Open"]) else None,
                                "high": float(row["High"]) if pd.notna(row["High"]) else None,
                                "low": float(row["Low"]) if pd.notna(row["Low"]) else None,
                                "close": float(row["Close"]) if pd.notna(row["Close"]) else None,
                                "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                            }
                        )

                    result_data = {
                        "index": index_type,
                        "symbol": ticker,
                        "name": INDEX_NAMES.get(index_type, index_type),
                        "period": period,
                        "data": data,
                        "count": len(data),
                        "currency": "USD",
                    }

                    self._record_success()
                    return DataSourceResult(
                        success=True,
                        data=result_data,
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"index_type": index_type, "period": period},
                    )

                except asyncio.TimeoutError:
                    return DataSourceResult(
                        success=False,
                        error=f"获取历史数据超时 ({self.YFINANCE_TIMEOUT * 2}s)",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"index_type": index_type, "period": period},
                    )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="yfinance 未安装",
                timestamp=time.time(),
                source=self.name,
            )
        except Exception as e:
            return self._handle_error(e, self.name)


class TencentIndexSource(IndexDataSource):
    """腾讯财经指数数据源 (A股、港股、美股 - 实时)"""

    def __init__(self, timeout: float = 10.0):
        super().__init__(name="tencent_index", timeout=timeout)
        self.base_url = "https://qt.gtimg.cn/q"

    async def fetch(self, index_type: str) -> DataSourceResult:
        """
        获取单个指数数据

        Args:
            index_type: 指数类型 (如 shanghai, hang_seng, dow_jones 等)

        Returns:
            DataSourceResult: 指数数据结果
        """
        try:
            tencent_code = TENCENT_CODES.get(index_type)
            if not tencent_code:
                return DataSourceResult(
                    success=False,
                    error=f"腾讯财经不支持的指数类型: {index_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
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
                    metadata={"index_type": index_type},
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
                    metadata={"index_type": index_type},
                )

            parts = match.group(1).split("~")

            # 判断市场类型
            is_us = tencent_code.startswith("us")
            is_hk = tencent_code.startswith("hk")

            if is_us:
                # 美股格式
                price = float(parts[3]) if parts[3] else 0.0
                open_price = float(parts[5]) if len(parts) > 5 and parts[5] else 0.0
                prev_close = float(parts[4]) if parts[4] else 0.0
                high = float(parts[33]) if len(parts) > 33 and parts[33] else 0.0
                low = float(parts[34]) if len(parts) > 34 and parts[34] else 0.0
                change = float(parts[31]) if len(parts) > 31 and parts[31] else 0.0
                # 涨跌幅计算
                if price > 0 and prev_close > 0:
                    change_percent = (change / prev_close) * 100
                else:
                    change_percent = 0.0
                currency = "USD"
                exchange = "US"
            elif is_hk:
                # 港股格式: 3=当前价, 4=昨日收盘, 5=开盘, 33=最高, 34=最低
                price = float(parts[3]) if parts[3] else 0.0
                open_price = float(parts[5]) if len(parts) > 5 and parts[5] else 0.0
                prev_close = float(parts[4]) if parts[4] else 0.0
                high = float(parts[33]) if len(parts) > 33 and parts[33] else 0.0
                low = float(parts[34]) if len(parts) > 34 and parts[34] else 0.0
                change = float(parts[31]) if len(parts) > 31 and parts[31] else 0.0
                if price > 0 and prev_close > 0:
                    change_percent = (change / prev_close) * 100
                else:
                    change_percent = 0.0
                currency = "HKD"
                exchange = "HKEX"
            else:
                # A股格式: 3=当前价, 4=昨日收盘, 5=开盘, 33=最高, 34=最低, 31=涨跌, 32=涨跌幅
                price = float(parts[3]) if parts[3] else 0.0
                open_price = float(parts[5]) if parts[5] else 0.0
                prev_close = float(parts[4]) if parts[4] else 0.0
                high = float(parts[33]) if parts[33] else 0.0
                low = float(parts[34]) if parts[34] else 0.0
                change = float(parts[31]) if parts[31] else 0.0
                change_percent = float(parts[32]) if parts[32] else 0.0
                currency = "CNY"
                # Fix: A股代码格式是 sh000001 或 sz399001，不是 s_sh
                exchange = "SSE" if tencent_code.startswith("sh") else "SZSE"

            # 从腾讯数据中提取时间戳（格式：YYYYMMDDHHmmss）
            # 例如：20210105154040 表示 2021-01-05 15:40:40
            data_timestamp: datetime | None = None
            for i in range(len(parts) - 1, -1, -1):
                if parts[i] and len(parts[i]) == 14 and parts[i].isdigit():
                    try:
                        data_timestamp = datetime.strptime(parts[i], "%Y%m%d%H%M%S")
                        break
                    except ValueError:
                        continue

            # 如果找到时间戳则使用，否则使用当前时间
            if data_timestamp:
                time_str = data_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
                "data_timestamp": data_timestamp.isoformat() if data_timestamp else None,
                "high": high,
                "low": low,
                "open": open_price,
                "prev_close": prev_close,
                "region": INDEX_REGIONS.get(index_type, "unknown"),
                "market_hours": MARKET_HOURS.get(index_type, {}),
            }

            self._record_success()
            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )

        except httpx.HTTPError as e:
            return self._handle_error(e, self.name)
        except Exception as e:
            return self._handle_error(e, self.name)

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["supported_indices"] = list(TENCENT_CODES.keys())
        return status


class AKShareIndexSource(IndexDataSource):
    """AKShare A股指数数据源（支持实时和历史数据）

    使用优化配置：
    - 浏览器请求头模拟
    - 请求限流和重试机制
    - 支持实时数据接口
    """

    # 并发控制：最多 3 个并发请求
    _semaphore: asyncio.Semaphore | None = None

    # AKShare 调用超时时间（秒）
    AKSHARE_TIMEOUT = 30.0

    # 限流配置：每秒请求数
    RATE_LIMIT_CPS = DEFAULT_RATE_LIMIT

    # 重试次数
    MAX_RETRIES = MAX_RETRIES

    def __init__(
        self,
        timeout: float = 30.0,
        rate_limit_cps: float = DEFAULT_RATE_LIMIT,
        max_retries: int = MAX_RETRIES,
    ):
        super().__init__(name="akshare_index", timeout=timeout)
        self.rate_limit_cps = rate_limit_cps
        self.max_retries = max_retries

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        """获取并发控制信号量（懒加载）"""
        if cls._semaphore is None:
            cls._semaphore = asyncio.Semaphore(3)
        return cls._semaphore

    async def fetch(self, index_type: str) -> DataSourceResult:
        """
        获取单个A股指数实时数据（使用优化配置）

        使用 stock_zh_index_spot_em 接口获取A股指数实时行情

        Args:
            index_type: 指数类型 (如 shanghai, shenzhen, shanghai50 等)

        Returns:
            DataSourceResult: 指数数据结果
        """
        # 检查是否支持该指数
        if index_type not in AKSHARE_INDEX_CODES:
            return DataSourceResult(
                success=False,
                error=f"AKShare不支持的指数类型: {index_type}",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )

        symbol = AKSHARE_INDEX_CODES[index_type]

        try:
            import akshare as ak

            async with self._get_semaphore():
                # 使用带限流和重试的调用方式
                df = await call_akshare_with_retry(
                    ak.stock_zh_index_spot_em,
                    max_retries=self.max_retries,
                    rate_limit_cps=self.rate_limit_cps,
                )

                if df is None or df.empty:
                    return DataSourceResult(
                        success=False,
                        error="无法获取实时指数数据",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"index_type": index_type},
                    )

                # 查找对应指数的数据
                # stock_zh_index_spot_em 返回的代码格式为 "sh000001"
                index_row = df[df["代码"] == symbol]

                if index_row.empty:
                    return DataSourceResult(
                        success=False,
                        error=f"未找到指数数据: {symbol}",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"index_type": index_type, "symbol": symbol},
                    )

                # 提取数据（取第一行）
                row = index_row.iloc[0]

                # 解析数据
                price = float(row.get("最新价", 0)) if pd.notna(row.get("最新价")) else 0.0
                open_price = float(row.get("开盘", 0)) if pd.notna(row.get("开盘")) else 0.0
                prev_close = float(row.get("昨收", 0)) if pd.notna(row.get("昨收")) else 0.0
                high = float(row.get("最高", 0)) if pd.notna(row.get("最高")) else 0.0
                low = float(row.get("最低", 0)) if pd.notna(row.get("最低")) else 0.0
                change = float(row.get("涨跌额", 0)) if pd.notna(row.get("涨跌额")) else 0.0
                change_percent = float(row.get("涨跌幅", 0)) if pd.notna(row.get("涨跌幅")) else 0.0

                # 获取时间戳
                time_str = row.get("时间", "")
                if not time_str or pd.isna(time_str):
                    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                data = {
                    "index": index_type,
                    "symbol": symbol,
                    "name": INDEX_NAMES.get(index_type, index_type),
                    "price": price,
                    "change": change,
                    "change_percent": change_percent,
                    "currency": "CNY",
                    "exchange": "SSE" if symbol.startswith("sh") else "SZSE",
                    "time": time_str,
                    "data_timestamp": datetime.now().isoformat(),
                    "high": high,
                    "low": low,
                    "open": open_price,
                    "prev_close": prev_close,
                    "region": INDEX_REGIONS.get(index_type, "china"),
                    "market_hours": MARKET_HOURS.get(index_type, {}),
                }

                self._record_success()
                logger.info(f"[AKShareIndexSource] 成功获取 {index_type} 实时数据")

                return DataSourceResult(
                    success=True,
                    data=data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type, "symbol": symbol},
                )

        except asyncio.TimeoutError:
            logger.warning(f"[AKShareIndexSource] 获取 {index_type} 实时数据超时")
            return DataSourceResult(
                success=False,
                error=f"获取实时数据超时 ({self.AKSHARE_TIMEOUT}s)",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )
        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 未安装，请运行: pip install akshare",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type, "error_type": "ImportError"},
            )
        except Exception as e:
            logger.error(f"[AKShareIndexSource] 获取 {index_type} 实时数据失败: {e}")
            return self._handle_error(e, self.name)

    async def fetch_hk_spot(self) -> DataSourceResult:
        """
        获取港股实时行情（使用优化配置）

        使用 stock_hk_spot_em 接口获取港股实时行情

        Returns:
            DataSourceResult: 港股实时数据结果
        """
        try:
            import akshare as ak

            async with self._get_semaphore():
                df = await call_akshare_with_retry(
                    ak.stock_hk_spot_em,
                    max_retries=self.max_retries,
                    rate_limit_cps=self.rate_limit_cps,
                )

                if df is None or df.empty:
                    return DataSourceResult(
                        success=False,
                        error="无法获取港股实时数据",
                        timestamp=time.time(),
                        source=self.name,
                    )

                self._record_success()

                return DataSourceResult(
                    success=True,
                    data={
                        "count": len(df),
                        "columns": list(df.columns),
                        "sample": df.head(5).to_dict("records"),
                    },
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"source": "stock_hk_spot_em"},
                )

        except Exception as e:
            logger.error(f"[AKShareIndexSource] 获取港股实时数据失败: {e}")
            return self._handle_error(e, self.name)

    async def fetch_us_spot(self) -> DataSourceResult:
        """
        获取美股实时行情（使用优化配置）

        使用 stock_us_spot_em 接口获取美股实时行情

        Returns:
            DataSourceResult: 美股实时数据结果
        """
        try:
            import akshare as ak

            async with self._get_semaphore():
                df = await call_akshare_with_retry(
                    ak.stock_us_spot_em,
                    max_retries=self.max_retries,
                    rate_limit_cps=self.rate_limit_cps,
                )

                if df is None or df.empty:
                    return DataSourceResult(
                        success=False,
                        error="无法获取美股实时数据",
                        timestamp=time.time(),
                        source=self.name,
                    )

                self._record_success()

                return DataSourceResult(
                    success=True,
                    data={
                        "count": len(df),
                        "columns": list(df.columns),
                        "sample": df.head(5).to_dict("records"),
                    },
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"source": "stock_us_spot_em"},
                )

        except Exception as e:
            logger.error(f"[AKShareIndexSource] 获取美股实时数据失败: {e}")
            return self._handle_error(e, self.name)

    async def fetch_history(self, index_type: str, period: str = "1y") -> DataSourceResult:
        """获取A股指数历史数据（使用优化配置）

        Args:
            index_type: 指数类型
            period: 时间周期 (1w, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)

        Returns:
            DataSourceResult: 包含历史数据的结果
        """
        try:
            symbol = AKSHARE_INDEX_CODES.get(index_type)
            if not symbol:
                return DataSourceResult(
                    success=False,
                    error=f"AKShare不支持的指数类型: {index_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            import akshare as ak

            async with self._get_semaphore():
                try:
                    # 使用带限流和重试的调用方式获取历史数据
                    df = await call_akshare_with_retry(
                        ak.stock_zh_index_daily,
                        symbol=symbol,
                        max_retries=self.max_retries,
                        rate_limit_cps=self.rate_limit_cps,
                    )

                    if df is None or df.empty:
                        return DataSourceResult(
                            success=False,
                            error="无法获取历史数据",
                            timestamp=time.time(),
                            source=self.name,
                            metadata={"index_type": index_type, "period": period},
                        )

                    # 根据period过滤数据
                    period_days = {
                        "1w": 7,
                        "1mo": 30,
                        "3mo": 90,
                        "6mo": 180,
                        "1y": 365,
                        "2y": 730,
                        "5y": 1825,
                        "max": None,
                    }
                    
                    days = period_days.get(period, 365)
                    if days:
                        df = df.tail(days)

                    # 转换数据格式
                    data = []
                    for _, row in df.iterrows():
                        data.append({
                            "time": str(row["date"]) if "date" in row else str(row.name),
                            "open": float(row["open"]) if pd.notna(row.get("open")) else None,
                            "high": float(row["high"]) if pd.notna(row.get("high")) else None,
                            "low": float(row["low"]) if pd.notna(row.get("low")) else None,
                            "close": float(row["close"]) if pd.notna(row.get("close")) else None,
                            "volume": int(row["volume"]) if pd.notna(row.get("volume")) else None,
                        })

                    result_data = {
                        "index": index_type,
                        "symbol": symbol,
                        "name": INDEX_NAMES.get(index_type, index_type),
                        "period": period,
                        "data": data,
                        "count": len(data),
                        "currency": "CNY",
                    }

                    self._record_success()
                    return DataSourceResult(
                        success=True,
                        data=result_data,
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"index_type": index_type, "period": period},
                    )

                except asyncio.TimeoutError:
                    return DataSourceResult(
                        success=False,
                        error=f"获取历史数据超时 ({self.AKSHARE_TIMEOUT}s)",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"index_type": index_type, "period": period},
                    )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 未安装，请运行: pip install akshare",
                timestamp=time.time(),
                source=self.name,
            )
        except Exception as e:
            logger.error(f"[AKShare Index] 获取 {index_type} 历史数据失败: {e}")
            return self._handle_error(e, self.name)

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["supported_indices"] = list(AKSHARE_INDEX_CODES.keys())
        return status


class HybridIndexSource(IndexDataSource):
    """混合指数数据源
    根据指数类型自动选择最佳数据源:
    - A股/港股/美股 -> 腾讯财经 (实时)
    - 日经/欧洲 -> yfinance (有延迟)
    - A股历史数据 -> AKShare
    """

    def __init__(self, timeout: float = 10.0):
        super().__init__(name="hybrid_index", timeout=timeout)
        self._tencent = TencentIndexSource(timeout=10.0)
        self._yahoo = YahooIndexSource(timeout=10.0)
        self._akshare = AKShareIndexSource(timeout=15.0)

    async def fetch(self, index_type: str) -> DataSourceResult:
        """获取指数数据，自动选择数据源"""
        # 根据指数类型选择数据源
        if uses_tencent(index_type):
            return await self._tencent.fetch(index_type)
        else:
            return await self._yahoo.fetch(index_type)

    async def close(self) -> None:
        """关闭数据源"""
        await self._tencent.close()
        await self._yahoo.close()
        # AKShare数据源没有需要关闭的资源

    async def health_check(self) -> bool:
        """
        健康检查

        测试腾讯数据源（上证指数）来验证健康状态，
        因为腾讯数据源覆盖 A股/港股/美股，是主要数据源。
        """
        try:
            # 测试腾讯数据源（上证指数）
            result = await self._tencent.fetch("shanghai")
            return result.success
        except Exception:
            return False

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["tencent_status"] = self._tencent.get_status()
        status["yahoo_status"] = self._yahoo.get_status()
        status["akshare_status"] = self._akshare.get_status()
        return status

    async def fetch_history(self, index_type: str, period: str = "1y") -> DataSourceResult:
        """获取指数历史数据，根据指数类型选择数据源

        - A股指数 -> AKShare
        - 日经/欧洲/港股 -> Yahoo Finance
        """
        # A股指数使用AKShare获取历史数据
        if index_type in AKSHARE_INDEX_CODES:
            return await self._akshare.fetch_history(index_type, period)
        
        # 其他指数使用Yahoo Finance
        if index_type in YAHOO_TICKERS:
            return await self._yahoo.fetch_history(index_type, period)
        
        # 不支持的指数
        return DataSourceResult(
            success=False,
            error=f"指数 {INDEX_NAMES.get(index_type, index_type)} 暂不支持历史数据查询",
            timestamp=time.time(),
            source=self.name,
            metadata={"index_type": index_type, "period": period},
        )

    async def fetch_intraday(self, index_type: str) -> DataSourceResult:
        """获取指数日内分时数据

        根据指数类型自动选择数据源:
        - A股/港股 -> 腾讯财经 (实时)
        - 美股/日经/欧洲 -> yfinance (有延迟)

        Args:
            index_type: 指数类型

        Returns:
            DataSourceResult: 包含日内分时数据的结果
        """
        try:
            # 验证指数类型
            if index_type not in INDEX_NAMES:
                return DataSourceResult(
                    success=False,
                    error=f"不支持的指数类型: {index_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            # 根据指数类型选择数据源
            # A股和港股使用腾讯财经，美股/日经/欧洲使用yfinance
            if index_type in A_SHARE_INDICES or index_type in HK_INDICES:
                result = await self._fetch_tencent_intraday(index_type)
                # 如果腾讯财经失败，尝试使用yfinance
                if not result.success and index_type in YAHOO_TICKERS:
                    logger.warning(f"[HybridIndexSource] 腾讯财经获取 {index_type} 失败，回退到yfinance")
                    return await self._fetch_yahoo_intraday(index_type)
                return result
            else:
                return await self._fetch_yahoo_intraday(index_type)

        except Exception as e:
            logger.error(f"[HybridIndexSource] 获取 {index_type} 日内分时数据失败: {e}")
            return DataSourceResult(
                success=False,
                error=str(e),
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )

    async def _fetch_tencent_intraday(self, index_type: str) -> DataSourceResult:
        """从腾讯财经获取日内分时数据

        使用腾讯财经的分钟线接口获取A股/港股/美股的分钟级数据
        对于A股指数，优先使用akshare获取真实分钟级数据
        对于港股指数，优先使用yfinance获取真实分钟级数据（腾讯只返回日线数据）
        """
        tencent_code = TENCENT_CODES.get(index_type)
        if not tencent_code:
            return DataSourceResult(
                success=False,
                error=f"腾讯财经不支持的指数类型: {index_type}",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )

        # 对于A股指数，优先使用akshare获取真实分钟级数据
        if tencent_code.startswith(("sh", "sz")):
            akshare_result = await self._fetch_akshare_intraday(index_type)
            if akshare_result.success:
                return akshare_result
            # 如果akshare失败，回退到腾讯财经日线接口
            logger.warning(f"[HybridIndexSource] akshare分钟数据获取失败，回退到腾讯日线接口: {index_type}")
        
        # 港股使用yfinance获取分钟级数据（腾讯分钟线接口对指数只返回日线数据）
        if tencent_code.startswith("hk"):
            yahoo_result = await self._fetch_yahoo_intraday(index_type)
            if yahoo_result.success:
                return yahoo_result
            # 如果yfinance失败，回退到腾讯财经日线接口
            logger.warning(f"[HybridIndexSource] yfinance港股分钟数据获取失败，回退到腾讯日线接口: {index_type}")
        
        # 使用日线接口（适用于美股或分钟线失败的情况）
        try:
            url = (
                f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
                f"?param={tencent_code},day,,,1,qfq"
            )

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            # 解析数据
            data_section = data.get("data", {})
            
            if isinstance(data_section, list):
                return DataSourceResult(
                    success=False,
                    error="数据格式错误",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )
            
            stock_data = data_section.get(tencent_code, {})
            if isinstance(stock_data, list):
                return DataSourceResult(
                    success=False,
                    error="股票数据格式错误",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )
                
            day_data = stock_data.get("day", []) if isinstance(stock_data, dict) else []

            if not day_data:
                return DataSourceResult(
                    success=False,
                    error="无法获取今日数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            # 获取今天的数据
            today_data = day_data[-1] if day_data else None
            if not today_data:
                return DataSourceResult(
                    success=False,
                    error="无法获取今日分时数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            # 解析日线数据
            # 腾讯财经格式: ["日期", "开盘", "收盘", "最低", "最高", "成交量"]
            open_price = float(today_data[1]) if len(today_data) > 1 else 0.0
            close_price = float(today_data[2]) if len(today_data) > 2 else 0.0
            
            # 注意：有些情况下腾讯返回的数据中最低和最高可能放反了
            # 我们取两个值中的较小值作为最低，较大值作为最高
            raw_low = float(today_data[3]) if len(today_data) > 3 else 0.0
            raw_high = float(today_data[4]) if len(today_data) > 4 else 0.0
            
            low_price = min(raw_low, raw_high)
            high_price = max(raw_low, raw_high)
            
            # 确保高低价格至少有一定差异，否则使用开盘收盘价格
            if high_price - low_price < 0.01:
                low_price = min(open_price, close_price) * 0.995
                high_price = max(open_price, close_price) * 1.005

            # 对于A股指数，如果走到这里说明akshare获取失败
            # 返回错误而不是生成模拟数据
            if tencent_code.startswith(("sh", "sz")):
                return DataSourceResult(
                    success=False,
                    error="无法获取A股指数分钟级数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            # 对于其他市场（如美股），返回日线数据点（单个数据点）
            # 注意：不再生成模拟数据
            intraday_points = [{
                "time": "15:00",
                "price": close_price,
                "change": 0.0,
            }]

            result_data = {
                "index": index_type,
                "symbol": tencent_code,
                "name": INDEX_NAMES.get(index_type, index_type),
                "data": intraday_points,
                "timestamp": datetime.now().isoformat() + "Z",
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
            }

            return DataSourceResult(
                success=True,
                data=result_data,
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type, "source": "tencent"},
            )

        except httpx.HTTPError as e:
            logger.warning(f"[HybridIndexSource] 腾讯财经请求失败: {e}")
            return DataSourceResult(
                success=False,
                error=f"请求失败: {e}",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )
        except Exception as e:
            logger.error(f"[HybridIndexSource] 解析腾讯财经数据失败: {e}")
            return DataSourceResult(
                success=False,
                error=f"数据解析失败: {e}",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )

    async def _fetch_akshare_intraday(self, index_type: str) -> DataSourceResult:
        """从akshare获取A股指数分钟级分时数据（使用优化配置）

        使用akshare的stock_zh_a_minute接口获取A股指数的真实分钟级数据。
        返回约240个数据点（1分钟间隔，4小时交易时间）。

        Args:
            index_type: 指数类型（如 shanghai, shenzhen 等）

        Returns:
            DataSourceResult: 包含分钟级分时数据的结果
        """
        symbol = AKSHARE_INDEX_CODES.get(index_type)
        if not symbol:
            return DataSourceResult(
                success=False,
                error=f"akshare不支持的指数类型: {index_type}",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )

        try:
            import akshare as ak

            # 使用带限流和重试的调用方式获取分钟级数据
            # period="1" 表示1分钟线，adjust="qfq" 表示前复权
            df = await call_akshare_with_retry(
                ak.stock_zh_a_minute,
                symbol=symbol,
                period="1",
                adjust="qfq",
                max_retries=self._akshare.max_retries if hasattr(self, "_akshare") else MAX_RETRIES,
                rate_limit_cps=self._akshare.rate_limit_cps if hasattr(self, "_akshare") else DEFAULT_RATE_LIMIT,
            )

            if df is None or df.empty:
                return DataSourceResult(
                    success=False,
                    error="无法获取分钟级数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            # 只保留最近一个交易日的数据
            # akshare返回的数据包含多天的分钟数据，我们需要过滤出最近交易日的
            df["day"] = pd.to_datetime(df["day"])
            latest_date = df["day"].dt.date.max()
            df_today = df[df["day"].dt.date == latest_date]
            
            if df_today.empty:
                return DataSourceResult(
                    success=False,
                    error="无法获取交易日数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            # 解析分钟数据
            # akshare返回格式: day, open, high, low, close, volume, amount
            intraday_points = []
            open_price = None
            high_price = float("-inf")
            low_price = float("inf")

            for _, row in df_today.iterrows():
                time_str = str(row["day"])
                # 提取 HH:MM 格式
                if " " in time_str:
                    hhmm = time_str.split(" ")[1][:5]  # "2026-03-07 09:30:00" -> "09:30"
                else:
                    continue

                price = float(row["close"]) if pd.notna(row.get("close")) else 0.0
                volume = int(row["volume"]) if pd.notna(row.get("volume")) else 0
                amount = float(row["amount"]) if pd.notna(row.get("amount")) else 0.0

                # 记录开盘价（第一个数据点）
                if open_price is None:
                    open_price = float(row["open"]) if pd.notna(row.get("open")) else price

                # 更新最高最低价
                high = float(row["high"]) if pd.notna(row.get("high")) else price
                low = float(row["low"]) if pd.notna(row.get("low")) else price
                high_price = max(high_price, high)
                low_price = min(low_price, low)

                # 计算涨跌幅（相对于开盘价）
                if open_price > 0:
                    change = ((price - open_price) / open_price * 100)
                else:
                    change = 0.0

                intraday_points.append({
                    "time": hhmm,
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "volume": volume,
                    "amount": round(amount, 2),
                })

            if not intraday_points:
                return DataSourceResult(
                    success=False,
                    error="解析分钟数据失败",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            # 获取最终统计数据
            close_price = float(df["close"].iloc[-1]) if not df.empty else 0.0
            if high_price == float("-inf"):
                high_price = close_price
            if low_price == float("inf"):
                low_price = close_price

            result_data = {
                "index": index_type,
                "symbol": symbol,
                "name": INDEX_NAMES.get(index_type, index_type),
                "data": intraday_points,
                "timestamp": datetime.now().isoformat() + "Z",
                "open": open_price if open_price else close_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
            }

            logger.info(f"[HybridIndexSource] akshare获取 {index_type} 分钟数据成功，共 {len(intraday_points)} 个点")

            return DataSourceResult(
                success=True,
                data=result_data,
                timestamp=time.time(),
                source=self.name,
                metadata={
                    "index_type": index_type,
                    "source": "akshare_minute",
                    "count": len(intraday_points)
                },
            )

        except asyncio.TimeoutError:
            logger.warning(f"[HybridIndexSource] akshare获取 {index_type} 分钟数据超时")
            return DataSourceResult(
                success=False,
                error="获取分钟数据超时",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )
        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 未安装",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )
        except Exception as e:
            logger.error(f"[HybridIndexSource] akshare获取 {index_type} 分钟数据失败: {e}")
            return DataSourceResult(
                success=False,
                error=f"获取分钟数据失败: {e}",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )

    async def _fetch_tencent_minute_intraday(self, index_type: str, tencent_code: str) -> DataSourceResult:
        """从腾讯财经获取分钟级分时数据

        使用腾讯财经的分钟线接口。注意：腾讯财经的分钟线接口对指数支持有限，
        通常只支持个股。对于指数，此方法会返回失败，调用方应回退到日线接口。
        对于A股指数，应使用 _fetch_akshare_intraday 方法获取真实分钟数据。
        """
        try:
            # 腾讯财经分钟线接口（主要用于个股，指数可能不支持）
            url = (
                f"https://ifzq.gtimg.cn/appstock/app/fqkline/get"
                f"?param={tencent_code},m1,,,240,qfq"
            )

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            # 检查接口返回的错误
            if data.get("code") != 0:
                error_msg = data.get("msg", "未知错误")
                logger.debug(f"[HybridIndexSource] 腾讯分钟线接口不支持 {index_type}: {error_msg}")
                return DataSourceResult(
                    success=False,
                    error=f"分钟线接口不支持指数: {error_msg}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            # 解析分钟数据
            data_section = data.get("data", {})
            
            # 处理数据可能是列表的情况
            if isinstance(data_section, list):
                return DataSourceResult(
                    success=False,
                    error="无法获取分钟级分时数据（数据格式错误）",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )
            
            stock_data = data_section.get(tencent_code, {})
            if isinstance(stock_data, list):
                return DataSourceResult(
                    success=False,
                    error="无法获取分钟级分时数据（股票数据格式错误）",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )
                
            minute_data = stock_data.get("m1", []) if isinstance(stock_data, dict) else []

            if not minute_data:
                return DataSourceResult(
                    success=False,
                    error="无法获取分钟级分时数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"index_type": index_type},
                )

            # 解析分钟数据
            # 格式: ["时间", "开盘", "收盘", "最低", "最高", "成交量"]
            intraday_points = []
            prev_price = None

            for item in minute_data:
                time_str = item[0]  # 格式: "2026-03-06 09:30:00"
                # 提取 HH:MM
                time_parts = time_str.split(" ")
                if len(time_parts) == 2:
                    hhmm = time_parts[1][:5]  # 取前5个字符 "09:30"
                else:
                    continue

                price = float(item[2]) if len(item) > 2 else 0.0  # 使用收盘价

                # 计算涨跌幅（相对于第一个数据点）
                if prev_price is None:
                    change = 0.0
                    prev_price = price
                else:
                    change = ((price - prev_price) / prev_price * 100) if prev_price > 0 else 0.0

                intraday_points.append({
                    "time": hhmm,
                    "price": price,
                    "change": round(change, 2),
                })

            # 获取今日开盘价（第一个数据点的开盘价）
            open_price = float(minute_data[0][1]) if minute_data else 0.0
            high_price = max([float(item[4]) for item in minute_data if len(item) > 4], default=0.0)
            low_price = min([float(item[3]) for item in minute_data if len(item) > 3], default=0.0)
            close_price = float(minute_data[-1][2]) if minute_data else 0.0

            result_data = {
                "index": index_type,
                "symbol": tencent_code,
                "name": INDEX_NAMES.get(index_type, index_type),
                "data": intraday_points,
                "timestamp": datetime.now().isoformat() + "Z",
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
            }

            return DataSourceResult(
                success=True,
                data=result_data,
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type, "source": "tencent_minute", "count": len(intraday_points)},
            )

        except Exception as e:
            logger.error(f"[HybridIndexSource] 获取腾讯分钟数据失败: {e}")
            return DataSourceResult(
                success=False,
                error=f"获取分钟数据失败: {e}",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )


    async def _fetch_yahoo_intraday(self, index_type: str) -> DataSourceResult:
        """从Yahoo Finance获取日内分时数据

        使用yfinance获取分钟级数据（适用于港股/日经/欧洲指数）
        对于港股指数，使用5天数据获取最近交易日的分钟数据
        """
        ticker = YAHOO_TICKERS.get(index_type)
        if not ticker:
            return DataSourceResult(
                success=False,
                error=f"Yahoo Finance不支持的指数类型: {index_type}",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )

        try:
            import yfinance as yf

            loop = asyncio.get_event_loop()

            async with self._yahoo._get_semaphore():
                try:
                    ticker_obj = yf.Ticker(ticker)
                    
                    # 港股指数需要使用5天数据才能获取分钟级数据
                    # 其他指数可以使用1天数据
                    period = "5d" if index_type in HK_INDICES else "1d"
                    
                    hist = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: ticker_obj.history(period=period, interval="1m")),
                        timeout=self._yahoo.YFINANCE_TIMEOUT * 2,
                    )

                    if hist is None or hist.empty:
                        return DataSourceResult(
                            success=False,
                            error="无法获取日内数据",
                            timestamp=time.time(),
                            source=self.name,
                            metadata={"index_type": index_type},
                        )
                    
                    # 对于港股指数，只保留最近一个交易日的数据
                    if index_type in HK_INDICES and not hist.empty:
                        # 获取最近日期
                        latest_date = hist.index[-1].date()
                        hist = hist[hist.index.date == latest_date]

                    # 解析分钟数据
                    intraday_points = []
                    prev_price = None

                    for idx, row in hist.iterrows():
                        # 转换时间为本地时间字符串
                        time_str = idx.strftime("%H:%M")
                        price = float(row["Close"]) if pd.notna(row["Close"]) else 0.0

                        # 计算涨跌幅
                        if prev_price is None:
                            change = 0.0
                            prev_price = price
                        else:
                            change = ((price - prev_price) / prev_price * 100) if prev_price > 0 else 0.0

                        intraday_points.append({
                            "time": time_str,
                            "price": round(price, 2),
                            "change": round(change, 2),
                        })

                    # 获取统计数据
                    open_price = float(hist["Open"].iloc[0]) if not hist.empty else 0.0
                    high_price = float(hist["High"].max()) if not hist.empty else 0.0
                    low_price = float(hist["Low"].min()) if not hist.empty else 0.0
                    close_price = float(hist["Close"].iloc[-1]) if not hist.empty else 0.0

                    result_data = {
                        "index": index_type,
                        "symbol": ticker,
                        "name": INDEX_NAMES.get(index_type, index_type),
                        "data": intraday_points,
                        "timestamp": datetime.now().isoformat() + "Z",
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                    }

                    return DataSourceResult(
                        success=True,
                        data=result_data,
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"index_type": index_type, "source": "yahoo", "count": len(intraday_points)},
                    )

                except asyncio.TimeoutError:
                    return DataSourceResult(
                        success=False,
                        error=f"获取日内数据超时 ({self._yahoo.YFINANCE_TIMEOUT * 2}s)",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"index_type": index_type},
                    )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="yfinance 未安装，请运行: pip install yfinance",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )
        except Exception as e:
            logger.error(f"[HybridIndexSource] 获取Yahoo日内数据失败: {e}")
            return DataSourceResult(
                success=False,
                error=f"获取数据失败: {e}",
                timestamp=time.time(),
                source=self.name,
                metadata={"index_type": index_type},
            )
