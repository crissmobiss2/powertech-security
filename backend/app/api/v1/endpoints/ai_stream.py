"""
Real-time AI frame analysis via WebSocket + LiveKit token endpoints.

WebSocket endpoint (/ai-stream/ws/analyze) accepts:
- Base64-encoded JPEG/PNG frames from browser webcam or IP camera
- Returns: face detections, person analysis, threat scores, bounding boxes

LiveKit endpoints:
- POST /ai-stream/livekit/camera-token — viewer token for camera room
- POST /ai-stream/livekit/enrollment-token — enrollment session token
- POST /ai-stream/livekit/operator-token — multi-camera operator token
- POST /ai-stream/livekit/camera-ingress — create RTSP ingress for camera
"""
import base64
import json
import logging
from typing import Any
from uuid import UUID

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TokenClaims, require_permissions
from app.services.livekit_service import LiveKitService

logger = logging.getLogger(__name__)
router = APIRouter()

_person_analysis_svc = None


def _get_person_analysis():
    global _person_analysis_svc
    if _person_analysis_svc is None:
        from app.services.person_analysis_service import PersonAnalysisService
        _person_analysis_svc = PersonAnalysisService()
    return _person_analysis_svc


# ── WebSocket Frame Analysis ──────────────────────────────────────────────────

@router.websocket("/ws/analyze")
async def analyze_frame_ws(websocket: WebSocket):
    """
    Real-time frame analysis WebSocket.

    Client sends JSON:
    {
      "token": "<jwt>",
      "frame": "<base64-jpeg>",
      "camera_id": "<uuid-or-null>",
      "enable_face": true,
      "enable_threat": true,
      "enable_anomaly": false
    }

    Server responds JSON:
    {
      "faces": [...],
      "threats": [...],
      "anomaly_score": 0.0,
      "processing_ms": 45
    }
    """
    import time
    import cv2

    await websocket.accept()
    logger.info("AI stream WebSocket connected")

    # Lazy-load services after connection
    face_svc_class = None
    threat_svc_class = None
    person_svc = None
    known_encodings: list[np.ndarray] = []
    known_metadata: list[dict] = []

    try:
        async for raw_message in websocket.iter_text():
            t0 = time.monotonic()
            try:
                msg = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "invalid_json"})
                continue

            frame_b64 = msg.get("frame", "")
            if not frame_b64:
                await websocket.send_json({"error": "no_frame"})
                continue

            # Decode frame
            try:
                frame_bytes = base64.b64decode(frame_b64)
                frame_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
                if frame is None:
                    await websocket.send_json({"error": "invalid_frame"})
                    continue
            except Exception as e:
                await websocket.send_json({"error": f"decode_error: {e}"})
                continue

            result: dict[str, Any] = {
                "faces": [],
                "threats": [],
                "anomaly_score": 0.0,
                "processing_ms": 0,
            }

            # Face detection + recognition
            if msg.get("enable_face", True):
                try:
                    if face_svc_class is None:
                        from app.services.face_recognition_service import FaceRecognitionService
                        face_svc_class = FaceRecognitionService

                    class _Claims:
                        tenant_id = UUID("00000000-0000-0000-0000-000000000001")
                        user_id = UUID("00000000-0000-0000-0000-000000000001")
                        client_id = None
                        role = "super_admin"
                        permissions = ["*"]

                    # Stateless face detection without DB (no known encodings in browser mode)
                    from app.services.face_recognition_service import _get_insightface
                    fa = _get_insightface()
                    if fa is not None:
                        faces = fa.get(frame)
                        for face in faces:
                            bbox = face.bbox.astype(int)
                            x1, y1, x2, y2 = bbox
                            face_data = {
                                "bbox": {"x": int(x1), "y": int(y1), "w": int(x2 - x1), "h": int(y2 - y1)},
                                "det_score": round(float(face.det_score), 3),
                                "estimated_age": int(face.age) if hasattr(face, "age") and face.age is not None else None,
                                "gender": ("male" if face.gender == 1 else "female") if hasattr(face, "gender") and face.gender is not None else None,
                            }
                            # Quick emotion analysis
                            try:
                                person_svc = _get_person_analysis()
                                analysis = person_svc._deepface_emotion(
                                    frame[max(0, int(y1)):int(y2), max(0, int(x1)):int(x2)]
                                )
                                face_data["emotion"] = analysis.get("primary_emotion")
                                face_data["mood"] = analysis.get("mood_category")
                                face_data["emotion_confidence"] = analysis.get("confidence", 0)
                            except Exception:
                                pass
                            result["faces"].append(face_data)

                except Exception as e:
                    logger.debug("Face analysis error: %s", e)

            # Object/threat detection
            if msg.get("enable_threat", True):
                try:
                    if threat_svc_class is None:
                        from app.services.face_recognition_service import ThreatDetectionService
                        threat_svc_class = ThreatDetectionService

                    class _FakeClaims:
                        tenant_id = UUID("00000000-0000-0000-0000-000000000001")
                        user_id = UUID("00000000-0000-0000-0000-000000000001")
                        client_id = None

                    threat_svc = threat_svc_class(None, _FakeClaims())
                    threats = threat_svc.analyze_frame(
                        frame,
                        {"detection_confidence_threshold": msg.get("confidence_threshold", 0.6)},
                    )
                    result["threats"] = threats
                except Exception as e:
                    logger.debug("Threat detection error: %s", e)

            # Anomaly detection
            if msg.get("enable_anomaly", False):
                try:
                    camera_id = msg.get("camera_id", "browser")
                    from app.services.anomaly_detection_service import get_anomaly_service
                    anomaly_svc = get_anomaly_service(camera_id)
                    score, _ = anomaly_svc.score_frame(frame)
                    result["anomaly_score"] = score
                    result["anomaly_level"] = anomaly_svc.classify_score(score)["level"]
                except Exception as e:
                    logger.debug("Anomaly detection error: %s", e)

            result["processing_ms"] = round((time.monotonic() - t0) * 1000)
            await websocket.send_json(result)

    except WebSocketDisconnect:
        logger.info("AI stream WebSocket disconnected")
    except Exception as e:
        logger.error("AI stream WebSocket error: %s", e)
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass


