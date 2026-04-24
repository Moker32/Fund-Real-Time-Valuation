# -*- coding: UTF-8 -*-
from __future__ import annotations

"""基金行业配置数据访问对象

提供基金行业配置数据的存储和查询功能。
"""

from datetime import datetime
from typing import TYPE_CHECKING

from src.db.models import FundIndustryRecord

if TYPE_CHECKING:
    from src.db.database import DatabaseManager


class FundIndustryDAO:
    """基金行业配置数据访问对象"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def save(
        self,
        fund_code: str,
        industry_name: str,
        proportion: float | None = None,
        report_date: str = "",
    ) -> bool:
        """保存行业配置记录"""
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO fund_industry
                (fund_code, industry_name, proportion, report_date, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (fund_code, industry_name, proportion, report_date, now),
            )
            return cursor.rowcount > 0

    def save_batch(
        self,
        fund_code: str,
        industries: list[dict],
        report_date: str,
    ) -> bool:
        """批量保存行业配置"""
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # 先清除该基金该报告期的旧数据
            cursor.execute(
                "DELETE FROM fund_industry WHERE fund_code = ? AND report_date = ?",
                (fund_code, report_date),
            )
            for item in industries:
                cursor.execute(
                    """
                    INSERT INTO fund_industry
                    (fund_code, industry_name, proportion, report_date, fetched_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        fund_code,
                        item.get("industry_name", ""),
                        item.get("proportion"),
                        report_date,
                        now,
                    ),
                )
            return True

    def get_latest(self, fund_code: str, limit: int = 5) -> list[FundIndustryRecord]:
        """获取基金最新的行业配置（按报告期倒序）"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM fund_industry
                WHERE fund_code = ?
                  AND report_date = (
                      SELECT MAX(report_date) FROM fund_industry WHERE fund_code = ?
                  )
                ORDER BY proportion DESC
                LIMIT ?
                """,
                (fund_code, fund_code, limit),
            )
            return [FundIndustryRecord(**row) for row in cursor.fetchall()]

    def get_latest_report_date(self, fund_code: str) -> str | None:
        """获取最新的报告期"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(report_date) FROM fund_industry WHERE fund_code = ?",
                (fund_code,),
            )
            row = cursor.fetchone()
            return row[0] if row and row[0] else None

    def delete(self, fund_code: str) -> bool:
        """删除基金的所有行业配置记录"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM fund_industry WHERE fund_code = ?", (fund_code,)
            )
            return cursor.rowcount > 0
