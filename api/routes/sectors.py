"""
行业板块和概念板块 API 路由
提供 A 股行业板块和概念板块相关的 REST API 端点
"""

from datetime import datetime, timezone
from typing import TypedDict

from fastapi import APIRouter, Depends, HTTPException

from src.datasources.manager import DataSourceManager

from ..dependencies import DataSourceDependency
from ..models import ErrorResponse


class SectorListData(TypedDict):
    """板块列表响应数据结构"""
    sectors: list[dict]
    timestamp: str
    type: str


class SectorDetailData(TypedDict):
    """板块详情响应数据结构"""
    sector_name: str
    stocks: list[dict]
    count: int
    timestamp: str


router = APIRouter(prefix="/api/sectors", tags=["行业板块"])


@router.get(
    "/industry",
    response_model=SectorListData,
    summary="获取行业板块列表",
    description="获取 A 股所有行业板块的实时行情（涨跌幅、领涨股票等）",
    responses={
        200: {"description": "成功获取行业板块列表"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_industry_sectors(
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> SectorListData:
    """
    获取 A 股行业板块列表

    Args:
        manager: 数据源管理器依赖

    Returns:
        SectorListData: 包含行业板块列表和时间戳的字典
    """
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    sector_type = "industry"

    # 使用 SinaSectorSource 获取行业板块数据
    result = await manager.fetch_with_source("sina_sector")

    if not result.success or not result.data:
        # Fallback to EastMoney if Sina fails
        result = await manager.fetch_with_source("sector_eastmoney_akshare", "industry")

    if not result.success or not result.data:
        # 抛出错误而不是返回空数据
        error_msg = result.error or "数据源暂时不可用"
        raise HTTPException(
            status_code=503,
            detail=f"暂时无法获取行业板块数据: {error_msg}"
        )

    data = result.data

    # 处理两种数据格式
    # 1. SinaSectorDataSource 返回 list
    # 2. EastMoneySectorSource 返回 dict with "sectors" key
    if isinstance(data, list):
        # Sina 格式转换
        sectors = []
        for item in data:
            sectors.append({
                "rank": len(sectors) + 1,
                "name": item.get("name"),
                "code": item.get("code"),
                "price": item.get("current"),
                "change": item.get("change"),
                "changePercent": item.get("change_pct"),
                "totalMarket": item.get("amount"),
                "turnover": "",
                "upCount": 0,
                "downCount": 0,
                "leadStock": "",
                "leadChange": 0,
            })
        return {"sectors": sectors, "timestamp": current_time, "type": sector_type}

    # EastMoney 格式处理
    if isinstance(data, dict):
        # EastMoneySectorSource 返回的数据格式
        sectors_data = data.get("sectors", [])
        sector_type = data.get("type", "industry")

        # 转换数据格式以适配前端
        sectors = []
        for item in sectors_data:
            sectors.append({
                "rank": item.get("rank"),
                "name": item.get("name"),
                "code": item.get("code"),
                "price": item.get("price"),
                "change": item.get("change"),
                "changePercent": item.get("change_percent"),
                "totalMarket": item.get("total_market"),
                "turnover": item.get("turnover"),
                "upCount": item.get("up_count"),
                "downCount": item.get("down_count"),
                "leadStock": item.get("lead_stock"),
                "leadChange": item.get("lead_change"),
            })

        return {"sectors": sectors, "timestamp": current_time, "type": sector_type}

    return {"sectors": [], "timestamp": current_time, "type": "industry"}


@router.get(
    "/concept",
    response_model=SectorListData,
    summary="获取概念板块列表",
    description="获取 A 股所有概念板块的实时行情（涨跌幅、领涨股票等）",
    responses={
        200: {"description": "成功获取概念板块列表"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_concept_sectors(
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> SectorListData:
    """
    获取 A 股概念板块列表

    Args:
        manager: 数据源管理器依赖

    Returns:
        SectorListData: 包含概念板块列表和时间戳的字典
    """
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 使用 EastMoney 数据源获取概念板块数据
    result = await manager.fetch_with_source("sector_eastmoney_akshare", "concept")

    if not result.success or not result.data:
        # 抛出错误而不是返回空数据
        error_msg = result.error or "数据源暂时不可用"
        raise HTTPException(
            status_code=503,
            detail=f"暂时无法获取概念板块数据: {error_msg}"
        )

    data = result.data

    # EastMoney 格式处理
    if isinstance(data, dict):
        sectors_data = data.get("sectors", [])
        sector_type = data.get("type", "concept")

        # 转换数据格式以适配前端
        sectors = []
        for item in sectors_data:
            sectors.append({
                "rank": item.get("rank"),
                "name": item.get("name"),
                "code": item.get("code"),
                "price": item.get("price"),
                "change": item.get("change"),
                "changePercent": item.get("change_percent"),
                "totalMarket": item.get("total_market"),
                "turnover": item.get("turnover"),
                "upCount": item.get("up_count"),
                "downCount": item.get("down_count"),
                "leadStock": item.get("lead_stock"),
                "leadChange": item.get("lead_change"),
            })

        return {"sectors": sectors, "timestamp": current_time, "type": sector_type}

    return {"sectors": [], "timestamp": current_time, "type": "concept"}


@router.get(
    "/industry/{sector_name}",
    response_model=SectorDetailData,
    summary="获取行业板块详情",
    description="获取指定行业板块的成份股列表",
    responses={
        200: {"description": "成功获取行业板块详情"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_industry_detail(
    sector_name: str,
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> SectorDetailData:
    """
    获取指定行业板块的成份股列表

    Args:
        sector_name: 板块名称（如"半导体"、"新能源汽车"）
        manager: 数据源管理器依赖

    Returns:
        SectorDetailData: 包含板块名称和成份股列表的字典
    """
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 使用 EastMoneyIndustryDetailSource 获取板块详情
    result = await manager.fetch_with_source("sector_industry_detail_akshare", sector_name)

    if not result.success or not result.data:
        # 抛出错误而不是返回空数据
        error_msg = result.error or "数据源暂时不可用"
        raise HTTPException(
            status_code=503,
            detail=f"暂时无法获取行业板块 [{sector_name}] 详情: {error_msg}"
        )

    data = result.data

    if isinstance(data, dict):
        stocks_data = data.get("stocks", [])

        # 转换数据格式
        stocks = []
        for item in stocks_data:
            stocks.append({
                "rank": item.get("rank"),
                "code": item.get("code"),
                "name": item.get("name"),
                "price": item.get("price"),
                "changePercent": item.get("change_percent"),
            })

        return {
            "sector_name": data.get("sector_name", sector_name),
            "stocks": stocks,
            "count": data.get("count", len(stocks)),
            "timestamp": current_time
        }

    return {
        "sector_name": sector_name,
        "stocks": [],
        "count": 0,
        "timestamp": current_time
    }


@router.get(
    "/concept/{sector_name}",
    response_model=SectorDetailData,
    summary="获取概念板块详情",
    description="获取指定概念板块的成份股列表",
    responses={
        200: {"description": "成功获取概念板块详情"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_concept_detail(
    sector_name: str,
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> SectorDetailData:
    """
    获取指定概念板块的成份股列表

    Args:
        sector_name: 板块名称（如"人工智能"、"新能源汽车"）
        manager: 数据源管理器依赖

    Returns:
        SectorDetailData: 包含板块名称和成份股列表的字典
    """
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 使用 EastMoneyConceptDetailSource 获取板块详情
    result = await manager.fetch_with_source("sector_concept_detail_akshare", sector_name)

    if not result.success or not result.data:
        # 抛出错误而不是返回空数据
        error_msg = result.error or "数据源暂时不可用"
        raise HTTPException(
            status_code=503,
            detail=f"暂时无法获取概念板块 [{sector_name}] 详情: {error_msg}"
        )

    data = result.data

    if isinstance(data, dict):
        stocks_data = data.get("stocks", [])

        # 转换数据格式
        stocks = []
        for item in stocks_data:
            stocks.append({
                "rank": item.get("rank"),
                "code": item.get("code"),
                "name": item.get("name"),
                "price": item.get("price"),
                "changePercent": item.get("change_percent"),
            })

        return {
            "sector_name": data.get("sector_name", sector_name),
            "stocks": stocks,
            "count": data.get("count", len(stocks)),
            "timestamp": current_time
        }

    return {
        "sector_name": sector_name,
        "stocks": [],
        "count": 0,
        "timestamp": current_time
    }
