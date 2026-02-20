"""
WebSocket 连接管理器模块

提供 WebSocket 客户端连接管理、订阅管理、消息广播功能。
支持按数据类型订阅、连接状态追踪、线程安全的实现。
"""

import asyncio
import logging
import uuid
from asyncio import Queue
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """连接状态枚举"""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


@dataclass
class WSMessage:
    """WebSocket 消息"""

    type: str
    data: Any
    timestamp: datetime = field(default_factory=datetime.now)
    subscription: str | None = None


@dataclass
class WSClient:
    """WebSocket 客户端"""

    client_id: str
    websocket: WebSocket
    subscriptions: set[str] = field(default_factory=set)
    state: ConnectionState = ConnectionState.CONNECTING
    connected_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_alive(self, heartbeat_timeout: float = 60.0) -> bool:
        """检查客户端是否存活（心跳超时检测）"""
        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
        return elapsed < heartbeat_timeout


class WebSocketManager:
    """
    WebSocket 连接管理器

    提供:
    - WebSocket 连接管理（连接、断开、心跳）
    - 订阅管理（支持按数据类型订阅）
    - 消息广播（向所有订阅者推送消息）
    - 连接状态追踪
    - 线程安全的实现
    """

    def __init__(
        self,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 60.0,
        max_connections: int = 1000,
    ):
        """
        初始化 WebSocket 管理器

        Args:
            heartbeat_interval: 心跳间隔（秒）
            heartbeat_timeout: 心跳超时（秒）
            max_connections: 最大连接数
        """
        self._clients: dict[str, WSClient] = {}
        self._subscriptions: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_timeout = heartbeat_timeout
        self._max_connections = max_connections

        self._heartbeat_task: asyncio.Task | None = None
        self._running = False

        logger.info(
            f"WebSocketManager 初始化完成: heartbeat_interval={heartbeat_interval}s, "
            f"heartbeat_timeout={heartbeat_timeout}s, max_connections={max_connections}"
        )

    @asynccontextmanager
    async def connection(self, websocket: WebSocket):
        """
        WebSocket 连接上下文管理器

        Args:
            websocket: FastAPI WebSocket 连接

        Yields:
            WSClient: 客户端实例
        """
        client_id = str(uuid.uuid4())
        client = WSClient(client_id=client_id, websocket=websocket)

        async with self._lock:
            if len(self._clients) >= self._max_connections:
                logger.warning(f"WebSocket 连接数已达上限: {self._max_connections}")
                await websocket.close(code=1013, reason="Server full")
                return

            self._clients[client_id] = client

        try:
            await websocket.accept()
            client.state = ConnectionState.CONNECTED
            logger.info(f"WebSocket 客户端连接: {client_id}, 当前连接数: {len(self._clients)}")

            yield client

        except Exception as e:
            logger.warning(f"WebSocket 连接异常: {client_id}, error: {e}")
            raise
        finally:
            await self.disconnect(client_id)
            logger.info(f"WebSocket 客户端断开: {client_id}, 当前连接数: {len(self._clients)}")

    async def disconnect(self, client_id: str) -> bool:
        """
        断开客户端连接

        Args:
            client_id: 客户端 ID

        Returns:
            bool: 是否成功断开
        """
        async with self._lock:
            client = self._clients.get(client_id)
            if not client:
                return False

            client.state = ConnectionState.DISCONNECTING

            for subscription in client.subscriptions:
                if subscription in self._subscriptions:
                    self._subscriptions[subscription].discard(client_id)
                    if not self._subscriptions[subscription]:
                        del self._subscriptions[subscription]

            try:
                await client.websocket.close()
            except Exception as e:
                logger.debug(f"关闭 WebSocket 连接时发生异常: {client_id}, error: {e}")

            del self._clients[client_id]
            client.state = ConnectionState.DISCONNECTED

        return True

    async def subscribe(self, client_id: str, subscription: str) -> bool:
        """
        客户端订阅数据类型

        Args:
            client_id: 客户端 ID
            subscription: 订阅类型（如 "funds", "commodities", "indices"）

        Returns:
            bool: 是否成功订阅
        """
        async with self._lock:
            client = self._clients.get(client_id)
            if not client or client.state != ConnectionState.CONNECTED:
                logger.warning(f"订阅失败: 客户端不存在或未连接: {client_id}")
                return False

            client.subscriptions.add(subscription)

            if subscription not in self._subscriptions:
                self._subscriptions[subscription] = set()
            self._subscriptions[subscription].add(client_id)

            logger.debug(f"客户端订阅: {client_id} -> {subscription}")
            return True

    async def unsubscribe(self, client_id: str, subscription: str) -> bool:
        """
        客户端取消订阅

        Args:
            client_id: 客户端 ID
            subscription: 订阅类型

        Returns:
            bool: 是否成功取消订阅
        """
        async with self._lock:
            client = self._clients.get(client_id)
            if not client:
                return False

            client.subscriptions.discard(subscription)

            if subscription in self._subscriptions:
                self._subscriptions[subscription].discard(client_id)
                if not self._subscriptions[subscription]:
                    del self._subscriptions[subscription]

            logger.debug(f"客户端取消订阅: {client_id} -> {subscription}")
            return True

    async def broadcast(
        self,
        message: WSMessage,
        subscription: str | None = None,
    ) -> int:
        """
        广播消息给订阅者

        Args:
            message: 消息内容
            subscription: 订阅类型（仅发送给订阅此类型的客户端，None 表示发送给所有客户端）

        Returns:
            int: 成功发送的数量
        """
        client_ids: set[str]

        async with self._lock:
            if subscription:
                client_ids = self._subscriptions.get(subscription, set()).copy()
            else:
                client_ids = set(self._clients.keys())

        if not client_ids:
            logger.debug(f"广播消息: 无订阅者, type={message.type}")
            return 0

        import json

        try:
            payload = json.dumps(
                {
                    "type": message.type,
                    "data": message.data,
                    "timestamp": message.timestamp.isoformat(),
                },
                ensure_ascii=False,
                default=str,
            )
        except Exception as e:
            logger.error(f"序列化消息失败: {e}")
            return 0

        async def send_to_client(client_id: str) -> bool:
            async with self._lock:
                client = self._clients.get(client_id)
                if not client or client.state != ConnectionState.CONNECTED:
                    return False

            try:
                await client.websocket.send_text(payload)
                client.last_heartbeat = datetime.now()
                return True
            except Exception as e:
                logger.warning(f"发送消息失败: {client_id}, error: {e}")
                await self.disconnect(client_id)
                return False

        results = await asyncio.gather(
            *[send_to_client(cid) for cid in client_ids],
            return_exceptions=True,
        )

        success_count = sum(1 for r in results if r is True)
        logger.debug(
            f"广播消息: type={message.type}, subscription={subscription}, "
            f"success={success_count}/{len(client_ids)}"
        )

        return success_count

    async def send_personal(
        self,
        client_id: str,
        message: WSMessage,
    ) -> bool:
        """
        发送消息给特定客户端

        Args:
            client_id: 客户端 ID
            message: 消息内容

        Returns:
            bool: 是否发送成功
        """
        import json

        async with self._lock:
            client = self._clients.get(client_id)
            if not client or client.state != ConnectionState.CONNECTED:
                return False

        try:
            payload = json.dumps(
                {
                    "type": message.type,
                    "data": message.data,
                    "timestamp": message.timestamp.isoformat(),
                },
                ensure_ascii=False,
                default=str,
            )
            await client.websocket.send_text(payload)
            client.last_heartbeat = datetime.now()
            return True
        except Exception as e:
            logger.warning(f"发送个人消息失败: {client_id}, error: {e}")
            await self.disconnect(client_id)
            return False

    async def broadcast_to_subscription(
        self,
        subscription: str,
        message_type: str,
        data: Any,
    ) -> int:
        """
        快捷方法：向订阅者广播消息

        Args:
            subscription: 订阅类型
            message_type: 消息类型
            data: 消息数据

        Returns:
            int: 成功发送的数量
        """
        message = WSMessage(type=message_type, data=data, subscription=subscription)
        return await self.broadcast(message, subscription=subscription)

    async def update_heartbeat(self, client_id: str) -> bool:
        """
        更新客户端心跳

        Args:
            client_id: 客户端 ID

        Returns:
            bool: 是否更新成功
        """
        async with self._lock:
            client = self._clients.get(client_id)
            if not client:
                return False
            client.last_heartbeat = datetime.now()
        return True

    async def start_heartbeat(self):
        """启动心跳检测任务"""
        if self._running:
            return

        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocket 心跳任务已启动")

    async def stop_heartbeat(self):
        """停止心跳检测任务"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket 心跳任务已停止")

    async def _heartbeat_loop(self):
        """心跳检测循环"""
        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                await self._check_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳检测循环异常: {e}")

    async def _check_heartbeat(self):
        """检查客户端心跳，超时断开"""
        disconnected_ids = []

        async with self._lock:
            for client_id, client in self._clients.items():
                if not client.is_alive(self._heartbeat_timeout):
                    logger.warning(
                        f"客户端心跳超时: {client_id}, timeout={self._heartbeat_timeout}s"
                    )
                    disconnected_ids.append(client_id)

        for client_id in disconnected_ids:
            await self.disconnect(client_id)

    def get_client_count(self) -> int:
        """获取当前连接数"""
        return len(self._clients)

    def get_subscribers_count(self, subscription: str) -> int:
        """获取指定订阅类型的订阅者数量"""
        return len(self._subscriptions.get(subscription, set()))

    def get_clients_info(self) -> list[dict[str, Any]]:
        """获取所有客户端信息"""
        result = []
        for client in self._clients.values():
            result.append(
                {
                    "client_id": client.client_id,
                    "state": client.state.value,
                    "subscriptions": list(client.subscriptions),
                    "connected_at": client.connected_at.isoformat(),
                    "last_heartbeat": client.last_heartbeat.isoformat(),
                }
            )
        return result

    def get_subscriptions_info(self) -> dict[str, int]:
        """获取所有订阅信息"""
        return {sub: len(clients) for sub, clients in self._subscriptions.items()}


_ws_manager: WebSocketManager | None = None


def get_websocket_manager() -> WebSocketManager:
    """获取全局 WebSocket 管理器实例"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


def set_websocket_manager(manager: WebSocketManager) -> None:
    """设置全局 WebSocket 管理器实例（用于测试）"""
    global _ws_manager
    _ws_manager = manager
