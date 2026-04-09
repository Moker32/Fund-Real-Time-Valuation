"""东方财富板块数据源 - akshare 接口实现"""

import asyncio
import logging
import time
from typing import Any

from ..base import DataSource, DataSourceResult, DataSourceType
from .sector_helpers import get_last_trading_day

logger = logging.getLogger(__name__)


class EastMoneySectorDataSource(DataSource):
    """东方财富行业板块数据源
    使用 akshare 的 stock_board_industry_spot_em 接口
    """

    # 东方财富行业板块配置
    SECTOR_CONFIG = [
        {"code": "BK1041", "name": "白酒", "category": "消费"},
        {"code": "BK1045", "name": "新能源车", "category": "新能源"},
        {"code": "BK1033", "name": "光伏", "category": "新能源"},
        {"code": "BK0465", "name": "医药", "category": "医药"},
        {"code": "BK1039", "name": "半导体", "category": "科技"},
        {"code": "BK1036", "name": "人工智能", "category": "科技"},
        {"code": "BK1037", "name": "消费电子", "category": "消费"},
        {"code": "BK0475", "name": "银行", "category": "金融"},
        {"code": "BK0474", "name": "证券", "category": "金融"},
        {"code": "BK0477", "name": "保险", "category": "金融"},
        {"code": "BK0451", "name": "房地产", "category": "周期"},
        {"code": "BK0435", "name": "基建", "category": "周期"},
        {"code": "BK0457", "name": "军工", "category": "制造"},
        {"code": "BK0440", "name": "机械", "category": "制造"},
        {"code": "BK0401", "name": "农林牧渔", "category": "消费"},
    ]

    def __init__(self, timeout: float = 15.0):
        super().__init__(
            name="eastmoney_sector", source_type=DataSourceType.SECTOR, timeout=timeout
        )
        self._cache: list[dict[str, Any]] = []
        self._cache_time: float = 0.0
        self._cache_timeout = 60.0

    def log(self, message: str) -> None:
        logger.info(f"[EastMoneySectorDataSource] {message}")

    async def fetch(self, sector_code: str | None = None) -> DataSourceResult:
        """获取板块数据"""
        # 检查缓存
        if self._is_cache_valid("all") and sector_code is None:
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
            import akshare as ak

            loop = asyncio.get_event_loop()

            # 使用东方财富行业板块行情接口
            df = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: ak.stock_board_industry_spot_em()),
                timeout=self.timeout,
            )

            if df is None or df.empty:
                return DataSourceResult(
                    success=False,
                    error="未获取到板块数据",
                    timestamp=time.time(),
                    source=self.name,
                )

            # 转换为统一格式
            sectors = []
            for _, row in df.iterrows():
                sector = {
                    "code": str(row.get("板块代码", "")),
                    "name": str(row.get("板块名称", "")),
                    "category": self._get_category(str(row.get("板块名称", ""))),
                    "current": float(row.get("最新价", 0) or 0),
                    "change_pct": float(row.get("涨跌幅", 0) or 0),
                    "change": float(row.get("涨跌额", 0) or 0),
                    "open": float(row.get("今开", 0) or 0),
                    "high": float(row.get("最高", 0) or 0),
                    "low": float(row.get("最低", 0) or 0),
                    "volume": str(row.get("成交量", "")),
                    "amount": str(row.get("成交额", "")),
                    "trading_status": "交易中",
                    "time": str(row.get("更新时间", "")),
                }
                sectors.append(sector)

            # 更新缓存
            self._cache = sectors
            self._cache_time = time.time()

            # 过滤指定板块
            if sector_code:
                sectors = [s for s in sectors if s.get("code") == sector_code]

            self._record_success()
            return DataSourceResult(
                success=True,
                data=sectors,
                timestamp=time.time(),
                source=self.name,
                metadata={"count": len(sectors), "sector_code": sector_code},
            )

        except asyncio.TimeoutError:
            return DataSourceResult(
                success=False,
                error="请求超时",
                timestamp=time.time(),
                source=self.name,
            )
        except Exception as e:
            return self._handle_error(e, self.name)

    def _get_category(self, name: str) -> str:
        """根据板块名称推断类别"""
        category_map = {
            "白酒": "消费",
            "食品饮料": "消费",
            "家电": "消费",
            "纺织服装": "消费",
            "新能源车": "新能源",
            "锂电池": "新能源",
            "光伏": "新能源",
            "风电": "新能源",
            "医药": "医药",
            "医疗器械": "医药",
            "中药": "医药",
            "生物疫苗": "医药",
            "半导体": "科技",
            "芯片": "科技",
            "人工智能": "科技",
            "软件服务": "科技",
            "银行": "金融",
            "证券": "金融",
            "保险": "金融",
            "房地产": "周期",
            "基建": "周期",
            "钢铁": "周期",
            "煤炭": "周期",
            "军工": "制造",
            "机械": "制造",
            "汽车": "制造",
        }
        return category_map.get(name, "其他")

    def _is_cache_valid(self, cache_key: str) -> bool:
        if not self._cache:
            return False
        return (time.time() - self._cache_time) < self._cache_timeout

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            import akshare as ak

            loop = asyncio.get_event_loop()
            df = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: ak.stock_board_industry_spot_em()),
                timeout=15.0,
            )
            return df is not None and not df.empty
        except Exception as e:
            logger.warning(f"东方财富板块数据源健康检查失败: {e}")
            return False


