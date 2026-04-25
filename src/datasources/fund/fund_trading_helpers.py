"""基金交易日辅助模块

提供交易日判断、净值缓存等辅助功能。
"""

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.datasources.trading_calendar_source import TradingCalendarSource

from zoneinfo import ZoneInfo

from .fund_cache_helpers import get_basic_info_dao

logger = logging.getLogger(__name__)

# 交易日历源单例
_trading_calendar_source: "TradingCalendarSource | None" = None


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


def _is_net_value_cache_valid(fund_code: str) -> tuple[bool, str | None, float | None]:
    """
    检查净值缓存是否有效（净值日期是否为最新交易日）

    Args:
        fund_code: 基金代码

    Returns:
        tuple[bool, str | None, float | None]: (是否有效, 净值日期, 净值)
    """
    from .fund_info_db import get_basic_info_db

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
