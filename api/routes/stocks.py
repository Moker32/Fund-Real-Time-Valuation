"""
股票 API 路由
提供股票相关的 REST API 端点
"""

import logging
from datetime import datetime
from typing import TypedDict

from fastapi import APIRouter, Depends, HTTPException, Query

from src.datasources.stock_source import SinaStockDataSource, YahooStockSource

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


# 创建数据源实例
_sina_stock_ds = None
_yahoo_stock_ds = None


def get_sina_stock_source():
    global _sina_stock_ds
    if _sina_stock_ds is None:
        _sina_stock_ds = SinaStockDataSource()
    return _sina_stock_ds


def get_yahoo_stock_source():
    global _yahoo_stock_ds
    if _yahoo_stock_ds is None:
        _yahoo_stock_ds = YahooStockSource()
    return _yahoo_stock_ds


def parse_stock_result(result, code: str) -> StockData | None:
    """解析股票数据源结果"""
    if not result or not result.data:
        return None
    
    data = result.data
    return StockData(
        code=code,
        name=data.get("name", ""),
        price=float(data.get("price", 0)),
        change=float(data.get("change", 0)),
        change_pct=float(data.get("change_pct", 0)),
        open=float(data.get("open", 0)),
        high=float(data.get("high", 0)),
        low=float(data.get("low", 0)),
        volume=data.get("volume", ""),
        amount=data.get("amount", ""),
        pre_close=float(data.get("pre_close", 0)),
        timestamp=datetime.now().isoformat(),
    )


@router.get("", response_model=list[StockData])
async def get_stocks(
    codes: str = Query(..., description="股票代码，多个用逗号分隔，如: sh600000,sz000001,AAPL"),
):
    """获取股票行情"""
    code_list = [c.strip().upper() for c in codes.split(",") if c.strip()]
    if not code_list:
        return []
    
    results: list[StockData] = []
    
    # 区分 A 股和港股/美股
    a_stocks = []
    other_stocks = []
    
    for code in code_list:
        if code.startswith("SH") or code.startswith("SZ") or code.startswith("HK"):
            a_stocks.append(code)
        else:
            other_stocks.append(code)
    
    # 新浪 API 获取 A 股
    if a_stocks:
        try:
            ds = get_sina_stock_source()
            batch_results = await ds.fetch_batch(a_stocks)
            for result in batch_results:
                if result and result.success and result.data:
                    # 从 result.metadata 中获取 code
                    stock_code = result.metadata.get("stock_code") if result.metadata else a_stocks[0]
                    parsed = parse_stock_result(result, stock_code)
                    if parsed:
                        results.append(parsed)
        except Exception as e:
            logger.error(f"获取A股数据失败: {e}")
    
    # Yahoo API 获取港股/美股
    if other_stocks:
        try:
            ds = get_yahoo_stock_source()
            batch_results = await ds.fetch_batch(other_stocks)
            for result in batch_results:
                if result and result.success and result.data:
                    stock_code = result.metadata.get("symbol") if result.metadata else other_stocks[0]
                    parsed = parse_stock_result(result, stock_code)
                    if parsed:
                        results.append(parsed)
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
