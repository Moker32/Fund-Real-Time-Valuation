"""
全球市场指数 API 路由
提供全球主要市场指数相关的 REST API 端点
"""

import asyncio
import logging
import time
from datetime import datetime
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import pytz
from fastapi import APIRouter, Depends, HTTPException
from typing_extensions import TypedDict

from src.datasources.base import DataSourceType
from src.datasources.index_source import INDEX_NAMES, INDEX_REGIONS, YAHOO_TICKERS
from src.datasources.manager import DataSourceManager

if TYPE_CHECKING:
    from src.datasources.index_source import HybridIndexSource

from ..dependencies import DataSourceDependency
from ..models import ErrorResponse

logger = logging.getLogger(__name__)

# yfinance marketState 到交易状态的映射
YAHOO_MARKET_STATE_MAP = {
    "REGULAR": "open",  # 交易中
    "CLOSED": "closed",  # 已收盘
    "PRE": "pre",  # 盘前
    "POST": "post",  # 盘后
    "PREPRE": "pre",  # 欧洲盘前
    "POSTPOST": "closed",  # 美股盘后（收盘）
    "HALF": "closed",  # 半天交易
    "REGULAR_RESTRICTED": "open",  # 限制性交易（可能涨跌幅受限）
    "EXTENDED": "open",  # 延长交易
}


class IndexListData(TypedDict):
    """指数列表响应数据结构"""

    indices: list[dict]
    timestamp: str


router = APIRouter(prefix="/api/indices", tags=["全球指数"])


# 支持的指数列表
SUPPORTED_INDICES = list(INDEX_NAMES.keys())

# 腾讯财经的延时指数
TENCENT_DELAYED_INDICES = {"dow_jones", "nasdaq", "sp500", "hang_seng", "hang_seng_tech"}

# yfinance marketState 缓存（避免重复请求）
_market_state_cache: dict[str, tuple[str, float]] = {}
_MARKET_STATE_CACHE_DURATION = 60  # 缓存 60 秒


async def fetch_yahoo_market_state(index_type: str) -> str | None:
    """
    从 yfinance 获取单个指数的 marketState

    Args:
        index_type: 指数类型

    Returns:
        marketState 字符串或 None
    """
    # 检查缓存
    now = time.time()
    if index_type in _market_state_cache:
        state, timestamp = _market_state_cache[index_type]
        if now - timestamp < _MARKET_STATE_CACHE_DURATION:
            return state

    ticker = YAHOO_TICKERS.get(index_type)
    if not ticker:
        return None

    try:
        import yfinance as yf

        ticker_obj = yf.Ticker(ticker)
        # 使用 run_in_executor 避免阻塞事件循环
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: ticker_obj.info)
        market_state = info.get("marketState")

        if market_state:
            _market_state_cache[index_type] = (market_state, now)
            logger.debug(f"[indices] yfinance marketState for {index_type}: {market_state}")

        return market_state
    except Exception as e:
        logger.warning(f"[indices] yfinance marketState fetch failed for {index_type}: {e}")
        return None


def get_trading_status(market_state: str | None) -> dict:
    """
    获取指数的交易状态

    使用 yfinance 的 marketState 动态判断。

    Args:
        market_state: yfinance 返回的 marketState

    Returns:
        dict: 包含交易状态和市场时间信息的字典
    """
    utc_now = datetime.now(pytz.UTC)
    local_now = utc_now.astimezone(pytz.UTC)

    if market_state:
        mapped_status = YAHOO_MARKET_STATE_MAP.get(market_state)
        if mapped_status:
            return {
                "status": mapped_status,
                "market_time": local_now.strftime("%Y-%m-%d %H:%M:%S"),
            }

    # 无法确定状态时返回 unknown
    return {
        "status": "unknown",
        "market_time": None,
    }


