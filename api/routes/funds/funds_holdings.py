"""
基金持仓 API 路由
提供基金持仓管理的 REST API 端点
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from typing_extensions import TypedDict

from src.config.manager import ConfigManager
from src.config.models import Holding
from src.datasources.base import DataSourceType
from src.datasources.manager import DataSourceManager

from ...dependencies import ConfigManagerDependency, DataSourceDependency
from ...models import ErrorResponse, OperationResponse

router = APIRouter(prefix="/api/funds", tags=["基金"])

logger = logging.getLogger(__name__)


class HoldingData(TypedDict):
    """持仓基金响应数据结构"""

    success: bool
    message: str


# ==================== 持仓管理路由 ====================


@router.put(
    "/{code}/holding",
    response_model=OperationResponse,
    summary="标记/取消持有基金",
    description="将基金标记为持有或取消持有",
    responses={
        200: {"description": "操作成功"},
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        404: {"model": ErrorResponse, "description": "基金不存在"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def toggle_holding(
    code: str,
    holding: bool = Query(..., description="True 表示标记为持有，False 表示取消持有"),
    manager: DataSourceManager = Depends(DataSourceDependency()),
    config_manager: ConfigManager = Depends(ConfigManagerDependency()),
) -> OperationResponse:
    """标记/取消持有基金"""
    fund_list = config_manager.load_funds()

    if holding:
        # 标记为持有
        if fund_list.is_holding(code):
            return OperationResponse(
                success=True,
                message=f"基金 {code} 已是持有状态",
            )

        # 验证基金是否存在
        result = await manager.fetch(DataSourceType.FUND, code)
        if not result.success:
            error_msg = result.error or "未知错误"
            raise HTTPException(
                status_code=404 if "不存在" in error_msg else 400,
                detail=error_msg,
            )

        fund_name = result.data.get("name", "") if result.data else ""

        # 如果在自选列表中，获取名称
        if not fund_name:
            for f in fund_list.watchlist:
                if f.code == code:
                    fund_name = f.name
                    break

        new_holding = Holding(code=code, name=fund_name)
        config_manager.add_holding(new_holding)

        # 标记为持有后，触发基金数据预热（非阻塞）
        asyncio.create_task(_prewarm_added_fund(code))

        return OperationResponse(
            success=True,
            message=f"基金 {code} 已标记为持有",
        )
    else:
        # 取消持有
        if not fund_list.is_holding(code):
            return OperationResponse(
                success=True,
                message=f"基金 {code} 不在持有列表中",
            )

        config_manager.remove_holding(code)

        # 取消持有后，清理相关缓存
        asyncio.create_task(_cleanup_removed_fund(code))

        return OperationResponse(
            success=True,
            message=f"基金 {code} 已取消持有",
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
