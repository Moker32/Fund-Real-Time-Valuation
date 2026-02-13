"""
全球市场指数 API 路由
提供全球主要市场指数相关的 REST API 端点
"""

from datetime import datetime, time
from typing import Any, TypedDict

import pytz
from fastapi import APIRouter, Depends

from src.datasources.base import DataSourceType
from src.datasources.index_source import INDEX_NAMES, INDEX_REGIONS, MARKET_HOURS
from src.datasources.manager import DataSourceManager

from ..dependencies import DataSourceDependency
from ..models import ErrorResponse


class IndexListData(TypedDict):
    """指数列表响应数据结构"""
    indices: list[dict]
    timestamp: str


router = APIRouter(prefix="/api/indices", tags=["全球指数"])


# 支持的指数列表
SUPPORTED_INDICES = list(INDEX_NAMES.keys())

# 腾讯财经的延时指数
# 美股数据延时15分钟，港股数据也有延时（几分钟）
TENCENT_DELAYED_INDICES = {"dow_jones", "nasdaq", "sp500", "hang_seng", "hang_seng_tech"}


def get_trading_status(index_type: str, data_timestamp: str | None = None) -> dict:
    """
    获取指数的交易状态

    使用启发式逻辑判断：
    1. 如果数据源返回了时间戳，检查数据是否及时更新
    2. 如果没有时间戳，使用当前时间作为数据获取时间
    3. 根据市场交易时间段判断状态

    Args:
        index_type: 指数类型
        data_timestamp: 数据源返回的数据时间戳 (ISO格式)

    Returns:
        dict: 包含交易状态和市场时间信息的字典
    """
    market_info = MARKET_HOURS.get(index_type, {})
    if not market_info:
        return {"status": "unknown", "market_time": None}

    tz_str = market_info.get("tz", "UTC")
    tz = pytz.timezone(tz_str)

    # 获取当前时间
    utc_now = datetime.now(pytz.UTC)
    local_now = utc_now.astimezone(tz)
    current_time = local_now.time()

    # 检查数据是否及时更新（启发式判断）
    # 如果没有数据时间戳，使用当前时间作为参考
    is_data_stale = False

    if data_timestamp:
        try:
            # 解析数据时间戳
            data_dt = datetime.fromisoformat(data_timestamp.replace('Z', '+00:00'))
            # 计算数据时间与当前时间的差距（分钟）
            data_age_minutes = (local_now.replace(tzinfo=None) - data_dt.replace(tzinfo=None)).total_seconds() / 60

            # 如果数据超过 15 分钟未更新，认为数据不新鲜
            if data_age_minutes > 15:
                is_data_stale = True
        except (ValueError, TypeError):
            pass

    # 特殊处理 A 股市场（有午间休市）
    if index_type in ["shanghai", "shenzhen", "shanghai50", "chi_next", "star50",
                       "csi500", "csi1000", "hs300", "csiall"]:
        # A 股交易时间：上午 9:30-11:30，下午 13:00-15:00
        morning_open = time(9, 30)
        morning_close = time(11, 30)
        afternoon_open = time(13, 0)
        afternoon_close = time(15, 0)

        # 周一到周五的交易时间
        if local_now.weekday() < 5:  # 0=Monday, 4=Friday
            if morning_open <= current_time <= morning_close:
                status = "open"
            elif afternoon_open <= current_time <= afternoon_close:
                status = "open"
            elif current_time < morning_open:
                status = "pre"
            else:
                status = "closed"
        else:
            status = "closed"  # 周末
    else:
        # 其他市场：使用原来的时间段逻辑
        open_utc = datetime.strptime(market_info["open"], "%H:%M")
        close_utc = datetime.strptime(market_info["close"], "%H:%M")

        today = local_now.date()
        open_utc_dt = datetime.combine(today, open_utc.time(), tzinfo=pytz.UTC)
        close_utc_dt = datetime.combine(today, close_utc.time(), tzinfo=pytz.UTC)
        open_time = open_utc_dt.astimezone(tz).time()
        close_time = close_utc_dt.astimezone(tz).time()

        if current_time < open_time:
            status = "pre"
        elif open_time <= current_time <= close_time:
            # 如果在交易时段内，但数据不新鲜，可能是午间休市或其他原因
            if is_data_stale:
                status = "stalled"  # 数据停滞
            else:
                status = "open"
        else:
            status = "closed"

    # 如果数据不新鲜且不是 closed 状态，添加提示
    reason = None
    if is_data_stale and status not in ["closed", "pre"]:
        reason = "数据超过15分钟未更新"

    return {
        "status": status,
        "market_time": local_now.strftime("%Y-%m-%d %H:%M:%S"),
        "data_timestamp": data_timestamp,
        "is_stale": is_data_stale,
        "reason": reason,
    }


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
    results = await manager.fetch_batch(DataSourceType.STOCK, [{"kwargs": {"index_type": it}} for it in index_types])

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
        trading_status = get_trading_status(index_type, data_timestamp)

        # 判断是否为延时数据（腾讯的美股数据延时15分钟）
        is_delayed = result.source == "tencent_index" and index_type in TENCENT_DELAYED_INDICES

        all_indices.append({
            "index": index_type,
            "symbol": data.get("symbol", ""),
            "name": data.get("name", ""),
            "price": data.get("price", 0.0),
            "change": data.get("change"),
            "changePercent": data.get("change_percent"),
            "currency": data.get("currency", ""),
            "exchange": data.get("exchange"),
            "timestamp": data.get("time"),
            "source": result.source,
            "high": data.get("high"),
            "low": data.get("low"),
            "open": data.get("open"),
            "prevClose": data.get("prev_close"),
            "region": INDEX_REGIONS.get(index_type),
            "tradingStatus": trading_status.get("status"),
            "marketTime": trading_status.get("market_time"),
            "isDelayed": is_delayed,
        })

    return {"indices": all_indices, "timestamp": current_time}


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
        raise ValueError(
            f"不支持的指数类型: {index_type}，支持类型: {', '.join(SUPPORTED_INDICES)}"
        )

    result = await manager.fetch(DataSourceType.STOCK, index_type)

    if not result.success or not result.data:
        error_msg = result.error or "获取数据失败"
        raise ValueError(error_msg)

    data = result.data
    index_type = data.get("index", "")
    data_timestamp = data.get("data_timestamp")
    trading_status = get_trading_status(index_type, data_timestamp)

    # 判断是否为延时数据（腾讯的美股数据延时15分钟）
    is_delayed = result.source == "tencent_index" and index_type in TENCENT_DELAYED_INDICES

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
        "source": result.source,
        "high": data.get("high"),
        "low": data.get("low"),
        "open": data.get("open"),
        "prevClose": data.get("prev_close"),
        "region": INDEX_REGIONS.get(index_type),
        "tradingStatus": trading_status.get("status"),
        "marketTime": trading_status.get("market_time"),
        "isDelayed": is_delayed,
    }


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
            regions[region] = {
                "name": region,
                "indices": []
            }
        regions[region]["indices"].append({
            "index": index_type,
            "name": INDEX_NAMES.get(index_type, index_type),
        })

    return {
        "regions": list(regions.values()),
        "supported_indices": SUPPORTED_INDICES,
    }