# ── LiveKit Token Endpoints ───────────────────────────────────────────────────

class CameraTokenRequest(BaseModel):
    camera_id: str


class OperatorTokenRequest(BaseModel):
    pass


class EnrollmentTokenRequest(BaseModel):
    pass


class IngressRequest(BaseModel):
    camera_id: str
    rtsp_url: str


@router.post("/livekit/camera-token")
async def get_camera_viewer_token(
    body: CameraTokenRequest,
    claims: TokenClaims = Depends(require_permissions("vision:read")),
):
    """Get a LiveKit JWT to view a specific camera feed in the browser."""
    svc = LiveKitService()
    return svc.create_camera_viewer_token(
        user_id=str(claims.user_id),
        camera_id=body.camera_id,
        tenant_id=str(claims.tenant_id),
    )


@router.post("/livekit/enrollment-token")
async def get_enrollment_token(
    claims: TokenClaims = Depends(require_permissions("vision:write")),
):
    """Get a LiveKit JWT for a webcam face enrollment session."""
    svc = LiveKitService()
    return svc.create_enrollment_token(
        user_id=str(claims.user_id),
        tenant_id=str(claims.tenant_id),
    )


@router.post("/livekit/operator-token")
async def get_operator_token(
    claims: TokenClaims = Depends(require_permissions("vision:read")),
):
    """Get a LiveKit JWT for the security operator multi-camera room."""
    svc = LiveKitService()
    return svc.create_operator_token(
        operator_id=str(claims.user_id),
        tenant_id=str(claims.tenant_id),
    )


@router.post("/livekit/camera-ingress")
async def create_camera_ingress(
    body: IngressRequest,
    claims: TokenClaims = Depends(require_permissions("vision:write")),
):
    """Create a LiveKit RTSP Ingress to pull a camera stream into WebRTC."""
    svc = LiveKitService()
    result = await svc.create_ingress_for_camera(body.camera_id, body.rtsp_url)
    if result.get("error"):
        raise HTTPException(500, result["error"])
    return result


