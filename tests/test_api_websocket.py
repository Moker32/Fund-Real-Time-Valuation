"""
websocket.py API 路由测试
测试 WebSocket 实时推送 API 端点的功能
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


class TestGetWsStatus:
    """测试 GET /ws/manager/status 端点"""

    def test_get_ws_status_success(self):
        """测试获取 WebSocket 连接状态"""
        with patch("api.routes.websocket.get_websocket_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_client_count.return_value = 5
            mock_manager.get_subscriptions_info.return_value = {
                "funds": 3,
                "indices": 2,
            }
            mock_manager.get_clients_info.return_value = [
                {"client_id": "test-1", "subscriptions": ["funds"]}
            ]
            mock_get_manager.return_value = mock_manager
            
            with TestClient(app) as client:
                response = client.get("/ws/manager/status")
            
            assert response.status_code == 200
            data = response.json()
            assert "connections" in data
            assert "subscriptions" in data
            assert "clients" in data
            assert data["connections"] == 5

    def test_get_ws_status_empty(self):
        """测试没有连接的情况"""
        with patch("api.routes.websocket.get_websocket_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_client_count.return_value = 0
            mock_manager.get_subscriptions_info.return_value = {}
            mock_manager.get_clients_info.return_value = []
            mock_get_manager.return_value = mock_manager
            
            with TestClient(app) as client:
                response = client.get("/ws/manager/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["connections"] == 0
            assert data["clients"] == []


class TestBroadcastMsg:
    """测试 POST /ws/manager/broadcast 端点"""

    def test_broadcast_msg_success(self):
        """测试广播消息成功 - 修复请求参数格式"""
        
        with patch("api.routes.websocket.get_websocket_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast_to_subscription = AsyncMock(return_value=3)
            mock_get_manager.return_value = mock_manager
            
            with TestClient(app) as client:
                # data 需要作为 JSON 字符串传递
                response = client.post(
                    "/ws/manager/broadcast",
                    params={
                        "subscription": "funds",
                        "message_type": "fund_update",
                    },
                    json={"fund_code": "000001", "price": 1.5},
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["sent_count"] == 3


class TestPushFunctions:
    """测试推送辅助函数"""

    @pytest.mark.asyncio
    async def test_push_fund_update(self):
        """测试推送基金更新"""
        with patch("api.routes.websocket.get_websocket_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast_to_subscription = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            from api.routes.websocket import push_fund_update
            await push_fund_update({"fund_code": "000001", "price": 1.5})
            
            mock_manager.broadcast_to_subscription.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_commodity_update(self):
        """测试推送商品更新"""
        with patch("api.routes.websocket.get_websocket_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast_to_subscription = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            from api.routes.websocket import push_commodity_update
            await push_commodity_update({"symbol": "AU9999", "price": 400.0})
            
            mock_manager.broadcast_to_subscription.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_index_update(self):
        """测试推送指数更新"""
        with patch("api.routes.websocket.get_websocket_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast_to_subscription = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            from api.routes.websocket import push_index_update
            await push_index_update({"index": "shanghai", "price": 3000.0})
            
            mock_manager.broadcast_to_subscription.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_sector_update(self):
        """测试推送板块更新"""
        with patch("api.routes.websocket.get_websocket_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast_to_subscription = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            from api.routes.websocket import push_sector_update
            await push_sector_update({"sector": "半导体", "change": 2.5})
            
            mock_manager.broadcast_to_subscription.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_all_update(self):
        """测试推送全量更新"""
        with patch("api.routes.websocket.get_websocket_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast_to_subscription = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            from api.routes.websocket import push_all_update
            await push_all_update({"type": "full_refresh", "timestamp": "2024-01-15"})
            
            mock_manager.broadcast_to_subscription.assert_called_once()


class TestWebSocketRouter:
    """测试 WebSocket 路由"""

    def test_websocket_route_exists(self):
        """测试 WebSocket 路由存在"""
        # 检查路由是否正确注册
        from api.routes import websocket
        
        # 验证 router 存在
        assert hasattr(websocket, "router")
        
        # 验证路由前缀
        assert websocket.router.prefix == "/ws"
        
        # 获取所有路由
        routes = [route.path for route in websocket.router.routes]
        
        # 验证路由 (注意路由前缀是 /ws)
        assert "/ws/realtime" in routes
        assert "/ws/manager/status" in routes
        assert "/ws/manager/broadcast" in routes