async def get_market_state_for_index(data: dict, index_type: str, source: str) -> str | None:
    """
    获取指数的 marketState

    优先使用数据源返回的 marketState，如果没有则从 yfinance 获取，
    如果 yfinance 获取失败则回退到 TradingCalendarSource

    Args:
        data: 数据源返回的数据
        index_type: 指数类型
        source: 数据源名称

    Returns:
        marketState 字符串或 None
    """
    # 优先使用数据源自带的 marketState
    if data.get("market_state"):
        return data.get("market_state")

    # 如果是 tencent 数据源，尝试从 yfinance 获取
    if source == "tencent_index" and index_type in YAHOO_TICKERS:
        yahoo_state = await fetch_yahoo_market_state(index_type)
        if yahoo_state:
            return yahoo_state

    # 回退到使用 TradingCalendarSource 判断交易状态
    try:
        from src.datasources.trading_calendar_source import Market, TradingCalendarSource

        calendar = TradingCalendarSource()

        # 根据指数类型映射到市场
        market_map = {
            # A股指数
            "shanghai": Market.CHINA,
            "shenzhen": Market.CHINA,
            "shanghai50": Market.CHINA,
            "hs300": Market.CHINA,
            "chi_next": Market.CHINA,
            "star50": Market.CHINA,
            "csi500": Market.CHINA,
            "csi1000": Market.CHINA,
            # 港股指数
            "hang_seng": Market.HONG_KONG,
            "hang_seng_tech": Market.HONG_KONG,
            # 美股指数
            "dow_jones": Market.USA,
            "nasdaq": Market.USA,
            "sp500": Market.USA,
            # 其他市场指数
            "nikkei225": Market.JAPAN,
            "dax": Market.GERMANY,
            "ftse": Market.UK,
            "cac40": Market.FRANCE,
        }

        market = market_map.get(index_type)
        if market:
            result = calendar.is_within_trading_hours(market)
            status = result.get("status")
            if status == "open":
                return "REGULAR"
            elif status == "closed":
                return "CLOSED"
            elif status == "break":
                return "CLOSED"  # 午休也算作关闭
            elif status == "pre_market":
                return "PRE"  # 盘前交易
    except Exception as e:
        logger.warning(f"[indices] TradingCalendarSource fallback failed: {e}")

    return None


