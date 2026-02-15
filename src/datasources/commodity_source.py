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
from datetime import datetime, timezone
from typing import Any, TypedDict

from src.db.commodity_repo import CommodityCacheDAO, CommodityCategory

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
        super().__init__(name=name, source_type=DataSourceType.COMMODITY, timeout=timeout)
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
                logger.error(f"保存商品数据到数据库失败: {e}")

    async def close(self):
        """关闭数据源（子类应重写此方法）"""
        pass


class YFinanceCommoditySource(CommodityDataSource):
    """yfinance 商品数据源"""

    # 商品 ticker 映射（yfinance 不支持上海黄金交易所 SG=f）
    COMMODITY_TICKERS = {
        # 贵金属
        "gold": "GC=F",  # COMEX 黄金期货
        "gold_pax": "PAXG-USD",  # Pax Gold (数字黄金)
        "silver": "SI=F",  # 国际白银
        "platinum": "PT=F",  # 铂金
        "palladium": "PA=F",  # 钯金
        # 能源
        "wti": "CL=F",  # WTI 原油
        "brent": "BZ=F",  # 布伦特原油
        "natural_gas": "NG=F",  # 天然气
        # 基本金属
        "copper": "HG=F",  # 铜
        "aluminum": "AL=f",  # 铝
        "zinc": "ZN=f",  # 锌
        "nickel": "NI=f",  # 镍
        # 农产品
        "soybean": "ZS=F",  # 大豆
        "corn": "ZC=F",  # 玉米
        "wheat": "ZW=F",  # 小麦
        "coffee": "KC=F",  # 咖啡
        "sugar": "SB=F",  # 白糖
        # 加密货币
        "btc": "BTC-USD",  # 比特币现货
        "btc_futures": "BTC=F",  # 比特币期货
        "eth": "ETH-USD",  # 以太坊现货
        "eth_futures": "ETH=F",  # 以太坊期货
    }

    def __init__(self, timeout: float = 15.0):
        super().__init__(name="yfinance_commodity", timeout=timeout)
        # 加密货币 ticker 映射 (使用 Binance)
        self._crypto_tickers = {
            "btc": "BTCUSDT",
            "eth": "ETHUSDT",
        }

    async def fetch(self, commodity_type: str = "gold") -> DataSourceResult:
        """
        获取商品数据

        Args:
            commodity_type: 商品类型 (gold, wti, brent, silver, natural_gas)

        Returns:
            DataSourceResult: 商品数据结果
        """
        # 加密货币使用 Binance (实时 ~100ms)
        if commodity_type in self._crypto_tickers:
            return await self._fetch_from_binance(commodity_type)
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
                        ).timestamp()
                        if data.get("timestamp")
                        else time.time(),
                        source=self.name,
                        metadata={"commodity_type": commodity_type, "from_cache": "database"},
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
                metadata={"commodity_type": commodity_type, "from_cache": "memory"},
            )

        try:
            import yfinance as yf

            ticker = self.COMMODITY_TICKERS.get(commodity_type)
            if not ticker:
                logger.warning(f"[YFinance] 不支持的商品类型: {commodity_type}")
                return DataSourceResult(
                    success=False,
                    error=f"不支持的商品类型: {commodity_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"commodity_type": commodity_type},
                )

            logger.debug(f"[YFinance] fetching {commodity_type} -> ticker={ticker}")

            # 获取数据
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            if not info or info.get("symbol") is None:
                logger.warning(f"[YFinance] ticker {ticker} 返回空数据或 404")

            price = info.get("currentPrice", info.get("regularMarketPrice"))
            change = info.get("regularMarketChange", info.get("change", 0))
            change_percent = info.get("regularMarketChangePercent", info.get("changePercent", 0))

            if price is None:
                return DataSourceResult(
                    success=False,
                    error="无法获取价格数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"commodity_type": commodity_type},
                )

            # 转换时间戳为 UTC ISO 格式
            market_time = info.get("regularMarketTime")
            if market_time:
                try:
                    utc_dt = datetime.fromtimestamp(market_time, timezone.utc)
                    timestamp_str = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                except (ValueError, TypeError, OSError):
                    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            data = {
                "commodity": commodity_type,
                "symbol": ticker,
                "name": self.get_name(commodity_type),
                "price": float(price),
                "change": float(change) if change else 0.0,
                "change_percent": float(change_percent) if change_percent else 0.0,
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange", ""),
                "timestamp": timestamp_str,
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
                metadata={"commodity_type": commodity_type},
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="yfinance 未安装，请运行: pip install yfinance",
                timestamp=time.time(),
                source=self.name,
                metadata={"commodity_type": commodity_type, "error_type": "ImportError"},
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
                        metadata={"commodity_type": commodity_types[i]},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def get_name(self, commodity_type: str) -> str:
        """获取商品名称"""
        names = {
            "gold": "黄金 (COMEX)",
            "gold_cny": "沪金",
            "gold_pax": "Pax Gold",
            "wti": "WTI原油",
            "brent": "布伦特原油",
            "silver": "白银",
            "natural_gas": "天然气",
            "platinum": "铂金",
            "palladium": "钯金",
            "copper": "铜",
            "aluminum": "铝",
            "zinc": "锌",
            "nickel": "镍",
            "soybean": "大豆",
            "corn": "玉米",
            "wheat": "小麦",
            "coffee": "咖啡",
            "sugar": "白糖",
            "btc": "比特币",
            "btc_futures": "比特币期货",
            "eth": "以太坊",
            "eth_futures": "以太坊期货",
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

    async def _fetch_from_binance(self, commodity_type: str) -> DataSourceResult:
        """从 Binance 获取加密货币数据"""
        import httpx

        symbol = self._crypto_tickers.get(commodity_type)
        if not symbol:
            return DataSourceResult(
                success=False,
                error=f"不支持的加密货币: {commodity_type}",
                timestamp=time.time(),
                source=self.name,
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://api.binance.com/api/v3/ticker/24hr"
                response = await client.get(url, params={"symbol": symbol})
                response.raise_for_status()
                data = response.json()

                crypto_names = {
                    "btc": "比特币",
                    "eth": "以太坊",
                }

                result_data = {
                    "commodity": commodity_type,
                    "symbol": symbol,
                    "name": crypto_names.get(commodity_type, commodity_type),
                    "price": float(data.get("lastPrice", 0)),
                    "change": float(data.get("priceChange", 0)),
                    "change_percent": float(data.get("priceChangePercent", 0)),
                    "currency": "USDT",
                    "exchange": "Binance",
                    "high": float(data.get("highPrice", 0)),
                    "low": float(data.get("lowPrice", 0)),
                    "open": float(data.get("openPrice", 0)),
                    "prev_close": float(data.get("prevClosePrice", 0)),
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }

                cache_key = commodity_type
                result_data["_cache_time"] = time.time()
                self._cache[cache_key] = result_data

                await self._save_to_database(commodity_type, result_data, self.name)

                self._record_success()
                return DataSourceResult(
                    success=True,
                    data=result_data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"commodity_type": commodity_type, "source": "binance"},
                )

        except Exception as e:
            return self._handle_error(e, self.name)


class AKShareCommoditySource(CommodityDataSource):
    """AKShare 商品数据源 - 用于国内黄金"""

    def __init__(self, timeout: float = 15.0):
        super().__init__(name="akshare_commodity", timeout=timeout)
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
                        ).timestamp()
                        if data.get("timestamp")
                        else time.time(),
                        source=self.name,
                        metadata={"commodity_type": commodity_type, "from_cache": "database"},
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
                metadata={"commodity_type": commodity_type, "from_cache": "memory"},
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
                    metadata={"commodity_type": commodity_type},
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
                    metadata={"commodity_type": commodity_type},
                )

            return DataSourceResult(
                success=False,
                error="获取商品数据为空",
                timestamp=time.time(),
                source=self.name,
                metadata={"commodity_type": commodity_type},
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="AKShare 未安装",
                timestamp=time.time(),
                source=self.name,
                metadata={"commodity_type": commodity_type},
            )
        except Exception as e:
            return self._handle_error(e, self.name)

    async def _fetch_gold_cny(self) -> dict[str, Any] | None:
        """获取上海黄金交易所 Au99.99 实时行情数据"""
        import akshare as ak

        try:
            # 优先使用实时行情接口
            df = ak.spot_quotations_sge()
            if df is not None and not df.empty:
                au_df = df[df["品种"] == "Au99.99"]
                if not au_df.empty:
                    latest = au_df.iloc[-1]
                price = float(latest.get("现价", 0) or 0)

                # 获取当日开盘价（第一条数据）
                open_price = float(au_df.iloc[0].get("现价", 0)) if len(au_df) > 0 else None
                # 获取当日最高最低
                high_price = au_df["现价"].astype(float).max()
                low_price = au_df["现价"].astype(float).min()

                # 获取昨日收盘价（从历史接口）
                prev_close = None
                try:
                    hist_df = ak.spot_hist_sge(symbol="Au99.99")
                    if hist_df is not None and len(hist_df) >= 2:
                        prev_close = float(hist_df.iloc[-2].get("close", 0) or 0)
                except Exception:
                    pass

                # 计算涨跌幅
                change = None
                change_percent = None
                if prev_close and prev_close > 0:
                    change = round(price - prev_close, 2)
                    change_percent = round((change / prev_close) * 100, 2)

                return {
                    "commodity": "gold_cny",
                    "symbol": "Au99.99",
                    "name": "Au99.99 (上海黄金)",
                    "price": price,
                    "change": change,
                    "change_percent": change_percent,
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "high": high_price if high_price > 0 else None,
                    "low": low_price if low_price > 0 else None,
                    "open": open_price if open_price and open_price > 0 else None,
                    "prev_close": prev_close,
                    "currency": "CNY",
                    "exchange": "SGE",
                }
        except Exception as e:
            logger.warning(f"获取沪金实时数据失败，尝试备用接口: {e}")

        # 备用：使用历史数据接口
        try:
            df = ak.spot_hist_sge(symbol="Au99.99")
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                trade_date = latest.get("date", "")
                price = float(latest.get("close", 0) or 0)
                open_price = float(latest.get("open", 0) or 0)
                high = float(latest.get("high", 0) or 0)
                low = float(latest.get("low", 0) or 0)
                prev_close = None
                if len(df) >= 2:
                    prev_close = float(df.iloc[-2].get("close", 0) or 0)

                change = None
                change_percent = None
                if prev_close and prev_close > 0:
                    change = round(price - prev_close, 2)
                    change_percent = round((change / prev_close) * 100, 2)

                return {
                    "commodity": "gold_cny",
                    "symbol": "Au99.99",
                    "name": "Au99.99 (上海黄金)",
                    "price": price,
                    "change": change,
                    "change_percent": change_percent,
                    "timestamp": f"{trade_date}T00:00:00Z",
                    "high": high if high > 0 else None,
                    "low": low if low > 0 else None,
                    "open": open_price if open_price > 0 else None,
                    "prev_close": prev_close,
                    "currency": "CNY",
                    "exchange": "SGE",
                }
        except Exception as e2:
            logger.warning(f"备用接口也失败: {e2}")

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
                        metadata={"commodity_type": commodity_types[i]},
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
        super().__init__(name="commodity_aggregator", timeout=timeout)
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
            metadata={"commodity_type": commodity_type, "errors": errors},
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
                        metadata={"commodity_type": commodity_types[i]},
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
            if hasattr(source, "close"):
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
        "gold_pax",
        "silver",
        # 能源
        "wti",
        "brent",
        "natural_gas",
        # 基本金属
        "copper",
        "aluminum",
        "zinc",
        "nickel",
        # 农产品
        "soybean",
        "corn",
        "wheat",
        "coffee",
        "sugar",
        # 加密货币
        "btc",
        "btc_futures",
        "eth",
        "eth_futures",
    ]


