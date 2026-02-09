"""
概览 API 路由
提供市场概览数据的 REST API 端点
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.config.manager import ConfigManager
from src.config.models import FundList
from src.datasources.base import DataSourceType
from src.datasources.manager import DataSourceManager

from ..dependencies import DataSourceDependency
from ..models import ErrorResponse, OverviewResponse


router = APIRouter(prefix="/api", tags=["概览"])


def load_default_fund_codes() -> list[str]:
    """
    加载默认的基金代码列表

    Returns:
        list[str]: 基金代码列表
    """
    # 默认基金列表（当配置文件不存在时使用）
    default_funds = [
        "161039",  # 易方达消费行业股票
        "161725",  # 招商中证白酒指数
        "110022",  # 易方达消费行业
        "000015",  # 华夏策略精选混合
        "161032",  # 富国中证新能源汽车指数
    ]

    try:
        config_manager = ConfigManager()
        fund_list: FundList = config_manager.load_funds()

        # 获取所有基金代码
        codes = fund_list.get_all_codes()

        # 如果没有基金代码，使用默认值
        if not codes:
            return default_funds

        return codes

    except Exception:
        # 如果加载失败，使用默认值
        return default_funds


@router.get(
    "/overview",
    response_model=OverviewResponse,
    summary="获取市场概览",
    description="获取所有关注基金的汇总数据，包括总价值、涨跌情况和基金数量",
    responses={
        200: {"description": "成功获取市场概览"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_overview(
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> dict:
    """
    获取市场概览数据

    Args:
        manager: 数据源管理器依赖

    Returns:
        OverviewResponse: 市场概览数据
    """
    # 加载基金代码列表
    fund_codes = load_default_fund_codes()

    if not fund_codes:
        # 没有基金时返回默认值
        return OverviewResponse(
            totalValue=0.0,
            totalChange=0.0,
            totalChangePercent=0.0,
            fundCount=0,
            lastUpdated=datetime.now().isoformat() + "Z",
        ).model_dump()

    # 批量获取基金数据
    results = await manager.fetch_batch(DataSourceType.FUND, fund_codes)

    # 计算统计数据
    total_value = 0.0
    total_change = 0.0
    successful_count = 0
    latest_update = None

    for result in results:
        if result.success:
            data = result.data

            # 获取估值和净值
            estimate_value = data.get("estimated_net_value")
            unit_net_value = data.get("unit_net_value")
            estimate_rate = data.get("estimated_growth_rate")

            # 计算持仓价值（假设持有1份，用于展示）
            if estimate_value is not None:
                total_value += estimate_value

            # 计算涨跌额
            if estimate_value is not None and unit_net_value is not None and unit_net_value != 0:
                change = estimate_value - unit_net_value
                total_change += change

            successful_count += 1

            # 获取最新更新时间
            update_time = data.get("estimate_time", "")
            if update_time:
                if latest_update is None or update_time > latest_update:
                    latest_update = update_time

    # 计算涨跌百分比（基于成功的基金）
    change_percent = 0.0
    if total_value > 0:
        change_percent = (total_change / total_value) * 100 if total_value != 0 else 0.0

    # 确定更新时间
    if latest_update:
        # 确保时间格式正确
        try:
            # 尝试解析并格式化时间
            dt = datetime.strptime(latest_update, "%Y-%m-%d %H:%M:%S")
            last_updated = dt.isoformat() + "Z"
        except ValueError:
            last_updated = latest_update
    else:
        last_updated = datetime.now().isoformat() + "Z"

    return OverviewResponse(
        totalValue=round(total_value, 2),
        totalChange=round(total_change, 4),
        totalChangePercent=round(change_percent, 2),
        fundCount=successful_count,
        lastUpdated=last_updated,
    ).model_dump()


@router.get(
    "/overview/simple",
    response_model=OverviewResponse,
    summary="获取简版市场概览",
    description="快速获取市场概览数据，仅返回基本统计信息",
    responses={
        200: {"description": "成功获取简版市场概览"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_simple_overview(
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> dict:
    """
    获取简版市场概览数据

    Args:
        manager: 数据源管理器依赖

    Returns:
        OverviewResponse: 市场概览数据
    """
    # 直接调用完整的概览接口
    return await get_overview(manager)
