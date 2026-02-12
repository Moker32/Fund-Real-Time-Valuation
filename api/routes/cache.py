"""
缓存统计 API 路由
提供缓存命中率监控和统计信息
"""

import logging

from fastapi import APIRouter

from src.datasources.fund_source import get_fund_cache_stats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cache", tags=["缓存"])


@router.get("/stats", summary="缓存统计", description="获取缓存统计信息，包括命中率监控")
async def get_cache_stats() -> dict:
    """
    获取缓存统计信息

    返回:
        - fund_cache: 基金数据缓存统计（双层缓存）
        - fund_info_cache: 基金信息缓存统计
    """
    stats = get_fund_cache_stats()
    logger.debug(f"缓存统计请求: {stats}")
    return stats
