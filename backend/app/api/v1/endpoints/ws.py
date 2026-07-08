"""WebSocket endpoint for real-time vision threat push notifications."""
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError

from app.core.security import decode_token
from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/vision/live")
async def vision_live_feed(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    Real-time threat + detection feed.
    Connect with: ws://host/api/v1/ws/vision/live?token=<JWT>

    Pushes events:
      threat_detected, face_detected, banned_person,
      camera_status, system_alert
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001, reason="Invalid token type")
            return
        tenant_id = payload["tenant_id"]
        role = payload.get("role", "")
        permissions = payload.get("permissions", [])
    except (JWTError, KeyError, ValueError):
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    has_vision = (
        role == "super_admin"
        or "vision:read" in permissions
        or "*" in permissions
    )
    if not has_vision:
        await websocket.close(code=4003, reason="Missing vision:read permission")
        return

    await ws_manager.connect(websocket, tenant_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error for tenant %s", tenant_id)
    finally:
        ws_manager.disconnect(websocket, tenant_id)
