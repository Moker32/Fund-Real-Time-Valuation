"""
行业板块和概念板块 API 路由
提供 A 股行业板块和概念板块相关的 REST API 端点
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from typing_extensions import TypedDict

from src.datasources.base import DataSourceResult
from src.datasources.manager import DataSourceManager

from ..dependencies import DataSourceDependency
from ..models import ErrorResponse

# 常量定义
FLOW_TYPE_INDUSTRY = "industry"
FLOW_TYPE_CONCEPT = "concept"
VALID_FLOW_TYPES = {FLOW_TYPE_INDUSTRY, FLOW_TYPE_CONCEPT}

SYMBOL_IMMEDIATE = "即时"
SYMBOL_3DAY = "3日排行"
SYMBOL_5DAY = "5日排行"
SYMBOL_10DAY = "10日排行"
SYMBOL_20DAY = "20日排行"
VALID_SYMBOLS = {SYMBOL_IMMEDIATE, SYMBOL_3DAY, SYMBOL_5DAY, SYMBOL_10DAY, SYMBOL_20DAY}


def _check_result_success(result: DataSourceResult | object) -> bool:
    """
    安全地检查数据源结果是否成功

    处理 MagicMock 在测试中返回 truthy 值导致的问题。
    """
    # 如果是 DataSourceResult 类型，检查 success 属性
    if isinstance(result, DataSourceResult):
        return bool(result.success) and result.data is not None
    # 对于其他类型（如 MagicMock），只检查 data 属性
    return getattr(result, "data", None) is not None


class SectorListData(TypedDict):
    """板块列表响应数据结构"""

    sectors: list[dict]
    timestamp: str
    type: str


class SectorDetailData(TypedDict):
    """板块详情响应数据结构"""

    sectorName: str
    stocks: list[dict]
    count: int
    timestamp: str


router = APIRouter(prefix="/api/sectors", tags=["行业板块"])


@router.get(
    "/industry",
    response_model=SectorListData,
    summary="获取行业板块列表",
    description="获取 A 股所有行业板块的实时行情（涨跌幅、资金流向等）",
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

    数据源优先级：
    1. ThsSectorSource - 同花顺行业板块，净流入字段（优先级最高）
    2. FundFlowIndustrySource - 资金流向接口，非交易时间可用
    3. EastMoneySectorSource - 实时行情接口，交易时间更及时
    4. SinaSectorDataSource - 最后备用
    """
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    sector_type = "industry"

    # 优先使用同花顺行业板块（净流入数据）
    result = await manager.fetch_with_source("sector_ths_akshare")

    if not _check_result_success(result):
        # 备用：资金流向接口（非交易时间可用）
        result = await manager.fetch_with_source("sector_industry_fund_flow", "industry")

    if not _check_result_success(result):
        # 备用：AKShare _spot_em 接口（实时行情，数据更完整）
        result = await manager.fetch_with_source("sector_eastmoney_akshare", "industry")

    if not _check_result_success(result):
        # 最后尝试 Sina
        result = await manager.fetch_with_source("sina_sector")

    # 检查所有数据源是否都失败
    if not _check_result_success(result):
        error_msg = getattr(result, "error", None) or "数据源暂时不可用"
        raise HTTPException(status_code=503, detail=f"暂时无法获取行业板块数据: {error_msg}")

    data = result.data
    # 使用数据源的 timestamp，如果没有则使用当前时间
    data_timestamp = data.get("timestamp") if isinstance(data, dict) else None
    if data_timestamp:
        current_time = (
            datetime.fromtimestamp(data_timestamp, timezone.utc).isoformat().replace("+00:00", "Z")
        )
    else:
        current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 处理三种数据格式
    if isinstance(data, list):
        # Sina 格式转换
        sectors: list[dict] = []
        for item in data:
            sectors.append(
                {
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
                    "timestamp": current_time,
                }
            )
        return {"sectors": sectors, "timestamp": current_time, "type": sector_type}

    # EastMoney 格式处理（包含资金流向）
    if isinstance(data, dict):
        sectors_data = data.get("sectors", [])
        sector_type = data.get("type", "industry")

        sectors = []
        for item in sectors_data:
            sector = {
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
                "leadStock": item.get("lead_stock", ""),
                "leadChange": item.get("lead_change", 0),
                "timestamp": current_time,
            }
            # 添加资金流向数据（如果存在）
            if "main_inflow" in item:
                sector["mainInflow"] = item.get("main_inflow")
                sector["mainInflowPct"] = item.get("main_inflow_pct")
                sector["smallInflow"] = item.get("small_inflow")
                sector["smallInflowPct"] = item.get("small_inflow_pct")
            # 添加净流入数据（同花顺ths_sector来源）
            if "net_inflow" in item:
                sector["mainInflow"] = item.get("net_inflow")
            sectors.append(sector)

        return {"sectors": sectors, "timestamp": current_time, "type": sector_type}

    return {"sectors": [], "timestamp": current_time, "type": "industry"}


