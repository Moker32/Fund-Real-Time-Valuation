# -*- coding: UTF-8 -*-
"""商品日内分时缓存数据访问对象

提供商品日内分时数据的存储和查询功能。
支持 60 秒缓存过期机制，用于减少 yfinance API 调用。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.db.models import CommodityIntradayRecord

if TYPE_CHECKING:
    from src.db.database import DatabaseManager


class CommodityIntradayCacheDAO:
    """商品日内分时缓存数据访问对象"""

    DEFAULT_CACHE_TTL = 60

    def __init__(self, db_manager: DatabaseManager, cache_ttl: int = DEFAULT_CACHE_TTL):
        self.db = db_manager
        self.cache_ttl = cache_ttl

    def save_intraday(self, commodity_type: str, date: str, data: list[dict]) -> bool:
        """保存商品日内分时数据到缓存"""
        if not data:
            return False

        fetched_at = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for item in data:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO commodity_intraday_cache
                    (commodity_type, date, time, price, fetched_at)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        commodity_type,
                        date,
                        item.get("time", ""),
                        item.get("price", 0.0),
                        fetched_at,
                    ),
                )
            return len(data) > 0

    def get_intraday(self, commodity_type: str, date: str | None = None) -> list[CommodityIntradayRecord]:
        """获取商品日内分时数据"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute(
                    """
                    SELECT * FROM commodity_intraday_cache
                    WHERE commodity_type = ? AND date = ?
                    ORDER BY time ASC
                """,
                    (commodity_type, date),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM commodity_intraday_cache
                    WHERE commodity_type = ?
                    ORDER BY date DESC, time ASC
                """,
                    (commodity_type,),
                )
            return [CommodityIntradayRecord(**row) for row in cursor.fetchall()]

    def is_expired(self, commodity_type: str, date: str | None = None) -> bool:
        """检查缓存是否过期"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute(
                    """
                    SELECT fetched_at FROM commodity_intraday_cache
                    WHERE commodity_type = ? AND date = ?
                    LIMIT 1
                """,
                    (commodity_type, date),
                )
            else:
                cursor.execute(
                    """
                    SELECT fetched_at FROM commodity_intraday_cache
                    WHERE commodity_type = ?
                    ORDER BY date DESC, fetched_at DESC
                    LIMIT 1
                """,
                    (commodity_type,),
                )
            row = cursor.fetchone()

            if row is None:
                return True

            fetched_at = row["fetched_at"]
            if not fetched_at:
                return True

            try:
                fetched_time = datetime.fromisoformat(fetched_at.replace("Z", ""))
                now = datetime.now()
                elapsed_seconds = (now - fetched_time).total_seconds()
                return elapsed_seconds > self.cache_ttl
            except (ValueError, TypeError):
                return True

    def clear_cache(self, commodity_type: str, date: str | None = None) -> int:
        """清除指定商品的缓存"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute(
                    "DELETE FROM commodity_intraday_cache WHERE commodity_type = ? AND date = ?",
                    (commodity_type, date),
                )
            else:
                cursor.execute(
                    "DELETE FROM commodity_intraday_cache WHERE commodity_type = ?",
                    (commodity_type,),
                )
            return cursor.rowcount
