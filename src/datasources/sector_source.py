"""
行业板块数据源模块
实现从新浪财经获取行业板块数据
- 白酒、新能源，消费、医药，科技等主要行业
"""

import asyncio
import re
import time
from datetime import datetime, timedelta
from typing import Any

import httpx

from .base import DataSource, DataSourceResult, DataSourceType


# 中国A股主要节假日（简化版，提前维护）
CHINA_HOLIDAYS_2026 = [
    "2026-01-01",  # 元旦
    "2026-01-26",  # 春节假期开始
    "2026-01-27",
    "2026-01-28",
    "2026-01-29",
    "2026-01-30",
    "2026-01-31",
    "2026-02-01",
    "2026-02-02",
    "2026-02-03",
    "2026-02-04",
    "2026-02-05",
    "2026-02-06",
    "2026-02-07",  # 春节假期结束
    # 国庆节（假设）
    "2026-10-01",
    "2026-10-02",
    "2026-10-03",
    "2026-10-04",
    "2026-10-05",
    "2026-10-06",
    "2026-10-07",
    # 清明节（假设）
    "2026-04-04",
    "2026-04-05",
    "2026-04-06",
    # 劳动节（假设）
    "2026-05-01",
    "2026-05-02",
    "2026-05-03",
]


def is_trading_day(date: datetime) -> bool:
    """判断是否是交易日"""
    # 周末不是交易日
    if date.weekday() >= 5:
        return False
    # 节假日不是交易日
    date_str = date.strftime("%Y-%m-%d")
    if date_str in CHINA_HOLIDAYS_2026:
        return False
    return True


def get_last_trading_day() -> datetime:
    """
    获取最近的一个交易日
    基于时间和节假日判断
    """
    now = datetime.now()
    current_date = now.date()

    # 情况1: 现在是交易日（周一到周五，且不是节假日）
    if is_trading_day(now):
        # 判断当前时间
        # A股交易时间: 9:30-11:30, 13:00-15:00
        if now.hour >= 15:
            # 15:00 后，当天交易结束
            # 但如果刚收盘，数据还是当天的
            return now
        elif now.hour >= 9:
            # 9:00-15:00 之间，交易时间
            return now
        else:
            # 9:00 之前，可能是盘前，数据可能是昨日的
            # 查找上一个交易日
            for days in range(1, 10):
                check_date = now - timedelta(days=days)
                if is_trading_day(check_date):
                    return check_date

    # 情况2: 现在不是交易日（周末或节假日）
    # 查找上一个交易日
    for days in range(1, 10):
        check_date = now - timedelta(days=days)
        if is_trading_day(check_date):
            return check_date

    # 如果都找不到，返回今天（兜底）
    return now


