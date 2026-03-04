"""
基金数据源模块
实现从天天基金/fund123.cn 接口获取基金实时估值数据
"""

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import pandas as pd

from src.db.database import (
    DatabaseManager,
    FundBasicInfoDAO,
    FundDailyCacheDAO,
    FundIntradayCacheDAO,
)

from .base import (
    DataParseError,
    DataSource,
    DataSourceResult,
    DataSourceType,
)
from .dual_cache import DualLayerCache

logger = logging.getLogger(__name__)

# 全局缓存实例（单例模式）
_fund_cache: DualLayerCache | None = None
# 基金基本信息缓存（全局 akshare 调用结果）
_fund_info_cache: dict[str, tuple[dict, float]] = {}  # {code: (info, timestamp)}
_fund_info_cache_ttl = 3600  # 1小时缓存
# 基金信息缓存命中率统计
_fund_info_hit_count = 0
_fund_info_miss_count = 0
# 日内分时缓存 DAO 单例
_intraday_cache_dao: FundIntradayCacheDAO | None = None
# 每日缓存 DAO 单例
_daily_cache_dao: FundDailyCacheDAO | None = None
# 基金基本信息缓存 DAO 单例
_basic_info_dao: FundBasicInfoDAO | None = None
# 交易日历源单例（用于净值缓存有效性判断）
_trading_calendar_source: "TradingCalendarSource | None" = None

if TYPE_CHECKING:
    from src.datasources.trading_calendar_source import TradingCalendarSource


def get_fund_cache() -> DualLayerCache:
    """获取基金缓存单例"""
    global _fund_cache
    if _fund_cache is None:
        cache_dir = Path.home() / ".fund-tui" / "cache" / "funds"
        _fund_cache = DualLayerCache(
            cache_dir=cache_dir,
            memory_ttl=0,  # 禁用内存缓存
            file_ttl=0,  # 禁用文件缓存
            max_memory_items=100,
        )
    return _fund_cache


def get_intraday_cache_dao() -> FundIntradayCacheDAO:
    """获取日内分时缓存 DAO 单例"""
    global _intraday_cache_dao
    if _intraday_cache_dao is None:
        db_manager = DatabaseManager()
        _intraday_cache_dao = FundIntradayCacheDAO(db_manager)
    return _intraday_cache_dao


def get_daily_cache_dao() -> FundDailyCacheDAO:
    """获取每日缓存 DAO 单例"""
    global _daily_cache_dao
    if _daily_cache_dao is None:
        db_manager = DatabaseManager()
        # 设置 5 分钟缓存过期时间
        _daily_cache_dao = FundDailyCacheDAO(db_manager, cache_ttl=300)
    return _daily_cache_dao


def get_basic_info_dao() -> FundBasicInfoDAO:
    """获取基金基本信息 DAO 单例"""
    global _basic_info_dao
    if _basic_info_dao is None:
        db_manager = DatabaseManager()
        _basic_info_dao = FundBasicInfoDAO(db_manager)
    return _basic_info_dao


def get_basic_info_db(fund_code: str) -> dict[str, Any] | None:
    """
    从数据库读取基金基本信息

    Args:
        fund_code: 基金代码

    Returns:
        基金基本信息字典，如果不存在返回 None
    """
    dao = get_basic_info_dao()
    info = dao.get(fund_code)
    if info:
        return {
            "code": info.code,
            "name": info.name,
            "short_name": info.short_name,
            "type": info.type,
            "fund_key": info.fund_key,
            "net_value": info.net_value,
            "net_value_date": info.net_value_date,
            "establishment_date": info.establishment_date,
            "manager": info.manager,
            "custodian": info.custodian,
            "fund_scale": info.fund_scale,
            "scale_date": info.scale_date,
            "risk_level": info.risk_level,
            "full_name": info.full_name,
        }
    return None


def save_basic_info_to_db(fund_code: str, info: dict[str, Any]) -> bool:
    """
    保存基金基本信息到数据库

    Args:
        fund_code: 基金代码
        info: 基金信息字典

    Returns:
        是否保存成功
    """
    dao = get_basic_info_dao()
    return dao.save_from_dict(fund_code, info)


def get_full_fund_info(fund_code: str) -> dict[str, Any] | None:
    """
    获取完整基金信息（从 akshare 获取更多字段）

    Args:
        fund_code: 基金代码

    Returns:
        包含完整基金信息的字典，失败返回 None
    """
    try:
        import akshare as ak

        info_dict: dict[str, Any] = {}

        # 1. 获取基金简称和全称
        try:
            daily_df = ak.fund_open_fund_daily_em()
            if "基金代码" in daily_df.columns:
                name_rows = daily_df[daily_df["基金代码"] == fund_code]
                if not name_rows.empty:
                    info_dict["short_name"] = str(name_rows.iloc[0].get("基金简称", ""))
                    info_dict["name"] = info_dict["short_name"]
        except Exception as e:
            logger.debug(f"获取基金简称失败: {fund_code}, error: {e}")

        # 2. 获取基金详细信息
        try:
            info_df = ak.fund_individual_basic_info_xq(symbol=fund_code)
            if info_df is not None and not info_df.empty:
                # 遍历所有字段
                for _, row in info_df.iterrows():
                    item = str(row.get("item", ""))
                    value = str(row.get("value", ""))

                    if "基金全称" in item:
                        info_dict["full_name"] = value
                    elif "基金简称" in item:
                        info_dict["short_name"] = value
                    elif "基金类型" in item:
                        # 保留完整的 akshare 格式：主类型-子类型
                        info_dict["type"] = value
                    elif "基金管理人" in item:
                        info_dict["manager"] = value
                    elif "基金托管人" in item:
                        info_dict["custodian"] = value
                    elif "成立日期" in item:
                        info_dict["establishment_date"] = value
                    elif "风险等级" in item:
                        info_dict["risk_level"] = value
        except Exception as e:
            logger.debug(f"获取基金详细信息失败: {fund_code}, error: {e}")

        # 3. 获取基金规模和净值信息
        try:
            fund_info = ak.fund_info_fund_code_em(fund_code=fund_code)
            if fund_info is not None:
                info_dict["fund_scale"] = fund_info.get("基金规模")
                info_dict["scale_date"] = fund_info.get("规模日期", "")
        except Exception as e:
            logger.debug(f"获取基金规模信息失败: {fund_code}, error: {e}")

        # 设置默认值
        info_dict.setdefault("short_name", "")
        info_dict.setdefault("name", "")
        info_dict.setdefault("full_name", "")
        info_dict.setdefault("type", "")
        info_dict.setdefault("manager", "")
        info_dict.setdefault("custodian", "")
        info_dict.setdefault("establishment_date", "")
        info_dict.setdefault("risk_level", "")
        info_dict.setdefault("fund_scale", None)
        info_dict.setdefault("scale_date", "")

        # 保存到数据库
        save_basic_info_to_db(fund_code, info_dict)

        return info_dict

    except Exception as e:
        logger.warning(f"获取完整基金信息失败: {fund_code}, error: {e}")
        return None


def _get_fund_type_from_fund_name_em(fund_code: str) -> str | None:
    """
    从 akshare fund_name_em API 获取基金类型

    该 API 返回完整的基金类型字符串，包含子类型信息。
    例如："指数型-股票"、"股票型"、"混合型-偏股" 等。

    Args:
        fund_code: 基金代码

    Returns:
        基金类型字符串（含子类型后缀），获取失败返回 None
    """
    try:
        import akshare as ak

        df = ak.fund_name_em()
        if df is None or df.empty:
            return None

        # 查找对应基金代码的记录
        if "基金代码" not in df.columns or "基金类型" not in df.columns:
            logger.debug(f"fund_name_em 返回数据格式不正确: {df.columns.tolist()}")
            return None

        fund_rows = df[df["基金代码"] == fund_code]
        if fund_rows.empty:
            return None

        fund_type = str(fund_rows.iloc[0].get("基金类型", "")).strip()
        if fund_type and fund_type != "nan":
            logger.debug(f"从 fund_name_em 获取基金类型: {fund_code} -> {fund_type}")
            return fund_type

        return None
    except Exception as e:
        logger.debug(f"fund_name_em 获取基金类型失败: {fund_code}, error: {e}")
        return None


def _infer_fund_type_from_name(fund_name: str) -> str:
    """
    从基金名称推断基金类型

    Args:
        fund_name: 基金名称

    Returns:
        基金类型字符串
    """
    if not fund_name:
        return ""

    name = fund_name.upper()

    # 根据名称中的关键词推断类型
    if "QDII" in name:
        return "QDII"
    if "FOF" in name:
        return "FOF"
    if "ETF" in name and "联接" in name:
        return "ETF-联接"
    if "ETF" in name:
        return "ETF"
    if "LOF" in name:
        return "LOF"
    if "货币" in name:
        return "货币型"
    if "债券" in name:
        return "债券型"
    if "混合" in name:
        return "混合型"
    # 指数型基金单独处理，保持与 akshare 返回格式一致
    if "指数" in name:
        return "指数型"
    if "股票" in name:
        return "股票型"

    return ""


def _has_real_time_estimate(fund_type: str, fund_name: str) -> bool:
    """
    判断基金是否有实时估值

    规则：
    - QDII 基金：无实时估值（投资海外市场，净值更新延迟）
    - FOF 基金投资海外基金（QDII-FOF）：无实时估值
    - 其他 FOF、ETF-联接基金：有实时估值（底层资产是国内基金）
    - 普通基金：有实时估值

    Args:
        fund_type: 基金类型
        fund_name: 基金名称

    Returns:
        bool: 是否有实时估值
    """
    if not fund_type:
        return False

    # QDII 基金无实时估值（包括 QDII-商品、QDII-股票等子类型）
    if fund_type.startswith("QDII"):
        return False

    # FOF 基金需要进一步判断是否投资海外
    if fund_type == "FOF":
        name_upper = (fund_name or "").upper()
        # QDII-FOF 或投资海外的 FOF 无实时估值
        if "QDII" in name_upper or "海外" in name_upper or "全球" in name_upper:
            return False
        return True

    # 其他类型有实时估值
    return True


