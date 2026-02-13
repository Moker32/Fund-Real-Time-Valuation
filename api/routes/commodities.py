"""
商品 API 路由
提供商品相关的 REST API 端点
"""

from datetime import datetime
import logging

logger = logging.getLogger(__name__)
from typing import Any, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Query

from src.config.commodities_config import CommoditiesConfig
from src.datasources.base import DataSourceType
from src.datasources.commodity_source import (
    AKShareCommoditySource,
    CommoditySearchResult,
    YFinanceCommoditySource,
    get_all_available_commodities,
    get_all_commodity_types,
    get_commodities_by_category,
    identify_category,
    search_commodities,
)
from src.datasources.manager import DataSourceManager
from src.db.commodity_repo import CommodityCacheDAO, CommodityCategory
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
            if result.success and result.data:
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
                        change_percent=data.get("change_percent"),
                        currency=data.get("currency"),
                        exchange=data.get("exchange"),
                        time=data.get("time"),
                        source=result.source,
                        high=data.get("high"),
                        low=data.get("low"),
                        open=data.get("open"),
                        prev_close=data.get("prev_close"),
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
                if result.success and result.data:
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
) -> CommodityHistoryResponse:
    """
    获取商品历史行情

    Args:
        commodity_type: 商品类型 (gold, wti, brent, silver, natural_gas, gold_cny)
        days: 获取天数，默认 30 天

    Returns:
        CommodityHistoryResponse: 历史行情数据
    """
    # 创建数据库管理器实例
    db = DatabaseManager()

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
        name = name_source.get_name(commodity_type)

        return {
            "commodity_type": commodity_type,
            "name": name,
            "history": history,
            "timestamp": datetime.now().isoformat() + "Z",
        }

    except Exception as e:
        logger.error(f"获取商品历史数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取历史数据失败，请稍后重试",
        )


# === 特定商品类型路由（在通用路由之前定义） ===

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

    if not result.success or not result.data:
        raise HTTPException(
            status_code=500,
            detail=result.error or "获取数据失败",
        )

    data = result.data
    return CommodityResponse(
        commodity=data.get("commodity", ""),
        symbol=data.get("symbol", ""),
        name=data.get("name", ""),
        price=data.get("price", 0.0),
        change=None,
        change_percent=data.get("change_percent"),
        currency="CNY",
        exchange="SGE",
        time=data.get("time"),
        source=result.source,
        high=data.get("high"),
        low=data.get("low"),
        open=data.get("open"),
        prev_close=data.get("prev_close"),
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

    if not result.success or not result.data:
        raise HTTPException(
            status_code=500,
            detail=result.error or "获取数据失败",
        )

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
        time=data.get("time"),
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
    """
    获取 WTI 原油行情

    Returns:
        CommodityResponse: WTI 原油行情
    """
    source = YFinanceCommoditySource()
    result = await source.fetch("wti")

    if not result.success or not result.data:
        raise HTTPException(
            status_code=500,
            detail=result.error or "获取数据失败",
        )

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
        time=data.get("time"),
        source=result.source,
        high=data.get("high"),
        low=data.get("low"),
        open=data.get("open"),
        prev_close=data.get("prev_close"),
    ).model_dump()


# === 关注列表 API ===
# 注意：这些路由必须在 /{commodity_type} 之前定义，以避免路由冲突

class WatchedCommodityResponse(TypedDict):
    """关注商品响应"""
    symbol: str
    name: str
    category: str
    added_at: str


class WatchedCommodityAddRequest(TypedDict):
    """添加关注商品请求"""
    symbol: str
    name: str
    category: str | None


class WatchedCommodityUpdateRequest(TypedDict):
    """更新关注商品请求"""
    name: str


class WatchlistResponse(TypedDict):
    """关注列表响应"""
    watchlist: list[WatchedCommodityResponse]
    count: int
    timestamp: str


class SearchResultItem(TypedDict):
    """搜索结果项"""
    symbol: str
    name: str
    exchange: str
    currency: str
    category: str


class SearchResultResponse(TypedDict):
    """搜索结果响应"""
    query: str
    results: list[SearchResultItem]
    count: int
    timestamp: str


class AddWatchlistResponse(TypedDict):
    """添加关注响应"""
    success: bool
    message: str


