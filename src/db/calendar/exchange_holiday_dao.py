# -*- coding: UTF-8 -*-
from __future__ import annotations

from typing import TYPE_CHECKING

"""交易所节假日数据访问对象

提供交易所节假日的存储和查询功能。
"""

from datetime import datetime

from src.db.models import ExchangeHoliday

if TYPE_CHECKING:
    from src.db.database import DatabaseManager


class ExchangeHolidayDAO:
    """交易所节假日数据访问对象"""

    def __init__(self, db: DatabaseManager):  # noqa: F821
        self.db = db

    def add_holiday(self, market: str, holiday_date: str, holiday_name: str | None = None) -> bool:
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO exchange_holidays
                    (market, holiday_date, holiday_name, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, 1, ?, ?)
                    """,
                    (market, holiday_date, holiday_name, now, now),
                )
                return True
            except Exception:
                cursor.execute(
                    """
                    UPDATE exchange_holidays
                    SET holiday_name = ?, is_active = 1, updated_at = ?
                    WHERE market = ? AND holiday_date = ?
                    """,
                    (holiday_name, now, market, holiday_date),
                )
                return True

    def add_holidays(self, holidays: list[ExchangeHoliday]) -> int:
        now = datetime.now().isoformat()
        count = 0
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for h in holidays:
                try:
                    cursor.execute(
                        """
                        INSERT INTO exchange_holidays
                        (market, holiday_date, holiday_name, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, 1, ?, ?)
                        """,
                        (h.market, h.holiday_date, h.holiday_name, now, now),
                    )
                    count += 1
                except Exception:
                    cursor.execute(
                        """
                        UPDATE exchange_holidays
                        SET holiday_name = ?, is_active = 1, updated_at = ?
                        WHERE market = ? AND holiday_date = ?
                        """,
                        (h.holiday_name, now, h.market, h.holiday_date),
                    )
                    count += 1
        return count

    def get_holidays(
        self, market: str | None = None, year: int | None = None, active_only: bool = True
    ) -> list[ExchangeHoliday]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT id, market, holiday_date, holiday_name, is_active, created_at, updated_at FROM exchange_holidays WHERE 1=1"
            params = []
            if market:
                query += " AND market = ?"
                params.append(market)
            if active_only:
                query += " AND is_active = 1"
            query += " ORDER BY holiday_date"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            result = []
            for row in rows:
                h = ExchangeHoliday(
                    id=row[0],
                    market=row[1],
                    holiday_date=row[2],
                    holiday_name=row[3],
                    is_active=row[4],
                    created_at=row[5],
                    updated_at=row[6],
                )
                if year:
                    try:
                        if h.holiday_date.startswith(str(year)):
                            result.append(h)
                    except Exception:
                        pass
                else:
                    result.append(h)
            return result

    def soft_delete(self, holiday_id: int) -> bool:
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE exchange_holidays SET is_active = 0, updated_at = ? WHERE id = ?",
                (now, holiday_id),
            )
            return cursor.rowcount > 0

    def restore(self, holiday_id: int) -> bool:
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE exchange_holidays SET is_active = 1, updated_at = ? WHERE id = ?",
                (now, holiday_id),
            )
            return cursor.rowcount > 0

    def delete(self, holiday_id: int) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM exchange_holidays WHERE id = ?", (holiday_id,))
            return cursor.rowcount > 0

    def clear_all(self, market: str | None = None) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if market:
                cursor.execute("DELETE FROM exchange_holidays WHERE market = ?", (market,))
            else:
                cursor.execute("DELETE FROM exchange_holidays")
            return cursor.rowcount
