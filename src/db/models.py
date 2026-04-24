# -*- coding: UTF-8 -*-
"""数据库数据模型

包含所有数据类定义，用于数据库表的映射。
"""

from dataclasses import dataclass


@dataclass
class FundConfig:
    """基金配置数据类"""

    code: str
    name: str
    watchlist: int = 1  # SQLite返回整数，1=True，0=False
    shares: float = 0.0  # 持有份额
    cost: float = 0.0  # 成本价
    is_hold: int = 0  # 持有标记 (1=持有, 0=不持有)
    sector: str = ""  # 板块标注
    notes: str = ""  # 备注
    created_at: str = ""
    updated_at: str = ""

    @property
    def is_watchlist(self) -> bool:
        """将整数转换为布尔值"""
        return bool(self.watchlist)

    @property
    def is_holding(self) -> bool:
        """检查是否标记为持有"""
        return bool(self.is_hold)


@dataclass
class CommodityConfig:
    """商品配置数据类"""

    symbol: str
    name: str
    source: str = "akshare"  # 数据源
    enabled: int = 1  # SQLite返回整数，1=True，0=False
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def is_enabled(self) -> bool:
        """将整数转换为布尔值"""
        return bool(self.enabled)


@dataclass
class FundHistoryRecord:
    """基金净值历史记录"""

    id: int | None = None  # 数据库自增ID
    fund_code: str = ""
    fund_name: str = ""
    date: str = ""
    unit_net_value: float = 0.0
    accumulated_net_value: float | None = None
    estimated_value: float | None = None
    growth_rate: float | None = None
    fetched_at: str = ""


@dataclass
class NewsRecord:
    """新闻记录"""

    title: str
    url: str
    source: str
    category: str
    publish_time: str
    content: str = ""
    fetched_at: str = ""


@dataclass
class FundIntradayRecord:
    """基金日内分时数据记录"""

    id: int | None = None  # 数据库自增ID
    fund_code: str = ""
    date: str = ""  # 日期 (YYYY-MM-DD 格式)
    time: str = ""  # "HH:mm" 格式
    price: float = 0.0  # 估算净值
    change_rate: float | None = None  # 涨跌率
    fetched_at: str = ""  # 抓取时间


@dataclass
class IndexIntradayRecord:
    """指数日内分时数据记录"""

    id: int | None = None  # 数据库自增ID
    index_type: str = ""  # 指数类型
    date: str = ""  # 日期 (YYYY-MM-DD 格式)
    time: str = ""  # "HH:mm" 格式
    price: float = 0.0  # 价格
    change_rate: float | None = None  # 涨跌率
    fetched_at: str = ""  # 抓取时间


@dataclass
class FundDailyRecord:
    """基金每日缓存数据记录

    用于存储近一周的每日基础数据，支持展示基金历史走势。
    """

    id: int | None = None  # 数据库自增ID
    fund_code: str = ""
    date: str = ""  # 日期 (YYYY-MM-DD 格式)
    unit_net_value: float | None = None  # 单位净值
    accumulated_net_value: float | None = None  # 累计净值
    estimated_value: float | None = None  # 估算净值
    change_rate: float | None = None  # 日增长率
    estimate_time: str = ""  # 估值时间 (YYYY-MM-DD HH:MM 格式，来自 gztime)
    fetched_at: str = ""  # 抓取时间


@dataclass
class FundBasicInfo:
    """基金基本信息"""

    code: str = ""  # 基金代码
    name: str = ""  # 基金全称
    short_name: str = ""  # 基金简称
    type: str = ""  # 基金类型
    fund_key: str = ""  # 基金关键字
    net_value: float | None = None  # 单位净值
    net_value_date: str = ""  # 净值日期
    establishment_date: str = ""  # 成立日期
    manager: str = ""  # 基金管理人
    custodian: str = ""  # 基金托管人
    fund_scale: float | None = None  # 基金规模
    scale_date: str = ""  # 规模日期
    risk_level: str = ""  # 风险等级
    full_name: str = ""  # 基金完整名称
    fetched_at: str = ""  # 抓取时间
    updated_at: str = ""  # 更新时间


@dataclass
class FundIndustryRecord:
    """基金行业配置记录"""

    fund_code: str = ""
    industry_name: str = ""
    proportion: float | None = None
    report_date: str = ""
    fetched_at: str = ""
    id: int | None = None  # 数据库自增ID


@dataclass
class StockConceptRecord:
    """股票概念标签缓存记录"""

    stock_code: str = ""
    concept_name: str = ""


@dataclass
class CacheMetadata:
    """缓存元数据"""

    fund_code: str = ""  # 基金代码
    cache_status: str = "unknown"  # 状态: unknown/valid/stale/refreshing/error
    last_updated: str = ""  # 最后更新时间
    expires_at: str = ""  # 过期时间
    last_error: str | None = None  # 最后错误信息
    retry_count: int = 0  # 重试次数
    created_at: str = ""  # 创建时间


@dataclass
class ApiCallStats:
    """API调用统计"""

    id: int | None = None  # 数据库自增ID
    api_name: str = ""  # API名称
    call_time: str = ""  # 调用时间
    duration_ms: int = 0  # 耗时（毫秒）
    success: bool = True  # 是否成功
    error_message: str | None = None  # 错误信息
    cache_hit: bool = False  # 是否命中缓存
    fund_code: str | None = None  # 关联的基金代码


@dataclass
class TradingCalendarRecord:
    """交易日历记录"""

    market: str
    year: int
    is_trading_day: bool
    holiday_name: str | None = None
    is_makeup_day: bool = False


@dataclass
class ExchangeHoliday:
    """交易所节假日记录"""

    id: int = 0
    market: str = ""
    holiday_date: str = ""
    holiday_name: str | None = None
    is_active: int = 1
    created_at: str = ""
    updated_at: str = ""

    @property
    def is_holiday_active(self) -> bool:
        return bool(self.is_active)
