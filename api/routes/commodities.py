"""
商品 API 路由
提供商品相关的 REST API 端点
"""

from datetime import datetime
from typing import TypedDict

from fastapi import APIRouter, Depends, HTTPException

from src.datasources.base import DataSourceType
from src.datasources.commodity_source import (
    AKShareCommoditySource,
    YFinanceCommoditySource,
    get_commodities_by_category,
    get_all_commodity_types,
)
from src.datasources.manager import DataSourceManager
from src.db.commodity_repo import CommodityCacheDAO, CommodityCategory, CommodityCategoryDAO
from src.db.database import DatabaseManager

from ..dependencies import DataSourceDependency
from ..models import CommodityResponse, ErrorResponse


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
    changePercent: float
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
    commodity_type: str
    name: str
    history: list[dict]
    timestamp: str


router = APIRouter(prefix="/api/commodities", tags=["商品"])

# 分类图标映射
CATEGORY_ICONS = {
    CommodityCategory.PRECIOUS_METAL.value: "diamond",
    CommodityCategory.ENERGY.value: "flame",
    CommodityCategory.BASE_METAL.value: "cube",
}

# 支持的商品类型列表
SUPPORTED_COMMODITIES = get_all_commodity_types()


def _commodity_to_item(data: dict, source: str) -> CommodityCategoryItem:
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
        "timestamp": data.get("time", data.get("timestamp", "")),
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
    """
    获取商品行情列表

    Args:
        types: 可选的商品类型列表，逗号分隔
        manager: 数据源管理器依赖

    Returns:
        CommodityListData: 包含商品列表和时间戳的字典
    """
    current_time = datetime.now().isoformat() + "Z"

    # 确定要获取的商品类型
    if types:
        commodity_types = [t.strip() for t in types.split(",") if t.strip()]
        if not commodity_types:
            return {"commodities": [], "timestamp": current_time}
    else:
        commodity_types = SUPPORTED_COMMODITIES

    # 获取所有商品数据源
    sources = manager.get_sources_by_type(DataSourceType.COMMODITY)

    # 聚合结果
    all_results = []
    seen_commodities = set()

    for source in sources:
        # 批量获取数据
        results = await source.fetch_batch(commodity_types)

        for result in results:
            if result.success:
                data = result.data
                commodity_key = data.get("commodity", "")

                # 避免重复
                if commodity_key not in seen_commodities:
                    seen_commodities.add(commodity_key)
                    all_results.append(CommodityResponse(
                        commodity=data.get("commodity", ""),
                        symbol=data.get("symbol", ""),
                        name=data.get("name", ""),
                        price=data.get("price", 0.0),
                        change=data.get("change"),
                        changePercent=data.get("change_percent"),
                        currency=data.get("currency"),
                        exchange=data.get("exchange"),
                        timestamp=data.get("time"),
                        source=result.source,
                        high=data.get("high"),
                        low=data.get("low"),
                        open=data.get("open"),
                        prevClose=data.get("prev_close"),
                    ).model_dump())

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
    """
    获取商品分类列表

    返回按分类组织的商品数据，包含每个分类的名称和商品列表。

    Returns:
        CommodityCategoriesResponse: 分类列表响应
    """
    current_time = datetime.now().isoformat() + "Z"

    # 获取数据源
    sources = manager.get_sources_by_type(DataSourceType.COMMODITY)

    # 获取按分类组织的商品类型
    category_map = get_commodities_by_category()

    # 构建分类数据
    categories: list[CommodityCategoryData] = []

    for category, commodity_types in category_map.items():
        if not commodity_types:
            # 空分类只包含基本信息
            categories.append({
                "id": category.value,
                "name": category.value.replace("_", " ").title(),
                "icon": CATEGORY_ICONS.get(category.value, "box"),
                "commodities": [],
            })
            continue

        # 获取该分类下所有商品的数据
        category_commodities: list[CommodityCategoryItem] = []

        for source in sources:
            results = await source.fetch_batch(commodity_types)

            for result in results:
                if result.success:
                    data = result.data
                    commodity_type = data.get("commodity", "")
                    if commodity_type:
                        item = _commodity_to_item(data, result.source)
                        category_commodities.append(item)

        categories.append({
            "id": category.value,
            "name": category.value.replace("_", " ").title(),
            "icon": CATEGORY_ICONS.get(category.value, "box"),
            "commodities": category_commodities,
        })

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
    db: DatabaseManager = Depends(DataSourceDependency()),
) -> CommodityHistoryResponse:
    """
    获取商品历史行情

    Args:
        commodity_type: 商品类型 (gold, wti, brent, silver, natural_gas, gold_cny)
        days: 获取天数，默认 30 天
        db: 数据库依赖

    Returns:
        CommodityHistoryResponse: 历史行情数据
    """
    # 验证商品类型
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
                "date": r.timestamp[:10] if r.timestamp else "",  # YYYY-MM-DD
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

        # 获取商品名称
        from src.datasources.commodity_source import YFinanceCommoditySource
        name_source = YFinanceCommoditySource()
        name = name_source._get_name(commodity_type)

        return {
            "commodity_type": commodity_type,
            "name": name,
            "history": history,
            "timestamp": datetime.now().isoformat() + "Z",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取历史数据失败: {str(e)}",
        )


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
    """
    获取单个商品行情

    Args:
        commodity_type: 商品类型 (gold, gold_cny, wti, brent, silver, natural_gas)
        manager: 数据源管理器依赖

    Returns:
        CommodityResponse: 商品行情
    """
    # 验证商品类型
    if commodity_type not in SUPPORTED_COMMODITIES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的商品类型: {commodity_type}，支持类型: {', '.join(SUPPORTED_COMMODITIES)}",
        )

    result = await manager.fetch(DataSourceType.COMMODITY, commodity_type)

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.error,
        )

    data = result.data
    return CommodityResponse(
        commodity=data.get("commodity", ""),
        symbol=data.get("symbol", ""),
        name=data.get("name", ""),
        price=data.get("price", 0.0),
        change=data.get("change"),
        changePercent=data.get("change_percent"),
        currency=data.get("currency"),
        exchange=data.get("exchange"),
        timestamp=data.get("time"),
        source=result.source,
        high=data.get("high"),
        low=data.get("low"),
        open=data.get("open"),
        prevClose=data.get("prev_close"),
    ).model_dump()


