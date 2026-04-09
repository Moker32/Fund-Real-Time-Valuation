"""资金流向板块数据源模块 - 非交易时间可用"""

import asyncio
import logging
import time
from typing import Any

from ..base import DataSource, DataSourceResult, DataSourceType
from .sector_helpers import get_last_trading_day

logger = logging.getLogger(__name__)


class FundFlowConceptSource(DataSource):
    """
    概念板块资金流向数据源 - 非交易时间可用

    功能:
    - 获取概念板块资金流向数据
    - 基于 akshare 的 stock_fund_flow_concept 接口
    - 非交易时间稳定可用（与 EastMoneySectorSource 相比）

    接口:
    - stock_fund_flow_concept(symbol="即时") - 概念板块资金流向
    """

    def __init__(self, timeout: float = 15.0):
        super().__init__(
            name="sector_concept_fund_flow", source_type=DataSourceType.SECTOR, timeout=timeout
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timeout = 60.0
        # 运行时检测 mini_racer 是否可用（防止 JS 引擎崩溃导致服务进程崩溃）
        self._mini_racer_ok = self._check_mini_racer_availability()

    def log(self, message: str) -> None:
        """日志方法"""
        logger.info(f"[FundFlowConceptSource] {message}")

    async def fetch(self, sector_type: str = "concept") -> DataSourceResult:
        """
        获取概念板块资金流向数据

        Args:
            sector_type: 板块类型（固定为 "concept"）

        Returns:
            DataSourceResult: 板块数据结果
        """
        cache_key = "concept"
        # 如果 mini_racer 不可用，直接降级退出，避免直接调用 akshare 的 JS 相关实现
        if not self._mini_racer_ok:
            return DataSourceResult(
                success=False,
                error="mini_racer 不可用，跳过 concept 资金流向数据源",
                timestamp=time.time(),
                source=self.name,
                metadata={"sector_type": sector_type},
            )
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

            # 使用 run_in_executor 包装同步调用，添加超时控制
            try:
                df = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: ak.stock_fund_flow_concept(symbol="即时")),
                    timeout=15.0,
                )
            except asyncio.TimeoutError:
                return DataSourceResult(
                    success=False,
                    error="获取概念板块资金流向数据超时（15秒）",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"sector_type": sector_type, "error_type": "TimeoutError"},
                )

            if df is not None and not df.empty:
                data = self._parse_dataframe(df)
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
                error="获取概念板块资金流向数据为空",
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
            logger.error(f"获取概念板块资金流向数据失败: {e}")
            return self._handle_error(e, self.name)

    def _check_mini_racer_availability(self) -> bool:
        """快速检查 py_mini_racer / mini_racer 的可用性。

        目标是避免因 JS 引擎崩溃导致 Python 进程不可用的问题。
        该检查仅做最基本的可用性测试：导入模块、创建上下文并执行简单表达式。
        """
        try:
            import importlib

            spec = importlib.util.find_spec("py_mini_racer")
            if spec is None:
                return False
            from py_mini_racer import MiniRacer

            mr = MiniRacer()
            # 运行一个简单表达式，确保引擎能工作
            res = mr.eval("1 + 1")
            return res == 2
        except Exception:
            return False

    def _parse_dataframe(self, df) -> dict[str, Any]:
        """
        解析 DataFrame 返回统一格式

        Args:
            df: akshare 返回的 DataFrame

        Returns:
            Dict: 统一格式的板块数据
        """
        sectors = []
        for _, row in df.iterrows():
            item = {
                "rank": self._safe_int(row.get("序号", 0)),
                "name": str(row.get("行业", "")),
                "code": str(row.get("行业指数", "")),
                "price": self._safe_float(row.get("当前价", 0)),
                "change_percent": self._safe_float(row.get("行业-涨跌幅", 0)),
                "net_inflow": self._safe_float(row.get("净额", 0)),
                "lead_stock": str(row.get("领涨股", "")),
                "lead_stock_change": self._safe_float(row.get("领涨股-涨跌幅", 0)),
                "stock_count": self._safe_int(row.get("公司家数", 0)),
                "sector_type": "concept",
            }
            # 兼容字段名（供前端使用）
            item["lead_change"] = item["lead_stock_change"]
            item["up_count"] = 0  # 该接口不提供上涨家数
            item["down_count"] = 0  # 该接口不提供下跌家数
            sectors.append(item)

        # 使用最近交易日作为时间戳
        trading_day = get_last_trading_day()

        return {
            "type": "concept",
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
        status["supported_types"] = ["concept"]
        status["api_version"] = "fund_flow"
        return status

    async def health_check(self) -> bool:
        """
        健康检查 - 概念板块资金流向接口

        Returns:
            bool: 健康状态
        """
        try:
            import akshare as ak

            loop = asyncio.get_event_loop()

            # 尝试获取数据，添加超时控制
            try:
                df = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: ak.stock_fund_flow_concept(symbol="即时")),
                    timeout=15.0,
                )
            except asyncio.TimeoutError:
                logger.warning("健康检查超时（15秒）")
                return False

            # 验证返回数据
            if df is not None and not df.empty:
                return True
            return False
        except Exception as e:
            logger.warning(f"健康检查失败: {e}")
            return False


