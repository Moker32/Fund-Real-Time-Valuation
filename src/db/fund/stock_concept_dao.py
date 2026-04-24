"""股票概念标签缓存 DAO

缓存 A 股个股所属概念板块（如 CPO、AI芯片、商业航天等）的映射关系。
"""

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.db.database import DatabaseManager


class StockConceptDAO:
    """股票概念标签缓存数据访问对象"""

    def __init__(self, db_manager: "DatabaseManager"):
        self.db = db_manager

    def save_batch(self, stock_concepts: list[tuple[str, str]]) -> int:
        """批量保存股票→概念映射

        Args:
            stock_concepts: [(stock_code, concept_name), ...]

        Returns:
            写入行数
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            count = 0
            for stock_code, concept_name in stock_concepts:
                cursor.execute(
                    """INSERT OR IGNORE INTO stock_concept_cache
                       (stock_code, concept_name) VALUES (?, ?)""",
                    (stock_code, concept_name),
                )
                count += cursor.rowcount
            return count

    def get_stock_concepts(self, stock_code: str) -> list[str]:
        """获取个股所属的所有概念标签"""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT concept_name FROM stock_concept_cache WHERE stock_code = ?",
                (stock_code,),
            ).fetchall()
            return [r[0] for r in rows]

    def count(self) -> int:
        """返回缓存中映射总数"""
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM stock_concept_cache"
            ).fetchone()
            return row[0] if row else 0

    def clear(self) -> None:
        """清空缓存"""
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM stock_concept_cache")

    def get_all_concept_names(self) -> list[str]:
        """获取所有概念板块名称"""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT concept_name FROM stock_concept_cache ORDER BY concept_name"
            ).fetchall()
            return [r[0] for r in rows]


class FundConceptTagsDAO:
    """基金概念标签缓存 DAO"""

    def __init__(self, db_manager: "DatabaseManager"):
        self.db = db_manager

    def save(self, fund_code: str, tags: list[str], report_period: str = "") -> None:
        """保存基金概念标签"""
        import json

        now = datetime.now().isoformat()
        with self.db.get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO fund_concept_tags
                   (fund_code, tags, report_period, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (fund_code, json.dumps(tags, ensure_ascii=False), report_period, now),
            )

    def get(self, fund_code: str) -> list[str] | None:
        """获取缓存的概念标签"""
        import json

        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT tags FROM fund_concept_tags WHERE fund_code = ?",
                (fund_code,),
            ).fetchone()
            if row and row[0]:
                return json.loads(row[0])
            return None

    def get_existing_codes(self) -> set[str]:
        """获取已有缓存的所有基金代码"""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT fund_code FROM fund_concept_tags"
            ).fetchall()
            return {r[0] for r in rows}
