"""板块数据源共享工具函数"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_holiday_cache: dict[int, set[str]] = {}


def _get_china_holidays_from_db(year: int) -> set[str]:
    """从数据库获取中国节假日集合"""
    if year in _holiday_cache:
        return _holiday_cache[year]
    try:
        from src.db.database import DatabaseManager

        dao = DatabaseManager().holiday_dao
        holidays = dao.get_holidays(market="china", year=year, active_only=True)
        holiday_dates = {h.holiday_date for h in holidays}
        _holiday_cache[year] = holiday_dates
        return holiday_dates
    except Exception:
        return set()


def is_trading_day(date: datetime) -> bool:
    """判断是否为交易日"""
    if date.weekday() >= 5:
        return False
    date_str = date.strftime("%Y-%m-%d")
    db_holidays = _get_china_holidays_from_db(date.year)
    if db_holidays:
        return date_str not in db_holidays
    from src.datasources.trading_calendar_source import TradingCalendarSource

    cal = TradingCalendarSource()
    return cal.is_trading_day("china", date)


def get_last_trading_day() -> datetime:
    """
    获取最近的一个交易日
    基于时间和节假日判断
    """
    now = datetime.now()

    # 情况1: 现在是交易日（周一到周五，且不是节假日）
    if is_trading_day(now):
        # 判断当前时间
        # A股交易时间: 9:30-11:30, 13:00-15:00
        if now.hour >= 15:
            # 15:00 后，当天交易结束
            # 但如果刚收盘，数据还是当天的
            return now
        elif now.hour >= 9:
            # 9:00-15:00 之间，交易时间
            return now
        else:
            # 9:00 之前，可能是盘前，数据可能是昨日的
            # 查找上一个交易日
            for days in range(1, 10):
                check_date = now - timedelta(days=days)
                if is_trading_day(check_date):
                    return check_date

    # 情况2: 现在不是交易日（周末或节假日）
    # 查找上一个交易日
    for days in range(1, 10):
        check_date = now - timedelta(days=days)
        if is_trading_day(check_date):
            return check_date

    # 如果都找不到，返回今天（兜底）
    return now
