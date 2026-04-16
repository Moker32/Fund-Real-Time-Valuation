# -*- coding: UTF-8 -*-
"""基金每日缓存数据访问对象

提供基金每日估值数据的存储和查询功能。
用于缓存当日基金估值数据，减少 API 调用频率。
"""

import logging
import sqlite3
from datetime import datetime
from typing import Any

from src.db.models import FundDailyRecord

logger = logging.getLogger(__name__)


class FundDailyCacheDAO:
    """基金每日缓存数据访问对象

    提供基金每日估值数据的存储和查询功能。
    用于缓存当日基金估值数据，减少 API 调用频率。
    """

    # 默认缓存过期时间（秒）- 0 表示禁用缓存
    DEFAULT_CACHE_TTL = 0

    def __init__(self, db_manager: "DatabaseManager", cache_ttl: int = DEFAULT_CACHE_TTL):
        """
        初始化每日缓存 DAO

        Args:
            db_manager: 数据库管理器实例
            cache_ttl: 缓存过期时间（秒），默认为 300 秒（5分钟）
        """
        self.db = db_manager
        self.cache_ttl = cache_ttl
        if cache_ttl == 0:
            logger.warning(
                "FundDailyCacheDAO 初始化时 cache_ttl=0，缓存将永不过期。"
                "这可能导致数据陈旧，建议在生产环境中设置合理的 TTL 值。"
            )

    def save_daily(
        self,
        fund_code: str,
        date: str,
        unit_net_value: float | None = None,
        accumulated_net_value: float | None = None,
        estimated_value: float | None = None,
        change_rate: float | None = None,
        estimate_time: str | None = None,
    ) -> bool:
        """
        保存基金每日数据

        Args:
            fund_code: 基金代码
            date: 日期 (YYYY-MM-DD 格式)
            unit_net_value: 单位净值
            accumulated_net_value: 累计净值
            estimated_value: 估算净值
            change_rate: 日增长率
            estimate_time: 估值时间 (YYYY-MM-DD HH:MM 格式，来自 gztime)

        Returns:
            bool: 是否保存成功
        """
        fetched_at = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO fund_daily_cache
                    (fund_code, date, unit_net_value, accumulated_net_value,
                     estimated_value, change_rate, estimate_time, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        fund_code,
                        date,
                        unit_net_value,
                        accumulated_net_value,
                        estimated_value,
                        change_rate,
                        estimate_time or "",
                        fetched_at,
                    ),
                )
                return True
            except sqlite3.IntegrityError:
                # 如果插入失败，尝试更新
                cursor.execute(
                    """
                    UPDATE fund_daily_cache
                    SET unit_net_value = ?, accumulated_net_value = ?,
                        estimated_value = ?, change_rate = ?, estimate_time = ?, fetched_at = ?
                    WHERE fund_code = ? AND date = ?
                """,
                    (
                        unit_net_value,
                        accumulated_net_value,
                        estimated_value,
                        change_rate,
                        estimate_time or "",
                        fetched_at,
                        fund_code,
                        date,
                    ),
                )
                return True

    def save_daily_from_fund_data(self, fund_code: str, data: dict[str, Any]) -> bool:
        """
        从基金数据字典保存每日数据

        Args:
            fund_code: 基金代码
            data: 基金数据字典，包含 net_value_date, unit_net_value,
                  accumulated_net_value, estimated_net_value, estimated_growth_rate,
                  estimate_time (估值时间，来自 gztime)

        Returns:
            bool: 是否保存成功
        """
        date = data.get("net_value_date", "") or data.get("date", "")
        # 过滤无效日期（NaT、空字符串等）
        if not date or date in ("NaT", "NaN", "None", "null"):
            return False
        if not date:
            return False

        # 获取估值时间（来自 API 的 gztime 字段）
        estimate_time = data.get("estimate_time", "")

        return self.save_daily(
            fund_code=fund_code,
            date=date,
            unit_net_value=data.get("unit_net_value"),
            accumulated_net_value=data.get("accumulated_net_value"),
            estimated_value=data.get("estimated_net_value"),
            change_rate=data.get("estimated_growth_rate") or data.get("change_rate"),
            estimate_time=estimate_time,
        )

    def get_daily(self, fund_code: str, date: str) -> FundDailyRecord | None:
        """
        获取基金指定日期的每日数据

        Args:
            fund_code: 基金代码
            date: 日期 (YYYY-MM-DD 格式)

        Returns:
            FundDailyRecord | None: 每日数据记录，不存在返回 None
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM fund_daily_cache
                WHERE fund_code = ? AND date = ?
            """,
                (fund_code, date),
            )
            row = cursor.fetchone()
            return FundDailyRecord(**row) if row else None

    def get_latest(self, fund_code: str) -> FundDailyRecord | None:
        """
        获取基金最新的每日数据

        Args:
            fund_code: 基金代码

        Returns:
            FundDailyRecord | None: 最新每日数据记录，不存在返回 None
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM fund_daily_cache
                WHERE fund_code = ?
                ORDER BY date DESC
                LIMIT 1
            """,
                (fund_code,),
            )
            row = cursor.fetchone()
            return FundDailyRecord(**row) if row else None

    def get_recent_days(self, fund_code: str, days: int = 7) -> list[FundDailyRecord]:
        """
        获取基金最近几天的每日数据

        Args:
            fund_code: 基金代码
            days: 获取天数，默认为 7 天

        Returns:
            list[FundDailyRecord]: 每日数据列表，按日期降序排列
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM fund_daily_cache
                WHERE fund_code = ?
                ORDER BY date DESC
                LIMIT ?
            """,
                (fund_code, days),
            )
            return [FundDailyRecord(**row) for row in cursor.fetchall()]

    def is_expired(self, fund_code: str, date: str | None = None) -> bool:
        """
        检查缓存是否过期

        缓存过期条件（满足任一）：
        1. 缓存不存在
        2. 缓存时间超过 TTL（如果 TTL > 0）

        注意：不再检查净值日期是否为今天，因为：
        - QDII 基金的净值日期通常比国内市场晚一天（投资海外市场）
        - 非交易日时净值日期也不会更新
        - 只要缓存时间未过期，数据就是有效的

        Args:
            fund_code: 基金代码
            date: 可选，指定日期，默认检查最新日期

        Returns:
            bool: True 表示缓存已过期或不存在，False 表示缓存有效
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute(
                    """
                    SELECT date, fetched_at FROM fund_daily_cache
                    WHERE fund_code = ? AND date = ?
                    LIMIT 1
                """,
                    (fund_code, date),
                )
            else:
                cursor.execute(
                    """
                    SELECT date, fetched_at FROM fund_daily_cache
                    WHERE fund_code = ?
                    ORDER BY date DESC
                    LIMIT 1
                """,
                    (fund_code,),
                )
            row = cursor.fetchone()

            if row is None:
                return True  # 不存在缓存，视为过期

            fetched_at = row["fetched_at"]

            if not fetched_at:
                return True

            # 检查 TTL 过期
            if self.cache_ttl > 0:
                try:
                    fetched_time = datetime.fromisoformat(fetched_at.replace("Z", ""))
                    now = datetime.now()
                    elapsed_seconds = (now - fetched_time).total_seconds()
                    return elapsed_seconds > self.cache_ttl
                except (ValueError, TypeError):
                    return True  # 时间解析失败，视为过期

            return False  # TTL=0，缓存永久有效

    def clear_cache(self, fund_code: str, date: str | None = None) -> int:
        """
        清除指定基金的每日缓存

        Args:
            fund_code: 基金代码
            date: 可选，指定日期，默认清除所有日期

        Returns:
            int: 删除的记录数
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if date:
                cursor.execute(
                    "DELETE FROM fund_daily_cache WHERE fund_code = ? AND date = ?",
                    (fund_code, date),
                )
            else:
                cursor.execute(
                    "DELETE FROM fund_daily_cache WHERE fund_code = ?",
                    (fund_code,),
                )
            return cursor.rowcount

    def cleanup_expired_cache(self, days: int = 7) -> int:
        """
        清理过期的每日缓存（保留最近 N 天）

        Args:
            days: 保留天数，默认为 7 天

        Returns:
            int: 删除的记录数
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM fund_daily_cache
                WHERE date < date('now', ?)
            """,
                (f"-{days} days",),
            )
            return cursor.rowcount

    def get_cache_info(self, fund_code: str) -> dict[str, Any]:
        """
        获取缓存信息

        Args:
            fund_code: 基金代码

        Returns:
            dict: 包含缓存信息的字典
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) as count, MAX(date) as latest_date, MAX(fetched_at) as last_fetched
                FROM fund_daily_cache
                WHERE fund_code = ?
            """,
                (fund_code,),
            )
            row = cursor.fetchone()

            if row is None or row["count"] == 0:
                return {
                    "fund_code": fund_code,
                    "count": 0,
                    "latest_date": None,
                    "last_fetched": None,
                    "expired": True,
                }

            return {
                "fund_code": fund_code,
                "count": row["count"],
                "latest_date": row["latest_date"],
                "last_fetched": row["last_fetched"],
                "expired": self.is_expired(fund_code),
            }
