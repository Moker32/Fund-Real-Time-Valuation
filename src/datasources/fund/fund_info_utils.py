"""基金信息工具模块

包含基金信息获取、类型推断、缓存管理等工具函数。
"""

import logging
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.datasources.trading_calendar_source import TradingCalendarSource
from zoneinfo import ZoneInfo

from src.db.database import DatabaseManager

from .cache_strategy import FundCacheStrategy
from .fund_cache_helpers import (
    _fund_info_cache,
    _fund_info_cache_ttl,
    _fund_info_hit_count,
    _fund_info_miss_count,
    get_basic_info_dao,
    get_fund_cache,
)

logger = logging.getLogger(__name__)

# 缓存策略单例
_cache_strategy: FundCacheStrategy | None = None
# 交易日历源单例
_trading_calendar_source: "TradingCalendarSource | None" = None


def get_cache_strategy() -> FundCacheStrategy:
    """
    获取缓存策略单例

    Returns:
        FundCacheStrategy: 缓存策略实例
    """
    global _cache_strategy
    if _cache_strategy is None:
        # 使用 DatabaseManager 实例
        db_manager = DatabaseManager()
        _cache_strategy = FundCacheStrategy(db_manager)
    return _cache_strategy


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
    - 类型未知时：从名称推断，仍无法判断时保守返回 True

    Args:
        fund_type: 基金类型
        fund_name: 基金名称

    Returns:
        bool: 是否有实时估值
    """
    # 类型为空时，尝试从名称推断
    effective_type = fund_type
    if not effective_type and fund_name:
        effective_type = _infer_fund_type_from_name(fund_name)

    # 仍无法判断类型时，保守返回 True（大多数基金有实时估值）
    if not effective_type:
        return True

    # QDII 基金无实时估值（包括 QDII-商品、QDII-股票等子类型）
    if effective_type.startswith("QDII"):
        return False

    # FOF 基金需要进一步判断是否投资海外
    if effective_type == "FOF":
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
    tz = ZoneInfo("Asia/Shanghai")
    now = datetime.now(tz)
    return now.date()


def _is_after_market_close() -> bool:
    """
    判断当前是否在收盘后（15:00 之后）

    Returns:
        bool: True 表示已收盘，False 表示未收盘或无法判断
    """
    from datetime import time as time_type

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
            # 无法获取交易日，无法验证缓存有效性，应该强制刷新
            return (False, cached_date, cached_value)

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