@router.get(
    "/gold/cny",
    response_model=CommodityResponse,
    summary="获取国内黄金行情",
    description="获取上海黄金交易所 Au99.99 实时行情",
    responses={
        200: {"description": "成功获取国内黄金行情"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_gold_cny() -> dict:
    """
    获取国内黄金行情（上海黄金交易所 Au99.99）

    Returns:
        CommodityResponse: 国内黄金行情
    """
    source = AKShareCommoditySource()
    result = await source.fetch("gold_cny")

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.error,
        )

    data = result.data
    return CommodityResponse(
        commodity=data.get("commodity", ""),
        symbol=data.get("symbol", ""),
        name=data.get("name", ""),
        price=data.get("price", 0.0),
        change=None,
        changePercent=data.get("change_percent"),
        currency="CNY",
        exchange="SGE",
        timestamp=data.get("time"),
        source=result.source,
        high=data.get("high"),
        low=data.get("low"),
        open=data.get("open"),
        prevClose=data.get("prev_close"),
    ).model_dump()


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
    """
    获取国际黄金行情（COMEX 黄金）

    Returns:
        CommodityResponse: 国际黄金行情
    """
    source = YFinanceCommoditySource()
    result = await source.fetch("gold")

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.error,
        )

    data = result.data
    return CommodityResponse(
        commodity=data.get("commodity", ""),
        symbol=data.get("symbol", ""),
        name=data.get("name", ""),
        price=data.get("price", 0.0),
        change=data.get("change"),
        changePercent=data.get("change_percent"),
        currency=data.get("currency", "USD"),
        exchange=data.get("exchange", "COMEX"),
        timestamp=data.get("time"),
        source=result.source,
        high=data.get("high"),
        low=data.get("low"),
        open=data.get("open"),
        prevClose=data.get("prev_close"),
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
    """
    获取 WTI 原油行情

    Returns:
        CommodityResponse: WTI 原油行情
    """
    source = YFinanceCommoditySource()
    result = await source.fetch("wti")

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.error,
        )

    data = result.data
    return CommodityResponse(
        commodity=data.get("commodity", ""),
        symbol=data.get("symbol", ""),
        name=data.get("name", ""),
        price=data.get("price", 0.0),
        change=data.get("change"),
        changePercent=data.get("change_percent"),
        currency=data.get("currency", "USD"),
        exchange=data.get("exchange", "NYMEX"),
        timestamp=data.get("time"),
        source=result.source,
        high=data.get("high"),
        low=data.get("low"),
        open=data.get("open"),
        prevClose=data.get("prev_close"),
    ).model_dump()
