# -*- coding: UTF-8 -*-
"""基金历史数据访问对象

提供基金净值历史数据的存储和查询功能。
"""

import sqlite3
from datetime import datetime
from typing import Any

from src.db.models import FundHistoryRecord


class FundHistoryDAO:
    """基金历史数据访问对象

    提供基金净值历史数据的存储和查询功能。
    """

    def __init__(self, db_manager: "DatabaseManager"):
        self.db = db_manager

    def add_history(
        self,
        fund_code: str,
        fund_name: str,
        date: str,
        unit_net_value: float,
        accumulated_net_value: float | None = None,
        estimated_value: float | None = None,
        growth_rate: float | None = None,
    ) -> bool:
        """
        添加单条历史记录

        Args:
            fund_code: 基金代码
            fund_name: 基金名称
            date: 日期
            unit_net_value: 单位净值
            accumulated_net_value: 累计净值
            estimated_value: 估算净值
            growth_rate: 增长率

        Returns:
            bool: 是否添加成功
        """
        fetched_at = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO fund_history
                    (fund_code, fund_name, date, unit_net_value, accumulated_net_value,
                     estimated_value, growth_rate, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        fund_code,
                        fund_name,
                        date,
                        unit_net_value,
                        accumulated_net_value,
                        estimated_value,
                        growth_rate,
                        fetched_at,
                    ),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def add_history_batch(self, records: list[FundHistoryRecord]) -> int:
        """
        批量添加历史记录

        Args:
            records: 历史记录列表

        Returns:
            int: 成功添加的记录数
        """
        if not records:
            return 0

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            count = 0
            for record in records:
                try:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO fund_history
                        (fund_code, fund_name, date, unit_net_value, accumulated_net_value,
                         estimated_value, growth_rate, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            record.fund_code,
                            record.fund_name,
                            record.date,
                            record.unit_net_value,
                            record.accumulated_net_value,
                            record.estimated_value,
                            record.growth_rate,
                            record.fetched_at,
                        ),
                    )
                    count += 1
                except sqlite3.IntegrityError:
                    continue
            return count

    def get_history(
        self,
        fund_code: str,
        limit: int = 365,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[FundHistoryRecord]:
        """
        获取基金历史记录

        Args:
            fund_code: 基金代码
            limit: 最大记录数
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[FundHistoryRecord]: 历史记录列表
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM fund_history WHERE fund_code = ?"
            params = [fund_code]

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            query += f" ORDER BY date DESC LIMIT {limit}"

            cursor.execute(query, params)
            return [FundHistoryRecord(**row) for row in cursor.fetchall()]

    def get_latest_record(self, fund_code: str) -> FundHistoryRecord | None:
        """获取最新历史记录"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM fund_history
                WHERE fund_code = ?
                ORDER BY date DESC LIMIT 1
            """,
                (fund_code,),
            )
            row = cursor.fetchone()
            return FundHistoryRecord(**row) if row else None

    def delete_old_history(self, days: int = 365) -> int:
        """
        删除旧的历史记录

        Args:
            days: 保留天数

        Returns:
            int: 删除的记录数
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM fund_history
                WHERE date < date('now', ?)
            """,
                (f"-{days} days",),
            )
            return cursor.rowcount

    def get_history_summary(self, fund_code: str) -> dict[str, Any]:
        """获取历史数据统计摘要"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_records,
                    MIN(unit_net_value) as min_value,
                    MAX(unit_net_value) as max_value,
                    AVG(unit_net_value) as avg_value,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM fund_history
                WHERE fund_code = ?
            """,
                (fund_code,),
            )
            row = cursor.fetchone()
            return dict(row) if row else {}
