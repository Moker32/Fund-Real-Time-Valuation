"""AKShare A股指数数据源（支持实时和历史数据）"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

import pandas as pd

from ..akshare_config import DEFAULT_RATE_LIMIT, MAX_RETRIES, call_akshare_with_retry
from ..base import DataSourceResult
from .base import (
    AKSHARE_INDEX_CODES,
    INDEX_NAMES,
    INDEX_REGIONS,
    MARKET_HOURS,
    IndexDataSource,
)

logger = logging.getLogger(__name__)


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
                        data.append(
                            {
                                "time": str(row["date"]) if "date" in row else str(row.name),
                                "open": float(row["open"]) if pd.notna(row.get("open")) else None,
                                "high": float(row["high"]) if pd.notna(row.get("high")) else None,
                                "low": float(row["low"]) if pd.notna(row.get("low")) else None,
                                "close": float(row["close"])
                                if pd.notna(row.get("close"))
                                else None,
                                "volume": int(row["volume"])
                                if pd.notna(row.get("volume"))
                                else None,
                            }
                        )

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
