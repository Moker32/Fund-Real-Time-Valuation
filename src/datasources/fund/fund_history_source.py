"""基金历史数据源模块

使用 akshare 和 yfinance 获取基金历史净值数据。
"""

import asyncio
import logging
import time
from typing import Any

from ..base import DataSource, DataSourceResult, DataSourceType

logger = logging.getLogger(__name__)


class FundHistorySource(DataSource):
    """基金历史数据源 - 使用 akshare 获取基金净值历史数据"""

    def __init__(self, timeout: float = 30.0):
        """
        初始化基金历史数据源

        Args:
            timeout: 请求超时时间
        """
        super().__init__(
            name="fund_history_akshare", source_type=DataSourceType.FUND, timeout=timeout
        )

    async def fetch(self, fund_code: str, period: str = "近一年") -> DataSourceResult:
        """
        获取基金历史净值数据

        Args:
            fund_code: 基金代码 (6位数字)
            period: 时间周期，可选值: "近一周", "近一月", "近三月", "近六月", "近一年", "近三年", "近五年", "成立以来"

        Returns:
            DataSourceResult: 包含历史净值数据的结果
        """
        if not self._validate_fund_code(fund_code):
            return DataSourceResult(
                success=False,
                error=f"无效的基金代码: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        try:
            import akshare as ak

            # 获取基金历史净值数据
            fund_df = ak.fund_etf_fund_info_em(fund=fund_code)

            if fund_df is None or fund_df.empty:
                return DataSourceResult(
                    success=False,
                    error="未获取到基金历史数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            # 解析数据并转换为 OHLCV 格式（K 线图需要）
            ohlcv_data = []
            for _, row in fund_df.iterrows():
                date = row.get("净值日期", "")
                net_value = row.get("单位净值", None)

                if date and net_value is not None:
                    try:
                        nav = float(net_value)
                        # 基金净值是单点数据，open/high/low/close 相同
                        ohlcv_data.append(
                            {
                                "time": str(date),
                                "open": round(nav, 4),
                                "high": round(nav, 4),
                                "low": round(nav, 4),
                                "close": round(nav, 4),
                                "volume": 0,  # 基金没有成交量
                            }
                        )
                    except (ValueError, TypeError):
                        continue

            # 按日期升序排序
            ohlcv_data.sort(key=lambda x: x["time"])

            # 根据 period 过滤数据
            filtered_data = self._filter_by_period(ohlcv_data, period)

            self._record_success()
            return DataSourceResult(
                success=True,
                data={"fund_code": fund_code, "data": filtered_data, "count": len(filtered_data)},
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code, "period": period},
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 库未安装，请运行: pip install akshare",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )
        except Exception as e:
            self._request_count += 1
            self._error_count += 1
            return DataSourceResult(
                success=False,
                error=f"获取历史数据失败: {str(e)}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

    def _filter_by_period(self, data: list[dict[str, Any]], period: str) -> list[dict[str, Any]]:
        """
        根据时间周期过滤数据

        Args:
            data: OHLCV 数据列表
            period: 时间周期

        Returns:
            过滤后的数据列表
        """
        from datetime import datetime, timedelta

        if not data:
            return []

        # 获取当前日期
        today = datetime.now()
        cutoff_date: datetime | None = None

        # 根据 period 计算截止日期
        if period == "近一周":
            cutoff_date = today - timedelta(days=7)
        elif period == "近一月":
            cutoff_date = today - timedelta(days=30)
        elif period == "近三月":
            cutoff_date = today - timedelta(days=90)
        elif period == "近六月":
            cutoff_date = today - timedelta(days=180)
        elif period == "近一年":
            cutoff_date = today - timedelta(days=365)
        elif period == "近三年":
            cutoff_date = today - timedelta(days=365 * 3)
        elif period == "近五年":
            cutoff_date = today - timedelta(days=365 * 5)
        else:
            # 成立以来，返回所有数据
            return data

        # 过滤数据
        filtered = []
        for item in data:
            try:
                item_date = datetime.strptime(item["time"], "%Y-%m-%d")
                if item_date >= cutoff_date:
                    filtered.append(item)
            except (ValueError, KeyError):
                continue

        return filtered

    def _validate_fund_code(self, fund_code: str) -> bool:
        """验证基金代码格式"""
        import re

        return bool(re.match(r"^\d{6}$", str(fund_code)))

    async def fetch_batch(self, *args, **kwargs) -> list[DataSourceResult]:
        """
        批量获取基金历史数据

        Args:
            *args: 位置参数（兼容旧接口）
            **kwargs: 关键字参数，可选 fund_codes

        Returns:
            List[DataSourceResult]: 返回结果列表
        """
        # 支持多种调用方式: fetch_batch() / fetch_batch([]) / fetch_batch(fund_codes=[])
        fund_codes: list[str] | None = None

        if args:
            fund_codes = list(args[0]) if args[0] else []
        elif kwargs.get("fund_codes"):
            fund_codes = kwargs.get("fund_codes")
        elif kwargs.get("fund_code"):
            # 单个 fund_code 兼容
            fund_codes = [kwargs.get("fund_code")]

        if not fund_codes:
            return [
                DataSourceResult(
                    success=False,
                    error="缺少 fund_code 参数",
                    timestamp=time.time(),
                    source=self.name,
                )
            ]

        async def fetch_one(code: str) -> DataSourceResult:
            return await self.fetch(code)

        tasks = [fetch_one(code) for code in fund_codes]
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
                        metadata={"fund_code": fund_codes[i]},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results


class FundHistoryYFinanceSource(DataSource):
    """基金历史数据源 - 使用 yfinance 获取历史数据（备用方案）"""

    def __init__(self, timeout: float = 30.0):
        super().__init__(
            name="fund_history_yfinance", source_type=DataSourceType.FUND, timeout=timeout
        )

    async def fetch(self, fund_code: str, period: str = "1y") -> DataSourceResult:
        """
        使用 yfinance 获取基金历史数据

        Args:
            fund_code: 基金代码 (对于中国基金，需要添加 .SS 后缀)
            period: 时间周期: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

        Returns:
            DataSourceResult: 包含历史数据的结果
        """
        try:
            import yfinance as yf

            # 构建 ticker 符号
            ticker_symbol = f"{fund_code}.SS" if fund_code.isdigit() else fund_code

            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period=period)

            if hist is None or hist.empty:
                return DataSourceResult(
                    success=False,
                    error="未获取到基金历史数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            history_data = []
            for index, row in hist.iterrows():
                history_data.append(
                    {
                        "date": index.strftime("%Y-%m-%d"),
                        "open": row.get("Open"),
                        "high": row.get("High"),
                        "low": row.get("Low"),
                        "close": row.get("Close"),
                        "volume": row.get("Volume"),
                        "dividends": row.get("Dividends"),
                        "stock_splits": row.get("Stock Splits"),
                    }
                )

            self._record_success()
            return DataSourceResult(
                success=True,
                data={
                    "fund_code": fund_code,
                    "ticker": ticker_symbol,
                    "history": history_data,
                    "count": len(history_data),
                },
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code, "period": period},
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="yfinance 库未安装，请运行: pip install yfinance",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )
        except Exception as e:
            self._request_count += 1
            self._error_count += 1
            return DataSourceResult(
                success=False,
                error=f"获取历史数据失败: {str(e)}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

    async def fetch_async(self, fund_code: str, period: str = "1y") -> DataSourceResult:
        """异步获取历史数据"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.fetch(fund_code, period))

    async def fetch_batch(self, *args, **kwargs) -> list[DataSourceResult]:
        """
        批量获取基金历史数据（未实现，返回单条结果）

        Returns:
            List[DataSourceResult]: 返回结果列表
        """
        fund_code = kwargs.get("fund_code")
        period = kwargs.get("period", "1y")

        if fund_code:
            result = await self.fetch(fund_code, period)
            return [result]
        return [
            DataSourceResult(
                success=False,
                error="缺少 fund_code 参数",
                timestamp=time.time(),
                source=self.name,
            )
        ]