def _get_net_value_date_from_akshare(fund_code: str) -> tuple[str, float] | None:
    """
    从 akshare 获取基金最新净值和日期

    Args:
        fund_code: 基金代码

    Returns:
        (净值日期, 单位净值) 元组，获取失败返回 None
    """
    try:
        import akshare as ak

        # 获取基金历史净值数据
        fund_df = ak.fund_etf_fund_info_em(fund=fund_code)

        if fund_df is None or fund_df.empty:
            return None

        # 获取最新一条记录（数据按日期升序排列，取最后一行）
        latest = fund_df.iloc[-1]
        date = str(latest.get("净值日期", ""))
        net_value = latest.get("单位净值", None)

        if date and net_value is not None:
            try:
                return (date, float(net_value))
            except (ValueError, TypeError):
                pass

        return None
    except Exception as e:
        logger.warning(f"akshare 获取净值失败: {e}")
        return None


def _get_trading_calendar():  # type: ignore[no-untyped-def]
    """
    获取交易日历源单例

    Returns:
        TradingCalendarSource: 交易日历源实例
    """
    global _trading_calendar_source
    if _trading_calendar_source is None:
        from src.datasources.trading_calendar_source import TradingCalendarSource

        _trading_calendar_source = TradingCalendarSource()
    return _trading_calendar_source