class EastMoneySectorSource(DataSource):
    """
    东方财富板块数据源 - 基于 akshare 的 _spot_em 接口

    功能:
    - 获取行业板块实时行情
    - 获取概念板块实时行情

    接口:
    - stock_board_industry_spot_em() - 行业板块实时行情
    - stock_board_concept_spot_em() - 概念板块实时行情

    数据字段映射:
    - 排名 -> rank
    - 板块名称 -> name
    - 板块代码 -> code
    - 最新价 -> price
    - 涨跌额 -> change
    - 涨跌幅 -> change_percent
    - 总市值 -> total_market_value
    - 换手率 -> turnover_rate
    - 上涨家数 -> up_count
    - 下跌家数 -> down_count
    - 领涨股票 -> lead_stock
    - 领涨股票-涨跌幅 -> lead_stock_change
    """

    def __init__(self, timeout: float = 15.0):
        super().__init__(
            name="sector_eastmoney_akshare", source_type=DataSourceType.SECTOR, timeout=timeout
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timeout = 60.0

    def log(self, message: str) -> None:
        """日志方法"""
        logger.info(f"[EastMoneySectorSource] {message}")

    async def fetch(self, sector_type: str = "industry") -> DataSourceResult:
        """
        获取板块实时行情

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

            loop = asyncio.get_event_loop()

            if sector_type == "industry":
                # 使用 run_in_executor 包装同步调用，添加10秒超时控制
                try:
                    df = await asyncio.wait_for(
                        loop.run_in_executor(None, ak.stock_board_industry_spot_em),
                        timeout=10.0,
                    )
                except asyncio.TimeoutError:
                    return DataSourceResult(
                        success=False,
                        error="获取行业板块数据超时（10秒）",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"sector_type": sector_type, "error_type": "TimeoutError"},
                    )
            elif sector_type == "concept":
                # 使用 run_in_executor 包装同步调用，添加10秒超时控制
                try:
                    df = await asyncio.wait_for(
                        loop.run_in_executor(None, ak.stock_board_concept_spot_em),
                        timeout=10.0,
                    )
                except asyncio.TimeoutError:
                    return DataSourceResult(
                        success=False,
                        error="获取概念板块数据超时（10秒）",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"sector_type": sector_type, "error_type": "TimeoutError"},
                    )
            else:
                return DataSourceResult(
                    success=False,
                    error=f"不支持的板块类型: {sector_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"sector_type": sector_type},
                )

            if df is not None and not df.empty:
                data = self._parse_dataframe(df, sector_type)
                data["_cache_time"] = time.time()
                self._cache[cache_key] = data
                self._record_success()
                return DataSourceResult(
                    success=True,
                    data=data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"sector_type": sector_type, "count": len(data.get("sectors", []))},
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
            logger.error(f"获取板块数据失败: {e}")
            return self._handle_error(e, self.name)

    def _parse_dataframe(self, df, sector_type: str) -> dict[str, Any]:
        """
        解析 DataFrame 返回统一格式

        Args:
            df: akshare 返回的 DataFrame
            sector_type: 板块类型

        Returns:
            Dict: 统一格式的板块数据
        """
        sectors = []
        for _, row in df.iterrows():
            item = {
                "rank": self._safe_int(row.get("排名", 0)),
                "name": str(row.get("板块名称", "")),
                "code": str(row.get("板块代码", "")),
                "price": self._safe_float(row.get("最新价", 0)),
                "change": self._safe_float(row.get("涨跌额", 0)),
                "change_percent": self._safe_float(row.get("涨跌幅", 0)),
                "total_market_value": self._safe_float(row.get("总市值", 0)),
                "turnover_rate": self._safe_float(row.get("换手率", 0)),
                "up_count": self._safe_int(row.get("上涨家数", 0)),
                "down_count": self._safe_int(row.get("下跌家数", 0)),
                "lead_stock": str(row.get("领涨股票", "")),
                "lead_stock_change": self._safe_float(row.get("领涨股票-涨跌幅", 0)),
                "sector_type": sector_type,
            }
            # 兼容字段名（供前端使用）
            item["total_market"] = item["total_market_value"]
            item["turnover"] = item["turnover_rate"]
            item["lead_change"] = item["lead_stock_change"]
            sectors.append(item)

        # 使用最近交易日作为时间戳
        trading_day = get_last_trading_day()

        return {
            "type": sector_type,
            "sectors": sectors,
            "count": len(sectors),
            "timestamp": trading_day.timestamp(),
        }

    def _safe_float(self, value: Any) -> float:
        """安全转换为浮点数"""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _safe_int(self, value: Any) -> int:
        """安全转换为整数"""
        if value is None:
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

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
        status["api_version"] = "spot_em"
        return status

    async def health_check(self) -> bool:
        """
        健康检查 - 东方财富板块实时行情接口

        Returns:
            bool: 健康状态
        """
        try:
            import akshare as ak

            loop = asyncio.get_event_loop()

            # 尝试获取行业板块实时数据，添加10秒超时控制
            try:
                df = await asyncio.wait_for(
                    loop.run_in_executor(None, ak.stock_board_industry_spot_em),
                    timeout=10.0,
                )
            except asyncio.TimeoutError:
                logger.warning("健康检查超时（10秒）")
                return False

            # 验证返回数据
            if df is not None and not df.empty:
                return True
            return False
        except Exception as e:
            logger.warning(f"健康检查失败: {e}")
            return False
