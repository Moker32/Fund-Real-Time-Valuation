"""
全球市场指数数据源 - 基础模块

提供全球市场指数数据源的基类和共享常量：
- A股: 上证、深证、创业板、科创50、沪深300、中证500/1000
- 港股: 恒生指数、恒生科技
- 美股: 道琼斯、纳斯达克、标普500
- 日经225、欧洲指数(DAX/FTSE/CAC40)

数据源策略:
- A股/港股/美股: 腾讯财经 (实时)
- 日经/欧洲: yfinance (有延迟)
"""

import asyncio
import logging
import time

from ..base import DataSource, DataSourceResult, DataSourceType

logger = logging.getLogger(__name__)


# ============================================================
# 模块级常量
# ============================================================

# 腾讯财经代码映射 (A股、港股、美股)
TENCENT_CODES = {
    # A股 (无 s_ 前缀才能获取完整盘口数据)
    "shanghai": "sh000001",
    "shenzhen": "sz399001",
    "shanghai50": "sh000016",
    "chi_next": "sz399006",
    "star50": "sh000688",
    "csi500": "sh000905",
    "csi1000": "sh000852",
    "hs300": "sh000300",
    # 港股 (hk 前缀)
    "hang_seng": "hkHSI",
    "hang_seng_tech": "hkHSTECH",  # 恒生科技
    # 美股 (us 前缀，腾讯财经格式)
    # 注意：腾讯财经支持道琼斯、纳斯达克和标普500
    "dow_jones": "usDJI",
    "nasdaq": "usIXIC",
    "sp500": "usINX",  # 腾讯财经代码是 usINX 不是 usGSPC
}

# Yahoo Finance ticker 映射 (只包含有历史数据的指数)
YAHOO_TICKERS = {
    # 日经
    "nikkei225": "^N225",
    # 欧洲
    "dax": "^GDAXI",
    "ftse": "^FTSE",
    "cac40": "^FCHI",
    # 港股
    "hang_seng": "^HSI",
    "hang_seng_tech": "HSTECH.HK",
    # 美股 (作为腾讯财经的回退)
    "dow_jones": "^DJI",
    "nasdaq": "^IXIC",
    "sp500": "^GSPC",
}

# 合并所有 ticker 映射
INDEX_TICKERS = {**TENCENT_CODES, **YAHOO_TICKERS}


# AKShare A股指数代码映射 (用于历史数据)
AKSHARE_INDEX_CODES = {
    "shanghai": "sh000001",  # 上证指数
    "shenzhen": "sz399001",  # 深证成指
    "shanghai50": "sh000016",  # 上证50
    "chi_next": "sz399006",  # 创业板指
    "star50": "sh000688",  # 科创50
    "csi500": "sh000905",  # 中证500
    "csi1000": "sh000852",  # 中证1000
    "hs300": "sh000300",  # 沪深300
}


# 判断是否使用腾讯财经
def uses_tencent(index_type: str) -> bool:
    """判断是否使用腾讯财经数据源"""
    return index_type in TENCENT_CODES


# 指数区域分组
INDEX_REGIONS = {
    "shanghai": "china",
    "shenzhen": "china",
    "shanghai50": "china",
    "chi_next": "china",
    "star50": "china",
    "csi500": "china",
    "csi1000": "china",
    "hs300": "china",
    "hang_seng": "hk",
    "hang_seng_tech": "hk",
    "nikkei225": "asia",
    "dow_jones": "america",
    "nasdaq": "america",
    "sp500": "america",
    "dax": "europe",
    "ftse": "europe",
    "cac40": "europe",
}


# 指数中文名称
INDEX_NAMES = {
    "shanghai": "上证指数",
    "shenzhen": "深证成指",
    "shanghai50": "上证 50",
    "chi_next": "创业板指",
    "star50": "科创 50",
    "csi500": "中证 500",
    "csi1000": "中证 1000",
    "hs300": "沪深 300",
    "hang_seng": "恒生指数",
    "hang_seng_tech": "恒生科技",
    "nikkei225": "日经 225",
    "dow_jones": "道琼斯",
    "nasdaq": "纳斯达克",
    "sp500": "标普 500",
    "dax": "德国 DAX",
    "ftse": "富时 100",
    "cac40": "CAC 40",
}


