"""
WebSocket 实时推送路由
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.utils.websocket_manager import WSMessage, get_websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/realtime")
async def websocket_realtime(websocket: WebSocket):
    """WebSocket realtime data push endpoint"""
    manager = get_websocket_manager()

    async with manager.connection(websocket) as client:
        if client is None:
            return

        await manager.start_heartbeat()

        try:
            while True:
                try:
                    raw_message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=60.0,
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Client {client.client_id} message timeout")
                    break

                try:
                    message = json.loads(raw_message)
                    action = message.get("action")
                    data = message.get("data")

                    if action == "subscribe":
                        if isinstance(data, list):
                            for subscription in data:
                                await manager.subscribe(client.client_id, subscription)
                            await manager.send_personal(
                                client.client_id,
                                WSMessage(
                                    type="subscribed",
                                    data={"subscriptions": list(client.subscriptions)},
                                ),
                            )
                        elif isinstance(data, str):
                            await manager.subscribe(client.client_id, data)
                            await manager.send_personal(
                                client.client_id,
                                WSMessage(
                                    type="subscribed",
                                    data={"subscriptions": [data]},
                                ),
                            )

                    elif action == "unsubscribe":
                        if isinstance(data, list):
                            for subscription in data:
                                await manager.unsubscribe(client.client_id, subscription)
                        elif isinstance(data, str):
                            await manager.unsubscribe(client.client_id, data)

                    elif action == "ping":
                        await manager.update_heartbeat(client.client_id)
                        await manager.send_personal(
                            client.client_id,
                            WSMessage(type="pong", data={"time": "ok"}),
                        )

                    elif action == "get_subscriptions":
                        await manager.send_personal(
                            client.client_id,
                            WSMessage(
                                type="subscriptions",
                                data={"subscriptions": list(client.subscriptions)},
                            ),
                        )

                    else:
                        logger.warning(f"Unknown action: {action}")

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON: {raw_message}")
                except Exception as e:
                    logger.error(f"Message handling error: {e}")

        except WebSocketDisconnect:
            logger.info(f"Client disconnected: {client.client_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            for subscription in list(client.subscriptions):
                await manager.unsubscribe(client.client_id, subscription)


@router.get("/manager/status")
async def get_ws_status():
    """Get WebSocket connection status"""
    manager = get_websocket_manager()
    return {
        "connections": manager.get_client_count(),
        "subscriptions": manager.get_subscriptions_info(),
        "clients": manager.get_clients_info(),
    }


@router.post("/manager/broadcast")
async def broadcast_msg(
    subscription: str,
    message_type: str,
    data: dict[str, Any],
):
    """Broadcast message to subscribers"""
    manager = get_websocket_manager()
    count = await manager.broadcast_to_subscription(
        subscription=subscription,
        message_type=message_type,
        data=data,
    )
    return {
        "success": True,
        "sent_count": count,
        "subscription": subscription,
        "message_type": message_type,
    }


async def push_fund_update(fund_data: dict[str, Any]):
    """Push fund update"""
    manager = get_websocket_manager()
    await manager.broadcast_to_subscription(
        subscription="funds",
        message_type="fund_update",
        data=fund_data,
    )


async def push_commodity_update(commodity_data: dict[str, Any]):
    """Push commodity update"""
    manager = get_websocket_manager()
    await manager.broadcast_to_subscription(
        subscription="commodities",
        message_type="commodity_update",
        data=commodity_data,
    )


async def push_index_update(index_data: dict[str, Any]):
    """Push index update"""
    manager = get_websocket_manager()
    await manager.broadcast_to_subscription(
        subscription="indices",
        message_type="index_update",
        data=index_data,
    )


async def push_sector_update(sector_data: dict[str, Any]):
    """Push sector update"""
    manager = get_websocket_manager()
    await manager.broadcast_to_subscription(
        subscription="sectors",
        message_type="sector_update",
        data=sector_data,
    )


async def push_stock_update(stock_data: dict[str, Any]):
    """Push stock update"""
    manager = get_websocket_manager()
    await manager.broadcast_to_subscription(
        subscription="stocks",
        message_type="stock_update",
        data=stock_data,
    )


async def push_bond_update(bond_data: dict[str, Any]):
    """Push bond update"""
    manager = get_websocket_manager()
    await manager.broadcast_to_subscription(
        subscription="bonds",
        message_type="bond_update",
        data=bond_data,
    )


async def push_all_update(data: dict[str, Any]):
    """Push full data update"""
    manager = get_websocket_manager()
    await manager.broadcast_to_subscription(
        subscription="all",
        message_type="data_update",
        data=data,
    )
