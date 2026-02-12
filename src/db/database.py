# -*- coding: UTF-8 -*-
"""SQLite 数据库管理器

提供基金实时估值应用的数据持久化支持。
支持基金配置、商品配置、历史数据和新闻缓存的存储与查询。
"""

import logging
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """将 sqlite3.Row 转换为字典，处理整数到布尔值的转换"""
    if row is None:
        return {}
    result = dict(row)
    # 转换特定字段从整数到布尔值
    if "watchlist" in result:
        result["watchlist"] = bool(result["watchlist"])
    if "enabled" in result:
        result["enabled"] = bool(result["enabled"])
    return result


@dataclass
class FundConfig:
    """基金配置数据类"""

    code: str
    name: str
    watchlist: int = 1  # SQLite返回整数，1=True，0=False
    shares: float = 0.0  # 持有份额
    cost: float = 0.0  # 成本价
    is_hold: int = 0  # 持有标记 (1=持有, 0=不持有)
    sector: str = ""  # 板块标注
    notes: str = ""  # 备注
    created_at: str = ""
    updated_at: str = ""

    @property
    def is_watchlist(self) -> bool:
        """将整数转换为布尔值"""
        return bool(self.watchlist)

    @property
    def is_holding(self) -> bool:
        """检查是否标记为持有"""
        return bool(self.is_hold)


@dataclass
class CommodityConfig:
    """商品配置数据类"""

    symbol: str
    name: str
    source: str = "akshare"  # 数据源
    enabled: int = 1  # SQLite返回整数，1=True，0=False
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def is_enabled(self) -> bool:
        """将整数转换为布尔值"""
        return bool(self.enabled)


@dataclass
class FundHistoryRecord:
    """基金净值历史记录"""

    id: int | None = None  # 数据库自增ID
    fund_code: str = ""
    fund_name: str = ""
    date: str = ""
    unit_net_value: float = 0.0
    accumulated_net_value: float | None = None
    estimated_value: float | None = None
    growth_rate: float | None = None
    fetched_at: str = ""


@dataclass
class NewsRecord:
    """新闻记录"""

    title: str
    url: str
    source: str
    category: str
    publish_time: str
    content: str = ""
    fetched_at: str = ""


@dataclass
class FundIntradayRecord:
    """基金日内分时数据记录"""

    id: int | None = None  # 数据库自增ID
    fund_code: str = ""
    time: str = ""  # "HH:mm" 格式
    price: float = 0.0  # 估算净值
    change_rate: float | None = None  # 涨跌率
    fetched_at: str = ""  # 抓取时间


class DatabaseManager:
    """数据库管理器

    管理 SQLite 数据库连接、执行迁移和维护数据完整性。
    """

    def __init__(self, db_path: str | None = None):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径，默认为 ~/.fund-tui/fund_data.db
        """
        if db_path is None:
            config_dir = os.environ.get(
                "FUND_TUI_CONFIG_DIR", str(Path.home() / ".fund-tui")
            )
            os.makedirs(config_dir, exist_ok=True)
            db_path = str(Path(config_dir) / "fund_data.db")

        self.db_path = db_path
        self._init_database()

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            conn.close()

    def _init_database(self) -> None:
        """初始化数据库表结构"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 基金配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_config (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    watchlist INTEGER DEFAULT 1,
                    shares REAL DEFAULT 0,
                    cost REAL DEFAULT 0,
                    is_hold INTEGER DEFAULT 0,
                    sector TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            # 执行数据库迁移：检查并添加缺失的列
            self._migrate_database(cursor)

            # 商品配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commodity_config (
                    symbol TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source TEXT DEFAULT 'akshare',
                    enabled INTEGER DEFAULT 1,
                    notes TEXT DEFAULT '',
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            # 基金净值历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fund_code TEXT NOT NULL,
                    fund_name TEXT,
                    date TEXT NOT NULL,
                    unit_net_value REAL,
                    accumulated_net_value REAL,
                    estimated_value REAL,
                    growth_rate REAL,
                    fetched_at TEXT,
                    UNIQUE(fund_code, date),
                    FOREIGN KEY (fund_code) REFERENCES fund_config(code) ON DELETE CASCADE
                )
            """)

            # 新闻缓存表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE,
                    source TEXT,
                    category TEXT,
                    publish_time TEXT,
                    content TEXT,
                    fetched_at TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)

            # 基金日内分时缓存表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_intraday_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fund_code TEXT NOT NULL,
                    time TEXT NOT NULL,
                    price REAL NOT NULL,
                    change_rate REAL,
                    fetched_at TEXT,
                    UNIQUE(fund_code, time)
                )
            """)

            # 创建索引
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_fund_history_code_date ON fund_history(fund_code, date)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_news_cache_category ON news_cache(category)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_news_cache_fetched_at ON news_cache(fetched_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_fund_intraday_code ON fund_intraday_cache(fund_code)"
            )

            conn.commit()

    def _migrate_database(self, cursor) -> None:
        """数据库迁移：检查并添加缺失的列"""
        try:
            # 检查 fund_config 表是否有 is_hold 列
            cursor.execute("PRAGMA table_info(fund_config)")
            columns = [row[1] for row in cursor.fetchall()]

            # 添加 is_hold 列（如果不存在）
            if "is_hold" not in columns:
                cursor.execute(
                    "ALTER TABLE fund_config ADD COLUMN is_hold INTEGER DEFAULT 0"
                )

        except Exception as e:
            logger.warning(f"数据库迁移警告: {e}")

    def vacuum(self) -> None:
        """清理数据库碎片"""
        with self.get_connection() as conn:
            conn.execute("VACUUM")

    def get_size(self) -> int:
        """获取数据库文件大小（字节）"""
        if os.path.exists(self.db_path):
            return os.path.getsize(self.db_path)
        return 0

    def backup(self, backup_path: str) -> bool:
        """
        备份数据库

        Args:
            backup_path: 备份文件路径

        Returns:
            bool: 是否备份成功
        """
        try:
            import shutil

            shutil.copy2(self.db_path, backup_path)
            return True
        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            return False


