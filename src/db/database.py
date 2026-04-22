# -*- coding: UTF-8 -*-
from __future__ import annotations

"""SQLite 数据库管理器

提供基金实时估值应用的数据持久化支持。
支持基金配置、商品配置、历史数据和新闻缓存的存储与查询。
"""

import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from src.db.calendar.exchange_holiday_dao import ExchangeHolidayDAO
    from src.db.calendar.trading_calendar_dao import TradingCalendarDAO


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
            config_dir = os.environ.get("FUND_TUI_CONFIG_DIR", str(Path.home() / ".fund-tui"))
            os.makedirs(config_dir, exist_ok=True)
            db_path = str(Path(config_dir) / "fund_data.db")

        self.db_path = db_path
        self._init_database()

    @property
    def trading_calendar_dao(self) -> TradingCalendarDAO:
        """获取交易日历 DAO"""
        from src.db.calendar.trading_calendar_dao import TradingCalendarDAO

        return TradingCalendarDAO(self)

    @property
    def holiday_dao(self) -> ExchangeHolidayDAO:
        """获取节假日 DAO"""
        from src.db.calendar.exchange_holiday_dao import ExchangeHolidayDAO

        return ExchangeHolidayDAO(self)

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
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    price REAL NOT NULL,
                    change_rate REAL,
                    fetched_at TEXT,
                    UNIQUE(fund_code, date, time)
                )
            """)

            # 指数日内分时缓存表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS index_intraday_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    index_type TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    price REAL NOT NULL,
                    change_rate REAL,
                    fetched_at TEXT,
                    UNIQUE(index_type, date, time)
                )
            """)

            # 基金每日缓存表（存储近一周的每日基础数据）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_daily_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fund_code TEXT NOT NULL,
                    date TEXT NOT NULL,
                    unit_net_value REAL,
                    accumulated_net_value REAL,
                    estimated_value REAL,
                    change_rate REAL,
                    estimate_time TEXT,
                    fetched_at TEXT,
                    UNIQUE(fund_code, date)
                )
            """)

            # 基金基本信息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_basic_info (
                    code TEXT PRIMARY KEY,
                    name TEXT,
                    short_name TEXT,
                    type TEXT,
                    fund_key TEXT,
                    net_value REAL,
                    net_value_date TEXT,
                    establishment_date TEXT,
                    manager TEXT,
                    custodian TEXT,
                    fund_scale REAL,
                    scale_date TEXT,
                    risk_level TEXT,
                    full_name TEXT,
                    fetched_at TEXT,
                    updated_at TEXT
                )
            """)

            # 商品行情缓存表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commodity_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    commodity_type TEXT NOT NULL,
                    symbol TEXT,
                    name TEXT,
                    price REAL DEFAULT 0,
                    change REAL DEFAULT 0,
                    change_percent REAL DEFAULT 0,
                    currency TEXT DEFAULT 'USD',
                    exchange TEXT,
                    high REAL DEFAULT 0,
                    low REAL DEFAULT 0,
                    open REAL DEFAULT 0,
                    prev_close REAL DEFAULT 0,
                    source TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # 交易日历缓存表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_calendar_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    day_of_year INTEGER NOT NULL,
                    is_trading_day INTEGER NOT NULL,
                    holiday_name TEXT,
                    is_makeup_day INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    UNIQUE(market, year, day_of_year)
                )
            """)

            # 节假日定义表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exchange_holidays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market TEXT NOT NULL,
                    holiday_date TEXT NOT NULL,
                    holiday_name TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
                    UNIQUE(market, holiday_date)
                )
            """)

            # 缓存元数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_cache_metadata (
                    fund_code TEXT PRIMARY KEY,
                    cache_status TEXT DEFAULT 'unknown',
                    last_updated TEXT,
                    expires_at TEXT,
                    last_error TEXT,
                    retry_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # API调用统计表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_call_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    api_name TEXT NOT NULL,
                    call_time TEXT NOT NULL,
                    duration_ms INTEGER DEFAULT 0,
                    success INTEGER DEFAULT 1,
                    error_message TEXT,
                    cache_hit INTEGER DEFAULT 0,
                    fund_code TEXT,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)

            # 创建索引
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_holidays_market_date ON exchange_holidays(market, holiday_date)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_holidays_active ON exchange_holidays(market, is_active)"
            )
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
                "CREATE INDEX IF NOT EXISTS idx_fund_intraday_code ON fund_intraday_cache(fund_code, date)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_index_intraday_type ON index_intraday_cache(index_type, date)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_fund_daily_code ON fund_daily_cache(fund_code, date)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_commodity_type ON commodity_cache(commodity_type)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_commodity_timestamp ON commodity_cache(created_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_cache_metadata_status ON fund_cache_metadata(cache_status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_cache_metadata_expires ON fund_cache_metadata(expires_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_api_stats_name ON api_call_stats(api_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_api_stats_fund ON api_call_stats(fund_code)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_api_stats_time ON api_call_stats(call_time)"
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
                cursor.execute("ALTER TABLE fund_config ADD COLUMN is_hold INTEGER DEFAULT 0")

            # 检查 fund_intraday_cache 表是否有 date 列
            cursor.execute("PRAGMA table_info(fund_intraday_cache)")
            intraday_columns = [row[1] for row in cursor.fetchall()]

            # 添加 date 列（如果不存在）
            if "date" not in intraday_columns:
                cursor.execute("ALTER TABLE fund_intraday_cache ADD COLUMN date TEXT DEFAULT ''")

            # 检查 fund_daily_cache 表是否有 estimate_time 列
            cursor.execute("PRAGMA table_info(fund_daily_cache)")
            daily_columns = [row[1] for row in cursor.fetchall()]

            # 添加 estimate_time 列（如果不存在）
            if "estimate_time" not in daily_columns:
                cursor.execute(
                    "ALTER TABLE fund_daily_cache ADD COLUMN estimate_time TEXT DEFAULT ''"
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