@router.get(
    "/concept",
    response_model=SectorListData,
    summary="获取概念板块列表",
    description="获取 A 股所有概念板块的实时行情（涨跌幅、资金流向等）",
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

    数据源优先级：
    1. FundFlowConceptSource - 资金流向接口，非交易时间可用
    2. EastMoneySectorSource - 实时行情接口，交易时间更及时
    3. EastMoneyDirectSource - 直连 API，兜底
    """
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 优先使用资金流向接口（非交易时间可用）
    result = await manager.fetch_with_source("sector_concept_fund_flow", "concept")

    if not _check_result_success(result):
        # 备用：AKShare _spot_em 接口（实时行情，数据更完整）
        result = await manager.fetch_with_source("sector_eastmoney_akshare", "concept")

    if not _check_result_success(result):
        # 最后备用：Sina 数据源
        result = await manager.fetch_with_source("sina_sector")

    # 检查所有数据源是否都失败
    if not _check_result_success(result):
        error_msg = getattr(result, "error", None) or "数据源暂时不可用"
        raise HTTPException(status_code=503, detail=f"暂时无法获取概念板块数据: {error_msg}")

    data = result.data
    # 使用数据源的 timestamp，如果没有则使用当前时间
    data_timestamp = data.get("timestamp") if isinstance(data, dict) else None
    if data_timestamp:
        current_time = (
            datetime.fromtimestamp(data_timestamp, timezone.utc).isoformat().replace("+00:00", "Z")
        )
    else:
        current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if isinstance(data, dict):
        sectors_data = data.get("sectors", [])
        sector_type = data.get("type", "concept")

        sectors = []
        for item in sectors_data:
            sector = {
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
                "leadStock": item.get("lead_stock", ""),
                "leadChange": item.get("lead_change", 0),
                "timestamp": current_time,
            }
            # 添加资金流向数据（如果存在）
            if "main_inflow" in item:
                sector["mainInflow"] = item.get("main_inflow")
                sector["mainInflowPct"] = item.get("main_inflow_pct")
                sector["smallInflow"] = item.get("small_inflow")
                sector["smallInflowPct"] = item.get("small_inflow_pct")
            sectors.append(sector)

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
            status_code=503, detail=f"暂时无法获取行业板块 [{sector_name}] 详情: {error_msg}"
        )

    data = result.data

    if isinstance(data, dict):
        stocks_data = data.get("stocks", [])

        # 转换数据格式
        stocks = []
        for item in stocks_data:
            stocks.append(
                {
                    "rank": item.get("rank"),
                    "code": item.get("code"),
                    "name": item.get("name"),
                    "price": item.get("price"),
                    "changePercent": item.get("change_percent"),
                }
            )

        return {
            "sectorName": data.get("sector_name", sector_name),
            "stocks": stocks,
            "count": data.get("count", len(stocks)),
            "timestamp": current_time,
        }

    return {"sectorName": sector_name, "stocks": [], "count": 0, "timestamp": current_time}


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
            status_code=503, detail=f"暂时无法获取概念板块 [{sector_name}] 详情: {error_msg}"
        )

    data = result.data

    if isinstance(data, dict):
        stocks_data = data.get("stocks", [])

        # 转换数据格式
        stocks = []
        for item in stocks_data:
            stocks.append(
                {
                    "rank": item.get("rank"),
                    "code": item.get("code"),
                    "name": item.get("name"),
                    "price": item.get("price"),
                    "changePercent": item.get("change_percent"),
                }
            )

        return {
            "sectorName": data.get("sector_name", sector_name),
            "stocks": stocks,
            "count": data.get("count", len(stocks)),
            "timestamp": current_time,
        }

    return {"sectorName": sector_name, "stocks": [], "count": 0, "timestamp": current_time}


# ============================================================
# 同花顺资金流向 API 端点
# ============================================================


class FundFlowData(TypedDict):
    """资金流向响应数据结构"""

    items: list[dict]
    timestamp: str
    type: str
    symbol: str


@router.get(
    "/fund-flow/{flow_type}",
    response_model=FundFlowData,
    summary="获取资金流向数据",
    description="获取行业或概念板块的资金流向数据（来源于同花顺数据中心）",
    responses={
        200: {"description": "成功获取资金流向数据"},
        400: {"model": ErrorResponse, "description": "参数错误"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_fund_flow(
    flow_type: str,
    symbol: str = "即时",
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> FundFlowData:
    """
    获取资金流向数据

    Args:
        flow_type: 资金流向类型
            - industry: 行业资金流向
            - concept: 概念资金流向
        symbol: 时间周期
            - 即时: 当日实时
            - 3日排行: 3日累计
            - 5日排行: 5日累计
            - 10日排行: 10日累计
            - 20日排行: 20日累计
    """
    # 参数验证
    if flow_type not in VALID_FLOW_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"无效的流向类型: {flow_type}，支持: industry, concept",
        )

    if symbol not in VALID_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail=f"无效的时间周期: {symbol}，支持: {', '.join(sorted(VALID_SYMBOLS))}",
        )

    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 获取资金流向数据
    result = await manager.fetch_with_source("fund_flow_ths_akshare", flow_type, symbol)

    if not result.success or not result.data:
        error_msg = result.error or "数据源暂时不可用"
        raise HTTPException(status_code=503, detail=f"暂时无法获取资金流向数据: {error_msg}")

    data = result.data

    # 使用数据源的 timestamp
    data_timestamp = data.get("timestamp") if isinstance(data, dict) else None
    if data_timestamp:
        current_time = (
            datetime.fromtimestamp(data_timestamp, timezone.utc).isoformat().replace("+00:00", "Z")
        )

    if isinstance(data, dict):
        items_data = data.get("items", [])

        # 转换数据格式
        items = []
        for item in items_data:
            items.append(
                {
                    "rank": item.get("rank"),
                    "name": item.get("name"),
                    "indexValue": item.get("index_value"),
                    "changePercent": item.get("change_percent"),
                    "inflow": item.get("inflow"),
                    "outflow": item.get("outflow"),
                    "netInflow": item.get("net_inflow"),
                    "companyCount": item.get("company_count"),
                    "leadStock": item.get("lead_stock"),
                    "leadStockChange": item.get("lead_stock_change"),
                    "price": item.get("price"),
                }
            )

        return {
            "items": items,
            "timestamp": current_time,
            "type": data.get("type", flow_type),
            "symbol": data.get("symbol", symbol),
        }

    return {"items": [], "timestamp": current_time, "type": flow_type, "symbol": symbol}
