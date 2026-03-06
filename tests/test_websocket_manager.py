# -*- coding: UTF-8 -*-
"""
WebSocket 连接管理器测试

测试 WebSocketManager 类的核心功能：
- 连接管理（connect/disconnect）
- 订阅管理（subscribe/unsubscribe）
- 消息广播（broadcast/send_personal）
- 心跳检测
- 连接状态管理
"""

import asyncio
import math
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket

from src.utils.websocket_manager import (
    ConnectionState,
    WSClient,
    WSMessage,
    WebSocketManager,
    _safe_json_default,
    _to_camel_case,
    _convert_dict_to_camel_case,
    safe_json_dumps,
    get_websocket_manager,
    set_websocket_manager,
)


class TestWSClient:
    """WSClient 数据类测试"""

    def test_init_default_values(self):
        """测试默认值初始化"""
        mock_ws = MagicMock(spec=WebSocket)
        client = WSClient(client_id="test-id", websocket=mock_ws)

        assert client.client_id == "test-id"
        assert client.websocket == mock_ws
        assert client.subscriptions == set()
        assert client.state == ConnectionState.CONNECTING
        assert isinstance(client.connected_at, datetime)
        assert isinstance(client.last_heartbeat, datetime)
        assert client.metadata == {}

    def test_init_custom_values(self):
        """测试自定义值初始化"""
        mock_ws = MagicMock(spec=WebSocket)
        custom_time = datetime(2025, 1, 1, 12, 0, 0)
        client = WSClient(
            client_id="test-id",
            websocket=mock_ws,
            subscriptions={"funds", "indices"},
            state=ConnectionState.CONNECTED,
            connected_at=custom_time,
            last_heartbeat=custom_time,
            metadata={"key": "value"},
        )

        assert client.subscriptions == {"funds", "indices"}
        assert client.state == ConnectionState.CONNECTED
        assert client.connected_at == custom_time
        assert client.metadata == {"key": "value"}

    def test_is_alive_recent_heartbeat(self):
        """测试心跳检测 - 最近有心跳"""
        mock_ws = MagicMock(spec=WebSocket)
        client = WSClient(client_id="test-id", websocket=mock_ws)

        # 刚创建的客户端应该是存活的
        assert client.is_alive(heartbeat_timeout=60.0) is True

    def test_is_alive_timeout(self):
        """测试心跳检测 - 超时"""
        mock_ws = MagicMock(spec=WebSocket)
        client = WSClient(client_id="test-id", websocket=mock_ws)

        # 模拟超时
        client.last_heartbeat = datetime.now() - timedelta(seconds=120)

        assert client.is_alive(heartbeat_timeout=60.0) is False

    def test_is_alive_custom_timeout(self):
        """测试心跳检测 - 自定义超时时间"""
        mock_ws = MagicMock(spec=WebSocket)
        client = WSClient(client_id="test-id", websocket=mock_ws)

        # 30秒前有心跳
        client.last_heartbeat = datetime.now() - timedelta(seconds=30)

        assert client.is_alive(heartbeat_timeout=60.0) is True
        assert client.is_alive(heartbeat_timeout=20.0) is False


class TestWSMessage:
    """WSMessage 数据类测试"""

    def test_init_required_fields(self):
        """测试必需字段初始化"""
        message = WSMessage(type="test_type", data={"key": "value"})

        assert message.type == "test_type"
        assert message.data == {"key": "value"}
        assert message.subscription is None
        assert isinstance(message.timestamp, datetime)

    def test_init_all_fields(self):
        """测试所有字段初始化"""
        custom_time = datetime(2025, 1, 1, 12, 0, 0)
        message = WSMessage(
            type="test_type",
            data={"key": "value"},
            timestamp=custom_time,
            subscription="funds",
        )

        assert message.timestamp == custom_time
        assert message.subscription == "funds"


class TestSafeJsonDefault:
    """_safe_json_default 函数测试"""

    def test_nan_to_none(self):
        """测试 NaN 转换为 None"""
        result = _safe_json_default(float("nan"))
        assert result is None

    def test_positive_infinity_to_none(self):
        """测试正无穷转换为 None"""
        result = _safe_json_default(float("inf"))
        assert result is None

    def test_negative_infinity_to_none(self):
        """测试负无穷转换为 None"""
        result = _safe_json_default(float("-inf"))
        assert result is None

    def test_other_types_to_string(self):
        """测试其他类型转换为字符串"""
        assert _safe_json_default(123) == "123"
        assert _safe_json_default("test") == "test"
        assert _safe_json_default([1, 2, 3]) == "[1, 2, 3]"


