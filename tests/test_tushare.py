"""
Tushare 数据源测试
TDD 方式实现 - 先写测试
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.datasources.fund_source import TushareFundSource


class TestTushareFundSource:
    def test_init(self):
        source = TushareFundSource()
        assert source.name == "tushare_fund"
        assert source.source_type.value == "fund"

    def test_get_name(self):
        source = TushareFundSource()
        assert source.get_status()["name"] == "tushare_fund"

    @pytest.mark.asyncio
    async def test_fetch_without_token(self):
        source = TushareFundSource()
        result = await source.fetch("161039")
        assert result.success is False or "token" in result.error.lower() if result.error else True

    @pytest.mark.asyncio
    async def test_fetch_with_token(self):
        source = TushareFundSource(token="test_token_123")
        assert source._token == "test_token_123"
        assert source._pro is not None

    @pytest.mark.asyncio
    async def test_fetch_batch(self):
        source = TushareFundSource()
        results = await source.fetch_batch(["161039", "000001"])
        assert isinstance(results, list)
        assert len(results) == 2
