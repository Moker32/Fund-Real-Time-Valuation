"""东方财富直连 API 数据源模块"""

import asyncio
import logging
import time
from typing import Any

import httpx

from ..base import DataSource, DataSourceResult, DataSourceType
from .sector_helpers import get_last_trading_day

logger = logging.getLogger(__name__)


class EastMoneyDirectSource(DataSource):
    """
    东方财富直连 API 数据源

    功能:
    - 获取行业板块/概念板块列表及涨跌幅
    - 获取主力资金流入数据 (主力净流入、小单净流入)
    - 数据更稳定，不依赖 AKShare

    接口:
    - https://push2.eastmoney.com/api/qt/clist/get
    """

    # 板块类型映射
    BOARD_TYPES = {
        "industry": "m:90+t:2",  # 行业板块
        "concept": "m:90+t:3",  # 概念板块
    }

    def __init__(self, timeout: float = 15.0):
        super().__init__(
            name="sector_eastmoney_direct", source_type=DataSourceType.SECTOR, timeout=timeout
        )
        self.client = httpx.AsyncClient(timeout=timeout)
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timeout = 60.0

    def log(self, message: str) -> None:
        logger.info(f"[EastMoneyDirectSource] {message}")

    async def fetch(self, sector_type: str = "industry") -> DataSourceResult:
        """
        获取板块数据

        Args:
            sector_type: 板块类型 ("industry" 行业板块, "concept" 概念板块)

        Returns:
            DataSourceResult: 板块数据结果
        """
        cache_key = sector_type
        if self._is_cache_valid(cache_key):
            return DataSourceResult(
                success=True,
                data=self._cache[cache_key],
                timestamp=self._cache[cache_key].get("_cache_time", time.time()),
                source=self.name,
                metadata={"sector_type": sector_type, "from_cache": True},
            )

        try:
            data = await self._fetch_sectors(sector_type)

            if data:
                data["_cache_time"] = time.time()
                self._cache[cache_key] = data
                self._record_success()
                return DataSourceResult(
                    success=True,
                    data=data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"sector_type": sector_type},
                )

            return DataSourceResult(
                success=False,
                error="获取板块数据为空",
                timestamp=time.time(),
                source=self.name,
                metadata={"sector_type": sector_type},
            )

        except Exception as e:
            return self._handle_error(e, self.name)

    async def _fetch_sectors(self, sector_type: str) -> dict[str, Any] | None:
        """从 EastMoney API 获取板块数据"""
        board_type = self.BOARD_TYPES.get(sector_type)
        if not board_type:
            return None

        # 获取两类数据：净流入（降序）和净流出（升序）
        all_sectors = []

        # 1. 获取净流入数据（按主力净流入降序）
        inflow_data = await self._fetch_sectors_by_order(board_type, "1", 50)
        if inflow_data:
            all_sectors.extend(inflow_data)

        # 2. 获取净流出数据（按主力净流入升序，获取负值）
        outflow_data = await self._fetch_sectors_by_order(board_type, "0", 50)
        if outflow_data:
            all_sectors.extend(outflow_data)

        if not all_sectors:
            return None

        # 按涨跌幅降序排序
        all_sectors = sorted(all_sectors, key=lambda x: x.get("change_percent", 0), reverse=True)

        # 去除重复数据
        seen = set()
        unique_sectors = []
        for s in all_sectors:
            key = (s.get("code"), s.get("name"))
            if key not in seen:
                seen.add(key)
                unique_sectors.append(s)
        all_sectors = unique_sectors

        # 添加排名
        for i, sector in enumerate(all_sectors):
            sector["rank"] = i + 1

        # 使用最近交易日作为时间戳
        trading_day = get_last_trading_day()

        return {
            "type": sector_type,
            "sectors": all_sectors,
            "count": len(all_sectors),
            "timestamp": trading_day.timestamp(),
        }

    async def _fetch_sectors_by_order(
        self, board_type: str, order: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """从 EastMoney API 获取板块数据（指定排序顺序）"""
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "cb": "",
            "fid": "f62",  # 按主力净流入排序
            "po": order,  # 1=降序（净流入）, 0=升序（净流出）
            "pz": str(limit),  # 获取条数
            "pn": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "ut": "8dec03ba335b81bf4ebdf7b29ec27d15",
            "fs": board_type,
            "fields": "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13",
        }

        sectors: list[dict[str, Any]] = []
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            json_data = response.json()

            if not json_data.get("data"):
                return sectors

            for bk in json_data["data"]["diff"]:
                # 解析资金流向数据（元转换为亿元）
                main_inflow = bk.get("f62", 0) or 0
                main_inflow_pct = bk.get("f184", 0) or 0
                small_inflow = bk.get("f84", 0) or 0
                small_inflow_pct = bk.get("f87", 0) or 0
                medium_inflow = bk.get("f72", 0) or 0
                large_inflow = bk.get("f75", 0) or 0
                huge_inflow = bk.get("f78", 0) or 0

                # 转换为亿元单位
                main_inflow_yi = round(main_inflow / 100000000, 2) if main_inflow else 0
                small_inflow_yi = round(small_inflow / 100000000, 2) if small_inflow else 0

                sectors.append(
                    {
                        "code": bk.get("f12", ""),
                        "name": bk.get("f14", ""),
                        "price": bk.get("f2", 0),
                        "change_percent": bk.get("f3", 0),
                        "change": self._calc_change(bk.get("f2", 0), bk.get("f3", 0)),
                        # 资金流向数据（已转换为亿元）
                        "main_inflow": main_inflow_yi,
                        "main_inflow_pct": main_inflow_pct,
                        "small_inflow": small_inflow_yi,
                        "small_inflow_pct": small_inflow_pct,
                        "medium_inflow": round(medium_inflow / 100000000, 2)
                        if medium_inflow
                        else 0,
                        "large_inflow": round(large_inflow / 100000000, 2) if large_inflow else 0,
                        "huge_inflow": round(huge_inflow / 100000000, 2) if huge_inflow else 0,
                        # 额外字段（兼容现有代码）
                        "total_market": bk.get("f124", ""),
                        "turnover": bk.get("f205", ""),
                        "up_count": bk.get("f66", 0),
                        "down_count": bk.get("f69", 0),
                    }
                )

        except Exception as e:
            self.log(f"获取板块数据失败: {e}")

        return sectors

    def _calc_change(self, price: float, change_pct: float) -> float:
        """计算涨跌额"""
        if not price or not change_pct:
            return 0.0
        return round(price * change_pct / 100, 2)

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
        """关闭HTTP客户端"""
        await self.client.aclose()

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["cache_size"] = len(self._cache)
        status["cache_timeout"] = self._cache_timeout
        status["supported_types"] = list(self.BOARD_TYPES.keys())
        return status

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            response = await self.client.get(
                "https://push2.eastmoney.com/api/qt/clist/get",
                params={
                    "cb": "",
                    "fid": "f62",
                    "po": "1",
                    "pz": "1",
                    "pn": "1",
                    "fltt": "2",
                    "invt": "2",
                    "ut": "8dec03ba335b81bf4ebdf7b29ec27d15",
                    "fs": "m:90+t:2",
                },
                timeout=self.timeout,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("data") is not None
            return False
        except Exception:
            return False

    async def fetch_batch(self, sector_types: list[str]) -> list[DataSourceResult]:
        """批量获取板块数据"""

        async def fetch_one(stype: str) -> DataSourceResult:
            return await self.fetch(stype)

        tasks = [fetch_one(stype) for stype in sector_types]
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
                        metadata={"sector_type": sector_types[i]},
                    )
                )
            else:
                processed_results.append(result)  # type: ignore[arg-type]
        return processed_results