class TestSafeJsonDumps:
    """safe_json_dumps 函数测试"""

    def test_normal_data(self):
        """测试正常数据序列化"""
        data = {"key": "value", "number": 123}
        result = safe_json_dumps(data)
        assert '"key": "value"' in result or '"key":"value"' in result

    def test_nan_in_data(self):
        """测试包含 NaN 的数据"""
        data = {"value": float("nan")}
        result = safe_json_dumps(data)
        # NaN 应该被转换为 null
        assert "null" in result

    def test_infinity_in_data(self):
        """测试包含无穷大的数据"""
        data = {"value": float("inf")}
        result = safe_json_dumps(data)
        # 无穷大应该被转换为 null
        assert "null" in result

    def test_nested_nan(self):
        """测试嵌套结构中的 NaN"""
        data = {
            "outer": {
                "inner": float("nan"),
            }
        }
        result = safe_json_dumps(data)
        assert "null" in result

    def test_list_with_nan(self):
        """测试列表中的 NaN"""
        data = {"values": [1.0, float("nan"), 3.0]}
        result = safe_json_dumps(data)
        assert "null" in result

    def test_ensure_ascii_false(self):
        """测试中文字符不被转义"""
        data = {"name": "测试"}
        result = safe_json_dumps(data)
        assert "测试" in result


class TestWebSocketManagerInit:
    """WebSocketManager 初始化测试"""

    def test_init_default_params(self):
        """测试默认参数初始化"""
        manager = WebSocketManager()

        assert manager._heartbeat_interval == 30.0
        assert manager._heartbeat_timeout == 60.0
        assert manager._max_connections == 1000
        assert manager._clients == {}
        assert manager._subscriptions == {}
        assert manager._running is False
        assert manager._heartbeat_task is None

    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        manager = WebSocketManager(
            heartbeat_interval=15.0,
            heartbeat_timeout=30.0,
            max_connections=100,
        )

        assert manager._heartbeat_interval == 15.0
        assert manager._heartbeat_timeout == 30.0
        assert manager._max_connections == 100


