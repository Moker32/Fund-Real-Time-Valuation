"""
商品数据 API 路由
提供商品数据相关的 REST API 端点
"""

import logging
from datetime import datetime
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from typing_extensions import TypedDict

from src.datasources.base import DataSourceType
from src.datasources.commodity_source import (
    CommodityRealtimeSource,
    get_all_commodity_types,
    get_commodities_by_category,
)
from src.datasources.manager import DataSourceManager
from src.db.commodity_repo import CommodityCacheDAO
from src.db.database import DatabaseManager

from ...dependencies import DataSourceDependency
from ...models import CommodityResponse, ErrorResponse

logger = logging.getLogger(__name__)


class CommodityListData(TypedDict):
    """商品列表响应数据结构"""

    commodities: list[dict]
    timestamp: str


class CommodityCategoryItem(TypedDict):
    """单个商品项"""

    symbol: str
    name: str
    price: float
    currency: str
    change: float | None
    changePercent: float | None
    high: float | None
    low: float | None
    open: float | None
    prevClose: float | None
    source: str
    timestamp: str


class CommodityCategoryData(TypedDict):
    """分类响应数据结构"""

    id: str
    name: str
    icon: str
    commodities: list[CommodityCategoryItem]


class CommodityCategoriesResponse(TypedDict):
    """分类列表响应数据结构"""

    categories: list[CommodityCategoryData]
    timestamp: str


class CommodityHistoryResponse(TypedDict):
    """历史数据响应"""

    commodityType: str
    name: str
    history: list[dict]
    timestamp: str


router = APIRouter(prefix="/api/commodities", tags=["商品"])

# 分类图标映射
CATEGORY_ICONS: dict[str, str] = {
    "precious_metal": "diamond",
    "energy": "flame",
    "base_metal": "cube",
}

# 支持的商品类型列表
SUPPORTED_COMMODITIES = get_all_commodity_types()


@lru_cache
def _get_realtime_source() -> CommodityRealtimeSource:
    """获取 CommodityRealtimeSource 实例（缓存）"""
    return CommodityRealtimeSource()


def _commodity_to_item(data: dict[str, Any], source: str) -> CommodityCategoryItem:
    """将商品数据转换为分类项格式"""
    return {
        "symbol": data.get("symbol", ""),
        "name": data.get("name", ""),
        "price": data.get("price", 0.0),
        "currency": data.get("currency", "USD"),
        "change": data.get("change"),
        "changePercent": data.get("change_percent", 0.0),
        "high": data.get("high"),
        "low": data.get("low"),
        "open": data.get("open"),
        "prevClose": data.get("prev_close"),
        "source": source,
        "timestamp": data.get("timestamp", data.get("time", "")),
    }


