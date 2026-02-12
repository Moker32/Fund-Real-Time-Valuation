# -*- coding: UTF-8 -*-
"""商品缓存数据访问层

提供商品行情数据的 SQLite 存储和查询功能。
支持贵金属、能源、基本金属三类商品的实时行情缓存。
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from src.db.database import DatabaseManager

logger = logging.getLogger(__name__)


class CommodityCategory(Enum):
    """商品分类枚举"""

    PRECIOUS_METAL = "precious_metal"  # 贵金属
    ENERGY = "energy"  # 能源化工
    BASE_METAL = "base_metal"  # 基本金属


# 商品到分类的映射
COMMODITY_CATEGORY_MAP: dict[str, CommodityCategory] = {
    # 贵金属
    "gold": CommodityCategory.PRECIOUS_METAL,
    "gold_cny": CommodityCategory.PRECIOUS_METAL,
    "silver": CommodityCategory.PRECIOUS_METAL,
    "platinum": CommodityCategory.PRECIOUS_METAL,
    "palladium": CommodityCategory.PRECIOUS_METAL,
    # 能源
    "wti": CommodityCategory.ENERGY,
    "brent": CommodityCategory.ENERGY,
    "natural_gas": CommodityCategory.ENERGY,
    # 基本金属
    "copper": CommodityCategory.BASE_METAL,
    "aluminum": CommodityCategory.BASE_METAL,
    "zinc": CommodityCategory.BASE_METAL,
    "nickel": CommodityCategory.BASE_METAL,
}

# 分类名称映射
CATEGORY_NAMES: dict[CommodityCategory, str] = {
    CommodityCategory.PRECIOUS_METAL: "贵金属",
    CommodityCategory.ENERGY: "能源化工",
    CommodityCategory.BASE_METAL: "基本金属",
}

# 商品显示名称
COMMODITY_NAMES: dict[str, str] = {
    "gold": "黄金 (COMEX)",
    "gold_cny": "Au99.99 (上海黄金)",
    "silver": "白银",
    "platinum": "铂金",
    "palladium": "钯金",
    "wti": "WTI原油",
    "brent": "布伦特原油",
    "natural_gas": "天然气",
    "copper": "铜",
    "aluminum": "铝",
    "zinc": "锌",
    "nickel": "镍",
}


@dataclass
class CommodityCacheRecord:
    """商品行情缓存记录"""

    id: int | None = None
    commodity_type: str = ""  # 商品类型标识
    symbol: str = ""  # 交易所代码
    name: str = ""  # 商品名称
    price: float = 0.0  # 当前价格
    change: float = 0.0  # 涨跌
    change_percent: float = 0.0  # 涨跌幅
    currency: str = "USD"  # 货币
    exchange: str = ""  # 交易所
    high: float = 0.0  # 最高价
    low: float = 0.0  # 最低价
    open: float = 0.0  # 开盘价
    prev_close: float = 0.0  # 昨收价
    source: str = ""  # 数据源
    timestamp: str = ""  # 数据时间
    created_at: str = ""  # 入库时间

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "commodity_type": self.commodity_type,
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "change": self.change,
            "change_percent": self.change_percent,
            "currency": self.currency,
            "exchange": self.exchange,
            "high": self.high,
            "low": self.low,
            "open": self.open,
            "prev_close": self.prev_close,
            "source": self.source,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommodityCacheRecord":
        """从字典创建"""
        return cls(
            id=data.get("id"),
            commodity_type=data.get("commodity_type", ""),
            symbol=data.get("symbol", ""),
            name=data.get("name", ""),
            price=float(data.get("price", 0) or 0),
            change=float(data.get("change", 0) or 0),
            change_percent=float(data.get("change_percent", 0) or 0),
            currency=data.get("currency", "USD"),
            exchange=data.get("exchange", ""),
            high=float(data.get("high", 0) or 0),
            low=float(data.get("low", 0) or 0),
            open=float(data.get("open", 0) or 0),
            prev_close=float(data.get("prev_close", 0) or 0),
            source=data.get("source", ""),
            timestamp=data.get("timestamp", ""),
            created_at=data.get("created_at", ""),
        )

    @classmethod
    def from_api_response(
        cls, commodity_type: str, data: dict[str, Any], source: str
    ) -> "CommodityCacheRecord":
        """从 API 响应数据创建记录"""
        now = datetime.now().isoformat()
        return cls(
            commodity_type=commodity_type,
            symbol=data.get("symbol", ""),
            name=data.get("name", COMMODITY_NAMES.get(commodity_type, commodity_type)),
            price=float(data.get("price", 0) or 0),
            change=float(data.get("change", 0) or 0),
            change_percent=float(data.get("change_percent", 0) or 0),
            currency=data.get("currency", "USD"),
            exchange=data.get("exchange", ""),
            high=float(data.get("high", 0) or 0),
            low=float(data.get("low", 0) or 0),
            open=float(data.get("open", 0) or 0),
            prev_close=float(data.get("prev_close", 0) or 0),
            source=source,
            timestamp=data.get("time", data.get("timestamp", now)),
            created_at=now,
        )


def get_category_info(category: CommodityCategory) -> dict[str, Any]:
    """获取分类信息"""
    return {
        "id": category.value,
        "name": CATEGORY_NAMES.get(category, category.value),
    }


def get_commodity_info(commodity_type: str) -> dict[str, Any]:
    """获取商品信息"""
    category = COMMODITY_CATEGORY_MAP.get(commodity_type)
    return {
        "type": commodity_type,
        "name": COMMODITY_NAMES.get(commodity_type, commodity_type),
        "category": category.value if category else None,
    }


class CommodityCacheDAO:
    """商品行情缓存数据访问对象

    提供商品行情数据的存储、查询和清理功能。
    """

    # 默认缓存过期时间（小时）
    DEFAULT_CACHE_TTL_HOURS = 24

    def __init__(self, db_manager: DatabaseManager, cache_ttl_hours: int = DEFAULT_CACHE_TTL_HOURS):
        """
        初始化商品缓存 DAO

        Args:
            db_manager: 数据库管理器实例
            cache_ttl_hours: 缓存过期时间（小时），默认为 24 小时
        """
        self.db = db_manager
        self.cache_ttl_hours = cache_ttl_hours

    def save(self, record: CommodityCacheRecord) -> bool:
        """
        保存商品行情数据

        Args:
            record: 商品缓存记录

        Returns:
            bool: 是否保存成功
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO commodity_cache (
                        commodity_type, symbol, name, price, change, change_percent,
                        currency, exchange, high, low, open, prev_close,
                        source, timestamp, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        record.commodity_type,
                        record.symbol,
                        record.name,
                        record.price,
                        record.change,
                        record.change_percent,
                        record.currency,
                        record.exchange,
                        record.high,
                        record.low,
                        record.open,
                        record.prev_close,
                        record.source,
                        record.timestamp,
                        record.created_at or datetime.now().isoformat(),
                    ),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def save_from_api(
        self, commodity_type: str, data: dict[str, Any], source: str
    ) -> bool:
        """
        从 API 响应保存商品数据

        Args:
            commodity_type: 商品类型
            data: API 响应数据
            source: 数据源名称

        Returns:
            bool: 是否保存成功
        """
        record = CommodityCacheRecord.from_api_response(commodity_type, data, source)
        return self.save(record)

    def get_latest(self, commodity_type: str) -> CommodityCacheRecord | None:
        """
        获取指定商品的最新行情

        Args:
            commodity_type: 商品类型

        Returns:
            CommodityCacheRecord | None: 最新行情记录，不存在返回 None
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM commodity_cache
                WHERE commodity_type = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (commodity_type,),
            )
            row = cursor.fetchone()
            return CommodityCacheRecord(**row) if row else None

    def get_all_latest(self) -> list[CommodityCacheRecord]:
        """
        获取所有商品的最新行情

        Returns:
            list[CommodityCacheRecord]: 所有商品的最新行情列表
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c1.* FROM commodity_cache c1
                LEFT JOIN commodity_cache c2
                    ON c1.commodity_type = c2.commodity_type
                    AND c1.created_at < c2.created_at
                WHERE c2.created_at IS NULL
                ORDER BY c1.commodity_type
            """
            )
            return [CommodityCacheRecord(**row) for row in cursor.fetchall()]

    def get_by_category(
        self, category: CommodityCategory
    ) -> list[CommodityCacheRecord]:
        """
        获取指定分类的商品最新行情

        Args:
            category: 商品分类

        Returns:
            list[CommodityCacheRecord]: 该分类商品的最新行情列表
        """
        commodity_types = [
            ct for ct, cat in COMMODITY_CATEGORY_MAP.items() if cat == category
        ]
        if not commodity_types:
            return []

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ", ".join("?" * len(commodity_types))
            cursor.execute(
                f"""
                SELECT c1.* FROM commodity_cache c1
                LEFT JOIN commodity_cache c2
                    ON c1.commodity_type = c2.commodity_type
                    AND c1.created_at < c2.created_at
                WHERE c2.created_at IS NULL
                    AND c1.commodity_type IN ({placeholders})
                ORDER BY c1.commodity_type
            """,
                commodity_types,
            )
            return [CommodityCacheRecord(**row) for row in cursor.fetchall()]

    def get_history(
        self, commodity_type: str, limit: int = 30
    ) -> list[CommodityCacheRecord]:
        """
        获取商品历史行情

        Args:
            commodity_type: 商品类型
            limit: 最大记录数

        Returns:
            list[CommodityCacheRecord]: 历史行情列表，按时间降序
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM commodity_cache
                WHERE commodity_type = ?
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (commodity_type, limit),
            )
            return [CommodityCacheRecord(**row) for row in cursor.fetchall()]

    def is_expired(self, commodity_type: str) -> bool:
        """
        检查商品缓存是否过期

        Args:
            commodity_type: 商品类型

        Returns:
            bool: True 表示缓存已过期或不存在，False 表示缓存有效
        """
        record = self.get_latest(commodity_type)
        if record is None or not record.created_at:
            return True

        try:
            created_time = datetime.fromisoformat(
                record.created_at.replace("Z", "+00:00")
            )
            now = datetime.now()
            elapsed_hours = (now - created_time).total_seconds() / 3600
            return elapsed_hours > self.cache_ttl_hours
        except (ValueError, TypeError):
            return True

    def cleanup_expired(self, hours: int | None = None) -> int:
        """
        清理过期的商品缓存

        Args:
            hours: 过期时间（小时），默认使用初始化时的 TTL

        Returns:
            int: 删除的记录数
        """
        ttl_hours = hours or self.cache_ttl_hours
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM commodity_cache
                WHERE created_at < datetime('now', ?)
            """,
                (f"-{ttl_hours} hours",),
            )
            return cursor.rowcount

    def clear_commodity(self, commodity_type: str) -> int:
        """
        清除指定商品的所有缓存

        Args:
            commodity_type: 商品类型

        Returns:
            int: 删除的记录数
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM commodity_cache WHERE commodity_type = ?",
                (commodity_type,),
            )
            return cursor.rowcount

    def clear_all(self) -> int:
        """
        清除所有商品缓存

        Returns:
            int: 删除的记录数
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM commodity_cache")
            return cursor.rowcount

    def get_cache_info(self, commodity_type: str) -> dict[str, Any]:
        """
        获取指定商品的缓存信息

        Args:
            commodity_type: 商品类型

        Returns:
            dict: 包含缓存信息的字典
        """
        record = self.get_latest(commodity_type)
        if record is None:
            return {
                "commodity_type": commodity_type,
                "count": 0,
                "latest_timestamp": None,
                "expired": True,
            }

        return {
            "commodity_type": commodity_type,
            "count": 1,
            "latest_timestamp": record.created_at,
            "expired": self.is_expired(commodity_type),
        }

    def get_all_cache_info(self) -> list[dict[str, Any]]:
        """
        获取所有商品的缓存信息

        Returns:
            list[dict]: 各商品缓存信息列表
        """
        records = self.get_all_latest()
        return [self.get_cache_info(r.commodity_type) for r in records]

    def count_records(self, commodity_type: str | None = None) -> int:
        """
        统计缓存记录数

        Args:
            commodity_type: 可选，指定商品类型

        Returns:
            int: 记录数
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if commodity_type:
                cursor.execute(
                    "SELECT COUNT(*) FROM commodity_cache WHERE commodity_type = ?",
                    (commodity_type,),
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM commodity_cache")
            return cursor.fetchone()[0]


class CommodityCategoryDAO:
    """商品分类数据访问对象

    提供商品分类信息的查询功能。
    """

    def get_all_categories(self) -> list[dict[str, Any]]:
        """
        获取所有商品分类信息

        Returns:
            list[dict]: 分类信息列表，每个包含 id, name
        """
        return [{"id": cat.value, "name": CATEGORY_NAMES[cat]} for cat in CommodityCategory]

    def get_commodity_types_by_category(
        self, category: CommodityCategory
    ) -> list[str]:
        """
        获取指定分类的所有商品类型

        Args:
            category: 商品分类

        Returns:
            list[str]: 商品类型列表
        ]
        """
        return [
            ct for ct, cat in COMMODITY_CATEGORY_MAP.items() if cat == category
        ]

    def get_category_by_commodity(self, commodity_type: str) -> CommodityCategory | None:
        """
        根据商品类型获取分类

        Args:
            commodity_type: 商品类型

        Returns:
            CommodityCategory | None: 商品分类，不存在返回 None
        """
        return COMMODITY_CATEGORY_MAP.get(commodity_type)