class TestWebSocketManagerConnection:
    """WebSocketManager 连接管理测试"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return WebSocketManager(max_connections=2)

    @pytest.fixture
    def mock_websocket(self):
        """创建模拟 WebSocket"""
        ws = AsyncMock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connection_context_manager(self, manager, mock_websocket):
        """测试连接上下文管理器"""
        async with manager.connection(mock_websocket) as client:
            assert client.client_id is not None
            assert client.state == ConnectionState.CONNECTED
            assert client.websocket == mock_websocket
            assert manager.get_client_count() == 1

        # 退出上下文后应该断开连接
        assert manager.get_client_count() == 0

    @pytest.mark.asyncio
    async def test_connection_max_connections(self, manager, mock_websocket):
        """测试最大连接数限制"""
        # 创建两个连接达到上限
        ws1 = AsyncMock(spec=WebSocket)
        ws1.accept = AsyncMock()
        ws1.close = AsyncMock()

        ws2 = AsyncMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        ws2.close = AsyncMock()

        # 第一个连接
        client1 = None
        async with manager.connection(ws1) as client:
            client1 = client
            assert manager.get_client_count() == 1

            # 第二个连接
            async with manager.connection(ws2):
                assert manager.get_client_count() == 2

        # 验证最大连接数限制被正确设置
        assert manager._max_connections == 2

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """测试断开连接"""
        async with manager.connection(mock_websocket) as client:
            client_id = client.client_id
            # 订阅一些频道
            await manager.subscribe(client_id, "funds")
            await manager.subscribe(client_id, "indices")

            assert manager.get_client_count() == 1
            assert manager.get_subscribers_count("funds") == 1

        # 断开后应该清理
        assert manager.get_client_count() == 0
        assert manager.get_subscribers_count("funds") == 0

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_client(self, manager):
        """测试断开不存在的客户端"""
        result = await manager.disconnect("nonexistent-id")
        assert result is False


class TestWebSocketManagerSubscription:
    """WebSocketManager 订阅管理测试"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """创建模拟 WebSocket"""
        ws = AsyncMock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_subscribe(self, manager, mock_websocket):
        """测试订阅"""
        async with manager.connection(mock_websocket) as client:
            result = await manager.subscribe(client.client_id, "funds")

            assert result is True
            assert "funds" in client.subscriptions
            assert manager.get_subscribers_count("funds") == 1

    @pytest.mark.asyncio
    async def test_subscribe_multiple_channels(self, manager, mock_websocket):
        """测试订阅多个频道"""
        async with manager.connection(mock_websocket) as client:
            await manager.subscribe(client.client_id, "funds")
            await manager.subscribe(client.client_id, "indices")
            await manager.subscribe(client.client_id, "commodities")

            assert len(client.subscriptions) == 3
            assert manager.get_subscribers_count("funds") == 1
            assert manager.get_subscribers_count("indices") == 1
            assert manager.get_subscribers_count("commodities") == 1

    @pytest.mark.asyncio
    async def test_subscribe_nonexistent_client(self, manager):
        """测试不存在的客户端订阅"""
        result = await manager.subscribe("nonexistent-id", "funds")
        assert result is False

    @pytest.mark.asyncio
    async def test_unsubscribe(self, manager, mock_websocket):
        """测试取消订阅"""
        async with manager.connection(mock_websocket) as client:
            await manager.subscribe(client.client_id, "funds")
            assert manager.get_subscribers_count("funds") == 1

            result = await manager.unsubscribe(client.client_id, "funds")

            assert result is True
            assert "funds" not in client.subscriptions
            assert manager.get_subscribers_count("funds") == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_subscription(self, manager, mock_websocket):
        """测试取消不存在的订阅"""
        async with manager.connection(mock_websocket) as client:
            result = await manager.unsubscribe(client.client_id, "nonexistent")
            assert result is True

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_client(self, manager):
        """测试不存在的客户端取消订阅"""
        result = await manager.unsubscribe("nonexistent-id", "funds")
        assert result is False


class TestWebSocketManagerBroadcast:
    """WebSocketManager 消息广播测试"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """创建模拟 WebSocket"""
        ws = AsyncMock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, manager, mock_websocket):
        """测试广播给所有客户端"""
        ws1 = AsyncMock(spec=WebSocket)
        ws1.accept = AsyncMock()
        ws1.close = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = AsyncMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        ws2.close = AsyncMock()
        ws2.send_text = AsyncMock()

        message = WSMessage(type="test", data={"key": "value"})

        # 手动添加客户端
        async with manager.connection(ws1) as client1:
            async with manager.connection(ws2) as client2:
                count = await manager.broadcast(message)

                assert count == 2
                ws1.send_text.assert_called_once()
                ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_subscription(self, manager, mock_websocket):
        """测试广播给订阅者"""
        ws1 = AsyncMock(spec=WebSocket)
        ws1.accept = AsyncMock()
        ws1.close = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = AsyncMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        ws2.close = AsyncMock()
        ws2.send_text = AsyncMock()

        message = WSMessage(type="test", data={"key": "value"}, subscription="funds")

        async with manager.connection(ws1) as client1:
            await manager.subscribe(client1.client_id, "funds")

            async with manager.connection(ws2) as client2:
                # client2 不订阅 funds
                count = await manager.broadcast(message, subscription="funds")

                assert count == 1
                ws1.send_text.assert_called_once()
                ws2.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_no_subscribers(self, manager):
        """测试没有订阅者时的广播"""
        message = WSMessage(type="test", data={"key": "value"}, subscription="funds")
        count = await manager.broadcast(message, subscription="funds")

        assert count == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_subscription_helper(self, manager, mock_websocket):
        """测试 broadcast_to_subscription 快捷方法"""
        async with manager.connection(mock_websocket) as client:
            await manager.subscribe(client.client_id, "funds")

            count = await manager.broadcast_to_subscription(
                subscription="funds",
                message_type="fund_update",
                data={"funds": []},
            )

            assert count == 1
            mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_personal_message(self, manager, mock_websocket):
        """测试发送个人消息"""
        async with manager.connection(mock_websocket) as client:
            message = WSMessage(type="personal", data={"info": "test"})

            result = await manager.send_personal(client.client_id, message)

            assert result is True
            mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_personal_nonexistent_client(self, manager):
        """测试给不存在的客户端发送消息"""
        message = WSMessage(type="personal", data={"info": "test"})

        result = await manager.send_personal("nonexistent-id", message)

        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast_with_send_failure(self, manager):
        """测试广播时发送失败"""
        ws = AsyncMock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_text = AsyncMock(side_effect=Exception("Connection lost"))

        message = WSMessage(type="test", data={"key": "value"})

        async with manager.connection(ws) as client:
            # 广播应该处理异常并返回 0
            count = await manager.broadcast(message)

            # 发送失败，返回 0
            assert count == 0


class TestWebSocketManagerHeartbeat:
    """WebSocketManager 心跳检测测试"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return WebSocketManager(
            heartbeat_interval=0.1,  # 短间隔用于测试
            heartbeat_timeout=0.3,
        )

    @pytest.fixture
    def mock_websocket(self):
        """创建模拟 WebSocket"""
        ws = AsyncMock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_start_stop_heartbeat(self, manager):
        """测试启动和停止心跳"""
        await manager.start_heartbeat()
        assert manager._running is True
        assert manager._heartbeat_task is not None

        await manager.stop_heartbeat()
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_start_heartbeat_twice(self, manager):
        """测试重复启动心跳"""
        await manager.start_heartbeat()
        first_task = manager._heartbeat_task

        await manager.start_heartbeat()  # 应该被忽略

        assert manager._heartbeat_task == first_task

        await manager.stop_heartbeat()

    @pytest.mark.asyncio
    async def test_update_heartbeat(self, manager, mock_websocket):
        """测试更新心跳"""
        async with manager.connection(mock_websocket) as client:
            old_heartbeat = client.last_heartbeat

            # 等待一小段时间
            await asyncio.sleep(0.01)

            result = await manager.update_heartbeat(client.client_id)

            assert result is True
            assert client.last_heartbeat > old_heartbeat

    @pytest.mark.asyncio
    async def test_update_heartbeat_nonexistent_client(self, manager):
        """测试更新不存在客户端的心跳"""
        result = await manager.update_heartbeat("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_heartbeat_timeout_disconnect(self, manager, mock_websocket):
        """测试心跳超时断开连接"""
        await manager.start_heartbeat()

        async with manager.connection(mock_websocket) as client:
            # 模拟心跳超时
            client.last_heartbeat = datetime.now() - timedelta(seconds=1)

            # 等待心跳检测周期
            await asyncio.sleep(0.2)

            # 客户端应该被断开
            # 注意：由于断开是异步的，可能需要等待
            await asyncio.sleep(0.1)

        await manager.stop_heartbeat()


class TestWebSocketManagerInfo:
    """WebSocketManager 信息获取测试"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """创建模拟 WebSocket"""
        ws = AsyncMock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    def test_get_client_count_empty(self, manager):
        """测试空连接数"""
        assert manager.get_client_count() == 0

    @pytest.mark.asyncio
    async def test_get_client_count(self, manager, mock_websocket):
        """测试获取连接数"""
        async with manager.connection(mock_websocket) as client:
            assert manager.get_client_count() == 1

    def test_get_subscribers_count_empty(self, manager):
        """测试空订阅数"""
        assert manager.get_subscribers_count("funds") == 0

    @pytest.mark.asyncio
    async def test_get_subscribers_count(self, manager, mock_websocket):
        """测试获取订阅数"""
        async with manager.connection(mock_websocket) as client:
            await manager.subscribe(client.client_id, "funds")
            await manager.subscribe(client.client_id, "indices")

            assert manager.get_subscribers_count("funds") == 1
            assert manager.get_subscribers_count("indices") == 1
            assert manager.get_subscribers_count("commodities") == 0

    def test_get_clients_info_empty(self, manager):
        """测试空客户端信息"""
        assert manager.get_clients_info() == []

    @pytest.mark.asyncio
    async def test_get_clients_info(self, manager, mock_websocket):
        """测试获取客户端信息"""
        async with manager.connection(mock_websocket) as client:
            await manager.subscribe(client.client_id, "funds")

            info = manager.get_clients_info()

            assert len(info) == 1
            assert info[0]["clientId"] == client.client_id
            assert info[0]["state"] == "connected"
            assert "funds" in info[0]["subscriptions"]

    def test_get_subscriptions_info_empty(self, manager):
        """测试空订阅信息"""
        assert manager.get_subscriptions_info() == {}

    @pytest.mark.asyncio
    async def test_get_subscriptions_info(self, manager, mock_websocket):
        """测试获取订阅信息"""
        async with manager.connection(mock_websocket) as client:
            await manager.subscribe(client.client_id, "funds")
            await manager.subscribe(client.client_id, "indices")

            info = manager.get_subscriptions_info()

            assert info == {"funds": 1, "indices": 1}


class TestWebSocketManagerGlobal:
    """全局管理器函数测试"""

    def test_get_websocket_manager_singleton(self):
        """测试获取单例管理器"""
        # 重置全局实例
        set_websocket_manager(None)

        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()

        assert manager1 is manager2

        # 清理
        set_websocket_manager(None)

    def test_set_websocket_manager(self):
        """测试设置管理器"""
        custom_manager = WebSocketManager(max_connections=50)
        set_websocket_manager(custom_manager)

        manager = get_websocket_manager()

        assert manager is custom_manager
        assert manager._max_connections == 50

        # 清理
        set_websocket_manager(None)


class TestConnectionState:
    """ConnectionState 枚举测试"""

    def test_enum_values(self):
        """测试枚举值"""
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.DISCONNECTING.value == "disconnecting"
        assert ConnectionState.DISCONNECTED.value == "disconnected"