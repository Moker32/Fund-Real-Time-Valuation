"""
数据源统计 API 路由
提供数据源请求统计和性能监控信息
"""

import logging

from fastapi import APIRouter, Depends

from src.datasources.manager import DataSourceManager

from ..dependencies import DataSourceDependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/datasource", tags=["数据源"])


@router.get(
    "/statistics",
    summary="数据源统计",
    description="获取数据源请求统计数据，包括成功率、响应时间等",
)
async def get_datasource_statistics(
    manager: DataSourceManager = Depends(DataSourceDependency),
) -> dict:
    """
    获取数据源统计信息

    返回:
        - total_requests: 总请求数
        - successful_requests: 成功请求数
        - failed_requests: 失败请求数
        - overall_success_rate: 整体成功率
        - source_statistics: 各数据源统计
        - registered_sources: 已注册数据源列表
    """
    stats = manager.get_statistics()
    logger.debug(f"数据源统计请求: {stats}")
    return stats


@router.get(
    "/health",
    summary="数据源健康状态",
    description="获取所有数据源的详细健康状态",
)
async def get_datasource_health(
    manager: DataSourceManager = Depends(DataSourceDependency),
) -> dict:
    """
    获取数据源健康状态

    返回:
        - total_sources: 数据源总数
        - healthy_count: 健康数量
        - degraded_count: 降级数量
        - unhealthy_count: 不健康数量
        - sources: 各数据源健康详情
    """
    health = await manager.health_check()
    return health


@router.get(
    "/sources",
    summary="数据源列表",
    description="获取所有已注册的数据源列表",
)
async def get_datasource_list(
    manager: DataSourceManager = Depends(DataSourceDependency),
) -> list[dict]:
    """
    获取数据源列表

    返回:
        - name: 数据源名称
        - type: 数据源类型
        - status: 数据源状态
    """
    sources = manager.list_sources()
    return sources
