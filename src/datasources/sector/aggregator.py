"""板块数据聚合器模块"""

import logging
import time
from typing import Any

from ..base import DataSource, DataSourceResult, DataSourceType

logger = logging.getLogger(__name__)


class SectorDataAggregator(DataSource):
    """板块数据聚合器"""

    def __init__(self, timeout: float = 15.0):
        super().__init__(
            name="sector_aggregator", source_type=DataSourceType.SECTOR, timeout=timeout
        )
        self._sources: list[DataSource] = []
        self._primary_source: DataSource | None = None

    def add_source(self, source: DataSource, is_primary: bool = False):
        """添加数据源"""
        self._sources.append(source)
        if is_primary or self._primary_source is None:
            self._primary_source = source

    async def fetch(self, sector_code: str | None = None) -> DataSourceResult:
        """获取板块数据"""
        errors = []

        # 优先使用主数据源
        if self._primary_source:
            try:
                result = await self._primary_source.fetch(sector_code)
                if result.success:
                    return result
                errors.append(f"{self._primary_source.name}: {result.error}")
            except Exception as e:
                errors.append(f"{self._primary_source.name}: {str(e)}")

        # 尝试其他数据源
        for source in self._sources:
            if source == self._primary_source:
                continue
            try:
                result = await source.fetch(sector_code)
                if result.success:
                    return result
                errors.append(f"{source.name}: {result.error}")
            except Exception as e:
                errors.append(f"{source.name}: {str(e)}")

        return DataSourceResult(
            success=False,
            error=f"所有数据源均失败: {'; '.join(errors)}",
            timestamp=time.time(),
            source=self.name,
            metadata={"sector_code": sector_code, "errors": errors},
        )

    async def fetch_all(self) -> DataSourceResult:
        """获取所有板块数据"""
        return await self.fetch()

    async def fetch_by_category(self, category: str) -> DataSourceResult:
        """按类别获取板块数据"""
        for source in self._sources:
            if hasattr(source, "fetch_by_category"):
                try:
                    result = await source.fetch_by_category(category)
                    if result.success:
                        return result
                except Exception:
                    continue

        return DataSourceResult(
            success=False,
            error=f"无法获取类别 {category} 的数据",
            timestamp=time.time(),
            source=self.name,
        )

    def get_status(self) -> dict[str, Any]:
        """获取聚合器状态"""
        status = super().get_status()
        status["source_count"] = len(self._sources)
        status["primary_source"] = self._primary_source.name if self._primary_source else None
        status["sources"] = [s.name for s in self._sources]
        return status

    async def fetch_batch(self, sector_codes: list[str]) -> list[DataSourceResult]:
        """批量获取板块数据"""
        results = []
        for code in sector_codes:
            result = await self.fetch(code)
            results.append(result)
        return results

    async def close(self):
        """关闭所有数据源"""
        for source in self._sources:
            if hasattr(source, "close"):
                try:
                    await source.close()
                except Exception:
                    pass
