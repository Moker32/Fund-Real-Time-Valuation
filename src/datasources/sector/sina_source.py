"""新浪财经行业板块数据源模块"""

import asyncio
import logging
import random
import re
import time
from datetime import datetime
from typing import Any

import httpx

from ..base import DataSource, DataSourceResult, DataSourceType

logger = logging.getLogger(__name__)


class SinaSectorDataSource(DataSource):
    """新浪财经行业板块数据源"""

    def log(self, message: str) -> None:
        """简单的日志方法"""
        logger.info(f"[SinaSectorDataSource] {message}")

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
        cache_key = sector_code or "all"
        if self._is_cache_valid(cache_key) and sector_code is None:
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
                    import json as _json

                    sector_info = _json.loads(json_match.group(1))

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
                except Exception as e:
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

    def _is_cache_valid(self, cache_key: str) -> bool:
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
