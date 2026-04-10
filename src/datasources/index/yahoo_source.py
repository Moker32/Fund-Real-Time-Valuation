"""Yahoo Finance 全球指数数据源"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

import pandas as pd

from ..base import DataSourceResult
from .base import (
    INDEX_NAMES,
    INDEX_REGIONS,
    INDEX_TICKERS,
    IndexDataSource,
)

logger = logging.getLogger(__name__)


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
                "market_state": info.get("marketState"),  # yfinance 动态市场状态
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
