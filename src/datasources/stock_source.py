"""
股票行情数据源模块
实现从新浪财经和 Yahoo Finance 获取股票行情

支持的股票类型:
- A股: sh600000, sz000001 (6/0/3开头)
- 港股: 0700.HK
- 美股: AAPL, MSFT
"""

import asyncio
import re
import time
from datetime import datetime
from typing import Any

import httpx

from .base import (
    DataSource,
    DataSourceResult,
    DataSourceType,
)


class SinaStockDataSource(DataSource):
    """新浪财经 A 股数据源

    提供上海和深圳 A 股的实时行情数据。
    API: https://hq.sinajs.cn/list=sh600000

    返回字段:
        - name: 股票名称
        - open: 开盘价
        - pre_close: 昨收价
        - price: 当前价
        - high: 最高价
        - low: 最低价
        - bid: 买入价
        - ask: 卖出价
        - volume: 成交量(手)
        - amount: 成交额(元)
        - change: 涨跌额
        - change_pct: 涨跌幅(%)
    """

    # 新浪股票 API 响应字段索引
    FIELD_NAMES = [
        "name",           # 0: 股票名称
        "pre_close",      # 1: 昨收价
        "open",           # 2: 开盘价
        "price",          # 3: 当前价
        "high",           # 4: 最高价
        "low",            # 5: 最低价
        "bid",            # 6: 买入价
        "ask",            # 7: 卖出价
        "volume",         # 8: 成交量(手)
        "amount",         # 9: 成交额(元)
        "bid_volume",     # 10: 买一量
        "ask_volume",     # 11: 卖一量
        "time",           # 12: 时间
    ]

    def __init__(self, timeout: float = 10.0):
        """初始化新浪股票数据源

        Args:
            timeout: 请求超时时间(秒), 默认 10 秒
        """
        super().__init__(
            name="sina_stock",
            source_type=DataSourceType.STOCK,
            timeout=timeout
        )
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://finance.sina.com.cn/",
            }
        )

    async def fetch(self, stock_code: str) -> DataSourceResult:
        """获取 A 股实时行情

        Args:
            stock_code: 股票代码 (如: 600000, 000001)

        Returns:
            DataSourceResult: 包含股票行情数据的结果对象
        """
        # 确定交易所前缀
        market = self._get_market(stock_code)
        url = f"https://hq.sinajs.cn/list={market}{stock_code}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = self._parse_response(response.text, stock_code, market)

            if data:
                self._record_success()
                return DataSourceResult(
                    success=True,
                    data=data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"stock_code": stock_code, "market": market}
                )

            return DataSourceResult(
                success=False,
                error="解析股票数据失败: 响应格式异常",
                timestamp=time.time(),
                source=self.name,
                metadata={"stock_code": stock_code, "market": market}
            )

        except httpx.HTTPStatusError as e:
            return self._handle_error(e, self.name)
        except httpx.RequestError as e:
            return self._handle_error(e, self.name)
        except Exception as e:
            return self._handle_error(e, self.name)

    def _get_market(self, stock_code: str) -> str:
        """根据股票代码判断交易所

        Args:
            stock_code: 股票代码

        Returns:
            'sh' 或 'sz'
        """
        if stock_code.startswith('6'):
            return 'sh'
        elif stock_code.startswith('0') or stock_code.startswith('3'):
            return 'sz'
        else:
            return 'sh'  # 默认上海

    def _parse_response(self, response_text: str, stock_code: str, market: str) -> dict[str, Any] | None:
        """解析新浪股票响应

        响应格式示例:
        var hq_str_sh600000="浦发银行,9.25,9.24,9.30,9.31,9.20,9.25,9.26,152300,1410000,...";

        Args:
            response_text: API 响应文本
            stock_code: 股票代码 (用于参数兼容)
            market: 交易所 (sh/sz)

        Returns:
            解析后的数据字典，解析失败返回 None
        """
        # 匹配 hq_str_sh600000 或 hq_str_sz000001 格式
        match = re.search(rf'hq_str_{market}(\d+?)="([^"]+)";', response_text)
        if not match:
            # 尝试从任意市场匹配
            match = re.search(r'hq_str_(?:sh|sz)(\d+?)="([^"]+)";', response_text)

        if not match:
            return None

        code = match.group(1)
        values = match.group(2).split(',')

        if len(values) < 13:
            return None

        # 提取基础数据
        pre_close = float(values[1])
        open_price = float(values[2])
        current_price = float(values[3])
        change = round(current_price - pre_close, 3)
        change_pct = round(change / pre_close * 100, 2) if pre_close > 0 else 0

        # 构建返回数据
        data = {
            "code": code,
            "name": values[0],
            "open": open_price,
            "pre_close": pre_close,
            "price": current_price,
            "high": float(values[4]),
            "low": float(values[5]),
            "bid": float(values[6]),
            "ask": float(values[7]),
            "volume": int(values[8]),      # 成交量(手)
            "amount": round(float(values[9]) / 10000, 2),  # 成交额(万元)
            "bid_volume": int(values[10]) if len(values) > 10 else 0,
            "ask_volume": int(values[11]) if len(values) > 11 else 0,
            "time": values[12] if len(values) > 12 else "",
            "change": change,
            "change_pct": change_pct,
            "market": market,
        }

        # 添加扩展字段（如果数据足够）
        if len(values) >= 32:
            # 市盈率、市净率等
            data["pe"] = float(values[13]) if values[13] else None
            data["pb"] = float(values[14]) if values[14] else None
            data["high_limit"] = float(values[15]) if values[15] else None
            data["low_limit"] = float(values[16]) if values[16] else None
            data["turnover_rate"] = float(values[21]) if len(values) > 21 else None  # 换手率

        return data

    async def fetch_batch(self, stock_codes: list[str]) -> list[DataSourceResult]:
        """批量获取股票数据

        Args:
            stock_codes: 股票代码列表

        Returns:
            DataSourceResult 列表
        """
        async def fetch_one(code: str) -> DataSourceResult:
            return await self.fetch(code)

        tasks = [fetch_one(code) for code in stock_codes]
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
                        metadata={"stock_code": stock_codes[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["description"] = "新浪财经 A 股数据源"
        status["supported_markets"] = ["sh", "sz"]
        return status


class YahooStockSource(DataSource):
    """Yahoo Finance 股票数据源

    提供全球股票行情支持:
    - A股: 000001.SZ, 600000.SH
    - 港股: 0700.HK
    - 美股: AAPL, MSFT, GOOGL

    特点:
    - 支持多市场
    - 数据丰富（包括市值、市盈率等）
    - 使用 yfinance 库
    """

    def __init__(self, timeout: float = 15.0):
        """初始化 Yahoo Finance 股票数据源

        Args:
            timeout: 请求超时时间(秒), 默认 15 秒
        """
        super().__init__(
            name="yahoo_stock",
            source_type=DataSourceType.STOCK,
            timeout=timeout
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timeout = 30.0  # 缓存 30 秒

    async def fetch(self, symbol: str) -> DataSourceResult:
        """获取股票行情

        Args:
            symbol: 股票代码
                - A股: 000001.SZ, 600000.SH
                - 港股: 0700.HK
                - 美股: AAPL, MSFT

        Returns:
            DataSourceResult: 包含股票行情数据的结果对象
        """
        # 检查缓存
        cache_key = symbol.upper()
        if self._is_cache_valid(cache_key):
            cached_data = self._cache[cache_key]
            return DataSourceResult(
                success=True,
                data=cached_data,
                timestamp=cached_data.get("_cache_time", time.time()),
                source=self.name,
                metadata={"symbol": symbol, "from_cache": True}
            )

        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            info = ticker.info

            # 提取关键数据
            price = info.get('currentPrice', info.get('regularMarketPrice'))
            if price is None:
                return DataSourceResult(
                    success=False,
                    error=f"无法获取 {symbol} 的价格数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"symbol": symbol}
                )

            # 构建返回数据
            data = {
                "symbol": symbol,
                "name": self._get_name(info, symbol),
                "price": float(price),
                "open": float(info.get('regularMarketOpen', 0)),
                "high": float(info.get('regularMarketDayHigh', 0)),
                "low": float(info.get('regularMarketDayLow', 0)),
                "change": float(info.get('regularMarketChange', 0)),
                "change_pct": float(info.get('regularMarketChangePercent', 0)),
                "volume": int(info.get('regularMarketVolume', 0)),
                "market_cap": info.get('marketCap'),
                "pe": info.get('trailingPE'),
                "pb": info.get('priceToBook'),
                "eps": info.get('trailingEps'),
                "dividend_yield": info.get('dividendYield'),
                "exchange": info.get('exchange'),
                "currency": info.get('currency', 'USD'),
            }

            # 获取交易时间
            market_time = info.get('regularMarketTime')
            if market_time:
                try:
                    data["time"] = datetime.fromtimestamp(market_time).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError, OSError):
                    data["time"] = str(market_time)
            else:
                data["time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 添加市场类型
            data["market_type"] = self._get_market_type(symbol)

            # 缓存数据
            data["_cache_time"] = time.time()
            self._cache[cache_key] = data

            self._record_success()
            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
                metadata={"symbol": symbol, "market_type": data["market_type"]}
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="yfinance 未安装，请运行: pip install yfinance",
                timestamp=time.time(),
                source=self.name,
                metadata={"symbol": symbol, "error_type": "ImportError"}
            )
        except Exception as e:
            return self._handle_error(e, self.name)

    def _get_name(self, info: dict, symbol: str) -> str:
        """获取股票名称

        Args:
            info: yfinance 返回的 info 字典
            symbol: 股票代码

        Returns:
            股票名称
        """
        # 优先使用 shortName，其次 longName，最后返回 symbol
        return info.get('shortName', info.get('longName', symbol))

    def _get_market_type(self, symbol: str) -> str:
        """判断市场类型

        Args:
            symbol: 股票代码

        Returns:
            'cn', 'hk', 'us' 或 'other'
        """
        symbol_upper = symbol.upper()

        if symbol_upper.endswith('.SH') or symbol_upper.endswith('.SZ'):
            return 'cn'  # A股
        elif symbol_upper.endswith('.HK'):
            return 'hk'  # 港股
        elif '.' not in symbol_upper:  # 美股通常不带后缀
            return 'us'
        else:
            return 'other'

    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效

        Args:
            cache_key: 缓存键

        Returns:
            缓存是否有效
        """
        if cache_key not in self._cache:
            return False
        cache_time = self._cache[cache_key].get("_cache_time", 0)
        return (time.time() - cache_time) < self._cache_timeout

    async def fetch_batch(self, symbols: list[str]) -> list[DataSourceResult]:
        """批量获取股票数据

        Args:
            symbols: 股票代码列表

        Returns:
            DataSourceResult 列表
        """
        async def fetch_one(sym: str) -> DataSourceResult:
            return await self.fetch(sym)

        tasks = [fetch_one(sym) for sym in symbols]
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
                        metadata={"symbol": symbols[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    async def fetch_history(self, symbol: str, period: str = "1mo") -> dict[str, Any] | None:
        """获取历史数据

        Args:
            symbol: 股票代码
            period: 时间周期 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            包含历史数据的字典，失败返回 None
        """
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)

            if hist.empty:
                return None

            return {
                "symbol": symbol,
                "period": period,
                "data": hist.to_dict("records"),
                "columns": list(hist.columns),
            }

        except Exception:
            return None

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()

    async def close(self):
        """关闭数据源（yfinance 不需要显式关闭）"""
        pass

    def get_status(self) -> dict[str, Any]:
        """获取数据源状态"""
        status = super().get_status()
        status["description"] = "Yahoo Finance 股票数据源"
        status["cache_size"] = len(self._cache)
        status["cache_timeout"] = self._cache_timeout
        status["supported_markets"] = ["cn (A)", "hk (港)", "us (美)"]
        return status


class StockDataAggregator(DataSource):
    """股票数据聚合器 - 支持多数据源自动切换"""

    def __init__(self, timeout: float = 15.0):
        super().__init__(
            name="stock_aggregator",
            source_type=DataSourceType.STOCK,
            timeout=timeout
        )
        self._sources: list[DataSource] = []
        self._primary_source: DataSource | None = None

    def add_source(self, source: DataSource, is_primary: bool = False):
        """添加数据源

        Args:
            source: 数据源实例
            is_primary: 是否作为主数据源
        """
        self._sources.append(source)
        if is_primary or self._primary_source is None:
            self._primary_source = source

    async def fetch(self, symbol: str) -> DataSourceResult:
        """获取股票数据，尝试多个数据源"""
        errors = []

        # 优先使用主数据源
        if self._primary_source:
            try:
                result = await self._primary_source.fetch(symbol)
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
                result = await source.fetch(symbol)
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
            metadata={"symbol": symbol, "errors": errors}
        )

    async def fetch_batch(self, symbols: list[str]) -> list[DataSourceResult]:
        """批量获取股票数据"""
        async def fetch_one(sym: str) -> DataSourceResult:
            return await self.fetch(sym)

        tasks = [fetch_one(sym) for sym in symbols]
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
                        metadata={"symbol": symbols[i]}
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
            if hasattr(source, 'close') and callable(getattr(source, 'close')):
                try:
                    await source.close()
                except Exception:
                    pass


__all__ = [
    "SinaStockDataSource",
    "YahooStockSource",
    "StockDataAggregator",
]
