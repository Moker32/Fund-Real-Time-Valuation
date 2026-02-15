"""
债券数据 API 路由
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.datasources.base import DataSourceType
from src.datasources.manager import DataSourceManager

from ..dependencies import get_data_source_manager

router = APIRouter(prefix="/api/bonds", tags=["债券数据"])


class BondResponse(BaseModel):
    """债券响应模型"""
    code: str
    name: str | None = None
    price: float | None = None
    change: float | None = None
    change_pct: float | None = None
    volume: int | None = None
    amount: float | None = None
    pre_close: float | None = None
    high: float | None = None
    low: float | None = None
    bid: float | None = None
    ask: float | None = None


class BondListResponse(BaseModel):
    """债券列表响应"""
    bonds: list[BondResponse]
    total: int
    source: str


class BondDetailResponse(BaseModel):
    """债券详情响应"""
    success: bool
    data: BondResponse | None = None
    error: str | None = None
    source: str
    timestamp: float


def _parse_bond(bond: Any) -> BondResponse:
    """解析债券数据"""
    if not isinstance(bond, dict):
        return BondResponse(code="")
    return BondResponse(
        code=bond.get("code", ""),
        name=bond.get("name"),
        price=bond.get("price"),
        change=bond.get("change"),
        change_pct=bond.get("change_pct"),
        volume=bond.get("volume"),
        amount=bond.get("turnover"),
    )


@router.get("", response_model=BondListResponse)
async def get_bonds(
    bond_type: str = Query("cbond", description="债券类型: cbond=可转债, bond_china=中国债券"),
    manager: DataSourceManager = Depends(get_data_source_manager),
):
    """
    获取债券列表
    
    Args:
        bond_type: 债券类型
        manager: 数据源管理器
    """
    result = await manager.fetch(
        DataSourceType.BOND,
        bond_type,
        failover=True,
    )
    
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error or "获取债券数据失败")
    
    data = result.data
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="债券数据格式错误")
    
    bonds_data: list[dict[str, Any]] = data.get("bonds", [])
    bonds = [_parse_bond(bond) for bond in bonds_data]
    
    return BondListResponse(
        bonds=bonds,
        total=len(bonds),
        source=result.source,
    )


@router.get("/{bond_code}", response_model=BondDetailResponse)
async def get_bond(
    bond_code: str,
    market: str | None = Query(None, description="市场: sh=上海, sz=深圳"),
    manager: DataSourceManager = Depends(get_data_source_manager),
):
    """
    获取单个债券详情
    
    Args:
        bond_code: 债券代码
        market: 市场 (可选)
        manager: 数据源管理器
    """
    # 使用新浪债券数据源
    source = manager.get_source("sina_bond")
    if not source:
        raise HTTPException(status_code=500, detail="债券数据源不可用")
    
    result = await source.fetch(bond_code)
    
    if not result.success:
        return BondDetailResponse(
            success=False,
            error=result.error,
            source=result.source,
            timestamp=result.timestamp,
        )
    
    data = result.data
    if not isinstance(data, dict):
        return BondDetailResponse(
            success=False,
            error="债券数据格式错误",
            source=result.source,
            timestamp=result.timestamp,
        )
    
    bond = BondResponse(
        code=data.get("code", ""),
        name=data.get("name"),
        price=data.get("price"),
        change=data.get("change"),
        change_pct=data.get("change_pct"),
        volume=data.get("volume"),
        amount=data.get("amount"),
        pre_close=data.get("pre_close"),
        high=data.get("high"),
        low=data.get("low"),
        bid=data.get("bid"),
        ask=data.get("ask"),
    )
    
    return BondDetailResponse(
        success=True,
        data=bond,
        source=result.source,
        timestamp=result.timestamp,
    )


@router.get("/search/cbonds")
async def search_cbonds(
    keyword: str = Query("", description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    manager: DataSourceManager = Depends(get_data_source_manager),
):
    """
    搜索可转债
    
    Args:
        keyword: 搜索关键词（代码或名称）
        limit: 返回数量限制
        manager: 数据源管理器
    """
    result = await manager.fetch(
        DataSourceType.BOND,
        "cbond",
        failover=True,
    )
    
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error or "获取可转债数据失败")
    
    data = result.data
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="可转债数据格式错误")
    
    bonds_data: list[dict[str, Any]] = data.get("bonds", [])
    
    # 过滤
    if keyword:
        keyword_upper = keyword.upper()
        bonds_data = [
            b for b in bonds_data
            if isinstance(b, dict) and (
                keyword_upper in b.get("code", "").upper()
                or keyword_upper in b.get("name", "").upper()
            )
        ]
    
    # 限制数量
    bonds_data = bonds_data[:limit]
    
    bonds = [_parse_bond(bond) for bond in bonds_data]
    
    return {
        "keyword": keyword,
        "bonds": bonds,
        "total": len(bonds),
    }
