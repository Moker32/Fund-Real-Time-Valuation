"""
商品数据源模块
实现从 yfinance 和 AKShare 获取商品数据
- 黄金: yfinance (GC=F)
- WTI原油: yfinance (CL=F)
- 布伦特原油: yfinance (BZ=F)
- Au99.99: AKShare (spot_golden_benchmark_sge)
"""

import asyncio
import time
from datetime import datetime
from typing import Any

from .base import DataSource, DataSourceResult, DataSourceType


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
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timeout = 60.0  # 缓存60秒

    async def fetch(self, commodity_type: str = "gold") -> DataSourceResult:
        """
        获取商品数据

        Args:
            commodity_type: 商品类型 (gold, wti, brent, silver, natural_gas)

        Returns:
            DataSourceResult: 商品数据结果
        """
        # 检查缓存
        cache_key = commodity_type
        if self._is_cache_valid(cache_key):
            return DataSourceResult(
                success=True,
                data=self._cache[cache_key],
                timestamp=self._cache[cache_key].get("_cache_time", time.time()),
                source=self.name,
                metadata={"commodity_type": commodity_type, "from_cache": True}
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
                "symbol": ticker,  # 添加 ticker symbol
                "name": self._get_name(commodity_type),
                "price": float(price),
                "change": float(change) if change else 0.0,
                # yfinance 返回的 change_percent 已经是百分比格式（如 3.37 表示 3.37%）
                "change_percent": float(change_percent) if change_percent else 0.0,
                "currency": info.get('currency', 'USD'),
                "exchange": info.get('exchange', ''),
                "time": time_str,
            }

            # 缓存数据
            data["_cache_time"] = time.time()
            self._cache[cache_key] = data

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
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timeout = 60.0

    async def fetch(self, commodity_type: str = "gold_cny") -> DataSourceResult:
        """获取国内商品数据"""
        cache_key = commodity_type
        if self._is_cache_valid(cache_key):
            return DataSourceResult(
                success=True,
                data=self._cache[cache_key],
                timestamp=self._cache[cache_key].get("_cache_time", time.time()),
                source=self.name,
                metadata={"commodity_type": commodity_type, "from_cache": True}
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
        """获取上海黄金交易所 Au99.99 数据"""
        import akshare as ak

        df = ak.spot_golden_benchmark_sge()
        if df is not None and not df.empty:
            latest = df.iloc[0]
            return {
                "commodity": "gold_cny",
                "symbol": "Au99.99",  # 添加 symbol
                "name": "Au99.99 (上海黄金)",
                "price": float(latest.get("早盘价", latest.get("晚盘价", 0))),
                "change_percent": 0.0,  # API 不提供涨跌幅
                "time": str(latest.get("交易时间", "")),
                "raw_data": df.to_dict("records")[:3]
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
