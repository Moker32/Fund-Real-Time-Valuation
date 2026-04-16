"""
商品自选 API 路由
提供商品自选列表管理的 REST API 端点
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from typing_extensions import TypedDict

from src.config.commodities_config import CommoditiesConfig, WatchedCommodityDict
from src.datasources.commodity_source import (
    get_all_available_commodities,
    identify_category,
    search_commodities,
)

from ...models import ErrorResponse

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/commodities", tags=["商品"])


class WatchedCommodityResponse(TypedDict):
    """关注商品响应"""

    symbol: str
    name: str
    category: str
    addedAt: str


def _convert_to_watched_commodity_response(
    item: dict[str, Any] | WatchedCommodityDict,
) -> WatchedCommodityResponse:
    """将 snake_case 字段名转换为 camelCase 响应格式"""
    return {
        "symbol": item["symbol"],
        "name": item["name"],
        "category": item["category"],
        "addedAt": item["added_at"],
    }


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
    """搜索可关注的大宗商品"""
    try:
        results = search_commodities(q)
    except Exception as e:
        logger.error(f"搜索商品失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="搜索失败，请稍后重试")

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
    """获取所有可关注的大宗商品列表"""
    try:
        results = get_all_available_commodities()
    except Exception as e:
        logger.error(f"获取可用商品列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取商品列表失败，请稍后重试")

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
    """获取关注的大宗商品列表"""
    config = CommoditiesConfig()
    watched = config.get_watched_commodities()

    watchlist = [_convert_to_watched_commodity_response(item) for item in watched]

    return {
        "watchlist": watchlist,
        "count": len(watchlist),
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
    """添加商品到关注列表"""
    symbol = request.get("symbol", "").strip()
    name = request.get("name", "").strip()
    category = request.get("category")

    if not symbol:
        return {"success": False, "message": "商品代码不能为空"}

    if not name:
        return {"success": False, "message": "商品名称不能为空"}

    if category is None:
        category = identify_category(symbol)

    try:
        config = CommoditiesConfig()
        success, message = config.add_watched_commodity(symbol, name, category)
        return {"success": success, "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加失败: {e}")


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
    """从关注列表移除商品"""
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
    """更新关注商品的名称"""
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
    """按分类获取关注的大宗商品列表"""
    config = CommoditiesConfig()
    watched = config.get_watched_by_category(category)

    watchlist = [_convert_to_watched_commodity_response(item) for item in watched]

    return {
        "watchlist": watchlist,
        "count": len(watchlist),
        "timestamp": datetime.now().isoformat() + "Z",
    }


__all__ = ["router"]
