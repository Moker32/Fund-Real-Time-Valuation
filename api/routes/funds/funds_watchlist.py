"""
基金自选 API 路由
提供基金自选列表管理的 REST API 端点
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from src.config.manager import ConfigManager
from src.config.models import Fund
from src.datasources.base import DataSourceType
from src.datasources.manager import DataSourceManager

from ...dependencies import ConfigManagerDependency, DataSourceDependency
from ...models import (
    AddFundRequest,
    ErrorResponse,
    OperationResponse,
    WatchlistItem,
    WatchlistResponse,
)

router = APIRouter(prefix="/api/funds", tags=["基金"])

logger = logging.getLogger(__name__)


# ==================== 自选相关路由 ====================
# 注意：这些路由必须在 /{code} 之前定义，否则会被 /{code} 路由匹配


@router.get(
    "/watchlist",
    response_model=WatchlistResponse,
    summary="获取自选基金列表",
    description="获取当前用户的自选基金列表",
    responses={
        200: {"description": "获取成功"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_watchlist(
    config_manager: ConfigManager = Depends(ConfigManagerDependency()),
) -> WatchlistResponse:
    """获取自选基金列表"""
    fund_list = config_manager.load_funds()

    watchlist_data = [
        WatchlistItem(code=f.code, name=f.name, isHolding=fund_list.is_holding(f.code))
        for f in fund_list.watchlist
    ]

    return WatchlistResponse(
        success=True,
        watchlist=watchlist_data,
        total=len(watchlist_data),
    )


@router.post(
    "/watchlist",
    response_model=OperationResponse,
    summary="添加自选基金",
    description="将基金添加到自选列表",
    responses={
        200: {"description": "添加成功"},
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        404: {"model": ErrorResponse, "description": "基金不存在"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def add_to_watchlist(
    request: AddFundRequest,
    manager: DataSourceManager = Depends(DataSourceDependency()),
    config_manager: ConfigManager = Depends(ConfigManagerDependency()),
) -> OperationResponse:
    """添加基金到自选列表"""
    # 验证基金是否存在
    result = await manager.fetch(DataSourceType.FUND, request.code)
    if not result.success:
        error_msg = result.error or "未知错误"
        raise HTTPException(
            status_code=404 if "不存在" in error_msg else 400,
            detail=error_msg,
        )

    # 获取基金名称（如果请求中没有提供）
    fund_name = request.name
    if not fund_name and result.data:
        fund_name = result.data.get("name", "")

    # 添加到自选列表
    fund = Fund(code=request.code, name=fund_name)
    config_manager.add_watchlist(fund)

    # 添加成功后，触发新基金数据预热（非阻塞）
    asyncio.create_task(_prewarm_added_fund(request.code))

    return OperationResponse(
        success=True,
        message=f"基金 {request.code} 已添加到自选",
    )


@router.delete(
    "/watchlist/{code}",
    response_model=OperationResponse,
    summary="删除自选基金",
    description="从自选列表中移除基金",
    responses={
        200: {"description": "删除成功"},
        404: {"model": ErrorResponse, "description": "基金不在自选列表中"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def remove_from_watchlist(
    code: str, config_manager: ConfigManager = Depends(ConfigManagerDependency())
) -> OperationResponse:
    """从自选列表中移除基金"""
    fund_list = config_manager.load_funds()
    if not fund_list.is_watching(code):
        raise HTTPException(
            status_code=404,
            detail=f"基金 {code} 不在自选列表中",
        )

    # 从自选列表中移除
    config_manager.remove_watchlist(code)

    # 如果该基金也在持有列表中，同时从持有列表中移除
    if fund_list.is_holding(code):
        config_manager.remove_holding(code)

    # 移除成功后，清理相关缓存
    asyncio.create_task(_cleanup_removed_fund(code))

    return OperationResponse(
        success=True,
        message=f"基金 {code} 已从自选移除",
    )


async def _prewarm_added_fund(fund_code: str):
    """预热新添加的基金数据"""
    try:
        from src.datasources.cache_warmer import prewarm_new_fund

        await prewarm_new_fund(fund_code, timeout=30.0)
    except Exception as e:
        logger.warning(f"预热基金数据失败: {fund_code} - {e}")


async def _cleanup_removed_fund(fund_code: str):
    """清理移除的基金缓存"""
    try:
        from src.datasources.cache_warmer import cleanup_fund_cache

        await cleanup_fund_cache(fund_code)
    except Exception as e:
        logger.warning(f"清理基金缓存失败: {fund_code} - {e}")


__all__ = ["router"]