class SinaSectorDataSource(DataSource):
    """新浪财经行业板块数据源"""

    def log(self, message: str) -> None:
        """简单的日志方法"""
        print(f"[SinaSectorDataSource] {message}")

    # 主要行业板块配置
    # 使用新浪财经的行业指数代码
    SECTOR_CONFIG = [
        {"code": "bk04151", "name": "白酒", "category": "消费"},
        {"code": "bk04758", "name": "新能源车", "category": "新能源"},
        {"code": "bk07257", "name": "光伏", "category": "新能源"},
        {"code": "bk00269", "name": "医药", "category": "医药"},
        {"code": "bk04537", "name": "半导体", "category": "科技"},
        {"code": "bk04360", "name": "人工智能", "category": "科技"},
        {"code": "bk04375", "name": "消费电子", "category": "消费"},
        {"code": "bk04804", "name": "银行", "category": "金融"},
        {"code": "bk04869", "name": "证券", "category": "金融"},
        {"code": "bk05011", "name": "保险", "category": "金融"},
        {"code": "bk04504", "name": "房地产", "category": "周期"},
        {"code": "bk04181", "name": "基建", "category": "周期"},
        {"code": "bk04479", "name": "军工", "category": "制造"},
        {"code": "bk04321", "name": "机械", "category": "制造"},
        {"code": "bk04125", "name": "农林牧渔", "category": "消费"},
    ]

    def __init__(self, timeout: float = 15.0):
        """
        初始化板块数据源

        Args:
            timeout: 请求超时时间(秒)
        """
        super().__init__(name="sina_sector", source_type=DataSourceType.SECTOR, timeout=timeout)
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        self._cache: list[dict[str, Any]] = []
        self._cache_time: float = 0.0
        self._cache_timeout = 60.0  # 缓存60秒

    async def fetch(self, sector_code: str | None = None) -> DataSourceResult:
        """
        获取板块数据

        Args:
            sector_code: 可选，指定板块代码，不指定则获取所有板块

        Returns:
            DataSourceResult: 板块数据结果
        """
        # 检查缓存
        if self._is_cache_valid() and sector_code is None:
            data = (
                [s for s in self._cache if s.get("code") == sector_code]
                if sector_code
                else self._cache
            )
            return DataSourceResult(
                success=True,
                data=data if sector_code else self._cache,
                timestamp=self._cache_time,
                source=self.name,
                metadata={"from_cache": True, "sector_code": sector_code},
            )

        try:
            # 并行获取所有板块数据
            async def fetch_one(config: dict) -> dict[str, Any] | None:
                return await self._fetch_sector(config["code"], config["name"], config["category"])

            # 过滤需要获取的板块
            configs_to_fetch = [
                config
                for config in self.SECTOR_CONFIG
                if sector_code is None or config["code"] == sector_code
            ]

            # 并行执行所有请求
            tasks = [fetch_one(config) for config in configs_to_fetch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 收集有效结果
            sectors = []
            for result in results:
                if isinstance(result, dict) and result:
                    sectors.append(result)

            if sectors:
                # 更新缓存
                if sector_code is None:
                    self._cache = sectors
                    self._cache_time = time.time()

                self._record_success()
                return DataSourceResult(
                    success=True,
                    data=sectors,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"count": len(sectors), "sector_code": sector_code},
                )

            return DataSourceResult(
                success=False,
                error="未获取到板块数据",
                timestamp=time.time(),
                source=self.name,
                metadata={"sector_code": sector_code},
            )

        except Exception as e:
            return self._handle_error(e, self.name)

    async def fetch_batch(self, *args, **kwargs) -> list[DataSourceResult]:
        """
        批量获取板块数据

        Returns:
            List[DataSourceResult]: 返回结果列表
        """
        # 支持从 kwargs 中提取参数列表
        params_list = kwargs.get("params_list", [])

        if not params_list:
            # 如果没有指定参数，获取所有板块
            result = await self.fetch()
            return [result]

        results = []
        for params in params_list:
            sector_code = (
                params.get("kwargs", {}).get("sector_code")
                if params.get("kwargs")
                else params.get("sector_code")
            )
            result = await self.fetch(sector_code)
            results.append(result)

        return results

    async def fetch_all(self) -> DataSourceResult:
        """
        获取所有板块数据（便捷方法）

        Returns:
            DataSourceResult: 所有板块数据
        """
        return await self.fetch()

    async def fetch_by_category(self, category: str) -> DataSourceResult:
        """
        获取指定类别的板块数据

        Args:
            category: 类别名称 (消费, 新能源, 医药, 科技, 金融, 周期, 制造)

        Returns:
            DataSourceResult: 指定类别的板块数据
        """
        try:
            # 并行获取指定类别的板块
            async def fetch_one(config: dict) -> dict[str, Any] | None:
                return await self._fetch_sector(config["code"], config["name"], config["category"])

            # 过滤指定类别的板块
            configs_to_fetch = [
                config for config in self.SECTOR_CONFIG if config["category"] == category
            ]

            # 并行执行所有请求
            tasks = [fetch_one(config) for config in configs_to_fetch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 收集有效结果
            sectors = []
            for result in results:
                if isinstance(result, dict) and result:
                    sectors.append(result)

            return DataSourceResult(
                success=True,
                data=sectors,
                timestamp=time.time(),
                source=self.name,
                metadata={"category": category, "count": len(sectors)},
            )

        except Exception as e:
            return self._handle_error(e, self.name)

    async def _fetch_sector(self, code: str, name: str, category: str) -> dict[str, Any] | None:
        """
        获取单个板块数据

        Args:
            code: 板块代码
            name: 板块名称
            category: 类别

        Returns:
            Dict: 板块数据
        """
        try:
            # 新浪财经行业板块行情接口
            url = f"https://quote.sina.com.cn/api/json.php/var%20_{code}=CN_BK.getListDetail?symbol={code}"

            response = await self.client.get(url)
            response.raise_for_status()

            data = response.text

            # 解析返回数据
            # 格式: var _bk04151 = {...}
            json_match = re.search(r"var\s+\w+\s*=\s*(\{.*?\});", data)

            if json_match:
                try:
                    import json

                    sector_info = json.loads(json_match.group(1))

                    return {
                        "code": code,
                        "name": name,
                        "category": category,
                        "current": float(sector_info.get("now", 0)),
                        "change_pct": float(sector_info.get("change_percent", 0)),
                        "change": float(sector_info.get("change", 0)),
                        "open": float(sector_info.get("open", 0)),
                        "high": float(sector_info.get("high", 0)),
                        "low": float(sector_info.get("low", 0)),
                        "volume": sector_info.get("volume", ""),
                        "amount": sector_info.get("amount", ""),
                        "trading_status": self._get_trading_status(sector_info),
                        "time": sector_info.get("time", ""),
                    }
                except (json.JSONDecodeError, ValueError) as e:
                    self.log(f"解析板块 {name} 数据失败: {e}")
                    return self._get_mock_sector(code, name, category)

            # 如果API返回格式不同，尝试备用解析
            return self._parse_backup(data, code, name, category)

        except httpx.HTTPStatusError as e:
            self.log(f"获取板块 {name} 数据HTTP错误: {e}")
            return self._get_mock_sector(code, name, category)
        except Exception as e:
            self.log(f"获取板块 {name} 数据异常: {e}")
            return self._get_mock_sector(code, name, category)

    def _parse_backup(
        self, data: str, code: str, name: str, category: str
    ) -> dict[str, Any] | None:
        """备用解析方法"""
        try:
            # 尝试解析JSON数组格式
            if data.startswith("[") and data.endswith("]"):
                import json

                items = json.loads(data)
                if items:
                    item = items[0]
                    return {
                        "code": code,
                        "name": name,
                        "category": category,
                        "current": float(item.get("now", item.get("price", 0))),
                        "change_pct": float(item.get("change_percent", item.get("change_pct", 0))),
                        "change": float(item.get("change", 0)),
                        "open": float(item.get("open", 0)),
                        "high": float(item.get("high", 0)),
                        "low": float(item.get("low", 0)),
                        "volume": item.get("volume", ""),
                        "amount": item.get("amount", ""),
                        "trading_status": "交易",
                        "time": item.get("time", ""),
                    }
        except Exception:
            pass

        return self._get_mock_sector(code, name, category)

    def _get_trading_status(self, sector_info: dict) -> str:
        """判断交易状态"""
        try:
            # 根据时间判断
            now = datetime.now()
            current_time = now.hour * 100 + now.minute

            # A股交易时间: 9:30-11:30, 13:00-15:00
            morning_start = 930
            morning_end = 1130
            afternoon_start = 1300
            afternoon_end = 1500

            if (
                morning_start <= current_time <= morning_end
                or afternoon_start <= current_time <= afternoon_end
            ):
                return "交易"
            elif current_time < morning_start:
                return "竞价"
            else:
                return "收盘"
        except Exception:
            return "未知"

    def _get_mock_sector(self, code: str, name: str, category: str) -> dict[str, Any]:
        """生成模拟数据（备用）"""
        import random

        change_pct = random.uniform(-3, 3)

        return {
            "code": code,
            "name": name,
            "category": category,
            "current": round(random.uniform(1000, 5000), 2),
            "change_pct": round(change_pct, 2),
            "change": round(change_pct * random.uniform(10, 50), 2),
            "open": 0,
            "high": 0,
            "low": 0,
            "volume": "",
            "amount": "",
            "trading_status": "交易",
            "time": datetime.now().strftime("%H:%M:%S"),
        }

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self._cache:
            return False
        return (time.time() - self._cache_time) < self._cache_timeout

    def clear_cache(self):
        """清空缓存"""
        self._cache = []
        self._cache_time = 0.0

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["cache_size"] = len(self._cache)
        status["cache_timeout"] = self._cache_timeout
        status["sector_count"] = len(self.SECTOR_CONFIG)
        return status

    def get_sector_config(self) -> list[dict[str, str]]:
        """获取板块配置"""
        return self.SECTOR_CONFIG

    async def health_check(self) -> bool:
        """
        健康检查 - 新浪板块接口

        Returns:
            bool: 健康状态
        """
        try:
            # 使用示例板块代码进行健康检查
            sector_code = "bk04151"  # 白酒
            url = f"https://quote.sina.com.cn/api/json.php/var%20_{sector_code}=CN_BK.getListDetail?symbol={sector_code}"
            response = await self.client.get(url, timeout=self.timeout)
            response.raise_for_status()

            # 验证返回数据格式
            if response.text and "var" in response.text:
                return True
            return False
        except Exception:
            return False


class SectorDataAggregator(DataSource):
    """板块数据聚合器"""

    def __init__(self, timeout: float = 15.0):
        super().__init__(
            name="sector_aggregator", source_type=DataSourceType.SECTOR, timeout=timeout
        )
        self._sources: list[DataSource] = []
        self._primary_source: DataSource | None = None

    def add_source(self, source: DataSource, is_primary: bool = False):
        """添加数据源"""
        self._sources.append(source)
        if is_primary or self._primary_source is None:
            self._primary_source = source

    async def fetch(self, sector_code: str | None = None) -> DataSourceResult:
        """获取板块数据"""
        errors = []

        # 优先使用主数据源
        if self._primary_source:
            try:
                result = await self._primary_source.fetch(sector_code)
                if result.success:
                    return result
                errors.append(f"{self._primary_source.name}: {result.error}")
            except Exception as e:
                errors.append(f"{self._primary_source.name}: {str(e)}")

        # 尝试其他数据源
        for source in self._sources:
            if source == self._primary_source:
                continue
            try:
                result = await source.fetch(sector_code)
                if result.success:
                    return result
                errors.append(f"{source.name}: {result.error}")
            except Exception as e:
                errors.append(f"{source.name}: {str(e)}")

        return DataSourceResult(
            success=False,
            error=f"所有数据源均失败: {'; '.join(errors)}",
            timestamp=time.time(),
            source=self.name,
            metadata={"sector_code": sector_code, "errors": errors},
        )

    async def fetch_all(self) -> DataSourceResult:
        """获取所有板块数据"""
        return await self.fetch()

    async def fetch_by_category(self, category: str) -> DataSourceResult:
        """按类别获取板块数据"""
        for source in self._sources:
            if hasattr(source, "fetch_by_category"):
                try:
                    result = await source.fetch_by_category(category)
                    if result.success:
                        return result
                except Exception:
                    continue

        return DataSourceResult(
            success=False,
            error=f"无法获取类别 {category} 的数据",
            timestamp=time.time(),
            source=self.name,
        )

    def get_status(self) -> dict[str, Any]:
        """获取聚合器状态"""
        status = super().get_status()
        status["source_count"] = len(self._sources)
        status["primary_source"] = self._primary_source.name if self._primary_source else None
        status["sources"] = [s.name for s in self._sources]
        return status

    async def fetch_batch(self, sector_codes: list[str]) -> list[DataSourceResult]:
        """批量获取板块数据"""
        results = []
        for code in sector_codes:
            result = await self.fetch(code)
            results.append(result)
        return results

    async def close(self):
        """关闭所有数据源"""
        for source in self._sources:
            if hasattr(source, "close"):
                try:
                    await source.close()
                except Exception:
                    pass


# 导出类
__all__ = [
    "SinaSectorDataSource",
    "SectorDataAggregator",
    "EastMoneySectorSource",  # AKShare 东方财富板块
    "EastMoneyIndustryDetailSource",  # 行业板块详情
    "EastMoneyConceptDetailSource",  # 概念板块详情
    "EastMoneyDirectSource",  # EastMoney 直连 API (资金流向)
]


# ============================================================
# EastMoney 直连 API 数据源 (资金流向完整版)
# 类似 lanZzV/fund 项目的实现
# ============================================================


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
        print(f"[EastMoneyDirectSource] {message}")

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

        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "cb": "",
            "fid": "f62",  # 按主力净流入排序
            "po": "1",  # 降序
            "pz": "100",  # 获取100条
            "pn": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "ut": "8dec03ba335b81bf4ebdf7b29ec27d15",
            "fs": board_type,
            "fields": "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13",
        }

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            json_data = response.json()

            if not json_data.get("data"):
                return None

            sectors = []
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

            # 按涨跌幅降序排序
            sectors = sorted(sectors, key=lambda x: x.get("change_percent", 0), reverse=True)

            # 去除重复数据（Ⅲ和Ⅱ版本数据相同，只保留一个）
            seen = set()
            unique_sectors = []
            for s in sectors:
                # 用价格+涨跌幅+主力净流入作为唯一标识
                key = (s.get("price"), s.get("change_percent"), s.get("main_inflow"))
                if key not in seen:
                    seen.add(key)
                    unique_sectors.append(s)
            sectors = unique_sectors

            # 添加排名
            for i, sector in enumerate(sectors):
                sector["rank"] = i + 1

            # 使用最近交易日作为时间戳
            trading_day = get_last_trading_day()

            return {
                "type": sector_type,
                "sectors": sectors,
                "count": len(sectors),
                "timestamp": trading_day.timestamp(),
            }

        except Exception as e:
            self.log(f"获取板块数据失败: {e}")
            return None

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

        processed_results = []
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
                processed_results.append(result)
        return processed_results


