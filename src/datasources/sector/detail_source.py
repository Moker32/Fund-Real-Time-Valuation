"""行业/概念板块详情数据源模块"""

import asyncio
import logging
import time
from typing import Any

from ..base import DataSource, DataSourceResult, DataSourceType

logger = logging.getLogger(__name__)


class EastMoneyIndustryDetailSource(DataSource):
    """
    行业板块详情数据源

    功能: 获取行业板块的成份股列表

    接口: stock_board_industry_cons_em(symbol)
    """

    def __init__(self, timeout: float = 15.0):
        super().__init__(
            name="sector_industry_detail_akshare",
            source_type=DataSourceType.SECTOR,
            timeout=timeout,
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timeout = 60.0

    async def fetch(self, sector_name: str = "") -> DataSourceResult:
        """获取行业板块成份股"""
        if not sector_name:
            return DataSourceResult(
                success=False,
                error="请指定板块名称",
                timestamp=time.time(),
                source=self.name,
                metadata={"sector_name": sector_name},
            )

        cache_key = sector_name
        if self._is_cache_valid(cache_key):
            return DataSourceResult(
                success=True,
                data=self._cache[cache_key],
                timestamp=self._cache[cache_key].get("_cache_time", time.time()),
                source=self.name,
                metadata={"sector_name": sector_name, "from_cache": True},
            )

        try:
            import akshare as ak

            loop = asyncio.get_event_loop()

            try:
                df = await asyncio.wait_for(
                    loop.run_in_executor(None, ak.stock_board_industry_cons_em, sector_name),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                return DataSourceResult(
                    success=False,
                    error=f"获取行业板块详情超时（{self.timeout}秒）",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"sector_name": sector_name, "error_type": "TimeoutError"},
                )

            if df is not None and not df.empty:
                stocks = []
                for _, row in df.iterrows():
                    stocks.append(
                        {
                            "rank": row.get("序号", 0),
                            "code": row.get("代码", ""),
                            "name": row.get("名称", ""),
                            "price": row.get("最新价", 0),
                            "change_percent": row.get("涨跌幅", 0),
                        }
                    )

                data = {"sector_name": sector_name, "stocks": stocks, "count": len(stocks)}
                data["_cache_time"] = time.time()
                self._cache[cache_key] = data
                self._record_success()

                return DataSourceResult(
                    success=True,
                    data=data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"sector_name": sector_name},
                )

            return DataSourceResult(
                success=False,
                error=f"未获取到板块 {sector_name} 的成份股",
                timestamp=time.time(),
                source=self.name,
                metadata={"sector_name": sector_name},
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 未安装",
                timestamp=time.time(),
                source=self.name,
                metadata={"sector_name": sector_name},
            )
        except Exception as e:
            return self._handle_error(e, self.name)

    async def fetch_batch(self, sector_names: list[str]) -> list[DataSourceResult]:
        async def fetch_one(name: str) -> DataSourceResult:
            return await self.fetch(name)

        tasks = [fetch_one(name) for name in sector_names]
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
                        metadata={"sector_name": sector_names[i]},
                    )
                )
            else:
                processed_results.append(result)
        return processed_results

    async def health_check(self) -> bool:
        """
        健康检查 - 行业板块详情接口

        Returns:
            bool: 健康状态
        """
        try:
            import akshare as ak

            loop = asyncio.get_event_loop()

            # 尝试获取行业板块列表，验证接口可用性
            try:
                df = await asyncio.wait_for(
                    loop.run_in_executor(None, ak.stock_board_industry_name_em),
                    timeout=10.0,
                )
            except asyncio.TimeoutError:
                logger.warning("行业板块详情健康检查超时（10秒）")
                return False

            # 验证返回数据
            if df is not None and not df.empty:
                return True
            return False
        except Exception as e:
            logger.warning(f"行业板块详情健康检查失败: {e}")
            return False

    def _is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self._cache:
            return False
        cache_time = self._cache[cache_key].get("_cache_time", 0)
        return (time.time() - cache_time) < self._cache_timeout

    def clear_cache(self):
        self._cache.clear()


