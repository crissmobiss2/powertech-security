"""WebSocket connection manager with Redis pub/sub for real-time threat push.

Each FastAPI worker process maintains its own set of WebSocket connections.
Redis pub/sub fans out events across all workers so every connected client
gets notified regardless of which process accepted the WebSocket.

Channels:
  vision:threats:{tenant_id}  — threat detections
  vision:faces:{tenant_id}    — face detection events
  vision:cameras:{tenant_id}  — camera status changes
  vision:system:{tenant_id}   — system-wide alerts (lockdown, etc.)
"""
import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._redis: Redis | None = None
        self._pubsub_task: asyncio.Task | None = None
        self._running = False

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
            )
        return self._redis

    async def start_pubsub_listener(self):
        if self._running:
            return
        self._running = True
        self._pubsub_task = asyncio.create_task(self._listen_redis())

    async def _listen_redis(self):
        redis = await self._get_redis()
        pubsub = redis.pubsub()
        await pubsub.psubscribe("vision:*")
        try:
            while self._running:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "pmessage":
                    channel = message["channel"]
                    data = message["data"]
                    parts = channel.split(":")
                    if len(parts) >= 3:
                        tenant_id = parts[2]
                        await self._broadcast_to_tenant(tenant_id, data)
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Redis pub/sub listener error")
        finally:
            await pubsub.punsubscribe("vision:*")
            await pubsub.close()

    async def _broadcast_to_tenant(self, tenant_id: str, raw_data: str):
        connections = self._connections.get(tenant_id, set())
        if not connections:
            return
        dead = []
        for ws in connections:
            try:
                await ws.send_text(raw_data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            connections.discard(ws)

    async def connect(self, websocket: WebSocket, tenant_id: str):
        await websocket.accept()
        self._connections[tenant_id].add(websocket)
        logger.info(
            "WebSocket connected: tenant=%s, total=%d",
            tenant_id,
            len(self._connections[tenant_id]),
        )
        if not self._running:
            await self.start_pubsub_listener()

    def disconnect(self, websocket: WebSocket, tenant_id: str):
        self._connections[tenant_id].discard(websocket)
        if not self._connections[tenant_id]:
            del self._connections[tenant_id]
        logger.info("WebSocket disconnected: tenant=%s", tenant_id)

    async def shutdown(self):
        self._running = False
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass
        if self._redis:
            await self._redis.close()


ws_manager = ConnectionManager()


async def publish_event(
    channel: str,
    event_type: str,
    payload: dict[str, Any],
    tenant_id: str | UUID,
):
    """Publish an event to Redis for fan-out to all WebSocket clients."""
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        message = json.dumps({
            "type": event_type,
            "payload": _serialize(payload),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        full_channel = f"{channel}:{tenant_id}"
        await redis.publish(full_channel, message)
    finally:
        await redis.close()


def _serialize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(i) for i in obj]
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj
