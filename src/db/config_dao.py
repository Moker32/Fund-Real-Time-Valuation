# -*- coding: UTF-8 -*-
from __future__ import annotations

"""配置数据访问对象

提供基金和商品配置的 CRUD 操作。
"""

import sqlite3
from datetime import datetime

from src.db.models import CommodityConfig, FundConfig


class ConfigDAO:
    """配置数据访问对象

    提供基金和商品配置的 CRUD 操作。
    """

    def __init__(self, db_manager: DatabaseManager):  # noqa: F821
        self.db = db_manager

    # ==================== 基金配置操作 ====================

    def add_fund(
        self,
        code: str,
        name: str,
        watchlist: bool = True,
        shares: float = 0.0,
        cost: float = 0.0,
        is_hold: bool = False,
        sector: str = "",
        notes: str = "",
    ) -> bool:
        """
        添加基金到配置

        Args:
            code: 基金代码
            name: 基金名称
            watchlist: 是否加入自选
            shares: 持有份额
            cost: 成本价
            is_hold: 是否标记为持有
            sector: 板块标注
            notes: 备注

        Returns:
            bool: 是否添加成功
        """
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO fund_config
                    (code, name, watchlist, shares, cost, is_hold, sector, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        code,
                        name,
                        int(watchlist),
                        shares,
                        cost,
                        int(is_hold),
                        sector,
                        notes,
                        now,
                        now,
                    ),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def get_watchlist(self) -> list[FundConfig]:
        """获取自选基金列表"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM fund_config WHERE watchlist = 1 ORDER BY updated_at DESC
            """)
            return [FundConfig(**row) for row in cursor.fetchall()]

    def get_all_funds(self) -> list[FundConfig]:
        """获取所有配置基金（含持仓）"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fund_config ORDER BY updated_at DESC")
            return [FundConfig(**row) for row in cursor.fetchall()]

    def get_fund(self, code: str) -> FundConfig | None:
        """根据代码获取基金配置"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fund_config WHERE code = ?", (code,))
            row = cursor.fetchone()
            return FundConfig(**row) if row else None

    def get_holdings(self) -> list[FundConfig]:
        """获取持仓基金列表（份额 > 0）"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fund_config WHERE shares > 0 ORDER BY updated_at DESC")
            return [FundConfig(**row) for row in cursor.fetchall()]

    def update_fund(self, code: str, **kwargs) -> bool:
        """
        更新基金配置

        Args:
            code: 基金代码
            **kwargs: 更新的字段（name, watchlist, shares, cost, is_hold, sector, notes）
        """
        allowed_fields = {
            "name",
            "watchlist",
            "shares",
            "cost",
            "is_hold",
            "sector",
            "notes",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        updates["updated_at"] = datetime.now().isoformat()
        updates["code"] = code

        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE fund_config SET {set_clause} WHERE code = :code", updates)
            return cursor.rowcount > 0

    def remove_fund(self, code: str) -> bool:
        """删除基金配置"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM fund_config WHERE code = ?", (code,))
            return cursor.rowcount > 0

    def remove_from_watchlist(self, code: str) -> bool:
        """从自选列表移除"""
        return self.update_fund(code, watchlist=False)

    def add_to_watchlist(self, code: str) -> bool:
        """添加到自选列表"""
        return self.update_fund(code, watchlist=True)

    def toggle_hold(self, code: str, is_hold: bool) -> bool:
        """切换持有标记"""
        return self.update_fund(code, is_hold=is_hold)

    def get_hold_funds(self) -> list[FundConfig]:
        """获取标记为持有的基金列表"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fund_config WHERE is_hold = 1 ORDER BY updated_at DESC")
            return [FundConfig(**row) for row in cursor.fetchall()]

    def get_funds_by_hold(self, holding: bool) -> list[FundConfig]:
        """根据持有标记获取基金列表"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM fund_config WHERE is_hold = ? ORDER BY updated_at DESC",
                (1 if holding else 0,),
            )
            return [FundConfig(**row) for row in cursor.fetchall()]

    # ==================== 商品配置操作 ====================

    def add_commodity(
        self,
        symbol: str,
        name: str,
        source: str = "akshare",
        enabled: bool = True,
        notes: str = "",
    ) -> bool:
        """添加商品配置"""
        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO commodity_config
                    (symbol, name, source, enabled, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (symbol, name, source, int(enabled), notes, now, now),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def get_commodities(self, enabled_only: bool = False) -> list[CommodityConfig]:
        """获取商品配置列表"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if enabled_only:
                cursor.execute(
                    "SELECT * FROM commodity_config WHERE enabled = 1 ORDER BY updated_at DESC"
                )
            else:
                cursor.execute("SELECT * FROM commodity_config ORDER BY updated_at DESC")
            return [CommodityConfig(**row) for row in cursor.fetchall()]

    def get_commodity(self, symbol: str) -> CommodityConfig | None:
        """根据代码获取商品配置"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM commodity_config WHERE symbol = ?", (symbol,))
            row = cursor.fetchone()
            return CommodityConfig(**row) if row else None

    def update_commodity(self, symbol: str, **kwargs) -> bool:
        """更新商品配置"""
        allowed_fields = {"name", "source", "enabled", "notes"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        updates["updated_at"] = datetime.now().isoformat()
        updates["symbol"] = symbol

        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE commodity_config SET {set_clause} WHERE symbol = :symbol",
                updates,
            )
            return cursor.rowcount > 0

    def remove_commodity(self, symbol: str) -> bool:
        """删除商品配置"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM commodity_config WHERE symbol = ?", (symbol,))
            return cursor.rowcount > 0

    # ==================== 默认数据 ====================

    def init_default_funds(self) -> None:
        """初始化默认基金列表"""
        default_funds = [
            ("161039", "富国中证新能源汽车指数"),
            ("161725", "招商中证白酒指数(LOF)"),
            ("110022", "易方达消费行业股票"),
        ]
        for code, name in default_funds:
            if not self.get_fund(code):
                self.add_fund(code, name, watchlist=True)

    def init_default_commodities(self) -> None:
        """初始化默认商品列表"""
        default_commodities = [
            ("gold_cny", "Au99.99 (上海黄金)", "akshare"),
            ("gold", "黄金 (COMEX)", "yfinance"),
            ("wti", "WTI原油", "yfinance"),
            ("silver", "白银", "yfinance"),
            ("natural_gas", "天然气", "yfinance"),
        ]
        for symbol, name, source in default_commodities:
            if not self.get_commodity(symbol):
                self.add_commodity(symbol, name, source=source)