@router.get(
    "",
    response_model=IndexListData,
    summary="获取全球市场指数",
    description="获取所有支持的全球市场指数实时行情",
    responses={
        200: {"description": "成功获取指数行情"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_indices(
    types: str | None = None,
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> IndexListData:
    """
    获取全球市场指数列表

    Args:
        types: 可选的指数类型列表，逗号分隔
        manager: 数据源管理器依赖

    Returns:
        IndexListData: 包含指数列表和时间戳的字典
    """
    current_time = datetime.now().isoformat() + "Z"

    # 确定要获取的指数类型
    if types:
        index_types = [t.strip() for t in types.split(",") if t.strip()]
        if not index_types:
            return {"indices": [], "timestamp": current_time}
    else:
        index_types = SUPPORTED_INDICES

    # 获取指数数据
    results = await manager.fetch_batch(
        DataSourceType.STOCK, [{"kwargs": {"index_type": it}} for it in index_types]
    )

    if not results or len(results) == 0:
        return {"indices": [], "timestamp": current_time}

    # 解析结果
    all_indices = []

    for _, result in enumerate(results):
        if not result.success or not result.data:
            continue

        data = result.data
        index_type = data.get("index", "")
        data_timestamp = data.get("data_timestamp")
        source = result.source

        # 获取 marketState
        market_state = await get_market_state_for_index(data, index_type, source)
        trading_status = get_trading_status(market_state)

        # 判断是否为延时数据（腾讯的美股数据延时15分钟）
        is_delayed = source == "tencent_index" and index_type in TENCENT_DELAYED_INDICES

        all_indices.append(
            {
                "index": index_type,
                "symbol": data.get("symbol", ""),
                "name": data.get("name", ""),
                "price": data.get("price", 0.0),
                "change": data.get("change"),
                "changePercent": data.get("change_percent"),
                "currency": data.get("currency", ""),
                "exchange": data.get("exchange"),
                "timestamp": data.get("time"),
                "source": source,
                "high": data.get("high"),
                "low": data.get("low"),
                "open": data.get("open"),
                "prevClose": data.get("prev_close"),
                "region": INDEX_REGIONS.get(index_type),
                "tradingStatus": trading_status.get("status"),
                "marketTime": trading_status.get("market_time"),
                "isDelayed": is_delayed,
                "dataTimestamp": data_timestamp,
            }
        )

    return {"indices": all_indices, "timestamp": current_time}


@router.get(
    "/regions",
    summary="获取支持的区域",
    description="获取所有支持的指数区域列表",
)
async def get_regions() -> dict:
    """
    获取支持的区域列表

    Returns:
        dict: 区域信息
    """
    regions: dict[str, dict[str, Any]] = {}
    for index_type, region in INDEX_REGIONS.items():
        if region not in regions:
            regions[region] = {"name": region, "indices": []}
        regions[region]["indices"].append(
            {
                "index": index_type,
                "name": INDEX_NAMES.get(index_type, index_type),
            }
        )

    return {
        "regions": list(regions.values()),
        "supported_indices": SUPPORTED_INDICES,
    }


@router.get(
    "/{index_type}",
    summary="获取单个指数",
    description="根据指数类型获取单个指数的实时行情",
    responses={
        200: {"description": "成功获取指数行情"},
        400: {"model": ErrorResponse, "description": "不支持的指数类型"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_index(
    index_type: str,
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> dict:
    """
    获取单个指数行情

    Args:
        index_type: 指数类型 (shanghai, shenzhen, hang_seng, nikkei225, dow_jones, nasdaq, sp500, dax, ftse, cac40)
        manager: 数据源管理器依赖

    Returns:
        dict: 指数行情数据
    """
    # 验证指数类型
    if index_type not in SUPPORTED_INDICES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的指数类型: {index_type}，支持类型: {', '.join(SUPPORTED_INDICES)}"
        )

    result = await manager.fetch(DataSourceType.STOCK, index_type)

    if not result.success or not result.data:
        error_msg = result.error or "获取数据失败"
        raise HTTPException(status_code=503, detail=error_msg)

    data = result.data
    data_index = data.get("index", "")
    data_timestamp = data.get("data_timestamp")
    source = result.source

    # 获取 marketState
    market_state = await get_market_state_for_index(data, data_index, source)
    trading_status = get_trading_status(market_state)

    # 判断是否为延时数据（腾讯的美股数据延时15分钟）
    is_delayed = source == "tencent_index" and data_index in TENCENT_DELAYED_INDICES

    return {
        "index": data.get("index", ""),
        "symbol": data.get("symbol", ""),
        "name": data.get("name", ""),
        "price": data.get("price", 0.0),
        "change": data.get("change"),
        "changePercent": data.get("change_percent"),
        "currency": data.get("currency", ""),
        "exchange": data.get("exchange"),
        "timestamp": data.get("time"),
        "source": source,
        "high": data.get("high"),
        "low": data.get("low"),
        "open": data.get("open"),
        "prevClose": data.get("prev_close"),
        "region": INDEX_REGIONS.get(data_index),
        "tradingStatus": trading_status.get("status"),
        "marketTime": trading_status.get("market_time"),
        "isDelayed": is_delayed,
        "dataTimestamp": data_timestamp,
    }


# 支持的历史周期参数
INDEX_HISTORY_PERIODS = ["1d", "5d", "1w", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]

# 历史数据源实例（通过依赖注入获取）
def _get_index_history_source() -> "HybridIndexSource":
    """获取指数历史数据源实例（通过依赖注入）"""
    from ..dependencies import get_index_history_source as get_source

    return get_source()


@lru_cache
def _validate_period(period: str) -> str:
    """验证并返回有效的时间周期参数"""
    if period not in INDEX_HISTORY_PERIODS:
        return "1y"
    return period


@router.get(
    "/{index_type}/history",
    response_model=dict,
    summary="获取指数历史数据",
    description="根据指数类型获取历史行情数据，支持多种时间周期",
    responses={
        200: {"description": "成功获取指数历史数据"},
        400: {"model": ErrorResponse, "description": "不支持的指数类型或周期"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_index_history(
    index_type: str,
    period: str = "1y",
) -> dict:
    """
    获取指数历史数据

    Args:
        index_type: 指数类型
        period: 时间周期

    Returns:
        dict: 包含历史数据的字典
    """
    if index_type not in SUPPORTED_INDICES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的指数类型: {index_type}，支持类型: {', '.join(SUPPORTED_INDICES)}"
        )

    validated_period = _validate_period(period)

    history_source = _get_index_history_source()
    result = await history_source.fetch_history(index_type, validated_period)

    if not result.success or result.data is None:
        error_msg = result.error or "获取历史数据失败"
        raise HTTPException(status_code=400, detail=error_msg)

    return result.data


# 指数日内分时数据源实例（通过依赖注入获取）
def _get_index_intraday_source() -> "HybridIndexSource":
    """获取指数日内分时数据源实例（通过依赖注入）"""
    from ..dependencies import get_index_intraday_source as get_source

    return get_source()


@router.get(
    "/{index_type}/intraday",
    response_model=dict,
    summary="获取指数日内分时数据",
    description="根据指数类型获取日内分时行情数据",
    responses={
        200: {"description": "成功获取指数日内分时数据"},
        400: {"model": ErrorResponse, "description": "不支持的指数类型"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_index_intraday(
    index_type: str,
) -> dict:
    """
    获取指数日内分时数据

    Args:
        index_type: 指数类型

    Returns:
        dict: 包含日内分时数据的字典
    """
    if index_type not in SUPPORTED_INDICES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的指数类型: {index_type}，支持类型: {', '.join(SUPPORTED_INDICES)}",
        )

    intraday_source = _get_index_intraday_source()
    result = await intraday_source.fetch_intraday(index_type)

    if not result.success or result.data is None:
        error_msg = result.error or "获取日内分时数据失败"
        raise HTTPException(status_code=400, detail=error_msg)

    return result.data
