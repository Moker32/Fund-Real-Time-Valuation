# -*- coding: UTF-8 -*-
"""基金日内分时缓存数据访问对象

提供基金日内分时数据的存储和查询功能。
支持 60 秒缓存过期机制，用于减少 API 调用。
"""

import logging
from datetime import datetime
from typing import Any

from src.db.models import FundIntradayRecord

logger = logging.getLogger(__name__)


class FundIntradayCacheDAO:
    """基金日内分时缓存数据访问对象

    提供基金日内分时数据的存储和查询功能。
    支持 60 秒缓存过期机制，用于减少 API 调用。
    """

    # 默认缓存过期时间（秒）- 0 表示禁用缓存
    DEFAULT_CACHE_TTL = 0

    def __init__(self, db_manager: "DatabaseManager", cache_ttl: int = DEFAULT_CACHE_TTL):
        """
        初始化日内分时缓存 DAO

        Args:
            db_manager: 数据库管理器实例
            cache_ttl: 缓存过期时间（秒），默认为 60 秒
        """
        self.db = db_manager
        self.cache_ttl = cache_ttl

    def save_intraday(self, fund_code: str, date: str, data: list[dict]) -> bool:
        """
        保存基金日内分时数据

        Args:
            fund_code: 基金代码
            date: 日期 (YYYY-MM-DD 格式)
            data: 日内分时数据列表，每个元素包含 time, price, change_rate

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
                    INSERT OR REPLACE INTO fund_intraday_cache
                    (fund_code, date, time, price, change_rate, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        fund_code,
                        date,
                        item.get("time", ""),
                        item.get("price", 0.0),
                        item.get("change"),
                        fetched_at,
                    ),
                )
            return len(data) > 0

    def get_intraday(self, fund_code: str, date: str | None = None) -> list[FundIntradayRecord]:
        """
        获取基金日内分时缓存数据

        Args:
            fund_code: 基金代码
            date: 可选的日期 (YYYY-MM-DD 格式)，不指定则返回最新的记录

        Returns:
            list[FundIntradayRecord]: 日内分时数据列表，按时间排序
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute(
                    """
                    SELECT * FROM fund_intraday_cache
                    WHERE fund_code = ? AND date = ?
                    ORDER BY time ASC
                """,
                    (fund_code, date),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM fund_intraday_cache
                    WHERE fund_code = ?
                    ORDER BY date DESC, time ASC
                """,
                    (fund_code,),
                )
            return [FundIntradayRecord(**row) for row in cursor.fetchall()]

    def is_expired(self, fund_code: str, date: str | None = None) -> bool:
        """
        检查缓存是否过期

        Args:
            fund_code: 基金代码
            date: 可选的日期 (YYYY-MM-DD 格式)

        Returns:
            bool: True 表示缓存已过期或不存在，False 表示缓存有效
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute(
                    """
                    SELECT fetched_at FROM fund_intraday_cache
                    WHERE fund_code = ? AND date = ?
                    LIMIT 1
                """,
                    (fund_code, date),
                )
            else:
                cursor.execute(
                    """
                    SELECT fetched_at FROM fund_intraday_cache
                    WHERE fund_code = ?
                    ORDER BY date DESC, fetched_at DESC
                    LIMIT 1
                """,
                    (fund_code,),
                )
            row = cursor.fetchone()

            if row is None:
                return True  # 不存在缓存，视为过期

            # 检查是否过期
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

    def clear_cache(self, fund_code: str, date: str | None = None) -> int:
        """
        清除指定基金的日内缓存

        Args:
            fund_code: 基金代码
            date: 可选的日期 (YYYY-MM-DD 格式)，不指定则清除该基金所有缓存

        Returns:
            int: 删除的记录数
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute(
                    "DELETE FROM fund_intraday_cache WHERE fund_code = ? AND date = ?",
                    (fund_code, date),
                )
            else:
                cursor.execute(
                    "DELETE FROM fund_intraday_cache WHERE fund_code = ?",
                    (fund_code,),
                )
            return cursor.rowcount

    def cleanup_expired_cache(self) -> int:
        """
        清理所有过期的日内缓存

        Returns:
            int: 删除的记录数
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM fund_intraday_cache
                WHERE fetched_at < datetime('now', ?)
            """,
                (f"-{self.cache_ttl} seconds",),
            )
            return cursor.rowcount

    def get_cache_info(self, fund_code: str, date: str | None = None) -> dict[str, Any]:
        """
        获取缓存信息

        Args:
            fund_code: 基金代码
            date: 可选的日期 (YYYY-MM-DD 格式)

        Returns:
            dict: 包含缓存信息的字典
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute(
                    """
                    SELECT COUNT(*) as count, MAX(fetched_at) as last_fetched
                    FROM fund_intraday_cache
                    WHERE fund_code = ? AND date = ?
                """,
                    (fund_code, date),
                )
            else:
                cursor.execute(
                    """
                    SELECT COUNT(*) as count, MAX(fetched_at) as last_fetched
                    FROM fund_intraday_cache
                    WHERE fund_code = ?
                """,
                    (fund_code,),
                )
            row = cursor.fetchone()

            if row is None or row["count"] == 0:
                return {
                    "fund_code": fund_code,
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
                "fund_code": fund_code,
                "date": date,
                "count": row["count"],
                "last_fetched": last_fetched,
                "expired": is_expired,
            }