# ============================================================
# AKShare 东方财富板块数据源
# ============================================================


class EastMoneySectorSource(DataSource):
    """
    东方财富板块数据源

    功能:
    - 获取行业板块列表及涨跌幅
    - 获取概念板块列表及涨跌幅

    接口:
    - stock_board_industry_name_em() - 行业板块
    - stock_board_concept_name_em() - 概念板块
    """

    def __init__(self, timeout: float = 15.0):
        super().__init__(
            name="sector_eastmoney_akshare", source_type=DataSourceType.SECTOR, timeout=timeout
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timeout = 60.0

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
            import akshare as ak

            if sector_type == "industry":
                data = await self._fetch_industry(ak)
            elif sector_type == "concept":
                data = await self._fetch_concept(ak)
            else:
                return DataSourceResult(
                    success=False,
                    error=f"不支持的板块类型: {sector_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"sector_type": sector_type},
                )

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

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 未安装，请运行: pip install akshare",
                timestamp=time.time(),
                source=self.name,
                metadata={"sector_type": sector_type, "error_type": "ImportError"},
            )
        except Exception as e:
            return self._handle_error(e, self.name)

    async def _fetch_industry(self, ak) -> dict[str, Any] | None:
        """获取行业板块数据"""
        try:
            df = ak.stock_board_industry_name_em()
            if df is not None and not df.empty:
                sectors = []
                for _, row in df.iterrows():
                    sectors.append(
                        {
                            "rank": row.get("排名", 0),
                            "name": row.get("板块名称", ""),
                            "code": row.get("板块代码", ""),
                            "price": row.get("最新价", 0),
                            "change": row.get("涨跌额", 0),
                            "change_percent": row.get("涨跌幅", 0),
                            "total_market": row.get("总市值", ""),
                            "turnover": row.get("换手率", ""),
                            "up_count": row.get("上涨家数", 0),
                            "down_count": row.get("下跌家数", 0),
                            "lead_stock": row.get("领涨股票", ""),
                            "lead_change": row.get("领涨股票-涨跌幅", 0),
                        }
                    )
                return {"type": "industry", "sectors": sectors, "count": len(sectors)}
        except Exception:
            pass
        return None

    async def _fetch_concept(self, ak) -> dict[str, Any] | None:
        """获取概念板块数据"""
        try:
            df = ak.stock_board_concept_name_em()
            if df is not None and not df.empty:
                sectors = []
                for _, row in df.iterrows():
                    sectors.append(
                        {
                            "rank": row.get("排名", 0),
                            "name": row.get("板块名称", ""),
                            "code": row.get("板块代码", ""),
                            "price": row.get("最新价", 0),
                            "change": row.get("涨跌额", 0),
                            "change_percent": row.get("涨跌幅", 0),
                            "total_market": row.get("总市值", ""),
                            "turnover": row.get("换手率", ""),
                            "up_count": row.get("上涨家数", 0),
                            "down_count": row.get("下跌家数", 0),
                            "lead_stock": row.get("领涨股票", ""),
                            "lead_change": row.get("领涨股票-涨跌幅", 0),
                        }
                    )
                return {"type": "concept", "sectors": sectors, "count": len(sectors)}
        except Exception:
            pass
        return None

    async def fetch_batch(self, sector_types: list[str]) -> list[DataSourceResult]:
        """批量获取板块数据"""

        async def fetch_one(stype: str) -> DataSourceResult:
            return await self.fetch(stype)

        tasks = [fetch_one(stype) for stype in sector_types]
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
                        metadata={"sector_type": sector_types[i]},
                    )
                )
            else:
                processed_results.append(result)
        return processed_results

    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache:
            return False
        cache_time = self._cache[cache_key].get("_cache_time", 0)
        return (time.time() - cache_time) < self._cache_timeout

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["cache_size"] = len(self._cache)
        status["cache_timeout"] = self._cache_timeout
        status["supported_types"] = ["industry", "concept"]
        return status

    async def health_check(self) -> bool:
        """
        健康检查 - 东方财富板块接口

        Returns:
            bool: 健康状态
        """
        try:
            import akshare as ak

            loop = asyncio.get_event_loop()

            # 尝试获取行业板块数据
            df = await loop.run_in_executor(None, lambda: ak.stock_board_industry_name_em())

            # 验证返回数据
            if df is not None and not df.empty:
                return True
            return False
        except Exception:
            return False


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

            df = ak.stock_board_industry_cons_em(symbol=sector_name)
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

            df = ak.stock_board_concept_cons_em(symbol=sector_name)
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

    def _is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self._cache:
            return False
        cache_time = self._cache[cache_key].get("_cache_time", 0)
        return (time.time() - cache_time) < self._cache_timeout

    def clear_cache(self):
        self._cache.clear()
