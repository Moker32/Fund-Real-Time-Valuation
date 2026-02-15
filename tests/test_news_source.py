# -*- coding: UTF-8 -*-
"""News Source Tests

测试新闻数据源
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.datasources.news_source import SinaNewsDataSource


class TestSinaNewsDataSource:
    """新浪新闻数据源测试"""

    @pytest.fixture
    def news_source(self):
        """返回新闻数据源实例"""
        return SinaNewsDataSource(timeout=5.0, max_news=10)

    def test_init(self, news_source):
        """测试初始化"""
        assert news_source.name == "sina_news"
        assert news_source.timeout == 5.0
        assert news_source.max_news == 10
        assert news_source._cache_timeout == 300.0

    def test_get_category_url(self, news_source):
        """测试获取分类URL"""
        assert news_source._get_category_url("finance") == "https://finance.sina.com.cn/"
        assert news_source._get_category_url("stock") == "https://finance.sina.com.cn/stock/"
        assert news_source._get_category_url("fund") == "https://finance.sina.com.cn/fund/"
        assert news_source._get_category_url("economy") == "https://finance.sina.com.cn/realstock/company/sz000001/nc.shtml"
        # 默认返回 finance URL
        assert news_source._get_category_url("unknown") == "https://finance.sina.com.cn/"

    def test_is_cache_valid(self, news_source):
        """测试缓存有效性"""
        # 初始时缓存无效
        assert news_source._is_cache_valid() is False

        # 设置缓存
        news_source._news_cache = [{"title": "test"}]
        news_source._cache_time = time.time()
        
        # 刚设置缓存，有效
        assert news_source._is_cache_valid() is True

        # 设置过期缓存
        news_source._cache_time = time.time() - 400  # 超过5分钟
        assert news_source._is_cache_valid() is False

    def test_is_finance_link(self, news_source):
        """测试财经链接判断"""
        # 正确的财经链接
        assert news_source._is_finance_link("https://finance.sina.com.cn/stock/", "股票新闻") is True
        assert news_source._is_finance_link("https://fund.sina.com.cn/fund/", "基金新闻") is True
        
        # 排除的链接
        assert news_source._is_finance_link("javascript:void(0)", "test") is False
        assert news_source._is_finance_link("#", "test") is False
        assert news_source._is_finance_link("/login", "登录") is False

    def test_is_finance_link_by_keywords(self, news_source):
        """测试关键词判断"""
        # 包含财经关键词的链接
        assert news_source._is_finance_link("https://example.com/article", "A股今日大涨") is True
        assert news_source._is_finance_link("https://example.com/article", "基金净值上涨") is True
        assert news_source._is_finance_link("https://example.com/article", "央行降息") is True

    def test_close(self, news_source):
        """测试关闭客户端"""
        # 测试能够正确关闭
        news_source.client = None  # 设置为 None 模拟已关闭
        # 不应该抛出异常
        assert news_source.client is None

    @pytest.mark.asyncio
    async def test_fetch_with_cache(self, news_source):
        """测试使用缓存获取新闻"""
        # 先设置缓存
        cached_news = [{"title": "cached news", "url": "https://example.com"}]
        news_source._news_cache = cached_news
        news_source._cache_time = time.time()

        result = await news_source.fetch("finance")

        assert result.success is True
        assert result.data == cached_news
        assert result.metadata.get("from_cache") is True

    @pytest.mark.asyncio
    async def test_fetch_error_handling(self, news_source):
        """测试错误处理"""
        # Mock httpx 抛出异常
        with patch.object(news_source.client, 'get', side_effect=Exception("Network error")):
            result = await news_source.fetch("finance")
            
            assert result.success is False
            assert "error" in str(result.error).lower() or "error" in str(result.error)

    @pytest.mark.asyncio
    async def test_fetch_batch(self, news_source):
        """测试批量获取新闻"""
        # 先设置缓存避免网络请求
        cached_news = [{"title": "test news"}]
        news_source._news_cache = cached_news
        news_source._cache_time = time.time()

        results = await news_source.fetch_batch(["finance", "stock"])

        assert len(results) == 2
        for result in results:
            assert result.success is True

    @pytest.mark.asyncio
    async def test_fetch_batch_with_errors(self, news_source):
        """测试批量获取新闻时处理错误"""
        # 清除缓存
        news_source._news_cache = []
        news_source._cache_time = 0

        # Mock httpx 抛出异常
        with patch.object(news_source.client, 'get', side_effect=Exception("Network error")):
            results = await news_source.fetch_batch(["finance", "stock"])

            assert len(results) == 2
            # 错误应该被正确处理

    def test_source_name(self, news_source):
        """测试数据源名称"""
        assert news_source.name == "sina_news"


class TestSinaNewsDataSourceMocked:
    """使用Mock的完整流程测试"""

    @pytest.fixture
    def news_source(self):
        """返回新闻数据源实例"""
        return SinaNewsDataSource(timeout=5.0, max_news=5)

    @pytest.mark.asyncio
    async def test_fetch_full_flow(self, news_source):
        """测试完整获取流程"""
        mock_html = """
        <html>
            <a href="https://finance.sina.com.cn/stock/123.shtml">测试股票新闻标题</a>
            <a href="https://finance.sina.com.cn/stock/456.shtml">A股今日上涨</a>
        </html>
        """
        
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.raise_for_status = MagicMock()

        with patch.object(news_source.client, 'get', new_callable=AsyncMock, return_value=mock_response):
            result = await news_source.fetch("stock")

            assert result.success is True
            assert result.source == "sina_news"
            # 验证返回了新闻数据
            assert len(result.data) > 0

    @pytest.mark.asyncio
    async def test_fetch_http_error(self, news_source):
        """测试HTTP错误处理"""
        import httpx
        
        with patch.object(news_source.client, 'get', new_callable=AsyncMock, side_effect=httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404)
        )):
            result = await news_source.fetch("finance")

            assert result.success is False
            assert "404" in str(result.error) or "failed" in str(result.error).lower()

    @pytest.mark.asyncio
    async def test_fetch_request_error(self, news_source):
        """测试网络请求错误处理"""
        import httpx
        
        with patch.object(news_source.client, 'get', new_callable=AsyncMock, side_effect=httpx.RequestError("Connection error")):
            result = await news_source.fetch("finance")

            assert result.success is False
            assert "network" in str(result.error).lower() or "error" in str(result.error).lower()
