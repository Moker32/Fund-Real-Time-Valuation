# -*- coding: UTF-8 -*-
from __future__ import annotations

"""基金基本信息数据访问对象

提供基金基本信息的存储和查询功能。
"""

import sqlite3
from datetime import datetime
from typing import Any

from src.db.models import FundBasicInfo


class FundBasicInfoDAO:
    """基金基本信息数据访问对象

    提供基金基本信息的存储和查询功能。
    """

    def __init__(self, db_manager: DatabaseManager):  # noqa: F821
        self.db = db_manager

    def save(
        self,
        code: str,
        name: str | None = None,
        short_name: str | None = None,
        type: str | None = None,
        fund_key: str | None = None,
        net_value: float | None = None,
        net_value_date: str | None = None,
        establishment_date: str | None = None,
        manager: str | None = None,
        custodian: str | None = None,
        fund_scale: float | None = None,
        scale_date: str | None = None,
        risk_level: str | None = None,
        full_name: str | None = None,
    ) -> bool:
        """
        保存基金基本信息

        Args:
            code: 基金代码
            name: 基金全称
            short_name: 基金简称
            type: 基金类型
            fund_key: 基金关键字
            net_value: 单位净值
            net_value_date: 净值日期
            establishment_date: 成立日期
            manager: 基金管理人
            custodian: 基金托管人
            fund_scale: 基金规模
            scale_date: 规模日期
            risk_level: 风险等级
            full_name: 基金完整名称

        Returns:
            bool: 是否保存成功
        """
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO fund_basic_info
                    (code, name, short_name, type, fund_key, net_value, net_value_date,
                     establishment_date, manager, custodian, fund_scale, scale_date,
                     risk_level, full_name, fetched_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        code,
                        name,
                        short_name,
                        type,
                        fund_key,
                        net_value,
                        net_value_date,
                        establishment_date,
                        manager,
                        custodian,
                        fund_scale,
                        scale_date,
                        risk_level,
                        full_name,
                        now,
                        now,
                    ),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def save_from_dict(self, code: str, data: dict[str, Any]) -> bool:
        """
        从字典保存基金基本信息

        Args:
            code: 基金代码
            data: 基金信息字典

        Returns:
            bool: 是否保存成功
        """
        return self.save(
            code=code,
            name=data.get("name"),
            short_name=data.get("short_name"),
            type=data.get("type"),
            fund_key=data.get("fund_key"),
            net_value=data.get("net_value"),
            net_value_date=data.get("net_value_date"),
            establishment_date=data.get("establishment_date"),
            manager=data.get("manager"),
            custodian=data.get("custodian"),
            fund_scale=data.get("fund_scale"),
            scale_date=data.get("scale_date"),
            risk_level=data.get("risk_level"),
            full_name=data.get("full_name"),
        )

    def get(self, code: str) -> FundBasicInfo | None:
        """
        获取基金基本信息

        Args:
            code: 基金代码

        Returns:
            FundBasicInfo | None: 基金基本信息，不存在返回 None
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fund_basic_info WHERE code = ?", (code,))
            row = cursor.fetchone()
            return FundBasicInfo(**row) if row else None

    def exists(self, code: str) -> bool:
        """
        检查基金基本信息是否存在

        Args:
            code: 基金代码

        Returns:
            bool: 是否存在
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM fund_basic_info WHERE code = ? LIMIT 1", (code,))
            return cursor.fetchone() is not None

    def delete(self, code: str) -> bool:
        """
        删除基金基本信息

        Args:
            code: 基金代码

        Returns:
            bool: 是否删除成功
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM fund_basic_info WHERE code = ?", (code,))
            return cursor.rowcount > 0

    def get_all(self) -> list[FundBasicInfo]:
        """
        获取所有基金基本信息

        Returns:
            list[FundBasicInfo]: 基金基本信息列表
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fund_basic_info ORDER BY updated_at DESC")
            return [FundBasicInfo(**row) for row in cursor.fetchall()]

    def get_by_type(self, fund_type: str) -> list[FundBasicInfo]:
        """
        根据基金类型获取基金基本信息

        Args:
            fund_type: 基金类型

        Returns:
            list[FundBasicInfo]: 基金基本信息列表
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM fund_basic_info WHERE type = ? ORDER BY updated_at DESC",
                (fund_type,),
            )
            return [FundBasicInfo(**row) for row in cursor.fetchall()]

    def search(self, keyword: str, limit: int = 20) -> list[FundBasicInfo]:
        """
        搜索基金基本信息

        支持按基金代码、基金名称模糊搜索。

        Args:
            keyword: 搜索关键词
            limit: 返回结果数量限制

        Returns:
            list[FundBasicInfo]: 匹配的基金基本信息列表
        """
        if not keyword:
            return []

        keyword = keyword.strip()
        pattern = f"%{keyword}%"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM fund_basic_info
                WHERE code LIKE ? OR name LIKE ? OR short_name LIKE ?
                ORDER BY 
                    CASE 
                        WHEN code = ? THEN 0
                        WHEN code LIKE ? THEN 1
                        WHEN name LIKE ? THEN 2
                        ELSE 3
                    END,
                    updated_at DESC
                LIMIT ?
                """,
                (pattern, pattern, pattern, keyword, f"{keyword}%", f"{keyword}%", limit),
            )
            return [FundBasicInfo(**row) for row in cursor.fetchall()]

    def get_by_code(self, code: str) -> FundBasicInfo | None:
        """
        根据基金代码获取基金基本信息

        Args:
            code: 基金代码

        Returns:
            FundBasicInfo | None: 基金基本信息，不存在返回 None
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fund_basic_info WHERE code = ?", (code,))
            row = cursor.fetchone()
            return FundBasicInfo(**row) if row else None

    def update(self, code: str, **kwargs) -> bool:
        """
        更新基金基本信息

        Args:
            code: 基金代码
            **kwargs: 更新的字段

        Returns:
            bool: 是否更新成功
        """
        allowed_fields = {
            "name",
            "short_name",
            "type",
            "fund_key",
            "net_value",
            "net_value_date",
            "establishment_date",
            "manager",
            "custodian",
            "fund_scale",
            "scale_date",
            "risk_level",
            "full_name",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        updates["updated_at"] = datetime.now().isoformat()
        updates["code"] = code

        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE fund_basic_info SET {set_clause} WHERE code = :code", updates)
            return cursor.rowcount > 0
