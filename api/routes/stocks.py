"""
股票 API 路由
提供股票相关的 REST API 端点
"""

import logging
from datetime import datetime
from typing import TypedDict

from fastapi import APIRouter, HTTPException, Query

from src.datasources.stock_source import SinaStockDataSource, YahooStockDataSource
from src.datasources.manager import DataSourceManager

router = APIRouter(prefix="/api/stocks", tags=["股票"])

logger = logging.getLogger(__name__)


class StockData(TypedDict):
    """股票数据响应结构"""
    code: str
    name: str
    price: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    volume: str
    amount: str
    pre_close: float
    timestamp: str


@router.get("", response_model=list[StockData])
async def get_stocks(
    codes: str = Query(..., description="股票代码，多个用逗号分隔，如: sh600000,sz000001,AAPL"),
):
    """获取股票行情"""
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return []
    
    results: list[StockData] = []
    
    # 区分 A 股和港股/美股
    a_stocks = []
    other_stocks = []
    
    for code in code_list:
        code_upper = code.upper()
        if code_upper.startswith("SH") or code_upper.startswith("SZ") or code_upper.startswith("HK"):
            a_stocks.append(code)
        else:
            other_stocks.append(code)
    
    # 新浪 API 获取 A 股
    if a_stocks:
        try:
            ds = DataSourceManager.get_source("sina_stock")
            if ds:
                data = await ds.get_data(",".join(a_stocks))
                if data:
                    for code, item in data.items():
                        results.append(StockData(
                            code=code,
                            name=item.get("name", ""),
                            price=float(item.get("price", 0)),
                            change=float(item.get("change", 0)),
                            change_pct=float(item.get("change_pct", 0)),
                            open=float(item.get("open", 0)),
                            high=float(item.get("high", 0)),
                            low=float(item.get("low", 0)),
                            volume=item.get("volume", ""),
                            amount=item.get("amount", ""),
                            pre_close=float(item.get("pre_close", 0)),
                            timestamp=datetime.now().isoformat(),
                        ))
        except Exception as e:
            logger.error(f"获取A股数据失败: {e}")
    
    # Yahoo API 获取港股/美股
    if other_stocks:
        try:
            ds = DataSourceManager.get_source("yahoo_stock")
            if ds:
                data = await ds.get_data(",".join(other_stocks))
                if data:
                    for code, item in data.items():
                        results.append(StockData(
                            code=code,
                            name=item.get("name", ""),
                            price=float(item.get("price", 0)),
                            change=float(item.get("change", 0)),
                            change_pct=float(item.get("change_pct", 0)),
                            open=float(item.get("open", 0)),
                            high=float(item.get("high", 0)),
                            low=float(item.get("low", 0)),
                            volume=item.get("volume", ""),
                            amount=item.get("amount", ""),
                            pre_close=float(item.get("pre_close", 0)),
                            timestamp=datetime.now().isoformat(),
                        ))
        except Exception as e:
            logger.error(f"获取港股/美股数据失败: {e}")
    
    return results


@router.get("/{code}", response_model=StockData)
async def get_stock(code: str):
    """获取单个股票行情"""
    stocks = await get_stocks(codes=code)
    if not stocks:
        raise HTTPException(status_code=404, detail="股票未找到")
    return stocks[0]
