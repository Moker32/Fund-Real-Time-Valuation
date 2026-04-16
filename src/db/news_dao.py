# -*- coding: UTF-8 -*-
from __future__ import annotations

from typing import TYPE_CHECKING

"""新闻缓存数据访问对象

提供新闻缓存的存储和查询功能。
"""

from datetime import datetime

from src.db.models import NewsRecord

if TYPE_CHECKING:
    from src.db.database import DatabaseManager


class NewsDAO:
    """新闻缓存数据访问对象"""

    def __init__(self, db_manager: DatabaseManager):  # noqa: F821
        self.db = db_manager

    def add_news(
        self,
        title: str,
        url: str,
        source: str,
        category: str,
        publish_time: str,
        content: str = "",
    ) -> bool:
        """添加新闻记录"""
        fetched_at = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO news_cache
                    (title, url, source, category, publish_time, content, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (title, url, source, category, publish_time, content, fetched_at),
                )
                return True
            except Exception:
                return False

    def get_news(self, category: str | None = None, limit: int = 50) -> list[NewsRecord]:
        """获取新闻列表"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute(
                    """
                    SELECT * FROM news_cache
                    WHERE category = ?
                    ORDER BY publish_time DESC
                    LIMIT ?
                """,
                    (category, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM news_cache
                    ORDER BY publish_time DESC
                    LIMIT ?
                """,
                    (limit,),
                )
            return [NewsRecord(**row) for row in cursor.fetchall()]

    def cleanup_old_news(self, hours: int = 24) -> int:
        """清理过期新闻"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM news_cache
                WHERE fetched_at < datetime('now', ?)
            """,
                (f"-{hours} hours",),
            )
            return cursor.rowcount