def _get_china_market_date():  # type: ignore[no-untyped-def]
    """
    获取中国市场的当前日期（时区感知）

    Returns:
        date: 中国时区下的当前日期
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("Asia/Shanghai")
    now = datetime.now(tz)
    return now.date()


def _is_after_market_close() -> bool:
    """
    判断当前是否在收盘后（15:00 之后）

    Returns:
        bool: True 表示已收盘，False 表示未收盘或无法判断
    """
    from datetime import datetime
    from datetime import time as time_type
    from zoneinfo import ZoneInfo

    try:
        # 使用中国时区
        tz = ZoneInfo("Asia/Shanghai")
        now = datetime.now(tz)
        current_time = now.time()

        # A股收盘时间为 15:00
        market_close_time = time_type(15, 0)

        return current_time >= market_close_time
    except Exception:
        # 无法判断时，默认返回 True（允许更新缓存）
        return True


def _get_latest_trading_day() -> str | None:
    """
    获取最新的交易日期（字符串格式 YYYY-MM-DD）

    Returns:
        str | None: 最新交易日，获取失败返回 None
    """
    from datetime import timedelta

    try:
        calendar = _get_trading_calendar()
        today = _get_china_market_date()

        # 如果今天不是交易日，找最近的交易日
        if not calendar.is_trading_day("china", today):
            # 往前找最近的交易日
            for i in range(1, 8):  # 最多往前找7天
                check_date = today - timedelta(days=i)
                if calendar.is_trading_day("china", check_date):
                    return check_date.isoformat()
            return None

        # 今天是交易日
        # 如果已收盘，返回今天的日期
        if _is_after_market_close():
            return today.isoformat()
        else:
            # 未收盘，返回上一个交易日
            for i in range(1, 8):
                check_date = today - timedelta(days=i)
                if calendar.is_trading_day("china", check_date):
                    return check_date.isoformat()
            return None
    except Exception as e:
        logger.warning(f"获取最新交易日失败: {e}")
        return None


def _is_net_value_cache_valid(fund_code: str) -> tuple[bool, str | None, float | None]:
    """
    检查净值缓存是否有效（净值日期是否为最新交易日）

    Args:
        fund_code: 基金代码

    Returns:
        tuple[bool, str | None, float | None]: (是否有效, 净值日期, 净值)
    """
    try:
        # 从数据库获取缓存的净值日期
        basic_info = get_basic_info_db(fund_code)
        if not basic_info:
            return (False, None, None)

        cached_date = basic_info.get("net_value_date")
        cached_value = basic_info.get("net_value")

        if not cached_date or cached_value is None:
            return (False, None, None)

        # 获取最新交易日
        latest_trading_day = _get_latest_trading_day()
        if not latest_trading_day:
            # 无法获取交易日，缓存可能有效
            return (True, cached_date, cached_value)

        # 比较净值日期和最新交易日
        if cached_date == latest_trading_day:
            # 净值日期是最新的，缓存有效
            return (True, cached_date, cached_value)

        # 净值日期落后，缓存无效
        logger.debug(
            f"净值缓存过期: {fund_code}, 缓存日期={cached_date}, 最新交易日={latest_trading_day}"
        )
        return (False, cached_date, cached_value)

    except Exception as e:
        logger.warning(f"检查净值缓存失败: {fund_code} - {e}")
        return (False, None, None)


def _update_net_value_cache(fund_code: str, net_value: float, net_value_date: str) -> bool:
    """
    更新数据库中的净值缓存

    Args:
        fund_code: 基金代码
        net_value: 单位净值
        net_value_date: 净值日期

    Returns:
        bool: 是否更新成功
    """
    try:
        dao = get_basic_info_dao()
        return dao.update(fund_code, net_value=net_value, net_value_date=net_value_date)
    except Exception as e:
        logger.warning(f"更新净值缓存失败: {fund_code} - {e}")
        return False


def get_fund_basic_info(fund_code: str) -> tuple[str, str] | None:
    """
    获取基金基本信息（名称和类型），使用全局缓存和数据库

    优先从数据库读取，如果不存在或类型为空则从 akshare 获取并保存到数据库

    Args:
        fund_code: 基金代码

    Returns:
        (name, type) 或 None（如果获取失败）
    """
    global _fund_info_cache, _fund_info_hit_count, _fund_info_miss_count
    now = time.time()

    # 1. 检查内存缓存
    if fund_code in _fund_info_cache:
        info, timestamp = _fund_info_cache[fund_code]
        if now - timestamp < _fund_info_cache_ttl:
            _fund_info_hit_count += 1
            return info

    # 2. 尝试从数据库读取
    db_info = get_basic_info_db(fund_code)
    if db_info:
        name = db_info.get("short_name", "") or ""
        fund_type = db_info.get("type", "") or ""
        # 只有当类型不为空时才使用缓存，否则需要重新获取
        if fund_type:
            result = (name, fund_type)
            _fund_info_cache[fund_code] = (result, now)
            _fund_info_hit_count += 1
            return result
        # 类型为空，需要从 akshare 重新获取
        _fund_info_miss_count += 1
    else:
        _fund_info_miss_count += 1

    # 3. 从 akshare 获取
    try:
        import akshare as ak

        # 获取基金简称
        fund_name = ""
        try:
            daily_df = ak.fund_open_fund_daily_em()
            if "基金代码" in daily_df.columns:
                name_rows = daily_df[daily_df["基金代码"] == fund_code]
                if not name_rows.empty:
                    fund_name = str(name_rows.iloc[0].get("基金简称", ""))
        except Exception as e:
            logger.debug(f"获取基金简称失败: {fund_code}, error: {e}")

        # 获取基金类型（保留完整的 akshare 格式：主类型-子类型）
        # 优先级：fund_individual_basic_info_xq > fund_name_em > 名称推断
        fund_type = ""
        
        # 方案1: fund_individual_basic_info_xq (最精确)
        try:
            info_df = ak.fund_individual_basic_info_xq(symbol=fund_code)
            if info_df is not None and not info_df.empty:
                type_row = info_df[info_df["item"] == "基金类型"]
                if not type_row.empty:
                    fund_type = str(type_row.iloc[0]["value"]).strip()
                    # 保留完整格式，如 "QDII-商品"、"股票型-增强指数"、"指数型-股票"
        except Exception as e:
            logger.debug(f"获取基金类型失败: {fund_code}, error: {e}")

        # 方案2: fund_name_em (备用，保留子类型)
        if not fund_type:
            fund_type = _get_fund_type_from_fund_name_em(fund_code) or ""

        # 方案3: 从基金名称中识别类型（最后回退）
        if not fund_type and fund_name:
            fund_type = _infer_fund_type_from_name(fund_name)

        result = (fund_name, fund_type)
        _fund_info_cache[fund_code] = (result, now)

        # 保存到数据库
        if fund_name or fund_type:
            save_basic_info_to_db(
                fund_code,
                {
                    "short_name": fund_name,
                    "name": fund_name,
                    "type": fund_type,
                },
            )

        return result

    except Exception as e:
        logger.warning(f"获取基金基本信息失败: {fund_code}, error: {e}")
        return None


class FundDataSource(DataSource):
    """基金数据源 - 从天天基金接口获取数据"""

    def __init__(self, timeout: float = 30.0, max_retries: int = 2, retry_delay: float = 1.0):
        """
        初始化基金数据源

        Args:
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            retry_delay: 重试间隔(秒)
        """
        super().__init__(name="fund_tiantian", source_type=DataSourceType.FUND, timeout=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/javascript, */*;q=0.8",
                "Referer": "http://fundgz.1234567.com.cn/",
            },
        )

    async def fetch(self, fund_code: str, use_cache: bool = True) -> DataSourceResult:
        """
        获取单个基金数据

        缓存策略：
        1. 优先从数据库读取（5分钟过期）
        2. 数据库缓存过期时，从 API 获取并更新数据库
        3. 最后回退到内存/文件缓存

        Args:
            fund_code: 基金代码 (6位数字)
            use_cache: 是否使用缓存

        Returns:
            DataSourceResult: 包含基金数据的结果
        """
        if not self._validate_fund_code(fund_code):
            return DataSourceResult(
                success=False,
                error=f"无效的基金代码: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        cache_key = f"fund:{self.name}:{fund_code}"

        # 1. 优先从数据库读取每日缓存（5分钟过期）
        if use_cache:
            daily_dao = get_daily_cache_dao()
            if not daily_dao.is_expired(fund_code):
                cached_daily = daily_dao.get_latest(fund_code)
                if cached_daily:
                    # 获取基金类型（从基本信息表）
                    fund_type = ""
                    basic_info = get_basic_info_db(fund_code)
                    if basic_info:
                        fund_type = basic_info.get("type", "") or ""

                    # 优先使用 estimate_time，如果为空则回退到 date
                    estimate_time = cached_daily.estimate_time or cached_daily.date

                    # 构建返回数据格式
                    result_data = {
                        "fund_code": fund_code,
                        "name": basic_info.get("name", "") if basic_info else "",
                        "type": fund_type,
                        "net_value_date": cached_daily.date,
                        "unit_net_value": cached_daily.unit_net_value,
                        "estimated_net_value": cached_daily.estimated_value,
                        "estimated_growth_rate": cached_daily.change_rate,
                        "estimate_time": estimate_time,
                        "has_real_time_estimate": cached_daily.estimated_value is not None,
                    }
                    return DataSourceResult(
                        success=True,
                        data=result_data,
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code, "cache": "database"},
                    )

        # 2. 检查内存/文件缓存
        if use_cache:
            cache = get_fund_cache()
            cached_value, cache_type = await cache.get(cache_key)
            if cached_value is not None:
                # 缓存命中
                return DataSourceResult(
                    success=True,
                    data=cached_value,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code, "cache": cache_type},
                )

        # 3. 从 API 获取数据
        # 场内基金（交易所交易）
        is_etf = fund_code.startswith("5") or fund_code.startswith("15")  # ETF
        is_lof = fund_code.startswith("16")  # LOF 基金

        for attempt in range(self.max_retries):
            try:
                # LOF 使用东方财富 LOF 接口
                if is_lof:
                    result = await self._fetch_lof(fund_code, has_real_time_estimate=True)
                    if result.success:
                        # 写入数据库缓存
                        daily_dao = get_daily_cache_dao()
                        daily_dao.save_daily_from_fund_data(fund_code, result.data)
                        # 写入内存/文件缓存
                        cache = get_fund_cache()
                        await cache.set(cache_key, result.data)
                        return result
                    # LOF 获取失败，返回错误（不再尝试其他接口）
                    return DataSourceResult(
                        success=False,
                        error=f"{fund_code} 是 LOF 基金，数据获取失败: {result.error}",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

                # ETF 使用东方财富 ETF 接口
                if is_etf:
                    result = await self._fetch_etf(fund_code)
                    if result.success:
                        # 写入数据库缓存
                        daily_dao = get_daily_cache_dao()
                        daily_dao.save_daily_from_fund_data(fund_code, result.data)
                        # 写入内存/文件缓存
                        cache = get_fund_cache()
                        await cache.set(cache_key, result.data)
                        return result
                    # ETF 获取失败，返回错误（不再尝试其他接口）
                    return DataSourceResult(
                        success=False,
                        error=f"{fund_code} 是 ETF 基金，数据获取失败: {result.error}",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

                # 普通基金使用天天基金接口
                url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js?rt={int(time.time() * 1000)}"
                response = await self.client.get(url)
                response.raise_for_status()

                # 检查是否是空响应
                if response.text.strip() in ("jsonpgz();", "jsonpgz()"):
                    # 判断基金类型并返回友好错误
                    if fund_code.startswith("5") or fund_code.startswith("15"):
                        return DataSourceResult(
                            success=False,
                            error=f"{fund_code} 是 ETF 基金，请使用场内基金交易接口",
                            timestamp=time.time(),
                            source=self.name,
                            metadata={"fund_code": fund_code},
                        )
                    if fund_code.startswith("16"):
                        return DataSourceResult(
                            success=False,
                            error=f"{fund_code} 是 LOF 基金，请使用场内基金交易接口",
                            timestamp=time.time(),
                            source=self.name,
                            metadata={"fund_code": fund_code},
                        )

                # 检查是否是空响应
                if response.text.strip() in ("jsonpgz();", "jsonpgz()"):
                    # 天天基金不支持的基金，尝试使用东方财富开放式基金接口
                    # QDII/FOF 基金（如 470888）可能在这里获取到
                    # 这些基金没有实时估值，只有上一个交易日的日增长率
                    result = await self._fetch_lof(fund_code, has_real_time_estimate=False)
                    if result.success:
                        return result

                    # 东方财富接口也失败，返回友好错误
                    if fund_code.startswith("5") or fund_code.startswith("15"):
                        return DataSourceResult(
                            success=False,
                            error=f"{fund_code} 是 ETF 基金，请使用场内基金交易接口",
                            timestamp=time.time(),
                            source=self.name,
                            metadata={"fund_code": fund_code},
                        )
                    if fund_code.startswith("16"):
                        return DataSourceResult(
                            success=False,
                            error=f"{fund_code} 是 LOF 基金，请使用场内基金交易接口",
                            timestamp=time.time(),
                            source=self.name,
                            metadata={"fund_code": fund_code},
                        )
                    return DataSourceResult(
                        success=False,
                        error=f"基金 {fund_code} 数据获取失败: {result.error}",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

                # 解析返回的 JS 数据
                data = self._parse_response(response.text, fund_code)

                if data:
                    # 获取基金类型
                    fund_type = await self._get_fund_type(fund_code)
                    if fund_type:
                        data["type"] = fund_type
                    else:
                        # Fallback: 从基金名称中识别 QDII/FOF
                        fund_name = data.get("name", "")
                        if "(QDII)" in fund_name or fund_name.endswith("QDII"):
                            data["type"] = "QDII"
                            fund_type = "QDII"
                        elif fund_name.endswith("FOF") or "(FOF)" in fund_name:
                            data["type"] = "FOF"
                            fund_type = "FOF"

                    # 根据基金类型和名称判断是否有实时估值
                    fund_name = data.get("name", "")
                    data["has_real_time_estimate"] = _has_real_time_estimate(fund_type, fund_name)

                    # QDII 基金或投资海外的 FOF 需要获取上一交易日净值用于对比
                    if not data["has_real_time_estimate"]:
                        # 调用东方财富接口获取上一净值
                        lof_result = await self._fetch_lof(fund_code, has_real_time_estimate=False)
                        if lof_result.success:
                            data["prev_net_value"] = lof_result.data.get("prev_net_value")
                            data["prev_net_value_date"] = lof_result.data.get("prev_net_value_date")
                        else:
                            data["prev_net_value"] = None
                            data["prev_net_value_date"] = None
                    else:
                        data["prev_net_value"] = None
                        data["prev_net_value_date"] = None

                    self._record_success()

                    # 保存基金基本信息到数据库
                    save_basic_info_to_db(
                        fund_code,
                        {
                            "short_name": data.get("name", ""),
                            "name": data.get("name", ""),
                            "type": data.get("type", ""),
                            "net_value": data.get("unit_net_value"),
                            "net_value_date": data.get("net_value_date", ""),
                        },
                    )

                    # 写入数据库缓存
                    daily_dao = get_daily_cache_dao()
                    daily_dao.save_daily_from_fund_data(fund_code, data)
                    # 写入内存/文件缓存
                    cache = get_fund_cache()
                    await cache.set(cache_key, data)

                    return DataSourceResult(
                        success=True,
                        data=data,
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return DataSourceResult(
                        success=False,
                        error=f"基金不存在: {fund_code}",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code, "status_code": 404},
                    )
                await self._handle_retry_delay(attempt)

            except httpx.RequestError:
                await self._handle_retry_delay(attempt)

            except json.JSONDecodeError as e:
                self._request_count += 1
                self._error_count += 1
                return DataSourceResult(
                    success=False,
                    error=f"数据解析失败: {str(e)}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

        # 如果是 LOF，返回更明确的错误信息
        if is_lof:
            return DataSourceResult(
                success=False,
                error=f"{fund_code} 是 QDII/LOF 基金，akshare 东方财富接口返回数据为空",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        # 如果是 ETF，返回更明确的错误信息
        if is_etf:
            return DataSourceResult(
                success=False,
                error=f"{fund_code} 是 ETF 基金，当前数据源暂不支持",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        return DataSourceResult(
            success=False,
            error=f"获取基金数据失败，已重试 {self.max_retries} 次",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code},
        )

    async def _fetch_etf(self, fund_code: str) -> DataSourceResult:
        """
        获取 ETF 数据 - 使用东方财富接口

        Args:
            fund_code: ETF 代码

        Returns:
            DataSourceResult: ETF 数据结果
        """
        try:
            # 使用 akshare 获取 ETF 数据
            import asyncio

            loop = asyncio.get_running_loop()
            import akshare as ak

            # 获取 ETF 最新数据
            df = await loop.run_in_executor(None, lambda: ak.fund_etf_fund_info_em(fund=fund_code))

            if df is None or df.empty:
                return DataSourceResult(
                    success=False,
                    error=f"ETF {fund_code} 无数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            # 获取最新一条数据
            latest = df.iloc[0]

            # 使用缓存获取基金名称
            fund_info = get_fund_basic_info(fund_code)
            if fund_info:
                fund_name, fund_type = fund_info
            else:
                fund_name, fund_type = "", ""

            # 如果没获取到名称，使用基金代码作为名称
            if not fund_name:
                fund_name = f"ETF {fund_code}"

            # 提取数据
            data = {
                "fund_code": fund_code,
                "name": fund_name,
                "type": fund_type,
                "net_value_date": str(latest.get("净值日期", "")),
                "unit_net_value": float(latest.get("单位净值", 0))
                if pd.notna(latest.get("单位净值"))
                else None,
                "estimated_net_value": float(latest.get("单位净值", 0))
                if pd.notna(latest.get("单位净值"))
                else None,
                "estimated_growth_rate": float(latest.get("日增长率", 0))
                if pd.notna(latest.get("日增长率"))
                else None,
                "estimate_time": str(latest.get("净值日期", "")),
                "has_real_time_estimate": True,  # ETF 有实时估值
            }

            self._record_success()

            # 保存基金基本信息到数据库
            save_basic_info_to_db(
                fund_code,
                {
                    "short_name": fund_name,
                    "name": fund_name,
                    "type": fund_type,
                    "net_value": data.get("unit_net_value"),
                    "net_value_date": data.get("net_value_date", ""),
                },
            )

            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 库未安装",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )
        except Exception as e:
            return DataSourceResult(
                success=False,
                error=f"ETF 数据获取失败: {str(e)}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

    async def _fetch_lof(
        self, fund_code: str, has_real_time_estimate: bool = True
    ) -> DataSourceResult:
        """
        获取 LOF/QDII/FOF 基金数据 - 使用东方财富开放式基金接口

        支持: LOF、QDII、FOF 等所有在天天基金网显示的开放式基金

        Args:
            fund_code: 基金代码
            has_real_time_estimate: 是否有实时估值（默认为 True，QDII/FOF 应设为 False）

        Returns:
            DataSourceResult: 基金数据结果
        """
        try:
            import asyncio

            loop = asyncio.get_running_loop()
            import akshare as ak

            # 获取基金最新净值数据
            df = await loop.run_in_executor(
                None,
                lambda: ak.fund_open_fund_info_em(
                    symbol=fund_code, indicator="单位净值走势", period="近一年"
                ),
            )

            if df is None or df.empty:
                return DataSourceResult(
                    success=False,
                    error=f"基金 {fund_code} 无净值数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            # 获取最新一条数据（最后一行是最新的，因为数据是按日期升序排列的）
            # 注意：akshare 可能返回末尾的"封闭期"记录（净值为 NaT），需要过滤
            df_valid = df[df["净值日期"].notna()]
            if df_valid.empty:
                return DataSourceResult(
                    success=False,
                    error=f"基金 {fund_code} 无有效净值数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            # 使用缓存获取基金简称和类型
            fund_info = get_fund_basic_info(fund_code)
            if fund_info:
                fund_name, fund_type = fund_info
            else:
                fund_name, fund_type = "", ""

            # 如果没获取到名称，使用基金代码作为名称
            if not fund_name:
                fund_name = f"基金 {fund_code}"

            # 根据基金类型和名称判断是否有实时估值
            has_real_time = has_real_time_estimate and _has_real_time_estimate(fund_type, fund_name)

            # 提取数据
            # 使用已过滤的有效数据 df_valid 获取最新和上一条记录
            latest = df_valid.iloc[-1]
            prev_row = df_valid.iloc[-2] if len(df_valid) >= 2 else df_valid.iloc[-1]

            net_date = str(latest.get("净值日期", ""))
            prev_net_date = str(prev_row.get("净值日期", ""))
            unit_net = (
                float(latest.get("单位净值", 0)) if pd.notna(latest.get("单位净值")) else None
            )
            prev_unit_net = (
                float(prev_row.get("单位净值", 0)) if pd.notna(prev_row.get("单位净值")) else None
            )
            daily_change = (
                float(latest.get("日增长率", 0)) if pd.notna(latest.get("日增长率")) else None
            )

            data = {
                "fund_code": fund_code,
                "name": fund_name,
                "type": fund_type,
                "net_value_date": net_date,
                "unit_net_value": unit_net,
                "prev_net_value_date": prev_net_date,
                "prev_net_value": prev_unit_net,
                "estimated_net_value": unit_net,  # 开放式基金暂无实时估值，使用单位净值
                "estimated_growth_rate": daily_change,
                "estimate_time": net_date,
                "has_real_time_estimate": has_real_time,  # 根据基金类型判断是否有实时估值
            }

            self._record_success()

            # 保存基金基本信息到数据库
            save_basic_info_to_db(
                fund_code,
                {
                    "short_name": fund_name,
                    "name": fund_name,
                    "type": fund_type,
                    "net_value": unit_net,
                    "net_value_date": net_date,
                },
            )

            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 库未安装",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )
        except Exception as e:
            return DataSourceResult(
                success=False,
                error=f"基金数据获取失败: {str(e)}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

    async def fetch_batch(self, fund_codes: list[str]) -> list[DataSourceResult]:
        """
        批量获取基金数据

        Args:
            fund_codes: 基金代码列表

        Returns:
            List[DataSourceResult]: 每个基金的结果列表
        """

        async def fetch_one(code: str) -> DataSourceResult:
            return await self.fetch(code)

        tasks = [fetch_one(code) for code in fund_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常情况
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_codes[i]},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def _validate_fund_code(self, fund_code: str) -> bool:
        """
        验证基金代码格式

        Args:
            fund_code: 基金代码

        Returns:
            bool: 是否有效
        """
        return bool(re.match(r"^\d{6}$", str(fund_code)))

    async def _get_fund_type(self, fund_code: str) -> str:
        """
        获取基金类型信息

        Args:
            fund_code: 基金代码

        Returns:
            str: 基金类型（如：股票型、混合型、债券型、QDII、ETF等）
        """
        # 使用缓存获取基金信息
        fund_info = get_fund_basic_info(fund_code)
        if fund_info:
            _, fund_type = fund_info
            return fund_type
        return ""

    def _parse_response(self, response_text: str, fund_code: str) -> dict[str, Any] | None:
        """
        解析天天基金返回的 JS 数据

        Args:
            response_text: 原始响应文本
            fund_code: 基金代码

        Returns:
            Optional[Dict]: 解析后的数据字典
        """
        try:
            # 天天基金返回格式: jsonpgz({"fundcode":"161039",...});
            # 使用正则提取 JSON 内容
            pattern = r"jsonpgz\((.*)\);?"
            match = re.search(pattern, response_text)

            if not match:
                raise DataParseError(
                    message="无法解析基金数据响应",
                    source_type=self.source_type,
                    details={"response_preview": response_text[:100]},
                )

            json_str = match.group(1)
            data = json.loads(json_str)

            # 标准化字段名
            return {
                "fund_code": data.get("fundcode", ""),
                "name": data.get("name", ""),
                "net_value_date": data.get("jzrq", ""),
                "unit_net_value": self._safe_float(data.get("dwjz")),
                "estimated_net_value": self._safe_float(data.get("gsz")),
                "estimated_growth_rate": self._safe_float(data.get("gszzl")),
                "estimate_time": data.get("gztime", ""),
                "raw_data": data,
            }

        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            raise DataParseError(
                message=f"基金数据解析错误: {str(e)}",
                source_type=self.source_type,
                details={"fund_code": fund_code},
            )

    def _safe_float(self, value: Any) -> float | None:
        """
        安全转换为浮点数

        Args:
            value: 待转换的值

        Returns:
            Optional[float]: 转换后的值，失败返回 None
        """
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def _handle_retry_delay(self, attempt: int):
        """处理重试延迟"""
        if attempt < self.max_retries - 1:
            await asyncio.sleep(self.retry_delay * (attempt + 1))

    async def close(self):
        """关闭异步客户端"""
        await self.client.aclose()

    def __del__(self):
        """析构时确保关闭客户端（异步客户端需要在异步上下文中关闭）"""
        try:
            if hasattr(self, "client") and self.client.is_closed is False:
                # Note: 异步客户端无法在 __del__ 中安全关闭
                # 应使用 async with 或显式调用 close() 方法
                pass
        except Exception:
            pass

    async def health_check(self) -> bool:
        """
        健康检查 - 天天基金接口

        Returns:
            bool: 健康状态
        """
        try:
            # 天天基金接口支持批量查询，使用一个示例基金代码
            url = f"http://fundgz.1234567.com.cn/js/161039.js?rt={int(time.time() * 1000)}"
            response = await self.client.get(url, timeout=self.timeout)
            response.raise_for_status()

            # 验证返回数据格式
            data = response.text
            if data and "jsonpgz" in data and "fundcode" in data:
                return True
            return False
        except Exception:
            return False


# 导出类
__all__ = [
    "FundDataSource",
    "SinaFundDataSource",
    "FundHistorySource",
    "FundHistoryYFinanceSource",
    "Fund123DataSource",
    "get_fund_cache",
    "get_fund_cache_stats",
    "get_intraday_cache_dao",
    "get_daily_cache_dao",
    "get_basic_info_dao",
    "get_basic_info_db",
    "save_basic_info_to_db",
    "get_fund_basic_info",
    "get_full_fund_info",
]


def get_fund_cache_stats() -> dict:
    """
    获取基金缓存统计信息

    Returns:
        dict: 包含 fund_cache 和 fund_info_cache 的统计信息
    """
    global _fund_info_hit_count, _fund_info_miss_count

    # 获取基金信息缓存统计
    info_total = _fund_info_hit_count + _fund_info_miss_count
    info_hit_rate = _fund_info_hit_count / info_total if info_total > 0 else 0.0

    # 获取基金数据缓存统计
    fund_cache = get_fund_cache()
    fund_cache_stats = fund_cache.get_stats() if fund_cache else {}

    return {
        "fund_cache": fund_cache_stats,
        "fund_info_cache": {
            "hit_count": _fund_info_hit_count,
            "miss_count": _fund_info_miss_count,
            "hit_rate": round(info_hit_rate, 4),
            "total_requests": info_total,
            "cached_items": len(_fund_info_cache),
            "ttl_seconds": _fund_info_cache_ttl,
        },
    }


class FundHistorySource(DataSource):
    """基金历史数据源 - 使用 akshare 获取基金净值历史数据"""

    def __init__(self, timeout: float = 30.0):
        """
        初始化基金历史数据源

        Args:
            timeout: 请求超时时间
        """
        super().__init__(
            name="fund_history_akshare", source_type=DataSourceType.FUND, timeout=timeout
        )

    async def fetch(self, fund_code: str, period: str = "近一年") -> DataSourceResult:
        """
        获取基金历史净值数据

        Args:
            fund_code: 基金代码 (6位数字)
            period: 时间周期，可选值: "近一周", "近一月", "近三月", "近六月", "近一年", "近三年", "近五年", "成立以来"

        Returns:
            DataSourceResult: 包含历史净值数据的结果
        """
        if not self._validate_fund_code(fund_code):
            return DataSourceResult(
                success=False,
                error=f"无效的基金代码: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        try:
            # 在异步上下文中使用 akshare
            import akshare as ak

            # 获取基金历史净值数据
            fund_df = ak.fund_etf_fund_info_em(fund=fund_code)

            if fund_df is None or fund_df.empty:
                return DataSourceResult(
                    success=False,
                    error="未获取到基金历史数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            # 解析数据并转换为 OHLCV 格式（K 线图需要）
            ohlcv_data = []
            for _, row in fund_df.iterrows():
                date = row.get("净值日期", "")
                net_value = row.get("单位净值", None)

                if date and net_value is not None:
                    try:
                        nav = float(net_value)
                        # 基金净值是单点数据，open/high/low/close 相同
                        ohlcv_data.append(
                            {
                                "time": str(date),
                                "open": round(nav, 4),
                                "high": round(nav, 4),
                                "low": round(nav, 4),
                                "close": round(nav, 4),
                                "volume": 0,  # 基金没有成交量
                            }
                        )
                    except (ValueError, TypeError):
                        continue

            # 按日期升序排序
            ohlcv_data.sort(key=lambda x: x["time"])

            self._record_success()
            return DataSourceResult(
                success=True,
                data={"fund_code": fund_code, "data": ohlcv_data, "count": len(ohlcv_data)},
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code, "period": period},
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 库未安装，请运行: pip install akshare",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )
        except Exception as e:
            self._request_count += 1
            self._error_count += 1
            return DataSourceResult(
                success=False,
                error=f"获取基金历史数据失败: {str(e)}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

    async def fetch_async(self, fund_code: str, period: str = "近一年") -> DataSourceResult:
        """
        异步获取基金历史净值数据（推荐使用）

        Args:
            fund_code: 基金代码 (6位数字)
            period: 时间周期

        Returns:
            DataSourceResult: 包含历史净值数据的结果
        """
        # akshare 本身是同步的，我们在异步任务中运行
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.fetch(fund_code, period))

    def _validate_fund_code(self, fund_code: str) -> bool:
        """验证基金代码格式"""
        return bool(re.match(r"^\d{6}$", str(fund_code)))

    async def fetch_batch(self, *args, **kwargs) -> list[DataSourceResult]:
        """
        批量获取基金历史数据（未实现，返回单条结果）

        Returns:
            List[DataSourceResult]: 返回结果列表
        """
        # 从 kwargs 中提取参数
        fund_code = kwargs.get("fund_code")
        period = kwargs.get("period", "近一年")

        if fund_code:
            result = await self.fetch(fund_code, period)
            return [result]
        return [
            DataSourceResult(
                success=False,
                error="缺少 fund_code 参数",
                timestamp=time.time(),
                source=self.name,
            )
        ]


class FundHistoryYFinanceSource(DataSource):
    """基金历史数据源 - 使用 yfinance 获取历史数据（备用方案）"""

    def __init__(self, timeout: float = 30.0):
        super().__init__(
            name="fund_history_yfinance", source_type=DataSourceType.FUND, timeout=timeout
        )

    async def fetch(self, fund_code: str, period: str = "1y") -> DataSourceResult:
        """
        使用 yfinance 获取基金历史数据

        Args:
            fund_code: 基金代码 (对于中国基金，需要添加 .SS 后缀)
            period: 时间周期: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

        Returns:
            DataSourceResult: 包含历史数据的结果
        """
        try:
            import yfinance as yf

            # 构建 ticker 符号
            ticker_symbol = f"{fund_code}.SS" if fund_code.isdigit() else fund_code

            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period=period)

            if hist is None or hist.empty:
                return DataSourceResult(
                    success=False,
                    error="未获取到基金历史数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            history_data = []
            for index, row in hist.iterrows():
                history_data.append(
                    {
                        "date": index.strftime("%Y-%m-%d"),
                        "open": row.get("Open"),
                        "high": row.get("High"),
                        "low": row.get("Low"),
                        "close": row.get("Close"),
                        "volume": row.get("Volume"),
                        "dividends": row.get("Dividends"),
                        "stock_splits": row.get("Stock Splits"),
                    }
                )

            self._record_success()
            return DataSourceResult(
                success=True,
                data={
                    "fund_code": fund_code,
                    "ticker": ticker_symbol,
                    "history": history_data,
                    "count": len(history_data),
                },
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code, "period": period},
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="yfinance 库未安装，请运行: pip install yfinance",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )
        except Exception as e:
            self._request_count += 1
            self._error_count += 1
            return DataSourceResult(
                success=False,
                error=f"获取历史数据失败: {str(e)}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

    async def fetch_async(self, fund_code: str, period: str = "1y") -> DataSourceResult:
        """异步获取历史数据"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.fetch(fund_code, period))

    async def fetch_batch(self, *args, **kwargs) -> list[DataSourceResult]:
        """
        批量获取基金历史数据（未实现，返回单条结果）

        Returns:
            List[DataSourceResult]: 返回结果列表
        """
        fund_code = kwargs.get("fund_code")
        period = kwargs.get("period", "1y")

        if fund_code:
            result = await self.fetch(fund_code, period)
            return [result]
        return [
            DataSourceResult(
                success=False,
                error="缺少 fund_code 参数",
                timestamp=time.time(),
                source=self.name,
            )
        ]


