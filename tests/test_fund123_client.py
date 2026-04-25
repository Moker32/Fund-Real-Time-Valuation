# -*- coding: UTF-8 -*-
"""Fund123Client 模块测试"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.datasources.fund.fund123_client import (
    CSRF_TOKEN_TTL,
    MAX_CONCURRENT_REQUESTS,
    Fund123Client,
)


class TestFund123ClientSingleton:
    """测试 Fund123Client 单例行为"""

    def test_get_instance_returns_same_instance(self):
        """测试 get_instance 返回同一实例"""
        # 重置单例
        Fund123Client._instance = None

        instance1 = Fund123Client.get_instance()
        instance2 = Fund123Client.get_instance()

        assert instance1 is instance2

    def test_instance_has_initial_state(self):
        """测试实例初始状态"""
        # 重置单例
        Fund123Client._instance = None

        instance = Fund123Client.get_instance()

        assert instance._client is None
        assert instance._csrf_token is None
        assert instance._csrf_token_time == 0.0
        assert instance._semaphore is None
        assert instance._csrf_lock is None
        assert instance._close_lock is None


class TestFund123ClientBackwardCompat:
    """测试向后兼容的静态方法接口"""

    @pytest.mark.asyncio
    async def test_ensure_client_class_method(self):
        """测试 _ensure_client 类方法"""
        # 重置单例
        Fund123Client._instance = None

        client = Fund123Client._ensure_client()

        assert client is not None
        assert hasattr(client, "get")

    @pytest.mark.asyncio
    async def test_get_semaphore_class_method(self):
        """测试 _get_semaphore 类方法"""
        # 重置单例
        Fund123Client._instance = None

        semaphore = Fund123Client._get_semaphore()

        assert semaphore is not None
        assert semaphore._value == MAX_CONCURRENT_REQUESTS

    @pytest.mark.asyncio
    async def test_get_csrf_lock_class_method(self):
        """测试 _get_csrf_lock 类方法"""
        # 重置单例
        Fund123Client._instance = None

        lock = Fund123Client._get_csrf_lock()

        assert lock is not None

    @pytest.mark.asyncio
    async def test_get_csrf_token_class_method(self):
        """测试 _get_csrf_token 类方法"""
        # 重置单例
        Fund123Client._instance = None

        # 设置缓存的 token
        client = Fund123Client.get_instance()
        client._csrf_token = "test_token_123"
        client._csrf_token_time = time.time()

        token = await Fund123Client._get_csrf_token()
        assert token == "test_token_123"

    @pytest.mark.asyncio
    async def test_refresh_csrf_token(self):
        """测试 _refresh_csrf_token 类方法"""
        # 重置单例
        Fund123Client._instance = None

        client = Fund123Client.get_instance()
        client._csrf_token = "old_token"
        client._csrf_token_time = time.time()

        # Mock _get_csrf_token to return a new token
        async def mock_csrf_getter():
            client._csrf_token = "new_token"
            return "new_token"

        # Replace the internal method with mock
        original_method = client._Fund123Client__csrf_token_getter
        client._Fund123Client__csrf_token_getter = mock_csrf_getter

        try:
            result = await client._Fund123Client__refresh_csrf_token()

            assert result is True
            assert client._csrf_token == "new_token"
        finally:
            client._Fund123Client__csrf_token_getter = original_method


class TestFund123ClientCSRFToken:
    """测试 CSRF Token 管理"""

    @pytest.mark.asyncio
    async def test_csrf_token_caching(self):
        """测试 CSRF token 缓存"""
        # 重置单例
        Fund123Client._instance = None

        client = Fund123Client.get_instance()
        client._csrf_token = "cached_token"
        client._csrf_token_time = time.time()

        token = await client._Fund123Client__csrf_token_getter()

        assert token == "cached_token"

    @pytest.mark.asyncio
    async def test_csrf_token_expired(self):
        """测试过期的 CSRF token 会被重新获取"""
        # 重置单例
        Fund123Client._instance = None

        client = Fund123Client.get_instance()
        client._csrf_token = "old_token"
        # 设置为很久以前的时间，触发过期
        client._csrf_token_time = time.time() - CSRF_TOKEN_TTL - 100

        # Mock the HTTP client to return a new token
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.text = '{"csrf":"new_token_from_server"}'
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            client, "_Fund123Client__ensure_client", return_value=MagicMock()
        ) as mock_ensure:
            mock_client = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_ensure.return_value = mock_client

            # Reset the token to trigger refresh
            client._csrf_token = None
            client._csrf_token_time = 0

            token = await client._Fund123Client__csrf_token_getter()


class TestFund123ClientConcurrency:
    """测试并发控制"""

    def test_semaphore_limit(self):
        """测试信号量并发限制"""
        # 重置单例
        Fund123Client._instance = None

        semaphore = Fund123Client._get_semaphore()

        assert semaphore._value == MAX_CONCURRENT_REQUESTS

    def test_semaphore_is_singleton(self):
        """测试信号量是单例"""
        # 重置单例
        Fund123Client._instance = None

        sem1 = Fund123Client._get_semaphore()
        sem2 = Fund123Client._get_semaphore()

        assert sem1 is sem2


class TestFund123ClientClose:
    """测试客户端关闭"""

    @pytest.mark.asyncio
    async def test_close_resets_state(self):
        """测试 close 方法重置状态"""
        # 重置单例
        Fund123Client._instance = None

        client = Fund123Client.get_instance()

        # 设置一些状态
        mock_client = MagicMock()
        mock_client.aclose = AsyncMock()
        client._client = mock_client
        client._csrf_token = "some_token"

        await client._Fund123Client__close_async()

        assert client._client is None
        assert client._csrf_token is None

    @pytest.mark.asyncio
    async def test_class_close_method(self):
        """测试类级别的 close 方法"""
        # 重置单例
        Fund123Client._instance = None

        client = Fund123Client.get_instance()
        mock_client = MagicMock()
        mock_client.aclose = AsyncMock()
        client._client = mock_client

        await Fund123Client.close()

        assert client._client is None


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
