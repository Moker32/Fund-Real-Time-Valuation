"""
商品 API 路由
提供商品相关的 REST API 端点
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.datasources.base import DataSourceType
from src.datasources.commodity_source import YFinanceCommoditySource, AKShareCommoditySource
from src.datasources.manager import DataSourceManager

from ..dependencies import DataSourceDependency
from ..models import CommodityResponse, ErrorResponse


router = APIRouter(prefix="/api/commodities", tags=["商品"])


# 支持的商品类型列表
SUPPORTED_COMMODITIES = [
    "gold",       # COMEX 黄金
    "gold_cny",   # 上海黄金
    "wti",        # WTI 原油
    "brent",      # 布伦特原油
    "silver",     # 白银
    "natural_gas",  # 天然气
]


@router.get(
    "",
    response_model=list[CommodityResponse],
    summary="获取商品行情",
    description="获取所有支持的商品实时行情",
    responses={
        200: {"description": "成功获取商品行情"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_commodities(
    types: Optional[str] = None,
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> list[dict]:
    """
    获取商品行情列表

    Args:
        types: 可选的商品类型列表，逗号分隔
        manager: 数据源管理器依赖

    Returns:
        list[CommodityResponse]: 商品行情列表
    """
    # 确定要获取的商品类型
    if types:
        commodity_types = [t.strip() for t in types.split(",") if t.strip()]
        if not commodity_types:
            return []
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

    return all_results


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