@router.get(
    "/search",
    response_model=SearchResultResponse,
    summary="搜索商品",
    description="搜索可关注的大宗商品",
    responses={
        200: {"description": "成功获取搜索结果"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def search_commodities_handler(
    q: str = Query(..., min_length=1, description="搜索关键词"),
) -> SearchResultResponse:
    """
    搜索可关注的大宗商品

    支持按代码或名称模糊搜索，返回匹配的商品列表。

    Args:
        q: 搜索关键词

    Returns:
        SearchResultResponse: 搜索结果
    """
    try:
        results = search_commodities(q)
    except Exception as e:
        logger.error(f"搜索商品失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="搜索失败，请稍后重试",
        )
    return {
        "query": q,
        "results": results,
        "count": len(results),
        "timestamp": datetime.now().isoformat() + "Z",
    }


@router.get(
    "/available",
    response_model=SearchResultResponse,
    summary="获取所有可用商品",
    description="获取所有可关注的大宗商品列表",
    responses={
        200: {"description": "成功获取商品列表"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_available_commodities() -> SearchResultResponse:
    """
    获取所有可关注的大宗商品列表

    Returns:
        SearchResultResponse: 所有可用商品
    """
    try:
        results = get_all_available_commodities()
    except Exception as e:
        logger.error(f"获取可用商品列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取商品列表失败，请稍后重试",
        )
    return {
        "query": "",
        "results": results,
        "count": len(results),
        "timestamp": datetime.now().isoformat() + "Z",
    }


@router.get(
    "/watchlist",
    response_model=WatchlistResponse,
    summary="获取关注列表",
    description="获取用户关注的大宗商品列表",
    responses={
        200: {"description": "成功获取关注列表"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_watchlist() -> WatchlistResponse:
    """
    获取关注的大宗商品列表

    Returns:
        WatchlistResponse: 关注列表
    """
    config = CommoditiesConfig()
    watched = config.get_watched_commodities()

    return {
        "watchlist": watched,
        "count": len(watched),
        "timestamp": datetime.now().isoformat() + "Z",
    }


@router.post(
    "/watchlist",
    response_model=AddWatchlistResponse,
    summary="添加关注商品",
    description="将商品添加到关注列表",
    responses={
        200: {"description": "成功添加"},
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def add_to_watchlist(
    request: WatchedCommodityAddRequest,
) -> AddWatchlistResponse:
    """
    添加商品到关注列表

    Args:
        request: 添加请求，包含 symbol, name, 可选的 category

    Returns:
        AddWatchlistResponse: 添加结果
    """
    symbol = request.get("symbol", "").strip()
    name = request.get("name", "").strip()
    category = request.get("category")

    if not symbol:
        return {"success": False, "message": "商品代码不能为空"}

    if not name:
        return {"success": False, "message": "商品名称不能为空"}

    # 如果没有提供分类，自动识别
    if category is None:
        category = identify_category(symbol)

    try:
        config = CommoditiesConfig()
        success, message = config.add_watched_commodity(symbol, name, category)
        return {"success": success, "message": message}
    except Exception as e:
        return {"success": False, "message": f"添加失败: {e}"}


@router.delete(
    "/watchlist/{symbol}",
    response_model=AddWatchlistResponse,
    summary="移除关注商品",
    description="将商品从关注列表移除",
    responses={
        200: {"description": "成功移除"},
        400: {"model": ErrorResponse, "description": "商品不在关注列表中"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def remove_from_watchlist(
    symbol: str,
) -> AddWatchlistResponse:
    """
    从关注列表移除商品

    Args:
        symbol: 商品代码

    Returns:
        AddWatchlistResponse: 移除结果
    """
    try:
        config = CommoditiesConfig()
        success, message = config.remove_watched_commodity(symbol)
        return {"success": success, "message": message}
    except Exception as e:
        return {"success": False, "message": f"移除失败: {e}"}


@router.put(
    "/watchlist/{symbol}",
    response_model=AddWatchlistResponse,
    summary="更新关注商品",
    description="更新关注商品的名称",
    responses={
        200: {"description": "成功更新"},
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def update_watchlist_commodity(
    symbol: str,
    request: WatchedCommodityUpdateRequest,
) -> AddWatchlistResponse:
    """
    更新关注商品的名称

    Args:
        symbol: 商品代码
        request: 更新请求，包含新的 name

    Returns:
        AddWatchlistResponse: 更新结果
    """
    name = request.get("name", "").strip()

    if not name:
        return {"success": False, "message": "商品名称不能为空"}

    try:
        config = CommoditiesConfig()
        success, message = config.update_watched_commodity_name(symbol, name)
        return {"success": success, "message": message}
    except Exception as e:
        return {"success": False, "message": f"更新失败: {e}"}


@router.get(
    "/watchlist/category/{category}",
    response_model=WatchlistResponse,
    summary="按分类获取关注",
    description="按分类获取关注的大宗商品列表",
    responses={
        200: {"description": "成功获取关注列表"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_watchlist_by_category(
    category: str,
) -> WatchlistResponse:
    """
    按分类获取关注的大宗商品列表

    Args:
        category: 分类名称

    Returns:
        WatchlistResponse: 关注列表
    """
    config = CommoditiesConfig()
    watched = config.get_watched_by_category(category)

    return {
        "watchlist": watched,
        "count": len(watched),
        "timestamp": datetime.now().isoformat() + "Z",
    }


# === 通用商品类型路由（必须在所有特定路由之后定义） ===

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

    if not result.success or not result.data:
        raise HTTPException(
            status_code=500,
            detail=result.error or "获取数据失败",
        )

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
        time=data.get("time"),
        source=result.source,
        high=data.get("high"),
        low=data.get("low"),
        open=data.get("open"),
        prev_close=data.get("prev_close"),
    ).model_dump()
