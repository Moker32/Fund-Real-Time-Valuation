"""
Pydantic 数据模型
定义 API 响应数据结构
"""

from datetime import datetime

from pydantic import BaseModel, Field


class FundResponse(BaseModel):
    """基金响应模型"""
    code: str = Field(..., alias="fund_code", description="基金代码")
    name: str = Field(..., description="基金名称")
    type: str | None = Field(None, description="基金类型（如：股票型、混合型、债券型、QDII等）")
    netValue: float | None = Field(None, alias="unit_net_value", description="单位净值")
    netValueDate: str | None = Field(None, alias="net_value_date", description="净值日期")
    estimateValue: float | None = Field(None, alias="estimated_net_value", description="估值")
    estimateChangePercent: float | None = Field(None, alias="estimated_growth_rate", description="估算增长率(%)")
    estimateTime: str | None = Field(None, alias="estimate_time", description="估值时间")
    source: str = Field(..., description="数据源")

    # 添加 estimateChange 字段（计算属性）
    estimateChange: float | None = Field(None, description="估算涨跌额")

    # 是否持有
    isHolding: bool = Field(False, description="是否持有该基金")

    model_config = {
        "populate_by_name": True,
    }


class FundListResponse(BaseModel):
    """基金列表响应模型"""
    funds: list[dict] = Field(..., description="基金列表")
    total: int = Field(..., description="基金总数")
    timestamp: str = Field(..., description="响应时间戳")


class FundDetailResponse(FundResponse):
    """基金详情响应模型"""
    pass


class FundEstimateResponse(BaseModel):
    """基金估值响应模型"""
    code: str = Field(..., alias="fund_code", description="基金代码")
    name: str = Field(..., description="基金名称")
    type: str | None = Field(None, description="基金类型（如：股票型、混合型、债券型、QDII等）")
    netValue: float | None = Field(None, alias="unit_net_value", description="最新单位净值")
    netValueDate: str | None = Field(None, alias="net_value_date", description="净值日期")
    estimateValue: float | None = Field(None, alias="estimated_net_value", description="单位净值估算")
    estimateChangePercent: float | None = Field(None, alias="estimated_growth_rate", description="估算增长率(%)")
    estimateTime: str | None = Field(None, alias="estimate_time", description="估值时间")

    # 添加 estimateChange 字段（计算属性）
    estimateChange: float | None = Field(None, description="估算涨跌额")

    # 是否持有
    isHolding: bool = Field(False, description="是否持有该基金")

    model_config = {
        "populate_by_name": True,
    }


class CommodityResponse(BaseModel):
    """商品响应模型"""
    commodity: str | None = Field(None, description="商品类型")
    symbol: str = Field(..., description="交易符号")
    name: str = Field(..., description="商品名称")
    price: float = Field(..., description="当前价格")
    change: float | None = Field(None, description="涨跌额")
    changePercent: float | None = Field(None, alias="change_percent", description="涨跌幅(%)")
    currency: str | None = Field(None, description="货币")
    exchange: str | None = Field(None, description="交易所")
    timestamp: str | None = Field(None, alias="time", description="更新时间")
    source: str = Field(..., description="数据源")

    # 扩展字段（可选，用于更多行情数据）
    high: float | None = Field(None, description="最高价")
    low: float | None = Field(None, description="最低价")
    open: float | None = Field(None, description="开盘价")
    prevClose: float | None = Field(None, alias="prev_close", description="昨收价")

    model_config = {
        "populate_by_name": True,
    }


class CommodityListResponse(BaseModel):
    """商品列表响应模型"""
    commodities: list[dict] = Field(..., description="商品列表")
    timestamp: str = Field(..., description="响应时间戳")


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="应用版本")
    timestamp: datetime = Field(..., description="检查时间")


class DataSourceHealthItem(BaseModel):
    """数据源健康状态项"""
    source: str = Field(..., description="数据源名称")
    status: str = Field(..., description="健康状态")
    response_time_ms: float | None = Field(None, description="响应时间(ms)")


class HealthDetailResponse(HealthResponse):
    """详细健康检查响应模型"""
    total_sources: int = Field(..., description="数据源总数")
    healthy_count: int = Field(..., description="健康数据源数")
    unhealthy_count: int = Field(..., description="不健康数据源数")
    data_sources: list[DataSourceHealthItem] = Field(default_factory=list, description="数据源健康状态列表")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = Field(default=False, description="是否成功")
    error: str = Field(..., description="错误类型")
    detail: str | None = Field(None, description="详细错误信息")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat() + "Z", description="错误发生时间")


class OverviewResponse(BaseModel):
    """市场概览响应模型"""
    totalValue: float = Field(..., description="持仓总值")
    totalChange: float = Field(..., description="今日涨跌金额")
    totalChangePercent: float = Field(..., description="今日涨跌百分比")
    fundCount: int = Field(..., description="基金数量")
    lastUpdated: str = Field(..., description="更新时间")

    model_config = {
        "populate_by_name": True,
    }


class AddFundRequest(BaseModel):
    """添加基金请求模型"""
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d+$", description="基金代码")
    name: str = Field(..., min_length=1, max_length=100, description="基金名称")


class AddFundResponse(BaseModel):
    """添加基金响应模型"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(..., description="响应消息")
    fund: dict = Field(..., description="添加的基金信息")
