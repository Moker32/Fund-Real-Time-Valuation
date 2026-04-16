# -*- coding: UTF-8 -*-
from __future__ import annotations

"""交易日历数据访问对象

提供交易日历的存储和查询功能。
"""

from datetime import datetime

from src.db.models import TradingCalendarRecord


class TradingCalendarDAO:
    """交易日历数据访问对象"""

    def __init__(self, db: DatabaseManager):  # noqa: F821
        self.db = db

    def save_calendar(self, market: str, year: int, days: list[TradingCalendarRecord]) -> bool:
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM trading_calendar_cache WHERE market = ? AND year = ?", (market, year)
            )
            for i, day in enumerate(days):
                cursor.execute(
                    """
                    INSERT INTO trading_calendar_cache
                    (market, year, day_of_year, is_trading_day, holiday_name, is_makeup_day, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        market,
                        year,
                        i + 1,
                        1 if day.is_trading_day else 0,
                        day.holiday_name,
                        1 if day.is_makeup_day else 0,
                        now,
                    ),
                )
            return True

    def get_calendar(self, market: str, year: int) -> list[TradingCalendarRecord] | None:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT market, year, day_of_year, is_trading_day, holiday_name, is_makeup_day FROM trading_calendar_cache WHERE market = ? AND year = ? ORDER BY day_of_year",
                (market, year),
            )
            rows = cursor.fetchall()
            if not rows:
                return None
            return [
                TradingCalendarRecord(
                    market=row[0],
                    year=row[1],
                    is_trading_day=bool(row[3]),
                    holiday_name=row[4],
                    is_makeup_day=bool(row[5]),
                )
                for row in rows
            ]

    def clear_cache(self, market: str | None = None) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if market:
                cursor.execute("DELETE FROM trading_calendar_cache WHERE market = ?", (market,))
            else:
                cursor.execute("DELETE FROM trading_calendar_cache")
            return cursor.rowcount