def get_commodities_by_category() -> dict[CommodityCategory, list[str]]:
    """获取按分类组织的商品类型"""
    return {
        CommodityCategory.PRECIOUS_METAL: ["gold", "gold_cny", "gold_pax", "silver"],
        CommodityCategory.ENERGY: ["wti", "brent", "natural_gas"],
        CommodityCategory.BASE_METAL: ["copper", "aluminum", "zinc", "nickel"],
        CommodityCategory.AGRICULTURE: ["soybean", "corn", "wheat", "coffee", "sugar"],
        CommodityCategory.CRYPTO: ["btc", "btc_futures", "eth", "eth_futures"],
    }


# 搜索商品配置映射（用于自定义关注商品搜索）
SEARCHABLE_COMMODITIES: dict[str, dict[str, str]] = {
    # 贵金属
    "GC=F": {
        "name": "黄金 (COMEX)",
        "category": "precious_metal",
        "exchange": "CME",
        "currency": "USD",
    },
    "Au99.99": {
        "name": "上海黄金 (Au99.99)",
        "category": "precious_metal",
        "exchange": "SGE",
        "currency": "CNY",
    },
    "SI=F": {"name": "白银", "category": "precious_metal", "exchange": "CME", "currency": "USD"},
    "PT=F": {"name": "铂金", "category": "precious_metal", "exchange": "NYMEX", "currency": "USD"},
    "PA=F": {"name": "钯金", "category": "precious_metal", "exchange": "NYMEX", "currency": "USD"},
    # 能源
    "CL=F": {"name": "WTI 原油", "category": "energy", "exchange": "NYMEX", "currency": "USD"},
    "BZ=F": {"name": "布伦特原油", "category": "energy", "exchange": "ICE", "currency": "USD"},
    "NG=F": {"name": "天然气", "category": "energy", "exchange": "NYMEX", "currency": "USD"},
    "HO=F": {"name": "燃油", "category": "energy", "exchange": "NYMEX", "currency": "USD"},
    "RB=F": {"name": "汽油", "category": "energy", "exchange": "NYMEX", "currency": "USD"},
    # 基本金属
    "HG=F": {"name": "铜", "category": "base_metal", "exchange": "CME", "currency": "USD"},
    "ALU": {"name": "铝", "category": "base_metal", "exchange": "LME", "currency": "USD"},
    "ZN=F": {"name": "锌", "category": "base_metal", "exchange": "LME", "currency": "USD"},
    "NI=F": {"name": "镍", "category": "base_metal", "exchange": "LME", "currency": "USD"},
    "PB=F": {"name": "铅", "category": "base_metal", "exchange": "LME", "currency": "USD"},
    "SN=F": {"name": "锡", "category": "base_metal", "exchange": "LME", "currency": "USD"},
    # 农产品
    "ZS=F": {"name": "大豆", "category": "agriculture", "exchange": "CBOT", "currency": "USD"},
    "ZC=F": {"name": "玉米", "category": "agriculture", "exchange": "CBOT", "currency": "USD"},
    "ZW=F": {"name": "小麦", "category": "agriculture", "exchange": "CBOT", "currency": "USD"},
    "KC=F": {"name": "咖啡", "category": "agriculture", "exchange": "ICE", "currency": "USD"},
    "SB=F": {"name": "白糖", "category": "agriculture", "exchange": "ICE", "currency": "USD"},
    "CC=F": {"name": "可可", "category": "agriculture", "exchange": "ICE", "currency": "USD"},
    "CT=F": {"name": "棉花", "category": "agriculture", "exchange": "ICE", "currency": "USD"},
    "LE=F": {"name": "活牛", "category": "agriculture", "exchange": "CME", "currency": "USD"},
    "HE=F": {"name": "瘦肉猪", "category": "agriculture", "exchange": "CME", "currency": "USD"},
    "ZR=F": {"name": "糙米", "category": "agriculture", "exchange": "CBOT", "currency": "USD"},
    "OJ=F": {"name": "橙汁", "category": "agriculture", "exchange": "ICE", "currency": "USD"},
    # 加密货币现货
    "BTC-USD": {"name": "比特币", "category": "crypto", "exchange": "Spot", "currency": "USD"},
    "ETH-USD": {"name": "以太坊", "category": "crypto", "exchange": "Spot", "currency": "USD"},
    # 加密货币期货
    "BTC=F": {"name": "比特币期货", "category": "crypto", "exchange": "CME", "currency": "USD"},
    "ETH=F": {"name": "以太坊期货", "category": "crypto", "exchange": "CME", "currency": "USD"},
}