class ConfigDAO:
    """配置数据访问对象

    提供基金和商品配置的 CRUD 操作。
    """

    def __init__(self, db_manager: DatabaseManager):
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
            cursor.execute(
                "SELECT * FROM fund_config WHERE shares > 0 ORDER BY updated_at DESC"
            )
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
            cursor.execute(
                f"UPDATE fund_config SET {set_clause} WHERE code = :code", updates
            )
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

    def get_hold_funds(self) -> list["FundConfig"]:
        """获取标记为持有的基金列表"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM fund_config WHERE is_hold = 1 ORDER BY updated_at DESC"
            )
            return [FundConfig(**row) for row in cursor.fetchall()]

    def get_funds_by_hold(self, holding: bool) -> list["FundConfig"]:
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
                cursor.execute(
                    "SELECT * FROM commodity_config ORDER BY updated_at DESC"
                )
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


class FundHistoryDAO:
    """基金历史数据访问对象

    提供基金净值历史数据的存储和查询功能。
    """

    def __init__(self, db_manager: DatabaseManager):
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


class NewsDAO:
    """新闻缓存数据访问对象"""

    def __init__(self, db_manager: DatabaseManager):
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
            except sqlite3.IntegrityError:
                return False

    def get_news(
        self, category: str | None = None, limit: int = 50
    ) -> list[NewsRecord]:
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


class FundIntradayCacheDAO:
    """基金日内分时缓存数据访问对象

    提供基金日内分时数据的存储和查询功能。
    支持 60 秒缓存过期机制，用于减少 API 调用。
    """

    # 默认缓存过期时间（秒）
    DEFAULT_CACHE_TTL = 60

    def __init__(self, db_manager: DatabaseManager, cache_ttl: int = DEFAULT_CACHE_TTL):
        """
        初始化日内分时缓存 DAO

        Args:
            db_manager: 数据库管理器实例
            cache_ttl: 缓存过期时间（秒），默认为 60 秒
        """
        self.db = db_manager
        self.cache_ttl = cache_ttl

    def save_intraday(self, fund_code: str, data: list[dict]) -> bool:
        """
        保存基金日内分时数据

        Args:
            fund_code: 基金代码
            data: 日内分时数据列表，每个元素包含 time, price, change_rate

        Returns:
            bool: 是否保存成功
        """
        if not data:
            return False

        fetched_at = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            count = 0
            for item in data:
                try:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO fund_intraday_cache
                        (fund_code, time, price, change_rate, fetched_at)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            fund_code,
                            item.get("time", ""),
                            item.get("price", 0.0),
                            item.get("change"),
                            fetched_at,
                        ),
                    )
                    count += 1
                except sqlite3.IntegrityError:
                    # 如果插入失败（唯一约束），尝试更新
                    cursor.execute(
                        """
                        UPDATE fund_intraday_cache
                        SET price = ?, change_rate = ?, fetched_at = ?
                        WHERE fund_code = ? AND time = ?
                    """,
                        (
                            item.get("price", 0.0),
                            item.get("change"),
                            fetched_at,
                            fund_code,
                            item.get("time", ""),
                        ),
                    )
                    count += 1
            return count > 0

    def get_intraday(self, fund_code: str) -> list[FundIntradayRecord]:
        """
        获取基金日内分时缓存数据

        Args:
            fund_code: 基金代码

        Returns:
            list[FundIntradayRecord]: 日内分时数据列表，按时间排序
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM fund_intraday_cache
                WHERE fund_code = ?
                ORDER BY time ASC
            """,
                (fund_code,),
            )
            return [FundIntradayRecord(**row) for row in cursor.fetchall()]

    def is_expired(self, fund_code: str) -> bool:
        """
        检查缓存是否过期

        Args:
            fund_code: 基金代码

        Returns:
            bool: True 表示缓存已过期或不存在，False 表示缓存有效
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT fetched_at FROM fund_intraday_cache
                WHERE fund_code = ?
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
                # 解析 ISO 格式的时间
                fetched_time = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
                now = datetime.now()
                elapsed_seconds = (now - fetched_time).total_seconds()
                return elapsed_seconds > self.cache_ttl
            except (ValueError, TypeError):
                return True  # 时间解析失败，视为过期

    def clear_cache(self, fund_code: str) -> int:
        """
        清除指定基金的日内缓存

        Args:
            fund_code: 基金代码

        Returns:
            int: 删除的记录数
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
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
                    "count": 0,
                    "last_fetched": None,
                    "expired": True,
                }

            return {
                "fund_code": fund_code,
                "count": row["count"],
                "last_fetched": row["last_fetched"],
                "expired": self.is_expired(fund_code),
            }