# ── SOAR Trigger Endpoints ────────────────────────────────────────────────────

class SOARAnalysisRequest(BaseModel):
    threat_id: str
    threat: dict
    camera: dict


@router.post("/soar/analyze")
async def run_soar(
    body: SOARAnalysisRequest,
    claims: TokenClaims = Depends(require_permissions("incidents:write")),
):
    """Run the LangGraph SOAR AI agent on a threat and get the automated response plan."""
    from app.services.soar_agent import run_soar_analysis
    result = await run_soar_analysis(
        threat=body.threat,
        camera=body.camera,
        tenant_id=str(claims.tenant_id),
    )
    return result


@router.post("/soar/crew-analyze")
async def run_crew_soar(
    body: SOARAnalysisRequest,
    claims: TokenClaims = Depends(require_permissions("incidents:write")),
):
    """
    Run the CrewAI multi-agent SOAR on a threat.
    Three specialized agents collaborate: Analyst → Coordinator → Reporter.
    Falls back to LangGraph SOAR if CrewAI is unavailable.
    """
    from app.services.crew_soar_service import run_crew_soar_analysis
    result = await run_crew_soar_analysis(
        threat=body.threat,
        camera=body.camera,
        tenant_id=str(claims.tenant_id),
    )
    return result


# ── Video Action Recognition Endpoint ─────────────────────────────────────────

class VideoActionRequest(BaseModel):
    frames: list[str]   # list of base64-encoded JPEG frames (8–16 frames)
    camera_id: str = "browser"


@router.post("/video-action/analyze")
async def analyze_video_action(
    body: VideoActionRequest,
    claims: TokenClaims = Depends(require_permissions("vision:read")),
):
    """
    Classify security actions in a video clip (8–16 frames).

    Detects: fighting, falling, running, crowd formation, suspicious movement.
    Uses VideoMAE (MCG-NJU/videomae-base-finetuned-kinetics) or optical flow fallback.
    """
    import base64
    import cv2

    if not body.frames:
        raise HTTPException(400, "No frames provided")
    if len(body.frames) > 64:
        raise HTTPException(400, "Too many frames (max 64)")

    try:
        from app.services.video_action_service import VideoActionService
        svc = VideoActionService(camera_id=body.camera_id)

        for frame_b64 in body.frames:
            frame_bytes = base64.b64decode(frame_b64)
            frame_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
            if frame is not None:
                svc.push_frame(frame)

        result = svc.get_latest_action()
        return {
            "action": result,
            "history": svc.get_action_history()[-3:],
            "frames_processed": len(body.frames),
        }
    except Exception as e:
        logger.error("Video action analysis error: %s", e)
        raise HTTPException(500, f"Video action analysis failed: {e}")


# ── Speaker Diarization Endpoint ──────────────────────────────────────────────

class DiarizationRequest(BaseModel):
    audio_base64: str   # base64-encoded WAV or raw PCM bytes
    sample_rate: int = 16000
    format: str = "wav"  # "wav" or "pcm_s16"


@router.post("/diarization/analyze")
async def diarize_audio(
    body: DiarizationRequest,
    claims: TokenClaims = Depends(require_permissions("vision:read")),
):
    """
    Speaker diarization — identifies who speaks when in audio.

    Requires pyannote.audio and HF_AUTH_TOKEN env var.
    Falls back to energy-based VAD (all speech labeled SPEAKER_00) if unavailable.
    """
    import base64

    try:
        audio_bytes = base64.b64decode(body.audio_base64)
        from app.services.speaker_diarization_service import get_diarization_service
        svc = get_diarization_service()

        if body.format == "wav":
            segments = svc.diarize_wav_bytes(audio_bytes)
        else:
            segments = svc.diarize_audio_bytes(audio_bytes, sample_rate=body.sample_rate)

        summary = svc.summarize_segments(segments)
        return {
            "segments": segments,
            "summary": summary,
        }
    except Exception as e:
        logger.error("Diarization error: %s", e)
        raise HTTPException(500, f"Diarization failed: {e}")


