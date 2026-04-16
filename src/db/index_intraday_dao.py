# -*- coding: UTF-8 -*-
"""指数日内分时缓存数据访问对象

提供指数日内分时数据的存储和查询功能。
支持 60 秒缓存过期机制，用于减少 API 调用。
"""

from datetime import datetime
from typing import Any

from src.db.models import IndexIntradayRecord


class IndexIntradayCacheDAO:
    """指数日内分时缓存数据访问对象

    提供指数日内分时数据的存储和查询功能。
    支持 60 秒缓存过期机制，用于减少 API 调用。
    """

    # 默认缓存过期时间（秒）
    DEFAULT_CACHE_TTL = 60

    def __init__(self, db_manager: "DatabaseManager", cache_ttl: int = DEFAULT_CACHE_TTL):
        self.db = db_manager
        self.cache_ttl = cache_ttl

    def save_intraday(self, index_type: str, date: str, data: list[dict]) -> bool:
        """保存指数日内分时数据到缓存

        Args:
            index_type: 指数类型
            date: 日期 (YYYY-MM-DD)
            data: 分时数据列表，每项包含 time, price, change

        Returns:
            bool: 是否保存成功
        """
        if not data:
            return False

        fetched_at = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # INSERT OR REPLACE 内部处理唯一约束冲突，无需 try/except
            for item in data:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO index_intraday_cache
                    (index_type, date, time, price, change_rate, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        index_type,
                        date,
                        item.get("time", ""),
                        item.get("price", 0.0),
                        item.get("change"),
                        fetched_at,
                    ),
                )
            return len(data) > 0

    def get_intraday(self, index_type: str, date: str | None = None) -> list[IndexIntradayRecord]:
        """获取指数日内分时数据

        Args:
            index_type: 指数类型
            date: 日期 (YYYY-MM-DD)，None 表示最新

        Returns:
            IndexIntradayRecord 列表
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute(
                    """
                    SELECT * FROM index_intraday_cache
                    WHERE index_type = ? AND date = ?
                    ORDER BY time ASC
                """,
                    (index_type, date),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM index_intraday_cache
                    WHERE index_type = ?
                    ORDER BY date DESC, time ASC
                """,
                    (index_type,),
                )
            return [IndexIntradayRecord(**row) for row in cursor.fetchall()]

    def is_expired(self, index_type: str, date: str | None = None) -> bool:
        """检查缓存是否过期

        Args:
            index_type: 指数类型
            date: 日期 (YYYY-MM-DD)

        Returns:
            bool: True 表示已过期或不存在，False 表示有效
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute(
                    """
                    SELECT fetched_at FROM index_intraday_cache
                    WHERE index_type = ? AND date = ?
                    LIMIT 1
                """,
                    (index_type, date),
                )
            else:
                cursor.execute(
                    """
                    SELECT fetched_at FROM index_intraday_cache
                    WHERE index_type = ?
                    ORDER BY date DESC, fetched_at DESC
                    LIMIT 1
                """,
                    (index_type,),
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

    def clear_cache(self, index_type: str, date: str | None = None) -> int:
        """清除指定指数的缓存

        Args:
            index_type: 指数类型
            date: 日期 (YYYY-MM-DD)，None 表示全部

        Returns:
            int: 删除的记录数
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute(
                    "DELETE FROM index_intraday_cache WHERE index_type = ? AND date = ?",
                    (index_type, date),
                )
            else:
                cursor.execute(
                    "DELETE FROM index_intraday_cache WHERE index_type = ?",
                    (index_type,),
                )
            return cursor.rowcount

    def get_cache_info(self, index_type: str, date: str | None = None) -> dict:
        """获取缓存信息

        Returns:
            dict: 包含 count, last_fetched, expired 等信息
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute(
                    """
                    SELECT COUNT(*) as count, MAX(fetched_at) as last_fetched
                    FROM index_intraday_cache
                    WHERE index_type = ? AND date = ?
                """,
                    (index_type, date),
                )
            else:
                cursor.execute(
                    """
                    SELECT COUNT(*) as count, MAX(fetched_at) as last_fetched
                    FROM index_intraday_cache
                    WHERE index_type = ?
                """,
                    (index_type,),
                )
            row = cursor.fetchone()

            if row is None or row["count"] == 0:
                return {
                    "index_type": index_type,
                    "date": date,
                    "count": 0,
                    "last_fetched": None,
                    "expired": True,
                }

            # 直接从 last_fetched 计算过期状态，避免二次查询
            last_fetched = row["last_fetched"]
            try:
                fetched_time = datetime.fromisoformat(last_fetched.replace("Z", ""))
                elapsed_seconds = (datetime.now() - fetched_time).total_seconds()
                is_expired = elapsed_seconds > self.cache_ttl
            except (ValueError, TypeError):
                is_expired = True

            return {
                "index_type": index_type,
                "date": date,
                "count": row["count"],
                "last_fetched": last_fetched,
                "expired": is_expired,
            }
