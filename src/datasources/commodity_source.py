"""
商品数据源模块

实现从 yfinance 和 AKShare 获取商品数据
- 黄金: yfinance (GC=F)
- WTI原油: yfinance (CL=F)
- 布伦特原油: yfinance (BZ=F)
- Au99.99: AKShare (spot_golden_benchmark_sge)

支持三级缓存：内存 → 数据库 → 外部API
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from src.db.commodity_repo import CommodityCacheDAO, CommodityCategory
from src.db.database import DatabaseManager

from .base import DataSource, DataSourceResult, DataSourceType

logger = logging.getLogger(__name__)


class CommodityDataSource(DataSource):
    """商品数据源基类"""

    def __init__(self, name: str, timeout: float = 15.0):
        """
        初始化商品数据源

        Args:
            name: 数据源名称
            timeout: 请求超时时间(秒)
        """
        super().__init__(
            name=name,
            source_type=DataSourceType.COMMODITY,
            timeout=timeout
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timeout = 60.0  # 内存缓存60秒
        self._db_dao: CommodityCacheDAO | None = None

    def set_db_dao(self, dao: CommodityCacheDAO) -> None:
        """设置数据库 DAO 用于缓存数据"""
        self._db_dao = dao

    async def _save_to_database(
        self, commodity_type: str, data: dict[str, Any], source: str
    ) -> None:
        """保存数据到数据库"""
        if self._db_dao:
            try:
                self._db_dao.save_from_api(commodity_type, data, source)
            except Exception as e:
                logger.warning(f"保存商品数据到数据库失败: {e}")

    async def close(self):
        """关闭数据源（子类应重写此方法）"""
        pass


class YFinanceCommoditySource(CommodityDataSource):
    """yfinance 商品数据源"""

    # 商品 ticker 映射
    COMMODITY_TICKERS = {
        # 国际期货
        "gold": "GC=F",       # COMEX 黄金
        "gold_cny": "SG=f",   # 上海黄金
        "wti": "CL=F",        # WTI 原油
        "brent": "BZ=F",      # 布伦特原油
        "silver": "SI=F",     # 白银
        "natural_gas": "NG=F",  # 天然气
        # 贵金属 (预留)
        "platinum": "PT=F",   # 铂金
        "palladium": "PA=F",  # 钯金
        # 基本金属 (预留)
        "copper": "HG=F",     # 铜
        "aluminum": "AL=f",   # 铝
        "zinc": "ZN=f",       # 锌
        "nickel": "NI=f",     # 镍
    }

    def __init__(self, timeout: float = 15.0):
        super().__init__(
            name="yfinance_commodity",
            timeout=timeout
        )

    async def fetch(self, commodity_type: str = "gold") -> DataSourceResult:
        """
        获取商品数据

        Args:
            commodity_type: 商品类型 (gold, wti, brent, silver, natural_gas)

        Returns:
            DataSourceResult: 商品数据结果
        """
        # 检查数据库缓存
        if self._db_dao:
            try:
                db_record = self._db_dao.get_latest(commodity_type)
                if db_record and not self._db_dao.is_expired(commodity_type):
                    data = db_record.to_dict()
                    # 移除内部字段
                    data.pop("id", None)
                    data.pop("created_at", None)
                    return DataSourceResult(
                        success=True,
                        data=data,
                        timestamp=datetime.fromisoformat(
                            data.get("timestamp", "").replace("Z", "+00:00")
                        ).timestamp() if data.get("timestamp") else time.time(),
                        source=self.name,
                        metadata={"commodity_type": commodity_type, "from_cache": "database"}
                    )
            except Exception as e:
                logger.warning(f"查询数据库缓存失败: {e}")

        # 检查内存缓存
        cache_key = commodity_type
        if self._is_cache_valid(cache_key):
            return DataSourceResult(
                success=True,
                data=self._cache[cache_key],
                timestamp=self._cache[cache_key].get("_cache_time", time.time()),
                source=self.name,
                metadata={"commodity_type": commodity_type, "from_cache": "memory"}
            )

        try:
            import yfinance as yf

            ticker = self.COMMODITY_TICKERS.get(commodity_type)
            if not ticker:
                return DataSourceResult(
                    success=False,
                    error=f"不支持的商品类型: {commodity_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"commodity_type": commodity_type}
                )

            # 获取数据
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            price = info.get('currentPrice', info.get('regularMarketPrice'))
            change = info.get('regularMarketChange', info.get('change', 0))
            change_percent = info.get('regularMarketChangePercent', info.get('changePercent', 0))

            if price is None:
                return DataSourceResult(
                    success=False,
                    error="无法获取价格数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"commodity_type": commodity_type}
                )

            # 转换时间戳为可读格式
            market_time = info.get('regularMarketTime')
            if market_time:
                try:
                    time_str = datetime.fromtimestamp(market_time).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError, OSError):
                    time_str = str(market_time)
            else:
                time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            data = {
                "commodity": commodity_type,
                "symbol": ticker,
                "name": self._get_name(commodity_type),
                "price": float(price),
                "change": float(change) if change else 0.0,
                "change_percent": float(change_percent) if change_percent else 0.0,
                "currency": info.get('currency', 'USD'),
                "exchange": info.get('exchange', ''),
                "time": time_str,
            }

            # 更新缓存
            data["_cache_time"] = time.time()
            self._cache[cache_key] = data

            # 异步保存到数据库
            await self._save_to_database(commodity_type, data, self.name)

            self._record_success()
            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
                metadata={"commodity_type": commodity_type}
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="yfinance 未安装，请运行: pip install yfinance",
                timestamp=time.time(),
                source=self.name,
                metadata={"commodity_type": commodity_type, "error_type": "ImportError"}
            )
        except Exception as e:
            return self._handle_error(e, self.name)

    async def fetch_batch(self, commodity_types: list[str]) -> list[DataSourceResult]:
        """批量获取商品数据"""
        async def fetch_one(ctype: str) -> DataSourceResult:
            return await self.fetch(ctype)

        tasks = [fetch_one(ctype) for ctype in commodity_types]
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
                        metadata={"commodity_type": commodity_types[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def _get_name(self, commodity_type: str) -> str:
        """获取商品名称"""
        names = {
            "gold": "黄金 (COMEX)",
            "gold_cny": "黄金 (上海)",
            "wti": "WTI原油",
            "brent": "布伦特原油",
            "silver": "白银",
            "natural_gas": "天然气",
            # 贵金属 (预留)
            "platinum": "铂金",
            "palladium": "钯金",
            # 基本金属 (预留)
            "copper": "铜",
            "aluminum": "铝",
            "zinc": "锌",
            "nickel": "镍",
        }
        return names.get(commodity_type, commodity_type)

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
        """获取数据源状态（含缓存信息）"""
        status = super().get_status()
        status["cache_size"] = len(self._cache)
        status["cache_timeout"] = self._cache_timeout
        status["supported_commodities"] = list(self.COMMODITY_TICKERS.keys())
        # 标记预留商品
        reserved = ["platinum", "palladium", "copper", "aluminum", "zinc", "nickel"]
        status["reserved_commodities"] = reserved
        return status

    async def close(self):
        """关闭数据源（yfinance 不需要显式关闭）"""
        pass


class AKShareCommoditySource(CommodityDataSource):
    """AKShare 商品数据源 - 用于国内黄金"""

    def __init__(self, timeout: float = 15.0):
        super().__init__(
            name="akshare_commodity",
            timeout=timeout
        )
        self._cache_timeout = 10.0  # 缓存10秒，商品价格实时性要求高

    async def fetch(self, commodity_type: str = "gold_cny") -> DataSourceResult:
        """获取国内商品数据"""
        # 检查数据库缓存
        if self._db_dao:
            try:
                db_record = self._db_dao.get_latest(commodity_type)
                if db_record and not self._db_dao.is_expired(commodity_type):
                    data = db_record.to_dict()
                    data.pop("id", None)
                    data.pop("created_at", None)
                    return DataSourceResult(
                        success=True,
                        data=data,
                        timestamp=datetime.fromisoformat(
                            data.get("timestamp", "").replace("Z", "+00:00")
                        ).timestamp() if data.get("timestamp") else time.time(),
                        source=self.name,
                        metadata={"commodity_type": commodity_type, "from_cache": "database"}
                    )
            except Exception as e:
                logger.warning(f"查询数据库缓存失败: {e}")

        # 检查内存缓存
        cache_key = commodity_type
        if self._is_cache_valid(cache_key):
            return DataSourceResult(
                success=True,
                data=self._cache[cache_key],
                timestamp=self._cache[cache_key].get("_cache_time", time.time()),
                source=self.name,
                metadata={"commodity_type": commodity_type, "from_cache": "memory"}
            )

        try:
            import akshare as ak  # noqa: F401  # 动态导入检查可用性

            if commodity_type == "gold_cny":
                data = await self._fetch_gold_cny()
            else:
                return DataSourceResult(
                    success=False,
                    error=f"不支持的商品类型: {commodity_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"commodity_type": commodity_type}
                )

            if data:
                data["_cache_time"] = time.time()
                self._cache[cache_key] = data
                # 异步保存到数据库
                await self._save_to_database(commodity_type, data, self.name)
                self._record_success()
                return DataSourceResult(
                    success=True,
                    data=data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"commodity_type": commodity_type}
                )

            return DataSourceResult(
                success=False,
                error="获取商品数据为空",
                timestamp=time.time(),
                source=self.name,
                metadata={"commodity_type": commodity_type}
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="AKShare 未安装",
                timestamp=time.time(),
                source=self.name,
                metadata={"commodity_type": commodity_type}
            )
        except Exception as e:
            return self._handle_error(e, self.name)

    async def _fetch_gold_cny(self) -> dict[str, Any] | None:
        """获取上海黄金交易所 Au99.99 实时数据"""
        import akshare as ak

        # 使用实时行情接口
        df = ak.spot_golden_sge()
        if df is not None and not df.empty:
            latest = df.iloc[0]
            return {
                "commodity": "gold_cny",
                "symbol": "Au99.99",
                "name": "Au99.99 (上海黄金)",
                "price": float(latest.get("价格", 0)),
                "change": float(latest.get("涨跌", 0)),
                "change_percent": float(latest.get("涨跌幅", 0)),
                "time": str(latest.get("时间", "")),
                "high": float(latest.get("最高", 0)),
                "low": float(latest.get("最低", 0)),
                "open": float(latest.get("开盘", 0)),
                "prev_close": float(latest.get("昨收", 0)),
                "currency": "CNY",
                "exchange": "SGE",
            }
        return None

    async def fetch_batch(self, commodity_types: list[str]) -> list[DataSourceResult]:
        """批量获取商品数据"""
        tasks = [self.fetch(ctype) for ctype in commodity_types]
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
                        metadata={"commodity_type": commodity_types[i]}
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

    async def close(self):
        """关闭数据源"""
        pass


class CommodityDataAggregator(CommodityDataSource):
    """商品数据聚合器 - 支持多数据源自动切换"""

    def __init__(self, timeout: float = 15.0):
        super().__init__(
            name="commodity_aggregator",
            timeout=timeout
        )
        self._sources: list[DataSource] = []
        self._primary_source: DataSource | None = None

    def add_source(self, source: DataSource, is_primary: bool = False):
        """添加数据源"""
        self._sources.append(source)
        if is_primary or self._primary_source is None:
            self._primary_source = source

    async def fetch(self, commodity_type: str = "gold") -> DataSourceResult:
        """获取商品数据，尝试多个数据源"""
        errors = []

        # 优先使用主数据源
        if self._primary_source:
            try:
                result = await self._primary_source.fetch(commodity_type)
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
                result = await source.fetch(commodity_type)
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
            metadata={"commodity_type": commodity_type, "errors": errors}
        )

    async def fetch_batch(self, commodity_types: list[str]) -> list[DataSourceResult]:
        """批量获取商品数据"""
        tasks = [self.fetch(ctype) for ctype in commodity_types]
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
                        metadata={"commodity_type": commodity_types[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def get_status(self) -> dict[str, Any]:
        """获取聚合器状态"""
        status = super().get_status()
        status["source_count"] = len(self._sources)
        status["primary_source"] = self._primary_source.name if self._primary_source else None
        status["sources"] = [s.name for s in self._sources]
        return status

    async def close(self):
        """关闭所有数据源"""
        for source in self._sources:
            if hasattr(source, 'close'):
                try:
                    await source.close()
                except Exception:
                    pass


def get_all_commodity_types() -> list[str]:
    """获取所有支持的商品类型"""
    return [
        # 贵金属
        "gold",
        "gold_cny",
        "silver",
        # 能源
        "wti",
        "brent",
        "natural_gas",
        # 基本金属（预留）
        # "copper",
        # "aluminum",
        # "zinc",
        # "nickel",
    ]


def get_commodities_by_category() -> dict[CommodityCategory, list[str]]:
    """获取按分类组织的商品类型"""
    return {
        CommodityCategory.PRECIOUS_METAL: ["gold", "gold_cny", "silver"],
        CommodityCategory.ENERGY: ["wti", "brent", "natural_gas"],
        CommodityCategory.BASE_METAL: [],
    }