# ── Violence Detection Endpoint ───────────────────────────────────────────────

class ViolenceDetectionRequest(BaseModel):
    frames: list[str]   # base64 JPEG frames (8–16)
    camera_id: str = "browser"


@router.post("/violence/detect")
async def detect_violence(
    body: ViolenceDetectionRequest,
    claims: TokenClaims = Depends(require_permissions("vision:read")),
):
    """
    Specialized violence/fighting detection using nickmuchi/video-classification-fine-tuned-violence-detection.

    VideoMAE fine-tuned on the RWF-2000 real-world fighting surveillance dataset.
    More accurate than general Kinetics-400 models for security scenarios.
    Falls back to optical flow motion analysis if model unavailable.
    """
    import base64
    import cv2

    if not body.frames:
        raise HTTPException(400, "No frames provided")
    if len(body.frames) > 64:
        raise HTTPException(400, "Too many frames (max 64)")

    try:
        from app.services.violence_detection_service import get_violence_service
        svc = get_violence_service(body.camera_id)

        for frame_b64 in body.frames:
            frame_bytes = base64.b64decode(frame_b64)
            frame_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
            if frame is not None:
                svc.push_frame(frame)

        result = svc.get_latest()
        return {
            "result": result,
            "alert_worthy": svc.is_alert_worthy(result),
            "recent_alerts": svc.get_alerts(limit=5),
            "frames_processed": len(body.frames),
        }
    except Exception as e:
        logger.error("Violence detection error: %s", e)
        raise HTTPException(500, f"Violence detection failed: {e}")


# ── Scene Understanding Endpoint ──────────────────────────────────────────────

class SceneAnalysisRequest(BaseModel):
    image_base64: str
    task: str = "caption"   # caption|detailed_caption|detect|ocr|vqa
    query: str | None = None  # required for detect and vqa tasks


@router.post("/scene/understand")
async def understand_scene(
    body: SceneAnalysisRequest,
    claims: TokenClaims = Depends(require_permissions("vision:read")),
):
    """
    Florence-2 scene understanding (microsoft/Florence-2-base-ft).

    Tasks:
    - caption: one-sentence scene description
    - detailed_caption: multi-sentence description
    - detect: open-vocabulary detection ("person with weapon")
    - ocr: read all text with bounding boxes
    - vqa: visual question answering ("Is anyone running?")
    """
    import base64
    import cv2

    try:
        img_bytes = base64.b64decode(body.image_base64)
        img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise HTTPException(400, "Invalid image data")

        from app.services.scene_understanding_service import get_scene_service
        svc = get_scene_service()
        result = svc.analyze(frame, task=body.task, query=body.query)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Scene understanding error: %s", e)
        raise HTTPException(500, f"Scene understanding failed: {e}")


# ── OCR Endpoint ──────────────────────────────────────────────────────────────

class OCRRequest(BaseModel):
    image_base64: str
    target: str = "general"   # general|license_plate|id_card


@router.post("/ocr/read")
async def read_text_ocr(
    body: OCRRequest,
    claims: TokenClaims = Depends(require_permissions("vision:read")),
):
    """
    Extract text from CCTV frames using PaddleOCR (PP-OCRv4).

    Targets:
    - general: all visible text
    - license_plate: Philippine plate filtering (ABC 1234 / 1234 ABC)
    - id_card: document text extraction

    Falls back to Florence-2 OCR if PaddleOCR unavailable.
    """
    import base64
    import cv2

    try:
        img_bytes = base64.b64decode(body.image_base64)
        img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise HTTPException(400, "Invalid image data")

        from app.services.ocr_service import get_ocr_service
        svc = get_ocr_service()
        result = svc.read_frame(frame, target=body.target)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("OCR error: %s", e)
        raise HTTPException(500, f"OCR failed: {e}")


# ── Semantic Search Endpoint ──────────────────────────────────────────────────

