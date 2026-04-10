"""混合指数数据源 - 自动选择最佳数据源"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

import httpx
import pandas as pd

from ..base import DataSourceResult
from ..fund.fund_cache_helpers import get_index_intraday_cache_dao
from .akshare_source import AKShareIndexSource
from .base import (
    A_SHARE_INDICES,
    AKSHARE_INDEX_CODES,
    HK_INDICES,
    INDEX_NAMES,
    TENCENT_CODES,
    YAHOO_TICKERS,
    IndexDataSource,
    uses_tencent,
)
from .tencent_source import TencentIndexSource
from .yahoo_source import YahooIndexSource

logger = logging.getLogger(__name__)


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
                    logger.warning(
                        f"[HybridIndexSource] 腾讯财经获取 {index_type} 失败，回退到yfinance"
                    )
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
            logger.warning(
                f"[HybridIndexSource] akshare分钟数据获取失败，回退到腾讯日线接口: {index_type}"
            )

        # 港股使用yfinance获取分钟级数据（腾讯分钟线接口对指数只返回日线数据）
        if tencent_code.startswith("hk"):
            yahoo_result = await self._fetch_yahoo_intraday(index_type)
            if yahoo_result.success:
                return yahoo_result
            # 如果yfinance失败，回退到腾讯财经日线接口
            logger.warning(
                f"[HybridIndexSource] yfinance港股分钟数据获取失败，回退到腾讯日线接口: {index_type}"
            )

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
            intraday_points = [
                {
                    "time": "15:00",
                    "price": close_price,
                    "change": 0.0,
                }
            ]

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
        from ..akshare_config import call_akshare_with_retry

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
                max_retries=self._akshare.max_retries,
                rate_limit_cps=self._akshare.rate_limit_cps,
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
                    change = (price - open_price) / open_price * 100
                else:
                    change = 0.0

                intraday_points.append(
                    {
                        "time": hhmm,
                        "price": round(price, 2),
                        "change": round(change, 2),
                        "volume": volume,
                        "amount": round(amount, 2),
                    }
                )

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

            logger.info(
                f"[HybridIndexSource] akshare获取 {index_type} 分钟数据成功，共 {len(intraday_points)} 个点"
            )

            return DataSourceResult(
                success=True,
                data=result_data,
                timestamp=time.time(),
                source=self.name,
                metadata={
                    "index_type": index_type,
                    "source": "akshare_minute",
                    "count": len(intraday_points),
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

    async def _fetch_tencent_minute_intraday(
        self, index_type: str, tencent_code: str
    ) -> DataSourceResult:
        """从腾讯财经获取分钟级分时数据

        使用腾讯财经的分钟线接口。注意：腾讯财经的分钟线接口对指数支持有限，
        通常只支持个股。对于指数，此方法会返回失败，调用方应回退到日线接口。
        对于A股指数，应使用 _fetch_akshare_intraday 方法获取真实分钟数据。
        """
        try:
            # 腾讯财经分钟线接口（主要用于个股，指数可能不支持）
            url = (
                f"https://ifzq.gtimg.cn/appstock/app/fqkline/get?param={tencent_code},m1,,,240,qfq"
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

                intraday_points.append(
                    {
                        "time": hhmm,
                        "price": price,
                        "change": round(change, 2),
                    }
                )

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
                metadata={
                    "index_type": index_type,
                    "source": "tencent_minute",
                    "count": len(intraday_points),
                },
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

        # 尝试从缓存读取
        cache_dao = get_index_intraday_cache_dao()
        today = datetime.now().strftime("%Y-%m-%d")

        if not cache_dao.is_expired(index_type, today):
            cached_records = cache_dao.get_intraday(index_type, today)
            if cached_records:
                logger.debug(f"[HybridIndexSource] Cache hit for {index_type}")
                intraday_points = [
                    {
                        "time": r.time,
                        "price": r.price,
                        "change": r.change_rate,
                    }
                    for r in cached_records
                ]
                # 获取统计数据
                prices = [r.price for r in cached_records if r.price > 0]
                open_price = cached_records[0].price if cached_records else 0.0
                close_price = cached_records[-1].price if cached_records else 0.0
                high_price = max(prices) if prices else 0.0
                low_price = min(prices) if prices else 0.0

                return DataSourceResult(
                    success=True,
                    data={
                        "index": index_type,
                        "symbol": ticker,
                        "name": INDEX_NAMES.get(index_type, index_type),
                        "data": intraday_points,
                        "timestamp": datetime.now().isoformat() + "Z",
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                    },
                    timestamp=time.time(),
                    source=self.name,
                    metadata={
                        "index_type": index_type,
                        "source": "cache",
                        "count": len(intraday_points),
                    },
                )

        # 缓存未命中，从 yfinance 获取
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
                        loop.run_in_executor(
                            None, lambda: ticker_obj.history(period=period, interval="1m")
                        ),
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
                            change = (
                                ((price - prev_price) / prev_price * 100) if prev_price > 0 else 0.0
                            )

                        intraday_points.append(
                            {
                                "time": time_str,
                                "price": round(price, 2),
                                "change": round(change, 2),
                            }
                        )

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

                    # 保存到缓存
                    cache_dao.save_intraday(index_type, today, intraday_points)
                    logger.debug(f"[HybridIndexSource] Saved {len(intraday_points)} points to cache for {index_type}")

                    return DataSourceResult(
                        success=True,
                        data=result_data,
                        timestamp=time.time(),
                        source=self.name,
                        metadata={
                            "index_type": index_type,
                            "source": "yahoo",
                            "count": len(intraday_points),
                        },
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