class CommoditySearchResult(TypedDict):
    """商品搜索结果"""

    symbol: str
    name: str
    exchange: str
    currency: str
    category: str


class CommoditySearchResponse(TypedDict):
    """商品搜索响应"""

    query: str
    results: list[CommoditySearchResult]
    timestamp: str


def identify_category(symbol: str) -> str:
    """
    识别商品分类

    Args:
        symbol: 商品代码

    Returns:
        str: 分类名称
    """
    clean_symbol = symbol.upper().strip()
    if clean_symbol in SEARCHABLE_COMMODITIES:
        return SEARCHABLE_COMMODITIES[clean_symbol]["category"]
    return "other"


def search_commodities(query: str) -> list[CommoditySearchResult]:
    """
    搜索可关注的大宗商品

    支持按代码或名称模糊搜索，返回匹配的 yfinance 可期货商品。

    Args:
        query: 搜索关键词（代码或名称）

    Returns:
        list[CommoditySearchResult]: 搜索结果列表
    """
    if not query or len(query.strip()) < 1:
        return []

    query_lower = query.lower().strip()
    results: list[CommoditySearchResult] = []

    for symbol, info in SEARCHABLE_COMMODITIES.items():
        # 检查代码是否匹配
        if query_lower in symbol.lower():
            results.append(
                {
                    "symbol": symbol,
                    "name": info["name"],
                    "exchange": info["exchange"],
                    "currency": info["currency"],
                    "category": info["category"],
                }
            )
            continue

        # 检查名称是否匹配
        if query_lower in info["name"].lower():
            results.append(
                {
                    "symbol": symbol,
                    "name": info["name"],
                    "exchange": info["exchange"],
                    "currency": info["currency"],
                    "category": info["category"],
                }
            )

    return results


def get_all_available_commodities() -> list[CommoditySearchResult]:
    """
    获取所有可关注的大宗商品列表

    Returns:
        list[CommoditySearchResult]: 所有可用商品列表
    """
    results: list[CommoditySearchResult] = []
    for symbol, info in SEARCHABLE_COMMODITIES.items():
        results.append(
            {
                "symbol": symbol,
                "name": info["name"],
                "exchange": info["exchange"],
                "currency": info["currency"],
                "category": info["category"],
            }
        )
    return results
