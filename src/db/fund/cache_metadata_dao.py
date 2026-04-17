# -*- coding: UTF-8 -*-
"""缓存元数据 DAO 模块

提供基金缓存状态的管理功能，支持缓存状态机实现。
"""

import logging
from datetime import datetime

from src.db.database import DatabaseManager
from src.db.models import CacheMetadata

logger = logging.getLogger(__name__)


class CacheMetadataDAO:
    """缓存元数据数据访问对象

    提供基金缓存状态的管理功能，支持缓存状态机实现。
    状态流转: unknown -> refreshing -> valid/stale/error
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化缓存元数据 DAO

        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager

    async def get_cache_status(self, fund_code: str) -> CacheMetadata | None:
        """
        获取基金的缓存状态

        Args:
            fund_code: 基金代码

        Returns:
            CacheMetadata | None: 缓存元数据，不存在返回 None
        """

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM fund_cache_metadata WHERE fund_code = ?",
                (fund_code,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return CacheMetadata(
                fund_code=row["fund_code"],
                cache_status=row["cache_status"],
                last_updated=row["last_updated"] or "",
                expires_at=row["expires_at"] or "",
                last_error=row["last_error"],
                retry_count=row["retry_count"] or 0,
                created_at=row["created_at"] or "",
            )

    async def set_cache_status(
        self,
        fund_code: str,
        status: str,
        expires_at: datetime,
        error: str | None = None,
    ) -> bool:
        """
        设置缓存状态

        Args:
            fund_code: 基金代码
            status: 缓存状态 (unknown/valid/stale/refreshing/error)
            expires_at: 过期时间
            error: 错误信息（可选）

        Returns:
            bool: 是否设置成功
        """
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO fund_cache_metadata
                    (fund_code, cache_status, last_updated, expires_at, last_error, retry_count, created_at)
                    VALUES (?, ?, ?, ?, ?, 0, COALESCE(
                        (SELECT created_at FROM fund_cache_metadata WHERE fund_code = ?),
                        datetime('now', 'localtime')
                    ))
                    ON CONFLICT(fund_code) DO UPDATE SET
                        cache_status = excluded.cache_status,
                        last_updated = excluded.last_updated,
                        expires_at = excluded.expires_at,
                        last_error = excluded.last_error,
                        retry_count = CASE WHEN excluded.cache_status = 'error' THEN retry_count + 1 ELSE 0 END
                    """,
                    (fund_code, status, now, expires_at.isoformat(), error, fund_code),
                )
                return True
            except Exception as e:
                logger.warning(f"设置缓存状态失败 fund_code={fund_code}: {e}")
                return False

    async def mark_refreshing(self, fund_code: str) -> bool:
        """
        标记缓存为刷新中状态，实现简单的锁机制

        Args:
            fund_code: 基金代码

        Returns:
            bool: 是否成功获取刷新锁
        """
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # 检查当前状态
            cursor.execute(
                "SELECT cache_status FROM fund_cache_metadata WHERE fund_code = ?",
                (fund_code,),
            )
            row = cursor.fetchone()
            if row is not None and row["cache_status"] == "refreshing":
                return False  # 已有其他进程在刷新

            # 设置为刷新中状态
            try:
                cursor.execute(
                    """
                    INSERT INTO fund_cache_metadata
                    (fund_code, cache_status, last_updated, expires_at, retry_count, created_at)
                    VALUES (?, 'refreshing', ?, datetime('now', 'localtime'), 0, datetime('now', 'localtime'))
                    ON CONFLICT(fund_code) DO UPDATE SET
                        cache_status = 'refreshing',
                        last_updated = excluded.last_updated
                    """,
                    (fund_code, now),
                )
                return True
            except Exception as e:
                logger.warning(f"标记缓存刷新失败 fund_code={fund_code}: {e}")
                return False

    async def release_refresh_lock(self, fund_code: str) -> bool:
        """
        释放刷新锁

        Args:
            fund_code: 基金代码

        Returns:
            bool: 是否成功释放
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE fund_cache_metadata SET cache_status = 'valid' WHERE fund_code = ?",
                (fund_code,),
            )
            return cursor.rowcount > 0

    async def get_expired_caches(self, batch_size: int = 100) -> list[str]:
        """
        获取已过期的缓存列表

        Args:
            batch_size: 批量大小

        Returns:
            list[str]: 过期缓存的基金代码列表
        """
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT fund_code FROM fund_cache_metadata
                WHERE expires_at < ? AND cache_status IN ('valid', 'stale', 'error')
                ORDER BY expires_at ASC
                LIMIT ?
                """,
                (now, batch_size),
            )
            return [row["fund_code"] for row in cursor.fetchall()]

    async def get_stale_caches(self, threshold_minutes: int = 30) -> list[str]:
        """
        获取陈旧缓存列表（即将过期或已过期但状态仍为valid）

        Args:
            threshold_minutes: 阈值（分钟）

        Returns:
            list[str]: 陈旧缓存的基金代码列表
        """
        threshold_time = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT fund_code FROM fund_cache_metadata
                WHERE cache_status = 'valid' AND expires_at < datetime(?, '+' || ? || ' minutes')
                ORDER BY expires_at ASC
                """,
                (threshold_time, threshold_minutes),
            )
            return [row["fund_code"] for row in cursor.fetchall()]

    async def mark_stale(self, fund_code: str) -> bool:
        """
        标记缓存为陈旧状态

        Args:
            fund_code: 基金代码

        Returns:
            bool: 是否成功标记
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE fund_cache_metadata SET cache_status = 'stale' WHERE fund_code = ?",
                (fund_code,),
            )
            return cursor.rowcount > 0

    async def mark_error(self, fund_code: str, error: str) -> bool:
        """
        标记缓存为错误状态

        Args:
            fund_code: 基金代码
            error: 错误信息

        Returns:
            bool: 是否成功标记
        """
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE fund_cache_metadata
                SET cache_status = 'error', last_error = ?, last_updated = ?, retry_count = retry_count + 1
                WHERE fund_code = ?
                """,
                (error, now, fund_code),
            )
            return cursor.rowcount > 0

    async def clear_error(self, fund_code: str) -> bool:
        """
        清除错误状态

        Args:
            fund_code: 基金代码

        Returns:
            bool: 是否成功清除
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE fund_cache_metadata SET last_error = NULL, retry_count = 0 WHERE fund_code = ?",
                (fund_code,),
            )
            return cursor.rowcount > 0

    async def delete(self, fund_code: str) -> bool:
        """
        删除缓存元数据

        Args:
            fund_code: 基金代码

        Returns:
            bool: 是否成功删除
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM fund_cache_metadata WHERE fund_code = ?",
                (fund_code,),
            )
            return cursor.rowcount > 0