@router.get(
    "",
    response_model=CommodityListData,
    summary="获取商品行情",
    description="获取所有支持的商品实时行情",
    responses={
        200: {"description": "成功获取商品行情"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_commodities(
    types: str | None = None,
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> CommodityListData:
    """获取商品行情列表"""
    current_time = datetime.now().isoformat() + "Z"

    if types:
        commodity_types = [t.strip() for t in types.split(",") if t.strip()]
        if not commodity_types:
            return {"commodities": [], "timestamp": current_time}
    else:
        commodity_types = SUPPORTED_COMMODITIES

    sources = manager.get_sources_by_type(DataSourceType.COMMODITY)

    all_results = []
    seen_commodities = set()

    for source in sources:
        results = await source.fetch_batch(commodity_types)

        for result in results:
            if result.success and result.data:
                data = result.data
                commodity_key = data.get("commodity", "")

                if commodity_key not in seen_commodities:
                    seen_commodities.add(commodity_key)
                    all_results.append(
                        CommodityResponse(
                            commodity=data.get("commodity", ""),
                            symbol=data.get("symbol", ""),
                            name=data.get("name", ""),
                            price=data.get("price", 0.0),
                            change=data.get("change"),
                            change_percent=data.get("change_percent"),
                            currency=data.get("currency"),
                            exchange=data.get("exchange"),
                            timestamp=data.get("timestamp"),
                            source=result.source,
                            high=data.get("high"),
                            low=data.get("low"),
                            open=data.get("open"),
                            prev_close=data.get("prev_close"),
                        ).model_dump()
                    )

    return {"commodities": all_results, "timestamp": current_time}


@router.get(
    "/categories",
    response_model=CommodityCategoriesResponse,
    summary="获取商品分类",
    description="获取所有商品分类及其包含的商品实时行情",
    responses={
        200: {"description": "成功获取分类数据"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_categories(
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> CommodityCategoriesResponse:
    """获取商品分类列表"""
    current_time = datetime.now().isoformat() + "Z"

    sources = manager.get_sources_by_type(DataSourceType.COMMODITY)
    category_map = get_commodities_by_category()

    categories: list[CommodityCategoryData] = []

    for category, commodity_types in category_map.items():
        if not commodity_types:
            categories.append(
                {
                    "id": category.value,
                    "name": category.value.replace("_", " ").title(),
                    "icon": CATEGORY_ICONS.get(category.value, "box"),
                    "commodities": [],
                }
            )
            continue

        category_commodities: list[CommodityCategoryItem] = []

        for source in sources:
            results = await source.fetch_batch(commodity_types)

            for result in results:
                if result.success and result.data:
                    data = result.data
                    commodity_type = data.get("commodity", "")
                    if commodity_type:
                        item = _commodity_to_item(data, result.source)
                        category_commodities.append(item)

        categories.append(
            {
                "id": category.value,
                "name": category.value.replace("_", " ").title(),
                "icon": CATEGORY_ICONS.get(category.value, "box"),
                "commodities": category_commodities,
            }
        )

    return {"categories": categories, "timestamp": current_time}


@router.get(
    "/history/{commodity_type}",
    response_model=CommodityHistoryResponse,
    summary="获取商品历史行情",
    description="获取指定商品的历史行情数据",
    responses={
        200: {"description": "成功获取历史数据"},
        400: {"model": ErrorResponse, "description": "不支持的商品类型"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_history(
    commodity_type: str,
    days: int = 30,
) -> CommodityHistoryResponse:
    """获取商品历史行情"""
    db = DatabaseManager()

    all_types = get_all_commodity_types()
    if commodity_type not in all_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的商品类型: {commodity_type}，支持类型: {', '.join(all_types)}",
        )

    try:
        dao = CommodityCacheDAO(db)
        records = dao.get_history(commodity_type, limit=days)

        history = [
            {
                "date": r.timestamp[:10] if r.timestamp else "",
                "price": r.price,
                "change": r.change,
                "changePercent": r.change_percent,
                "high": r.high,
                "low": r.low,
                "open": r.open,
                "prevClose": r.prev_close,
            }
            for r in records
        ]

        from src.db.commodity_repo import COMMODITY_NAMES

        name = COMMODITY_NAMES.get(commodity_type, commodity_type)

        return {
            "commodityType": commodity_type,
            "name": name,
            "history": history,
            "timestamp": datetime.now().isoformat() + "Z",
        }

    except Exception as e:
        logger.error(f"获取商品历史数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取历史数据失败，请稍后重试")


@router.get(
    "/gold/international",
    response_model=CommodityResponse,
    summary="获取国际黄金行情",
    description="获取 COMEX 黄金期货实时行情",
    responses={
        200: {"description": "成功获取国际黄金行情"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_gold_international() -> dict:
    """获取国际黄金行情（COMEX 黄金）"""
    source = _get_realtime_source()
    result = await source.fetch("gold")

    if not result.success or not result.data:
        raise HTTPException(status_code=500, detail=result.error or "获取数据失败")

    data = result.data
    return CommodityResponse(
        commodity=data.get("commodity", ""),
        symbol=data.get("symbol", ""),
        name=data.get("name", ""),
        price=data.get("price", 0.0),
        change=data.get("change"),
        change_percent=data.get("change_percent"),
        currency=data.get("currency", "USD"),
        exchange=data.get("exchange", "COMEX"),
        timestamp=data.get("timestamp"),
        source=result.source,
        high=data.get("high"),
        low=data.get("low"),
        open=data.get("open"),
        prev_close=data.get("prev_close"),
    ).model_dump()


@router.get(
    "/oil/wti",
    response_model=CommodityResponse,
    summary="获取 WTI 原油行情",
    description="获取 WTI 原油期货实时行情",
    responses={
        200: {"description": "成功获取 WTI 原油行情"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_wti_oil() -> dict:
    """获取 WTI 原油行情"""
    source = _get_realtime_source()
    result = await source.fetch("wti")

    if not result.success or not result.data:
        raise HTTPException(status_code=500, detail=result.error or "获取数据失败")

    data = result.data
    return CommodityResponse(
        commodity=data.get("commodity", ""),
        symbol=data.get("symbol", ""),
        name=data.get("name", ""),
        price=data.get("price", 0.0),
        change=data.get("change"),
        change_percent=data.get("change_percent"),
        currency=data.get("currency", "USD"),
        exchange=data.get("exchange", "NYMEX"),
        timestamp=data.get("timestamp"),
        source=result.source,
        high=data.get("high"),
        low=data.get("low"),
        open=data.get("open"),
        prev_close=data.get("prev_close"),
    ).model_dump()


@router.get(
    "/{commodity_type}",
    response_model=CommodityResponse,
    summary="获取单个商品行情",
    description="根据商品类型获取单个商品的实时行情",
    responses={
        200: {"description": "成功获取商品行情"},
        400: {"model": ErrorResponse, "description": "不支持的商品类型"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_commodity(
    commodity_type: str,
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> dict:
    """获取单个商品行情"""
    if commodity_type not in SUPPORTED_COMMODITIES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的商品类型: {commodity_type}，支持类型: {', '.join(SUPPORTED_COMMODITIES)}",
        )

    result = await manager.fetch(DataSourceType.COMMODITY, commodity_type)

    if not result.success or not result.data:
        raise HTTPException(status_code=500, detail=result.error or "获取数据失败")

    data = result.data
    return CommodityResponse(
        commodity=data.get("commodity", ""),
        symbol=data.get("symbol", ""),
        name=data.get("name", ""),
        price=data.get("price", 0.0),
        change=data.get("change"),
        change_percent=data.get("change_percent"),
        currency=data.get("currency"),
        exchange=data.get("exchange"),
        timestamp=data.get("timestamp"),
        source=result.source,
        high=data.get("high"),
        low=data.get("low"),
        open=data.get("open"),
        prev_close=data.get("prev_close"),
    ).model_dump()


# 导出辅助函数供 watchlist 模块使用
__all__ = [
    "router",
    "_get_realtime_source",
    "_commodity_to_item",
    "SUPPORTED_COMMODITIES",
]
