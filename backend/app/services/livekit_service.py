"""
LiveKit WebRTC session management.

LiveKit is an open-source WebRTC infrastructure for real-time video/audio.
It handles TURN/STUN, media relaying, and recording server-side.

This service creates access tokens and room configurations for:
1. Live camera feed viewing in the browser (client watches CCTV streams)
2. Webcam enrollment (user presents their face for encoding)
3. Security officer live feeds (multi-camera grid)

Installation: pip install livekit-api
Environment: LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL
"""
import logging
import os
from datetime import timedelta

logger = logging.getLogger(__name__)

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")

_livekit_available = False
try:
    from livekit import api as lk_api
    _livekit_available = bool(LIVEKIT_API_KEY and LIVEKIT_API_SECRET)
except ImportError:
    logger.warning("livekit-api not installed — WebRTC features require it")


class LiveKitService:
    """Create LiveKit rooms and JWT access tokens."""

    TOKEN_TTL = timedelta(hours=4)

    def create_camera_viewer_token(
        self,
        user_id: str,
        camera_id: str,
        tenant_id: str,
        can_publish: bool = False,
    ) -> dict:
        """
        Generate a LiveKit token for a user to view a camera feed.
        The RTSP stream should be published by the backend via LiveKit Ingress.
        """
        room_name = f"cam-{camera_id}"
        return self._make_token(
            identity=f"user-{user_id}",
            name=f"Security User",
            room=room_name,
            room_join=True,
            can_publish=can_publish,
            can_subscribe=True,
            can_publish_data=False,
            metadata=f'{{"tenant_id":"{tenant_id}","camera_id":"{camera_id}"}}',
        )

    def create_enrollment_token(self, user_id: str, tenant_id: str) -> dict:
        """
        Token for webcam face enrollment session.
        User publishes their webcam; backend subscribes and processes frames.
        """
        room_name = f"enroll-{tenant_id}-{user_id}"
        return self._make_token(
            identity=f"enrollee-{user_id}",
            name="Enrollment Session",
            room=room_name,
            room_join=True,
            can_publish=True,
            can_subscribe=False,
            can_publish_data=True,
            metadata=f'{{"type":"enrollment","tenant_id":"{tenant_id}"}}',
        )

    def create_operator_token(self, operator_id: str, tenant_id: str) -> dict:
        """
        Token for security operator to join a multi-camera monitoring room.
        """
        room_name = f"ops-{tenant_id}"
        return self._make_token(
            identity=f"operator-{operator_id}",
            name="Security Operator",
            room=room_name,
            room_join=True,
            can_publish=False,
            can_subscribe=True,
            can_publish_data=True,
            metadata=f'{{"type":"operator","tenant_id":"{tenant_id}"}}',
        )

    def _make_token(
        self,
        identity: str,
        name: str,
        room: str,
        room_join: bool,
        can_publish: bool,
        can_subscribe: bool,
        can_publish_data: bool,
        metadata: str = "",
    ) -> dict:
        if not _livekit_available:
            return {
                "token": None,
                "room": room,
                "livekit_url": LIVEKIT_URL,
                "error": "LiveKit not configured (missing API key/secret or package)",
            }

        try:
            token = (
                lk_api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
                .with_identity(identity)
                .with_name(name)
                .with_metadata(metadata)
                .with_ttl(self.TOKEN_TTL)
                .with_grants(
                    lk_api.VideoGrants(
                        room_join=room_join,
                        room=room,
                        can_publish=can_publish,
                        can_subscribe=can_subscribe,
                        can_publish_data=can_publish_data,
                    )
                )
                .to_jwt()
            )
            return {
                "token": token,
                "room": room,
                "livekit_url": LIVEKIT_URL,
                "error": None,
            }
        except Exception as e:
            logger.error("LiveKit token creation failed: %s", e)
            return {"token": None, "room": room, "livekit_url": LIVEKIT_URL, "error": str(e)}

    async def create_ingress_for_camera(self, camera_id: str, rtsp_url: str) -> dict:
        """
        Create a LiveKit RTSP Ingress to pull from a camera and publish to a room.
        This makes the RTSP stream available as a WebRTC track in the browser.
        """
        if not _livekit_available:
            return {"error": "LiveKit not configured"}
        try:
            from livekit import api as lk_api
            ingress_client = lk_api.IngressClient(
                LIVEKIT_URL.replace("ws://", "http://").replace("wss://", "https://"),
                LIVEKIT_API_KEY,
                LIVEKIT_API_SECRET,
            )
            from livekit.protocol.ingress import (
                CreateIngressRequest, IngressInput, IngressVideoOptions,
                IngressVideoEncodingOptions, IngressVideoEncodingPreset,
            )
            request = CreateIngressRequest(
                input_type=IngressInput.RTSP_INPUT,
                name=f"camera-{camera_id}",
                room_name=f"cam-{camera_id}",
                participant_identity=f"camera-ingress-{camera_id}",
                url=rtsp_url,
                video=IngressVideoOptions(
                    encoding=IngressVideoEncodingOptions(
                        video_codec=1,  # H264
                        frame_rate=25,
                        layers=[IngressVideoEncodingPreset.H264_720P_30FPS_3_LAYERS_HIGH_MOTION],
                    )
                ),
            )
            response = await ingress_client.create_ingress(request)
            return {
                "ingress_id": response.ingress_id,
                "stream_key": response.stream_key,
                "url": response.url,
                "status": "created",
            }
        except Exception as e:
            logger.error("Ingress creation failed for camera %s: %s", camera_id, e)
            return {"error": str(e)}
