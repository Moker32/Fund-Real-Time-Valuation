"""
基金 API 路由
提供基金相关的 REST API 端点
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.datasources.base import DataSourceType
from src.datasources.manager import DataSourceManager

from ..dependencies import DataSourceDependency
from ..models import (
    ErrorResponse,
    FundDetailResponse,
    FundEstimateResponse,
    FundResponse,
)


router = APIRouter(prefix="/api/funds", tags=["基金"])


@router.get(
    "",
    response_model=list[FundResponse],
    summary="获取基金列表",
    description="获取所有已注册基金数据源的基金信息",
    responses={
        200: {"description": "成功获取基金列表"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_funds_list(
    codes: Optional[str] = None,
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> list[dict]:
    """
    获取基金列表

    Args:
        codes: 可选的基金代码列表，逗号分隔
        manager: 数据源管理器依赖

    Returns:
        list[FundResponse]: 基金列表
    """
    # 如果指定了基金代码
    if codes:
        fund_codes = [c.strip() for c in codes.split(",") if c.strip()]
        if not fund_codes:
            return []

        results = await manager.fetch_batch(DataSourceType.FUND, fund_codes)
        funds = []
        for result in results:
            if result.success:
                data = result.data

                # 计算 estimateChange (估算涨跌额)
                unit_net = data.get("unit_net_value")
                estimate_net = data.get("estimated_net_value")
                estimate_change = None
                if unit_net is not None and estimate_net is not None and unit_net != 0:
                    estimate_change = round(estimate_net - unit_net, 4)

                funds.append(FundResponse(
                    code=data.get("fund_code", ""),
                    name=data.get("name", ""),
                    netValue=data.get("unit_net_value"),
                    netValueDate=data.get("net_value_date"),
                    estimateValue=data.get("estimated_net_value"),
                    estimateChangePercent=data.get("estimated_growth_rate"),
                    estimateTime=data.get("estimate_time"),
                    estimateChange=estimate_change,
                    source=result.source,
                ).model_dump())
            else:
                # 如果单个基金获取失败，记录错误但不中断
                pass
        return funds

    # 获取所有注册的基金数据源信息
    sources = manager.get_sources_by_type(DataSourceType.FUND)
    return [
        {
            "code": "",
            "name": f"基金数据源: {source.name}",
            "netValue": None,
            "netValueDate": None,
            "estimateValue": None,
            "estimateChangePercent": None,
            "estimateTime": None,
            "estimateChange": None,
            "source": source.name,
        }
        for source in sources
    ]


@router.get(
    "/{code}",
    response_model=FundDetailResponse,
    summary="获取基金详情",
    description="根据基金代码获取单个基金的详细信息",
    responses={
        200: {"description": "成功获取基金详情"},
        404: {"model": ErrorResponse, "description": "基金不存在"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_fund_detail(
    code: str,
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> dict:
    """
    获取基金详情

    Args:
        code: 基金代码 (6位数字)
        manager: 数据源管理器依赖

    Returns:
        FundDetailResponse: 基金详情
    """
    result = await manager.fetch(DataSourceType.FUND, code)

    if not result.success:
        raise HTTPException(
            status_code=404 if "不存在" in result.error else 500,
            detail=result.error,
        )

    data = result.data

    # 计算 estimateChange (估算涨跌额)
    unit_net = data.get("unit_net_value")
    estimate_net = data.get("estimated_net_value")
    estimate_change = None
    if unit_net is not None and estimate_net is not None and unit_net != 0:
        estimate_change = round(estimate_net - unit_net, 4)

    return FundDetailResponse(
        code=data.get("fund_code", ""),
        name=data.get("name", ""),
        netValue=data.get("unit_net_value"),
        netValueDate=data.get("net_value_date"),
        estimateValue=data.get("estimated_net_value"),
        estimateChangePercent=data.get("estimated_growth_rate"),
        estimateTime=data.get("estimate_time"),
        estimateChange=estimate_change,
        source=result.source,
    ).model_dump()


@router.get(
    "/{code}/estimate",
    response_model=FundEstimateResponse,
    summary="获取基金估值",
    description="根据基金代码获取基金的实时估值信息",
    responses={
        200: {"description": "成功获取基金估值"},
        404: {"model": ErrorResponse, "description": "基金不存在"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_fund_estimate(
    code: str,
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> dict:
    """
    获取基金估值

    Args:
        code: 基金代码 (6位数字)
        manager: 数据源管理器依赖

    Returns:
        FundEstimateResponse: 基金估值信息
    """
    result = await manager.fetch(DataSourceType.FUND, code)

    if not result.success:
        raise HTTPException(
            status_code=404 if "不存在" in result.error else 500,
            detail=result.error,
        )

    data = result.data

    # 计算 estimateChange (估算涨跌额)
    unit_net = data.get("unit_net_value")
    estimate_net = data.get("estimated_net_value")
    estimate_change = None
    if unit_net is not None and estimate_net is not None and unit_net != 0:
        estimate_change = round(estimate_net - unit_net, 4)

    return FundEstimateResponse(
        code=data.get("fund_code", ""),
        name=data.get("name", ""),
        estimateValue=data.get("estimated_net_value"),
        estimateChangePercent=data.get("estimated_growth_rate"),
        estimateTime=data.get("estimate_time"),
        netValue=data.get("unit_net_value"),
        netValueDate=data.get("net_value_date"),
        estimateChange=estimate_change,
    ).model_dump()


@router.get(
    "/{code}/history",
    response_model=dict,
    summary="获取基金历史净值",
    description="根据基金代码获取基金的历史净值数据",
    responses={
        200: {"description": "成功获取基金历史净值"},
        404: {"model": ErrorResponse, "description": "基金不存在"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_fund_history(
    code: str,
    period: str = "近一年",
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> dict:
    """
    获取基金历史净值

    Args:
        code: 基金代码 (6位数字)
        period: 时间周期，可选值: "近一周", "近一月", "近三月", "近六月", "近一年", "近三年", "近五年", "成立以来"
        manager: 数据源管理器依赖

    Returns:
        dict: 包含历史净值数据的字典
    """
    from src.datasources.fund_source import FundHistorySource

    history_source = FundHistorySource()
    result = await history_source.fetch(code, period)

    if not result.success:
        raise HTTPException(
            status_code=404 if "不存在" in result.error else 500,
            detail=result.error,
        )

    return result.data