class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = 10
    index_incidents: list[dict] | None = None  # optional batch to index first


@router.post("/semantic/search")
async def semantic_incident_search(
    body: SemanticSearchRequest,
    claims: TokenClaims = Depends(require_permissions("incidents:read")),
):
    """
    Semantic similarity search over incidents using sentence-transformers.

    Finds past incidents most similar to the query text.
    If index_incidents is provided, those are indexed first (useful for priming
    the search with the current tenant's incident list on first call).
    """
    from app.services.semantic_search_service import get_semantic_search_service
    svc = get_semantic_search_service(str(claims.tenant_id))

    if body.index_incidents:
        count = svc.index_batch(body.index_incidents)
        logger.info("Indexed %d incidents for tenant %s", count, claims.tenant_id)

    results = svc.search(body.query, top_k=body.limit)
    return {
        "query": body.query,
        "results": results,
        "index_stats": svc.index_stats(),
    }


# ── Speaker Verification Endpoints ────────────────────────────────────────────

class SpeakerEnrollRequest(BaseModel):
    audio_base64: str
    speaker_id: str
    display_name: str
    sample_rate: int = 16000


class SpeakerVerifyRequest(BaseModel):
    audio_base64: str
    speaker_id: str
    sample_rate: int = 16000


@router.post("/speaker/enroll")
async def enroll_speaker(
    body: SpeakerEnrollRequest,
    claims: TokenClaims = Depends(require_permissions("vision:write")),
):
    """
    Enroll a speaker voice sample using SpeechBrain ECAPA-TDNN.
    Multiple samples improve verification accuracy (up to 10 stored).
    """
    import base64

    try:
        audio_bytes = base64.b64decode(body.audio_base64)
        from app.services.speaker_verification_service import get_speaker_verification_service
        svc = get_speaker_verification_service(str(claims.tenant_id))
        return svc.enroll(body.speaker_id, body.display_name, audio_bytes, body.sample_rate)
    except Exception as e:
        logger.error("Speaker enrollment error: %s", e)
        raise HTTPException(500, f"Enrollment failed: {e}")


@router.post("/speaker/verify")
async def verify_speaker(
    body: SpeakerVerifyRequest,
    claims: TokenClaims = Depends(require_permissions("vision:read")),
):
    """
    Verify if an audio clip matches an enrolled speaker's voice.
    Returns score, threshold, and verification verdict.
    """
    import base64

    try:
        audio_bytes = base64.b64decode(body.audio_base64)
        from app.services.speaker_verification_service import get_speaker_verification_service
        svc = get_speaker_verification_service(str(claims.tenant_id))
        return svc.verify(body.speaker_id, audio_bytes, body.sample_rate)
    except Exception as e:
        logger.error("Speaker verification error: %s", e)
        raise HTTPException(500, f"Verification failed: {e}")


@router.get("/speaker/gallery")
async def speaker_gallery(
    claims: TokenClaims = Depends(require_permissions("vision:read")),
):
    """List enrolled speakers and their enrollment status."""
    from app.services.speaker_verification_service import get_speaker_verification_service
    svc = get_speaker_verification_service(str(claims.tenant_id))
    return svc.gallery_summary()


# ── Person ReID Endpoints ─────────────────────────────────────────────────────

@router.get("/reid/gallery")
async def reid_gallery(
    claims: TokenClaims = Depends(require_permissions("vision:read")),
):
    """Summary of tracked persons across cameras."""
    from app.services.person_reid_service import get_reid_service
    svc = get_reid_service(str(claims.tenant_id))
    return svc.get_gallery_summary()


@router.get("/reid/{reid_id}/footprint")
async def reid_footprint(
    reid_id: str,
    claims: TokenClaims = Depends(require_permissions("vision:read")),
):
    """Get all cameras where a re-identified person was seen."""
    from app.services.person_reid_service import get_reid_service
    svc = get_reid_service(str(claims.tenant_id))
    result = svc.get_camera_footprint(reid_id)
    if not result:
        raise HTTPException(404, "ReID track not found")
    return result