class FundFlowIndustrySource(DataSource):
    """
    行业板块资金流向数据源 - 非交易时间可用

    功能:
    - 获取行业板块资金流向数据
    - 基于 akshare 的 stock_fund_flow_industry 接口
    - 非交易时间稳定可用（与 EastMoneySectorSource 相比）

    接口:
    - stock_fund_flow_industry(symbol="即时") - 行业板块资金流向
    """

    def __init__(self, timeout: float = 15.0):
        super().__init__(
            name="sector_industry_fund_flow", source_type=DataSourceType.SECTOR, timeout=timeout
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timeout = 60.0

    def log(self, message: str) -> None:
        """日志方法"""
        logger.info(f"[FundFlowIndustrySource] {message}")

    async def fetch(self, sector_type: str = "industry") -> DataSourceResult:
        """
        获取行业板块资金流向数据

        Args:
            sector_type: 板块类型（固定为 "industry"）

        Returns:
            DataSourceResult: 板块数据结果
        """
        cache_key = "industry"
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

            # 使用 run_in_executor 包装同步调用，添加超时控制
            try:
                df = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: ak.stock_fund_flow_industry(symbol="即时")),
                    timeout=15.0,
                )
            except asyncio.TimeoutError:
                return DataSourceResult(
                    success=False,
                    error="获取行业板块资金流向数据超时（15秒）",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"sector_type": sector_type, "error_type": "TimeoutError"},
                )

            if df is not None and not df.empty:
                data = self._parse_dataframe(df)
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
                error="获取行业板块资金流向数据为空",
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
            logger.error(f"获取行业板块资金流向数据失败: {e}")
            return self._handle_error(e, self.name)

    def _parse_dataframe(self, df) -> dict[str, Any]:
        """
        解析 DataFrame 返回统一格式

        Args:
            df: akshare 返回的 DataFrame

        Returns:
            Dict: 统一格式的板块数据
        """
        sectors = []
        for _, row in df.iterrows():
            item = {
                "rank": self._safe_int(row.get("序号", 0)),
                "name": str(row.get("行业", "")),
                "code": str(row.get("行业指数", "")),
                "price": self._safe_float(row.get("当前价", 0)),
                "change_percent": self._safe_float(row.get("行业-涨跌幅", 0)),
                "net_inflow": self._safe_float(row.get("净额", 0)),
                "lead_stock": str(row.get("领涨股", "")),
                "lead_stock_change": self._safe_float(row.get("领涨股-涨跌幅", 0)),
                "stock_count": self._safe_int(row.get("公司家数", 0)),
                "sector_type": "industry",
            }
            # 兼容字段名（供前端使用）
            item["lead_change"] = item["lead_stock_change"]
            item["up_count"] = 0  # 该接口不提供上涨家数
            item["down_count"] = 0  # 该接口不提供下跌家数
            sectors.append(item)

        # 使用最近交易日作为时间戳
        trading_day = get_last_trading_day()

        return {
            "type": "industry",
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
        status["supported_types"] = ["industry"]
        status["api_version"] = "fund_flow"
        return status

    async def health_check(self) -> bool:
        """
        健康检查 - 行业板块资金流向接口

        Returns:
            bool: 健康状态
        """
        try:
            import akshare as ak

            loop = asyncio.get_event_loop()

            # 尝试获取数据，添加超时控制
            try:
                df = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: ak.stock_fund_flow_industry(symbol="即时")),
                    timeout=15.0,
                )
            except asyncio.TimeoutError:
                logger.warning("健康检查超时（15秒）")
                return False

            # 验证返回数据
            if df is not None and not df.empty:
                return True
            return False
        except Exception as e:
            logger.warning(f"健康检查失败: {e}")
            return False