# A股市场配置 (共享)
A_SHARE_MARKET_HOURS = {
    "open": "01:30",
    "close": "08:00",
    "tz": "Asia/Shanghai",
    "lunch_start": "03:30",
    "lunch_end": "05:00",
}

# A股指数列表
A_SHARE_INDICES = [
    "shanghai",
    "shenzhen",
    "shanghai50",
    "chi_next",
    "star50",
    "csi500",
    "csi1000",
    "hs300",
]

# 港股市场配置 (无午休)
HK_MARKET_HOURS = {
    "open": "01:30",
    "close": "08:00",
    "tz": "Asia/Hong_Kong",
}

# 港股指数列表
HK_INDICES = ["hang_seng", "hang_seng_tech"]

# 美股市场配置
US_MARKET_HOURS = {
    "open": "14:30",
    "close": "21:00",
    "tz": "America/New_York",
}

# 美股指数列表
US_INDICES = ["dow_jones", "nasdaq", "sp500"]


# 各市场开盘时间段 (UTC 时间)
MARKET_HOURS: dict[str, dict[str, str]] = {
    # A股 (9:30-11:30, 13:00-15:00 UTC+8) - 使用字典推导式生成
    **{idx: A_SHARE_MARKET_HOURS.copy() for idx in A_SHARE_INDICES},
    # 港股 (9:30-16:00 UTC+8, 无午休)
    **{idx: HK_MARKET_HOURS.copy() for idx in HK_INDICES},
    # 日经 (9:00-15:00 JST, 午休 12:30-13:30 JST)
    # 注意：lunch_start/lunch_end 是市场本地时间，不是 UTC
    "nikkei225": {"open": "00:00", "close": "06:00", "tz": "Asia/Tokyo", "lunch_start": "12:30", "lunch_end": "13:30"},
    # 欧洲 (9:00-17:30 CET, 无午休)
    "dax": {"open": "08:00", "close": "16:30", "tz": "Europe/Berlin"},
    "ftse": {"open": "08:00", "close": "16:30", "tz": "Europe/London"},
    "cac40": {"open": "08:00", "close": "16:30", "tz": "Europe/Paris"},
    # 美股 (9:30-16:00 EST, 无午休)
    **{idx: US_MARKET_HOURS.copy() for idx in US_INDICES},
}


# ============================================================
# 基类
# ============================================================

class IndexDataSource(DataSource):
    """全球指数数据源基类

    由于实时数据不需要缓存，该类移除了缓存逻辑。
    如果未来需要缓存，可以在子类中实现。
    """

    def __init__(self, name: str, timeout: float = 30.0):
        """
        初始化指数数据源

        Args:
            name: 数据源名称
            timeout: 请求超时时间(秒)
        """
        super().__init__(
            name=name,
            source_type=DataSourceType.STOCK,  # 复用 STOCK 类型
            timeout=timeout,
        )

    async def close(self) -> None:
        """关闭数据源"""
        pass

    async def fetch_history(self, index_type: str, period: str = "1y") -> DataSourceResult:
        """
        获取指数历史数据

        Args:
            index_type: 指数类型
            period: 时间周期 (1d, 5d, 1w, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)

        Returns:
            DataSourceResult: 包含历史数据的结果
        """
        raise NotImplementedError("子类必须实现 fetch_history 方法")

    async def fetch_batch(self, index_types: list[str]) -> list[DataSourceResult]:
        """批量获取指数数据的通用实现

        Args:
            index_types: 指数类型列表

        Returns:
            结果列表，与输入顺序一致
        """

        async def fetch_one(itype: str) -> DataSourceResult:
            return await self.fetch(itype)

        tasks = [fetch_one(itype) for itype in index_types]
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
                        metadata={"index_type": index_types[i]},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results
