"""
全球市场指数 API 路由
提供全球主要市场指数相关的 REST API 端点
"""

from datetime import datetime
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


def get_trading_status(index_type: str) -> dict:
    """
    获取指数的交易状态

    Args:
        index_type: 指数类型

    Returns:
        dict: 包含交易状态和市场时间信息的字典
    """
    market_info = MARKET_HOURS.get(index_type, {})
    if not market_info:
        return {"status": "unknown", "market_time": None}

    tz_str = market_info.get("tz", "UTC")
    tz = pytz.timezone(tz_str)

    # 获取当前 UTC 时间
    utc_now = datetime.now(pytz.UTC)
    # 转换为目标时区
    local_now = utc_now.astimezone(tz)

    # 解析开盘和收盘时间
    open_time = datetime.strptime(market_info["open"], "%H:%M").time()
    close_time = datetime.strptime(market_info["close"], "%H:%M").time()

    # 判断交易状态
    current_time = local_now.time()

    # 开盘前
    if current_time < open_time:
        status = "pre"  # 盘前
    # 交易时间
    elif open_time <= current_time <= close_time:
        status = "open"  # 交易中
    # 收盘后
    else:
        status = "closed"  # 已收盘

    return {
        "status": status,
        "market_time": local_now.strftime("%Y-%m-%d %H:%M:%S"),
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
        trading_status = get_trading_status(index_type)

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
    trading_status = get_trading_status(index_type)

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