class SinaFundDataSource(DataSource):
    """新浪基金数据源 - 备用基金数据源"""

    def __init__(self, timeout: float = 30.0, max_retries: int = 2, retry_delay: float = 1.0):
        """
        初始化新浪基金数据源

        Args:
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            retry_delay: 重试间隔(秒)
        """
        super().__init__(name="fund_sina", source_type=DataSourceType.FUND, timeout=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json, text/javascript, */*;q=0.8",
            },
        )

    async def fetch(self, fund_code: str) -> DataSourceResult:
        """
        获取单个基金数据 - 使用新浪基金接口

        Args:
            fund_code: 基金代码 (6位数字)

        Returns:
            DataSourceResult: 包含基金数据的结果
        """
        if not self._validate_fund_code(fund_code):
            return DataSourceResult(
                success=False,
                error=f"无效的基金代码: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        for attempt in range(self.max_retries):
            try:
                # 使用新浪基金 API
                url = f"https://finance.sina.com.cn/fund/qqjl/{fund_code}.js"
                response = await self.client.get(url, follow_redirects=True)
                response.raise_for_status()

                # 解析 JSON 数据
                text = response.text.strip()
                if not text or text == "null":
                    return DataSourceResult(
                        success=False,
                        error=f"基金 {fund_code} 无数据",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

                # 新浪返回格式: var LF_xx={...}
                json_match = re.search(r"\{.+\}", text)
                if not json_match:
                    return DataSourceResult(
                        success=False,
                        error=f"基金 {fund_code} 数据解析失败",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

                data = json.loads(json_match.group())

                # 提取数据
                net_value = self._safe_float(data.get("NAV", data.get("unit_nav")))
                estimate_value = (
                    self._safe_float(data.get("ACC_NAV", data.get("acc_nav"))) or net_value
                )
                change_percent = self._safe_float(
                    data.get("NAV_CHG_PCT", data.get("change_percent"))
                )

                # 解析日期
                net_date = str(data.get("UPDATE_DATE", data.get("nav_date", "")))

                result_data = {
                    "fund_code": fund_code,
                    "name": data.get("NAME", data.get("name", f"基金 {fund_code}")),
                    "net_value_date": net_date,
                    "unit_net_value": net_value,
                    "estimated_net_value": estimate_value,
                    "estimated_growth_rate": change_percent,
                    "estimate_time": net_date,
                }

                self._record_success()
                return DataSourceResult(
                    success=True,
                    data=result_data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            except asyncio.TimeoutError:
                await asyncio.sleep(self.retry_delay)
                continue
            except Exception:
                await asyncio.sleep(self.retry_delay)
                continue

        return DataSourceResult(
            success=False,
            error=f"基金 {fund_code} 获取失败，已重试 {self.max_retries} 次",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code},
        )

    def _validate_fund_code(self, fund_code: str) -> bool:
        """验证基金代码格式"""
        return bool(re.match(r"^\d{6}$", str(fund_code)))

    def _safe_float(self, value: Any) -> float | None:
        """安全转换为浮点数"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def fetch_batch(self, fund_codes: list[str]) -> list[DataSourceResult]:
        """批量获取基金数据"""

        async def fetch_one(code: str) -> DataSourceResult:
            return await self.fetch(code)

        tasks = [fetch_one(code) for code in fund_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_codes[i]},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results


class EastMoneyFundDataSource(DataSource):
    """东方财富基金数据源 - 备用基金数据源"""

    def __init__(self, timeout: float = 30.0, max_retries: int = 2, retry_delay: float = 1.0):
        """
        初始化东方财富基金数据源

        Args:
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            retry_delay: 重试间隔(秒)
        """
        super().__init__(name="fund_eastmoney", source_type=DataSourceType.FUND, timeout=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
            },
        )

    async def fetch(self, fund_code: str) -> DataSourceResult:
        """
        获取单个基金数据 - 使用东方财富基金接口

        Args:
            fund_code: 基金代码 (6位数字)

        Returns:
            DataSourceResult: 包含基金数据的结果
        """
        if not self._validate_fund_code(fund_code):
            return DataSourceResult(
                success=False,
                error=f"无效的基金代码: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        for attempt in range(self.max_retries):
            try:
                # 使用东方财富基金 API
                url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
                response = await self.client.get(url)
                response.raise_for_status()

                text = response.text.strip()
                if not text:
                    return DataSourceResult(
                        success=False,
                        error=f"基金 {fund_code} 无数据",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

                # 解析 JS 格式数据
                # 格式: var API_FUND_xxxx={...}
                json_match = re.search(r"=\{[\s\S]*\};?$", text)
                if not json_match:
                    # 尝试另一种格式
                    json_match = re.search(r"\{.+\}", text)

                if not json_match:
                    return DataSourceResult(
                        success=False,
                        error=f"基金 {fund_code} 数据解析失败",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

                data_str = json_match.group().rstrip(";")
                data = json.loads(data_str)

                # 提取数据
                net_value = self._safe_float(data.get("NET", data.get("unit_nav")))
                estimate_value = (
                    self._safe_float(data.get("ACC_NET", data.get("acc_nav"))) or net_value
                )
                change_percent = self._safe_float(data.get("CHANGEPCT", data.get("change_percent")))

                # 解析日期
                net_date = str(data.get("ENDDATE", data.get("nav_date", "")))

                # 获取基金名称
                fund_name = data.get("FUNDNAME", data.get("name", ""))
                if not fund_name:
                    fund_name = f"基金 {fund_code}"

                result_data = {
                    "fund_code": fund_code,
                    "name": fund_name,
                    "net_value_date": net_date,
                    "unit_net_value": net_value,
                    "estimated_net_value": estimate_value,
                    "estimated_growth_rate": change_percent,
                    "estimate_time": net_date,
                }

                self._record_success()
                return DataSourceResult(
                    success=True,
                    data=result_data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            except asyncio.TimeoutError:
                await asyncio.sleep(self.retry_delay)
                continue
            except Exception:
                await asyncio.sleep(self.retry_delay)
                continue

        return DataSourceResult(
            success=False,
            error=f"基金 {fund_code} 获取失败，已重试 {self.max_retries} 次",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code},
        )

    def _validate_fund_code(self, fund_code: str) -> bool:
        """验证基金代码格式"""
        return bool(re.match(r"^\d{6}$", str(fund_code)))

    def _safe_float(self, value: Any) -> float | None:
        """安全转换为浮点数"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def fetch_batch(self, fund_codes: list[str]) -> list[DataSourceResult]:
        """批量获取基金数据"""

        async def fetch_one(code: str) -> DataSourceResult:
            return await self.fetch(code)

        tasks = [fetch_one(code) for code in fund_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_codes[i]},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results


class Fund123DataSource(DataSource):
    """
    fund123.cn 基金数据源

    特点：
    - 速度快（~0.1秒/请求）
    - 需要 CSRF token 和 Cookie
    - 支持日内估值、历史净值查询
    """

    BASE_URL = "https://www.fund123.cn"

    # 全局 Session 和 CSRF token（单例模式）
    _client: httpx.AsyncClient | None = None
    _csrf_token: str | None = None
    _csrf_token_time: float = 0.0
    _csrf_token_ttl = 1800  # 30 分钟过期
    # 天天基金专用客户端（单例模式）
    _tiantian_client: httpx.AsyncClient | None = None
    # 并发控制：限制同时请求数，防止连接池耗尽或被限流
    _semaphore: asyncio.Semaphore | None = None
    # CSRF token 刷新锁：防止多请求同时刷新 token
    _csrf_lock: asyncio.Lock | None = None
    # 最大并发数
    MAX_CONCURRENT_REQUESTS = 5

    def __init__(self, timeout: float = 15.0, max_retries: int = 3, retry_delay: float = 0.5):
        """
        初始化 fund123 基金数据源

        Args:
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            retry_delay: 重试间隔(秒)
        """
        super().__init__(name="fund123", source_type=DataSourceType.FUND, timeout=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._ensure_client()

    @classmethod
    def _ensure_client(cls):
        """确保存在全局 AsyncClient"""
        if cls._client is None:
            cls._client = httpx.AsyncClient(
                verify=False,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Referer": "https://www.fund123.cn/fund",
                    "Origin": "https://www.fund123.cn",
                    "X-API-Key": "foobar",
                },
            )

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        """
        获取并发控制信号量（单例模式）

        Returns:
            asyncio.Semaphore: 并发控制信号量
        """
        if cls._semaphore is None:
            cls._semaphore = asyncio.Semaphore(cls.MAX_CONCURRENT_REQUESTS)
        return cls._semaphore

    @classmethod
    def _get_csrf_lock(cls) -> asyncio.Lock:
        """
        获取 CSRF token 刷新锁（单例模式）

        Returns:
            asyncio.Lock: CSRF token 刷新锁
        """
        if cls._csrf_lock is None:
            cls._csrf_lock = asyncio.Lock()
        return cls._csrf_lock

    @classmethod
    def _get_tiantian_client(cls) -> httpx.AsyncClient:
        """获取天天基金专用客户端（单例模式）"""
        if cls._tiantian_client is None:
            cls._tiantian_client = httpx.AsyncClient(
                timeout=5.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Referer": "http://fundgz.1234567.com.cn/",
                },
            )
        return cls._tiantian_client

    @classmethod
    async def _get_csrf_token(cls) -> str | None:
        """
        获取 CSRF token（带锁保护，防止并发刷新）

        Returns:
            CSRF token 字符串，获取失败返回 None
        """
        now = time.time()

        # 检查缓存的 token 是否有效
        if cls._csrf_token and (now - cls._csrf_token_time) < cls._csrf_token_ttl:
            return cls._csrf_token

        # 使用锁保护，防止多个请求同时刷新 token
        async with cls._get_csrf_lock():
            # 双重检查：可能在等待锁期间其他协程已经刷新了 token
            if cls._csrf_token and (now - cls._csrf_token_time) < cls._csrf_token_ttl:
                return cls._csrf_token

            try:
                # 访问首页获取 token
                response = await cls._client.get(f"{cls.BASE_URL}/fund", timeout=15.0)
                response.raise_for_status()

                # 从响应文本中提取 CSRF
                csrf_match = re.search(r'"csrf":"([^"]+)"', response.text)
                if csrf_match:
                    cls._csrf_token = csrf_match.group(1)
                    cls._csrf_token_time = time.time()  # 更新为获取成功的时间
                    logger.debug(f"获取到新的 CSRF token: {cls._csrf_token[:20]}...")
                    return cls._csrf_token

                logger.warning("无法从响应中提取 CSRF token")
                return None

            except Exception as e:
                logger.error(f"获取 CSRF token 失败: {e}")
                return None

    @classmethod
    async def _refresh_csrf_token(cls) -> bool:
        """刷新 CSRF token"""
        cls._csrf_token = None
        cls._csrf_token_time = 0
        token = await cls._get_csrf_token()
        return token is not None

    async def _get_prev_net_value(self, fund_code: str) -> tuple[float | None, str | None]:
        """
        获取上一交易日净值（用于折线图基准线）

        优先从数据库缓存获取，如果缓存无效或不存在则从 akshare 获取。

        Args:
            fund_code: 基金代码

        Returns:
            (prev_net_value, prev_net_value_date) 元组，获取失败返回 (None, None)
        """
        prev_net_value: float | None = None
        prev_net_value_date: str | None = None

        # 1. 优先从数据库缓存获取
        try:
            daily_dao = get_daily_cache_dao()
            recent_days = daily_dao.get_recent_days(fund_code, 2)
            if len(recent_days) >= 2:
                # 第二条记录是上一个交易日
                prev_record = recent_days[1]
                prev_net_value = prev_record.unit_net_value
                prev_net_value_date = prev_record.date
                logger.debug(
                    f"从数据库缓存获取前日净值: {fund_code} -> "
                    f"{prev_net_value}, 日期: {prev_net_value_date}"
                )
        except Exception as e:
            logger.warning(f"获取上一交易日净值失败: {e}")

        # 2. 如果数据库缓存无效或不存在，从 akshare 获取
        if prev_net_value is None:
            try:
                import akshare as ak

                loop = asyncio.get_running_loop()
                df = await loop.run_in_executor(
                    None,
                    lambda: ak.fund_etf_fund_info_em(fund=fund_code),
                )
                if df is not None and len(df) >= 2:
                    # 过滤有效数据
                    df_valid = df[df["净值日期"].notna()]
                    if len(df_valid) >= 2:
                        prev_row = df_valid.iloc[-2]
                        raw_value = prev_row.get("单位净值")
                        if pd.notna(raw_value):
                            prev_net_value = float(raw_value)
                            prev_net_value_date = str(prev_row.get("净值日期", ""))
                            logger.debug(
                                f"从 akshare 获取前日净值成功: {fund_code} -> "
                                f"{prev_net_value}, 日期: {prev_net_value_date}"
                            )
            except Exception as e:
                logger.warning(f"从 akshare 获取前日净值失败: {fund_code} - {e}")

        return prev_net_value, prev_net_value_date

    async def fetch(self, fund_code: str, use_cache: bool = True) -> DataSourceResult:
        """
        获取单个基金数据

        缓存策略：
        1. 优先从数据库读取每日缓存（5分钟过期）
        2. 数据库缓存过期时，从 API 获取并更新数据库
        3. 最后回退到内存/文件缓存

        Args:
            fund_code: 基金代码 (6位数字)
            use_cache: 是否使用缓存

        Returns:
            DataSourceResult: 包含基金数据的结果
        """
        if not self._validate_fund_code(fund_code):
            return DataSourceResult(
                success=False,
                error=f"无效的基金代码: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        today = time.strftime("%Y-%m-%d")
        cache_key = f"fund:{self.name}:{fund_code}"

        # 1. 优先从数据库读取每日缓存（5分钟过期）
        if use_cache:
            daily_dao = get_daily_cache_dao()
            if not daily_dao.is_expired(fund_code):
                cached_daily = daily_dao.get_latest(fund_code)
                if cached_daily:
                    # 获取基金类型（从基本信息表）
                    fund_type = ""
                    basic_info = get_basic_info_db(fund_code)
                    if basic_info:
                        fund_type = basic_info.get("type", "") or ""

                    # 获取上一交易日净值（用于折线图基准线）
                    prev_net_value, prev_net_value_date = await self._get_prev_net_value(fund_code)

                    # 优先使用 estimate_time，如果为空则回退到 date
                    estimate_time = cached_daily.estimate_time or cached_daily.date

                    # 构建返回数据格式
                    result_data = {
                        "fund_code": fund_code,
                        "name": basic_info.get("name", "") if basic_info else "",
                        "type": fund_type,
                        "net_value_date": cached_daily.date,
                        "unit_net_value": cached_daily.unit_net_value,
                        "prev_net_value": prev_net_value,
                        "prev_net_value_date": prev_net_value_date,
                        "estimated_net_value": cached_daily.estimated_value,
                        "estimated_growth_rate": cached_daily.change_rate,
                        "estimate_time": estimate_time,
                        "has_real_time_estimate": cached_daily.estimated_value is not None,
                        "from_cache": "database",
                    }
                    return DataSourceResult(
                        success=True,
                        data=result_data,
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code, "cache": "database"},
                    )

        # 2. 检查内存/文件缓存
        if use_cache:
            cache = get_fund_cache()
            cached_value, cache_type = await cache.get(cache_key)
            if cached_value is not None:
                cached_value["from_cache"] = cache_type
                return DataSourceResult(
                    success=True,
                    data=cached_value,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code, "cache": cache_type},
                )

        # 3. 从 API 获取数据
        for attempt in range(self.max_retries):
            try:
                # 直接调用异步方法
                result = await self._fetch_fund_data(fund_code)

                if result.success:
                    self._record_success()

                    # 写入数据库每日缓存
                    daily_dao = get_daily_cache_dao()
                    daily_dao.save_daily_from_fund_data(fund_code, result.data)

                    # 保存基金基本信息到数据库（使用已推断的类型）
                    save_basic_info_to_db(
                        fund_code,
                        {
                            "short_name": result.data.get("name", ""),
                            "name": result.data.get("name", ""),
                            "type": result.data.get("type", ""),
                            "net_value": result.data.get("unit_net_value"),
                            "net_value_date": result.data.get("net_value_date", ""),
                        },
                    )

                    # 写入内存/文件缓存
                    cache = get_fund_cache()
                    await cache.set(cache_key, result.data)

                    # 保存日内分时数据到数据库缓存
                    intraday_data = result.data.get("intraday", [])
                    if intraday_data:
                        intraday_dao = get_intraday_cache_dao()
                        intraday_dao.save_intraday(fund_code, today, intraday_data)

                    result.data["from_cache"] = "api"
                    return result
                else:
                    # 如果失败且还有重试次数，刷新 token 后重试
                    if attempt < self.max_retries - 1:
                        await self._refresh_csrf_token()
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    return result

            except Exception as e:
                logger.error(f"获取基金数据异常: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue

        return DataSourceResult(
            success=False,
            error=f"获取基金数据失败，已重试 {self.max_retries} 次",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code},
        )

    async def _fetch_fund_data(self, fund_code: str) -> DataSourceResult:
        """获取基金数据（带并发控制）"""
        # 使用 semaphore 限制并发数
        async with self._get_semaphore():
            return await self._do_fetch_fund_data(fund_code)

    async def _do_fetch_fund_data(self, fund_code: str) -> DataSourceResult:
        """实际获取基金数据的实现"""
        # 1. 获取基金基本信息（fund_key 和 fund_name）
        search_url = f"{self.BASE_URL}/api/fund/searchFund?_csrf={type(self)._csrf_token}"
        search_response = await type(self)._client.post(
            search_url, json={"fundCode": fund_code}, timeout=self.timeout
        )

        if not search_response.is_success:
            return DataSourceResult(
                success=False,
                error=f"搜索基金失败: {search_response.status_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        search_data = search_response.json()
        if not search_data.get("success"):
            return DataSourceResult(
                success=False,
                error=f"基金不存在: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        fund_info = search_data.get("fundInfo", {})
        fund_key = fund_info.get("key")
        fund_name = fund_info.get("fundName", f"基金 {fund_code}")

        # 2. 获取日内估值数据
        today = time.strftime("%Y-%m-%d")
        intraday_url = (
            f"{self.BASE_URL}/api/fund/queryFundEstimateIntraday?_csrf={type(self)._csrf_token}"
        )
        intraday_response = await type(self)._client.post(
            intraday_url,
            json={
                "startTime": today,
                "endTime": today,
                "limit": 200,
                "productId": fund_key,
                "format": True,
                "source": "WEALTHBFFWEB",
            },
            timeout=self.timeout,
        )

        if not intraday_response.is_success:
            return DataSourceResult(
                success=False,
                error=f"获取日内数据失败: {intraday_response.status_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        intraday_data = intraday_response.json()
        intraday_list = intraday_data.get("list", [])

        # 解析数据
        if intraday_list:
            latest = intraday_list[-1]
            estimate_value = float(latest.get("forecastNetValue", 0))
            growth_rate = float(latest.get("forecastGrowth", 0)) * 100
            estimate_time = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(latest.get("time", 0) / 1000)
            )
        else:
            estimate_value = None
            growth_rate = 0.0
            estimate_time = ""

        # 4. 如果日内数据为空，尝试从 search 结果中获取 dayOfGrowth（QDII 基金会有这个字段）
        day_of_growth = fund_info.get("dayOfGrowth", "")
        if not intraday_list and day_of_growth:
            # 解析 "5.59%" -> 5.59
            try:
                growth_rate = float(day_of_growth.rstrip('%'))
            except (ValueError, AttributeError):
                growth_rate = 0.0

        # 3. 获取最新净值信息
        # 注意：fund123 的 netValue 字段不是真正的已发布净值，需要从外部数据源获取
        # 重要：净值和净值日期必须来自同一数据源，确保数据关联正确
        # 天天基金接口的 jzrq 是"估值基准日期"（上一交易日），而非"最新确认净值日期"
        # 因此优先从 akshare 获取净值和净值日期，天天基金仅用于实时估值
        net_value = None
        net_date = ""

        # 1. 检查净值缓存是否有效（净值日期是否为最新交易日）
        cache_valid, cached_date, cached_value = _is_net_value_cache_valid(fund_code)
        if cache_valid and cached_date and cached_value is not None:
            # 缓存有效，直接使用缓存的净值数据
            net_value = cached_value
            net_date = cached_date
            logger.debug(
                f"使用净值缓存: {fund_code} -> {net_value}, 日期: {net_date}"
            )
        else:
            # 缓存无效或不存在，从 akshare 获取最新净值并更新缓存
            try:
                loop = asyncio.get_running_loop()
                history_result = await loop.run_in_executor(
                    None, lambda: _get_net_value_date_from_akshare(fund_code)
                )
                if history_result:
                    ak_net_date, ak_nav = history_result
                    if ak_nav and ak_net_date:
                        net_value = ak_nav
                        net_date = ak_net_date
                        logger.debug(f"从 akshare 获取净值: {fund_code} -> {net_value}, 日期: {net_date}")
                        # 更新数据库缓存
                        _update_net_value_cache(fund_code, net_value, net_date)
            except Exception as e:
                logger.warning(f"从 akshare 获取净值失败: {fund_code} - {e}")

            # 2. 如果 akshare 失败，尝试从天天基金获取（备用方案）
            # 注意：天天基金的 jzrq 是估值基准日期，可能不是最新净值日期
            if not net_date or net_value is None:
                try:
                    tiantian_url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js?rt={int(time.time() * 1000)}"
                    response = await self._get_tiantian_client().get(tiantian_url)
                    if response.is_success:
                        text = response.text.strip()
                        # 检查空响应（基金不支持）
                        if text not in ("jsonpgz();", "jsonpgz()"):
                            match = re.search(r'jsonpgz\((.+)\);?', text)
                            if match:
                                tiantian_data = json.loads(match.group(1))
                                tiantian_net_date = tiantian_data.get("jzrq", "")
                                tiantian_net_value = self._safe_float(tiantian_data.get("dwjz"))
                                if tiantian_net_date and tiantian_net_value is not None:
                                    net_date = tiantian_net_date
                                    net_value = tiantian_net_value
                                    logger.debug(
                                        f"从天天基金获取净值（备用）: {fund_code} -> "
                                        f"{net_value}, 日期: {net_date}"
                                    )
                except Exception as e:
                    logger.warning(f"从天天基金获取净值失败: {fund_code} - {e}")

            # 3. 最后尝试使用旧缓存（降级方案）
            if not net_date or net_value is None:
                if cached_date and cached_value is not None:
                    net_date = cached_date
                    net_value = cached_value
                    logger.debug(
                        f"使用旧缓存（降级）: {fund_code} -> {net_value}, 日期: {net_date}"
                    )
                else:
                    # 尝试从数据库每日缓存获取
                    try:
                        daily_dao = get_daily_cache_dao()
                        latest_record = daily_dao.get_latest(fund_code)
                        if latest_record and latest_record.date:
                            net_date = latest_record.date
                            if latest_record.unit_net_value:
                                net_value = latest_record.unit_net_value
                                logger.debug(f"从数据库缓存获取净值（兜底）: {fund_code} -> {net_value}, 日期: {net_date}")
                    except Exception as e:
                        logger.warning(f"从数据库获取净值日期失败: {e}")
        # 获取基金类型（优先从 akshare 获取并缓存到数据库）
        fund_type = ""
        basic_info = get_basic_info_db(fund_code)
        if basic_info:
            fund_type = basic_info.get("type", "") or ""

        # 如果数据库中没有类型，从 akshare 获取（首次获取时）
        if not fund_type:
            # get_fund_basic_info 会调用 akshare 获取类型并保存到数据库
            fund_info_result = get_fund_basic_info(fund_code)
            if fund_info_result:
                _, fund_type = fund_info_result

        # 备选方案：从基金名称中识别（akshare 获取失败时）
        if not fund_type:
            fund_type = _infer_fund_type_from_name(fund_name)

        # 判断是否有实时估值
        # QDII 基金和投资海外的 FOF 无实时估值，因为它们投资海外市场，净值更新延迟
        # ETF-联接和普通 FOF 基金有实时估值，因为它们跟踪的底层资产是国内基金
        has_real_time = _has_real_time_estimate(fund_type, fund_name) and estimate_value is not None

        # 获取上一交易日净值（用于折线图基准线）
        prev_net_value, prev_net_value_date = await self._get_prev_net_value(fund_code)

        result_data = {
            "fund_code": fund_code,
            "name": fund_name,
            "type": fund_type,
            "net_value_date": net_date,
            "unit_net_value": net_value,
            "prev_net_value": prev_net_value,
            "prev_net_value_date": prev_net_value_date,
            "estimated_net_value": estimate_value,
            "estimated_growth_rate": growth_rate if growth_rate else None,
            "estimate_time": estimate_time,
            "has_real_time_estimate": has_real_time,
            "intraday": [
                {
                    "time": time.strftime("%H:%M", time.localtime(item.get("time", 0) / 1000)),
                    "price": float(item.get("forecastNetValue", 0)),
                    "change": round(float(item.get("forecastGrowth", 0)) * 100, 4),
                }
                for item in intraday_list
            ],
        }

        return DataSourceResult(
            success=True,
            data=result_data,
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code},
        )

    async def fetch_batch(self, fund_codes: list[str]) -> list[DataSourceResult]:
        """
        批量获取基金数据

        Args:
            fund_codes: 基金代码列表

        Returns:
            List[DataSourceResult]: 每个基金的结果列表
        """

        async def fetch_one(code: str) -> DataSourceResult:
            return await self.fetch(code)

        tasks = [fetch_one(code) for code in fund_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_codes[i]},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def _validate_fund_code(self, fund_code: str) -> bool:
        """验证基金代码格式"""
        return bool(re.match(r"^\d{6}$", str(fund_code)))

    async def fetch_intraday(self, fund_code: str, use_cache: bool = True) -> DataSourceResult:
        """
        获取基金日内分时数据

        缓存策略：
        1. 优先从 SQLite 数据库读取（60秒过期）
        2. 数据库缓存过期时，从 API 获取并更新数据库
        3. 最后回退到内存/文件缓存

        Args:
            fund_code: 基金代码 (6位数字)
            use_cache: 是否使用缓存

        Returns:
            DataSourceResult: 包含日内分时数据的结果
        """
        if not self._validate_fund_code(fund_code):
            return DataSourceResult(
                success=False,
                error=f"无效的基金代码: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        cache_key = f"fund:{self.name}:{fund_code}:intraday"
        today = time.strftime("%Y-%m-%d")

        # 1. 优先从数据库读取日内分时缓存（60秒过期）
        if use_cache:
            intraday_dao = get_intraday_cache_dao()
            if not intraday_dao.is_expired(fund_code, today):
                cached_records = intraday_dao.get_intraday(fund_code, today)
                if cached_records:
                    # 从数据库记录构建返回数据
                    intraday_points = [
                        {"time": record.time, "price": record.price, "change": record.change_rate}
                        for record in cached_records
                    ]
                    result_data = {
                        "fund_code": fund_code,
                        "name": "",
                        "date": today,
                        "data": intraday_points,
                        "count": len(intraday_points),
                        "from_cache": "database",
                        "cache_expired": False,
                    }
                    return DataSourceResult(
                        success=True,
                        data=result_data,
                        timestamp=time.time(),
                        source=self.name,
                        metadata={
                            "fund_code": fund_code,
                            "cache": "database",
                            "cache_expired": False,
                        },
                    )

        # 2. 检查内存/文件缓存
        if use_cache:
            cache = get_fund_cache()
            cached_value, cache_type = await cache.get(cache_key)
            if cached_value is not None:
                cached_value["from_cache"] = cache_type
                cached_value["cache_expired"] = True
                return DataSourceResult(
                    success=True,
                    data=cached_value,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code, "cache": cache_type, "cache_expired": True},
                )

        for attempt in range(self.max_retries):
            try:
                # 直接调用异步方法
                result = await self._fetch_intraday_data(fund_code)

                if result.success:
                    self._record_success()

                    # 写入数据库缓存
                    intraday_dao = get_intraday_cache_dao()
                    intraday_dao.save_intraday(fund_code, today, result.data.get("data", []))

                    # 写入内存/文件缓存（缓存时间较短，5分钟）
                    cache = get_fund_cache()
                    await cache.set(cache_key, result.data, ttl_seconds=300)

                    result.data["from_cache"] = "api"
                    result.data["cache_expired"] = False
                    return result
                else:
                    if attempt < self.max_retries - 1:
                        await self._refresh_csrf_token()
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    return result

            except Exception as e:
                logger.error(f"获取日内数据异常: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue

        return DataSourceResult(
            success=False,
            error=f"获取日内数据失败，已重试 {self.max_retries} 次",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code},
        )

    async def _fetch_intraday_data(self, fund_code: str) -> DataSourceResult:
        """获取基金日内分时数据（带并发控制）"""
        # 使用 semaphore 限制并发数
        async with self._get_semaphore():
            return await self._do_fetch_intraday_data(fund_code)

    async def _do_fetch_intraday_data(self, fund_code: str) -> DataSourceResult:
        """实际获取基金日内分时数据的实现"""
        # 1. 获取基金基本信息（fund_key 和 fund_name）
        search_url = f"{self.BASE_URL}/api/fund/searchFund?_csrf={type(self)._csrf_token}"
        search_response = await type(self)._client.post(
            search_url, json={"fundCode": fund_code}, timeout=self.timeout
        )

        if not search_response.is_success:
            return DataSourceResult(
                success=False,
                error=f"搜索基金失败: {search_response.status_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        search_data = search_response.json()
        if not search_data.get("success"):
            return DataSourceResult(
                success=False,
                error=f"基金不存在: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        fund_info = search_data.get("fundInfo", {})
        fund_key = fund_info.get("key")
        fund_name = fund_info.get("fundName", f"基金 {fund_code}")

        # 2. 获取日内估值数据
        today = time.strftime("%Y-%m-%d")
        intraday_url = (
            f"{self.BASE_URL}/api/fund/queryFundEstimateIntraday?_csrf={type(self)._csrf_token}"
        )
        intraday_response = await type(self)._client.post(
            intraday_url,
            json={
                "startTime": today,
                "endTime": today,
                "limit": 200,
                "productId": fund_key,
                "format": True,
                "source": "WEALTHBFFWEB",
            },
            timeout=self.timeout,
        )

        if not intraday_response.is_success:
            return DataSourceResult(
                success=False,
                error=f"获取日内数据失败: {intraday_response.status_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        intraday_data = intraday_response.json()
        intraday_list = intraday_data.get("list", [])

        # 解析数据，返回前端直接可用的格式
        intraday_points = []
        if intraday_list:
            for item in intraday_list:
                time_ms = item.get("time", 0)
                # 将毫秒时间戳转换为 HH:mm 格式
                time_str = time.strftime("%H:%M", time.localtime(time_ms / 1000))
                intraday_points.append(
                    {
                        "time": time_str,
                        "price": float(item.get("forecastNetValue", 0)),
                        "change": round(float(item.get("forecastGrowth", 0)) * 100, 4),
                    }
                )

        result_data = {
            "fund_code": fund_code,
            "name": fund_name,
            "date": today,
            "data": intraday_points,
            "count": len(intraday_points),
        }

        return DataSourceResult(
            success=True,
            data=result_data,
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code},
        )

    async def fetch_intraday_by_date(self, fund_code: str, date: str) -> DataSourceResult:
        """
        获取指定日期的基金日内分时数据（仅从缓存读取）

        Args:
            fund_code: 基金代码 (6位数字)
            date: 日期 (YYYY-MM-DD 格式)

        Returns:
            DataSourceResult: 包含日内分时数据的结果
        """
        if not self._validate_fund_code(fund_code):
            return DataSourceResult(
                success=False,
                error=f"无效的基金代码: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        # 从数据库缓存读取指定日期的数据
        intraday_dao = get_intraday_cache_dao()
        cached_records = intraday_dao.get_intraday(fund_code, date)

        if cached_records:
            intraday_points = [
                {"time": record.time, "price": record.price, "change": record.change_rate}
                for record in cached_records
            ]
            result_data = {
                "fund_code": fund_code,
                "name": "",
                "date": date,
                "data": intraday_points,
                "count": len(intraday_points),
                "from_cache": "database",
            }
            return DataSourceResult(
                success=True,
                data=result_data,
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code, "date": date, "cache": "database"},
            )

        return DataSourceResult(
            success=False,
            error=f"指定日期 {date} 的数据不存在",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code, "date": date},
        )

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            bool: 健康状态
        """
        try:
            token = await self._get_csrf_token()
            return token is not None
        except Exception:
            return False

    def _safe_float(self, value: Any) -> float | None:
        """安全转换为浮点数"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def close(self):
        """关闭全局 AsyncClient"""
        if type(self)._client is not None:
            await type(self)._client.aclose()
            type(self)._client = None
            type(self)._csrf_token = None
        if type(self)._tiantian_client is not None:
            await type(self)._tiantian_client.aclose()
            type(self)._tiantian_client = None


class TushareFundSource(DataSource):
    """Tushare 基金数据源

    提供国内基金净值数据，需要 Tushare Token。
    API: https://tushare.pro/

    Token 获取: https://tushare.pro/register
    免费版有一定调用限制
    """

    def __init__(self, token: str | None = None, timeout: float = 10.0):
        super().__init__(name="tushare_fund", source_type=DataSourceType.FUND, timeout=timeout)
        self._token = token or os.environ.get("TUSHARE_TOKEN")
        self._pro = None
        if self._token:
            self._init_pro()

    def _init_pro(self):
        if not self._token:
            return
        try:
            import tushare as ts

            ts.set_token(self._token)
            self._pro = ts.pro_api()
        except ImportError:
            raise ImportError("请安装 tushare 库: pip install tushare")

    async def fetch(self, fund_code: str) -> DataSourceResult:
        self._request_count += 1
        if not self._token or not self._pro:
            self._error_count += 1
            return DataSourceResult(
                success=False,
                error="Tushare Token 未配置。请设置 TUSHARE_TOKEN 环境变量或传入 token 参数。访问 https://tushare.pro/register 注册获取 Token。",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, lambda: self._fetch_fund_nav(fund_code))
            return result
        except Exception as e:
            self._error_count += 1
            return DataSourceResult(
                success=False,
                error=str(e),
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

    def _fetch_fund_nav(self, fund_code: str) -> DataSourceResult:
        try:
            df = self._pro.fund_nav(fund_code=fund_code)
            if df is None or df.empty:
                return DataSourceResult(
                    success=False,
                    error=f"未找到基金数据: {fund_code}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            latest = df.iloc[-1]
            result_data = {
                "fund_code": fund_code,
                "nav": float(latest.get("nav", 0)),
                "acc_nav": float(latest.get("acc_nav", 0)),
                "date": latest.get("nav_date", ""),
            }

            return DataSourceResult(
                success=True,
                data=result_data,
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )
        except Exception as e:
            return DataSourceResult(
                success=False,
                error=str(e),
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

    async def fetch_batch(self, fund_codes: list[str]) -> list[DataSourceResult]:
        async def fetch_one(code: str) -> DataSourceResult:
            return await self.fetch(code)

        tasks = [fetch_one(code) for code in fund_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_codes[i]},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results


# 导入缓存策略模块
from src.datasources.fund.cache_strategy import (
    CacheLockManager,
    CacheLockTimeoutError,
    CacheResult,
    FundCacheStrategy,
    get_fund_data_with_cache,
)

# 缓存策略单例
_cache_strategy: FundCacheStrategy | None = None


def get_cache_strategy() -> FundCacheStrategy:
    """
    获取缓存策略单例

    Returns:
        FundCacheStrategy: 缓存策略实例
    """
    global _cache_strategy
    if _cache_strategy is None:
        # 复用现有的 DatabaseManager 实例，避免创建多个数据库连接
        db_manager = get_basic_info_db()
        _cache_strategy = FundCacheStrategy(db_manager)
    return _cache_strategy


__all__ = [
    "FundDataSource",
    "SinaFundDataSource",
    "FundHistorySource",
    "FundHistoryYFinanceSource",
    "Fund123DataSource",
    "TushareFundSource",
    "get_fund_cache",
    "get_fund_cache_stats",
    "get_intraday_cache_dao",
    "get_daily_cache_dao",
    "get_basic_info_dao",
    "get_basic_info_db",
    "save_basic_info_to_db",
    # 缓存策略相关
    "CacheLockManager",
    "CacheLockTimeoutError",
    "CacheResult",
    "FundCacheStrategy",
    "get_cache_strategy",
    "get_fund_data_with_cache",
]