class EastMoneyConceptDetailSource(DataSource):
    """
    概念板块详情数据源

    功能: 获取概念板块的成份股列表

    接口: stock_board_concept_cons_em(symbol)
    """

    def __init__(self, timeout: float = 15.0):
        super().__init__(
            name="sector_concept_detail_akshare", source_type=DataSourceType.SECTOR, timeout=timeout
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timeout = 60.0

    async def fetch(self, sector_name: str = "") -> DataSourceResult:
        """获取概念板块成份股"""
        if not sector_name:
            return DataSourceResult(
                success=False,
                error="请指定板块名称",
                timestamp=time.time(),
                source=self.name,
                metadata={"sector_name": sector_name},
            )

        cache_key = sector_name
        if self._is_cache_valid(cache_key):
            return DataSourceResult(
                success=True,
                data=self._cache[cache_key],
                timestamp=self._cache[cache_key].get("_cache_time", time.time()),
                source=self.name,
                metadata={"sector_name": sector_name, "from_cache": True},
            )

        try:
            import akshare as ak

            loop = asyncio.get_event_loop()

            try:
                df = await asyncio.wait_for(
                    loop.run_in_executor(None, ak.stock_board_concept_cons_em, sector_name),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                return DataSourceResult(
                    success=False,
                    error=f"获取概念板块详情超时（{self.timeout}秒）",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"sector_name": sector_name, "error_type": "TimeoutError"},
                )

            if df is not None and not df.empty:
                stocks = []
                for _, row in df.iterrows():
                    stocks.append(
                        {
                            "rank": row.get("序号", 0),
                            "code": row.get("代码", ""),
                            "name": row.get("名称", ""),
                            "price": row.get("最新价", 0),
                            "change_percent": row.get("涨跌幅", 0),
                        }
                    )

                data = {"sector_name": sector_name, "stocks": stocks, "count": len(stocks)}
                data["_cache_time"] = time.time()
                self._cache[cache_key] = data
                self._record_success()

                return DataSourceResult(
                    success=True,
                    data=data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"sector_name": sector_name},
                )

            return DataSourceResult(
                success=False,
                error=f"未获取到板块 {sector_name} 的成份股（接口可能不稳定）",
                timestamp=time.time(),
                source=self.name,
                metadata={"sector_name": sector_name},
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 未安装",
                timestamp=time.time(),
                source=self.name,
                metadata={"sector_name": sector_name},
            )
        except Exception as e:
            return self._handle_error(e, self.name)

    async def fetch_batch(self, sector_names: list[str]) -> list[DataSourceResult]:
        async def fetch_one(name: str) -> DataSourceResult:
            return await self.fetch(name)

        tasks = [fetch_one(name) for name in sector_names]
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
                        metadata={"sector_name": sector_names[i]},
                    )
                )
            else:
                processed_results.append(result)
        return processed_results

    async def health_check(self) -> bool:
        """
        健康检查 - 概念板块详情接口

        Returns:
            bool: 健康状态
        """
        try:
            import akshare as ak

            loop = asyncio.get_event_loop()

            # 尝试获取概念板块列表，验证接口可用性
            try:
                df = await asyncio.wait_for(
                    loop.run_in_executor(None, ak.stock_board_concept_name_em),
                    timeout=10.0,
                )
            except asyncio.TimeoutError:
                logger.warning("概念板块详情健康检查超时（10秒）")
                return False

            # 验证返回数据
            if df is not None and not df.empty:
                return True
            return False
        except Exception as e:
            logger.warning(f"概念板块详情健康检查失败: {e}")
            return False

    def _is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self._cache:
            return False
        cache_time = self._cache[cache_key].get("_cache_time", 0)
        return (time.time() - cache_time) < self._cache_timeout

    def clear_cache(self):
        self._cache.clear()
