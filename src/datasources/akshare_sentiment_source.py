"""
AKShare 舆情数据源模块

实现从 AKShare 获取：
1. 全球宏观事件（财经日历）- news_economic_baidu
2. 微博舆情 - stock_js_weibo_report
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

import pandas as pd

from .base import DataSource, DataSourceResult, DataSourceType

logger = logging.getLogger(__name__)


class AKShareEconomicNewsDataSource(DataSource):
    """AKShare 全球宏观事件（财经日历）数据源"""

    # 支持的时间周期
    DEFAULT_DATE = (datetime.now()).strftime("%Y%m%d")

    def __init__(self, timeout: float = 15.0):
        """
        初始化全球宏观事件数据源

        Args:
            timeout: 请求超时时间(秒)
        """
        super().__init__(
            name="akshare_economic_news", source_type=DataSourceType.NEWS, timeout=timeout
        )
        self._cache: list[dict[str, Any]] = []
        self._cache_time: float = 0.0
        self._cache_timeout = 300.0  # 缓存5分钟

    async def fetch(self, date: str | None = None) -> DataSourceResult:
        """
        获取全球宏观事件（财经日历）

        Args:
            date: 日期，格式 YYYYMMDD，默认今天

        Returns:
            DataSourceResult: 财经事件数据结果
        """
        # 检查缓存
        if self._is_cache_valid():
            return DataSourceResult(
                success=True,
                data=self._cache,
                timestamp=self._cache_time,
                source=self.name,
                metadata={"from_cache": True, "date": date or self.DEFAULT_DATE},
            )

        try:
            # 在线程池中运行同步的 akshare 调用
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, self._fetch_data, date)

            if df is not None and not df.empty:
                # 转换为字典列表
                data = df.to_dict(orient="records")

                # 更新缓存
                self._cache = data
                self._cache_time = time.time()

                self._record_success()
                return DataSourceResult(
                    success=True,
                    data=data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"date": date or self.DEFAULT_DATE, "count": len(data)},
                )

            return DataSourceResult(
                success=False,
                error="未获取到财经事件数据",
                timestamp=time.time(),
                source=self.name,
                metadata={"date": date or self.DEFAULT_DATE},
            )

        except Exception as e:
            return self._handle_error(e, self.name)

    def _fetch_data(self, date: str | None) -> pd.DataFrame | None:
        """同步获取数据"""
        import akshare as ak

        target_date = date or self.DEFAULT_DATE
        try:
            df = ak.news_economic_baidu(date=target_date)
            return df
        except Exception as e:
            logger.warning(f"获取财经事件数据失败: {e}")
            return None

    async def fetch_batch(self, dates: list[str]) -> list[DataSourceResult]:
        """批量获取多日财经事件"""

        async def fetch_one(d: str) -> DataSourceResult:
            return await self.fetch(d)

        tasks = [fetch_one(d) for d in dates]
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
                        metadata={"date": dates[i]},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self._cache:
            return False
        return (time.time() - self._cache_time) < self._cache_timeout

    def clear_cache(self):
        """清空缓存"""
        self._cache = []
        self._cache_time = 0.0


class AKShareWeiboSentimentDataSource(DataSource):
    """AKShare 微博舆情数据源"""

    # 支持的时间周期
    TIME_PERIODS = {
        "2h": "CNHOUR2",
        "6h": "CNHOUR6",
        "12h": "CNHOUR12",
        "24h": "CNHOUR24",
        "7d": "CNDAY7",
        "30d": "CNDAY30",
    }
    DEFAULT_PERIOD = "12h"

    def __init__(self, timeout: float = 15.0):
        """
        初始化微博舆情数据源

        Args:
            timeout: 请求超时时间(秒)
        """
        super().__init__(
            name="akshare_weibo_sentiment", source_type=DataSourceType.NEWS, timeout=timeout
        )
        self._cache: list[dict[str, Any]] = []
        self._cache_time: float = 0.0
        self._cache_timeout = 180.0  # 缓存3分钟

    async def fetch(self, period: str = "12h") -> DataSourceResult:
        """
        获取微博舆情报告

        Args:
            period: 时间周期 (2h, 6h, 12h, 24h, 7d, 30d)

        Returns:
            DataSourceResult: 微博舆情数据结果
        """
        # 检查缓存
        if self._is_cache_valid(period):
            return DataSourceResult(
                success=True,
                data=self._cache,
                timestamp=self._cache_time,
                source=self.name,
                metadata={"from_cache": True, "period": period},
            )

        try:
            # 转换周期参数
            akshare_period = self.TIME_PERIODS.get(period, self.TIME_PERIODS[self.DEFAULT_PERIOD])

            # 在线程池中运行同步的 akshare 调用
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, self._fetch_data, akshare_period)

            if df is not None and not df.empty:
                # 转换为字典列表
                data = df.to_dict(orient="records")

                # 更新缓存
                self._cache = data
                self._cache_time = time.time()

                self._record_success()
                return DataSourceResult(
                    success=True,
                    data=data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"period": period, "count": len(data)},
                )

            return DataSourceResult(
                success=False,
                error="未获取到微博舆情数据",
                timestamp=time.time(),
                source=self.name,
                metadata={"period": period},
            )

        except Exception as e:
            return self._handle_error(e, self.name)

    def _fetch_data(self, period: str) -> pd.DataFrame | None:
        """同步获取数据"""
        import akshare as ak

        try:
            df = ak.stock_js_weibo_report(time_period=period)
            return df
        except Exception as e:
            logger.warning(f"获取微博舆情数据失败: {e}")
            return None

    async def fetch_batch(self, periods: list[str]) -> list[DataSourceResult]:
        """批量获取多周期舆情数据"""

        async def fetch_one(p: str) -> DataSourceResult:
            return await self.fetch(p)

        tasks = [fetch_one(p) for p in periods]
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
                        metadata={"period": periods[i]},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def _is_cache_valid(self, period: str) -> bool:
        """检查缓存是否有效"""
        if not self._cache:
            return False
        return (time.time() - self._cache_time) < self._cache_timeout

    def clear_cache(self):
        """清空缓存"""
        self._cache = []
        self._cache_time = 0.0


class AKShareSentimentAggregatorDataSource(DataSource):
    """舆情聚合数据源 - 整合财经事件和微博舆情"""

    def __init__(self, timeout: float = 25.0):
        super().__init__(
            name="akshare_sentiment_aggregator", source_type=DataSourceType.NEWS, timeout=timeout
        )
        self._economic_news = AKShareEconomicNewsDataSource(timeout=timeout)
        self._weibo_sentiment = AKShareWeiboSentimentDataSource(timeout=timeout)

    async def fetch(self, data_type: str = "all", **kwargs) -> DataSourceResult:
        """
        获取舆情数据

        Args:
            data_type: 数据类型 (economic, weibo, all)
            **kwargs: 额外参数 (date for economic, period for weibo)

        Returns:
            DataSourceResult: 舆情数据结果
        """
        if data_type == "economic":
            date = kwargs.get("date")
            return await self._economic_news.fetch(date)
        elif data_type == "weibo":
            period = kwargs.get("period", "12h")
            return await self._weibo_sentiment.fetch(period)
        elif data_type == "all":
            # 并行获取所有数据
            economic_task = self._economic_news.fetch(kwargs.get("date"))
            weibo_task = self._weibo_sentiment.fetch(kwargs.get("period", "12h"))

            economic_result, weibo_result = await asyncio.gather(
                economic_task, weibo_task, return_exceptions=True
            )

            combined_data: dict[str, Any] = {"economic": None, "weibo": None, "errors": []}

            if isinstance(economic_result, DataSourceResult) and economic_result.success:
                combined_data["economic"] = economic_result.data
            elif isinstance(economic_result, Exception):
                combined_data["errors"].append(f"economic: {str(economic_result)}")

            if isinstance(weibo_result, DataSourceResult) and weibo_result.success:
                combined_data["weibo"] = weibo_result.data
            elif isinstance(weibo_result, Exception):
                combined_data["errors"].append(f"weibo: {str(weibo_result)}")

            has_data = combined_data["economic"] is not None or combined_data["weibo"] is not None

            return DataSourceResult(
                success=has_data,
                data=combined_data if has_data else None,
                error="; ".join(combined_data["errors"]) if combined_data["errors"] else None,
                timestamp=time.time(),
                source=self.name,
            )
        else:
            return DataSourceResult(
                success=False,
                error=f"未知数据类型: {data_type}",
                timestamp=time.time(),
                source=self.name,
            )

    async def fetch_batch(self, data_types: list[str]) -> list[DataSourceResult]:
        """批量获取多类型舆情数据"""

        async def fetch_one(dt: str) -> DataSourceResult:
            return await self.fetch(dt)

        tasks = [fetch_one(dt) for dt in data_types]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def close(self):
        """关闭数据源"""
        # 两个数据源都是无状态的，不需要关闭
        pass


# 导出类
__all__ = [
    "AKShareEconomicNewsDataSource",
    "AKShareWeiboSentimentDataSource",
    "AKShareSentimentAggregatorDataSource",
]
