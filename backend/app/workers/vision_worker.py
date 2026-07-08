"""
CCTV stream processing worker.
Connects to camera RTSP feeds, runs frame-by-frame analysis:
  - Face detection and recognition
  - Threat/weapon detection (YOLOv8)
  - Person tracking and dwell-time computation
  - Automatic incident creation + SOAR playbook triggering
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


async def _publish_ws_event(channel: str, event_type: str, payload: dict, tenant_id):
    """Publish real-time event to WebSocket clients via Redis."""
    try:
        from app.services.ws_manager import publish_event
        await publish_event(channel, event_type, payload, tenant_id)
    except Exception:
        logger.debug("WebSocket publish failed (non-critical)", exc_info=True)


@celery_app.task(
    name="app.workers.tasks.process_camera_feed",
    bind=True,
    max_retries=3,
    soft_time_limit=3600,
    time_limit=3660,
)
def process_camera_feed(self, camera_id: str, duration_seconds: int = 300):
    """
    Process a camera feed for a given duration.
    Pulls frames from RTSP, runs face recognition + threat detection,
    persists results to DB, and triggers SOAR actions for threats.
    """
    import cv2
    import numpy as np

    async def _process():
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from sqlalchemy import select
        from app.core.config import settings
        from app.core.dependencies import TokenClaims
        from app.models.vision import (
            CameraFeed, FaceDetection, ThreatDetection, PersonTrack,
        )
        from app.services.face_recognition_service import (
            FaceRecognitionService, ThreatDetectionService,
        )

        engine = create_async_engine(settings.DATABASE_URL)
        SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

        async with SessionFactory() as db:
            result = await db.execute(
                select(CameraFeed).where(CameraFeed.id == camera_id)
            )
            camera = result.scalar_one_or_none()
            if not camera or camera.status != "active":
                logger.info("Camera %s not active, skipping", camera_id)
                return

            claims = TokenClaims(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                tenant_id=camera.tenant_id,
                client_id=camera.client_id,
                role="super_admin",
                permissions=["*"],
            )

            face_svc = FaceRecognitionService(db, claims)
            threat_svc = ThreatDetectionService(db, claims)

            from app.services.person_analysis_service import PersonAnalysisService
            from app.services.anomaly_detection_service import get_anomaly_service
            from app.services.video_action_service import get_video_action_service
            person_analyzer = PersonAnalysisService()
            anomaly_svc = get_anomaly_service(camera_id)
            action_svc = get_video_action_service(camera_id)

            known_encodings, known_metadata = await face_svc.load_encodings_for_tenant()
            logger.info(
                "Camera %s: loaded %d known faces for tenant %s",
                camera.name, len(known_encodings), camera.tenant_id,
            )

            cap = cv2.VideoCapture(camera.stream_url)
            if not cap.isOpened():
                camera.status = "error"
                camera.error_message = "Failed to open stream"
                await db.commit()
                logger.error("Cannot open stream for camera %s: %s", camera.name, camera.stream_url)
                raise self.retry(countdown=120)

            camera.status = "processing"
            camera.error_message = None
            await db.commit()

            frame_interval = 1.0 / camera.processing_fps
            camera_config = {
                "detection_confidence_threshold": camera.detection_confidence_threshold,
                "face_recognition_enabled": camera.face_recognition_enabled,
                "threat_detection_enabled": camera.threat_detection_enabled,
                "person_tracking_enabled": camera.person_tracking_enabled,
            }

            active_tracks: dict[str, dict] = {}
            start_time = time.time()
            frame_count = 0
            detections_count = 0
            threats_count = 0

            try:
                while time.time() - start_time < duration_seconds:
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning("Camera %s: stream read failed, reconnecting...", camera.name)
                        cap.release()
                        await asyncio.sleep(2)
                        cap = cv2.VideoCapture(camera.stream_url)
                        if not cap.isOpened():
                            break
                        continue

                    frame_count += 1
                    now = datetime.now(timezone.utc)
                    camera.last_frame_at = now

                    # Face recognition + full person analysis
                    if camera_config["face_recognition_enabled"]:
                        face_results = face_svc.identify_faces_in_frame(
                            frame, known_encodings, known_metadata
                        )
                        for face in face_results:
                            person_id = UUID(face["person_id"]) if face["person_id"] else None

                            analysis = person_analyzer.analyze_person_full(
                                frame, face["bbox"], person_bbox=None
                            )

                            detection = FaceDetection(
                                tenant_id=camera.tenant_id,
                                camera_id=camera.id,
                                person_id=person_id,
                                match_confidence=face["confidence"] if face["is_recognized"] else None,
                                is_recognized=face["is_recognized"],
                                is_authorized=face["is_authorized"],
                                person_type_detected=face.get("person_type", "unknown"),
                                person_name=face.get("person_name"),
                                bbox_x=face["bbox"]["x"],
                                bbox_y=face["bbox"]["y"],
                                bbox_w=face["bbox"]["w"],
                                bbox_h=face["bbox"]["h"],
                                estimated_age=analysis["demographics"].get("estimated_age"),
                                age_range=analysis["demographics"].get("age_range"),
                                gender=analysis["demographics"].get("gender"),
                                primary_emotion=analysis["emotion"].get("primary_emotion"),
                                mood_category=analysis["emotion"].get("mood_category"),
                                emotion_scores=analysis["emotion"].get("all_emotions"),
                                body_language=analysis["body_language"],
                                appearance=analysis["appearance"],
                                threat_score=analysis["threat_assessment"].get("score"),
                                threat_level=analysis["threat_assessment"].get("level"),
                                threat_factors=analysis["threat_assessment"].get("factors"),
                                full_analysis=analysis,
                                frame_timestamp=now,
                            )
                            db.add(detection)
                            detections_count += 1

                            if analysis["threat_assessment"]["score"] >= 0.5:
                                threat_desc = (
                                    f"Behavioral threat detected: "
                                    f"{analysis['emotion']['primary_emotion']} emotion, "
                                    f"{', '.join(analysis['threat_assessment']['factors'])}"
                                )
                                threat = ThreatDetection(
                                    tenant_id=camera.tenant_id,
                                    client_id=camera.client_id,
                                    site_id=camera.site_id,
                                    camera_id=camera.id,
                                    threat_type="behavioral_threat",
                                    severity=analysis["threat_assessment"]["level"],
                                    confidence=analysis["threat_assessment"]["score"],
                                    description=threat_desc,
                                    detected_objects=[{
                                        "class": "person",
                                        "emotion": analysis["emotion"]["primary_emotion"],
                                        "body_language": analysis["body_language"].get("indicators", []),
                                        "threat_score": analysis["threat_assessment"]["score"],
                                    }],
                                    zone=camera.zone,
                                    frame_timestamp=now,
                                    auto_response_triggered=analysis["threat_assessment"]["score"] >= 0.7,
                                )
                                db.add(threat)
                                threats_count += 1

                                await _publish_ws_event(
                                    "vision:threats", "threat_detected",
                                    {
                                        "threat_type": "behavioral_threat",
                                        "severity": analysis["threat_assessment"]["level"],
                                        "confidence": analysis["threat_assessment"]["score"],
                                        "description": threat_desc,
                                        "camera_name": camera.name,
                                        "camera_id": str(camera.id),
                                        "zone": camera.zone,
                                        "emotion": analysis["emotion"]["primary_emotion"],
                                        "threat_factors": analysis["threat_assessment"]["factors"],
                                    },
                                    camera.tenant_id,
                                )

                            if face.get("person_type") == "banned" and face["is_recognized"]:
                                banned_desc = f"Banned person detected: {face['person_name']}"
                                threat = ThreatDetection(
                                    tenant_id=camera.tenant_id,
                                    client_id=camera.client_id,
                                    site_id=camera.site_id,
                                    camera_id=camera.id,
                                    threat_type="banned_person",
                                    severity="critical",
                                    confidence=face["confidence"],
                                    description=banned_desc,
                                    detected_objects=[{
                                        "class": "banned_person",
                                        "name": face["person_name"],
                                        "confidence": face["confidence"],
                                    }],
                                    zone=camera.zone,
                                    frame_timestamp=now,
                                    auto_response_triggered=True,
                                    response_actions=[{"action": "alert_security", "status": "triggered"}],
                                )
                                db.add(threat)
                                threats_count += 1

                                await _publish_ws_event(
                                    "vision:threats", "banned_person",
                                    {
                                        "threat_type": "banned_person",
                                        "severity": "critical",
                                        "confidence": face["confidence"],
                                        "description": banned_desc,
                                        "person_name": face["person_name"],
                                        "camera_name": camera.name,
                                        "camera_id": str(camera.id),
                                        "zone": camera.zone,
                                    },
                                    camera.tenant_id,
                                )

                            if not face["is_recognized"]:
                                track_key = f"unknown_{face['bbox']['x']}_{face['bbox']['y']}"
                                if track_key not in active_tracks:
                                    active_tracks[track_key] = {
                                        "track_id": f"trk_{uuid4().hex[:12]}",
                                        "first_seen": now,
                                        "last_seen": now,
                                        "camera_id": camera.id,
                                    }
                                else:
                                    active_tracks[track_key]["last_seen"] = now

                    # Anomaly detection (runs on every frame)
                    anomaly_score, _ = anomaly_svc.score_frame(frame)
                    if anomaly_score > 0.65:
                        anomaly_class = anomaly_svc.classify_score(anomaly_score)
                        anomaly_threat = ThreatDetection(
                            tenant_id=camera.tenant_id,
                            client_id=camera.client_id,
                            site_id=camera.site_id,
                            camera_id=camera.id,
                            threat_type="scene_anomaly",
                            severity=anomaly_class["level"],
                            confidence=round(anomaly_score, 3),
                            description=f"Scene anomaly detected (score: {anomaly_score:.2f}): {anomaly_class['description']}",
                            detected_objects=[{"anomaly_score": anomaly_score}],
                            zone=camera.zone,
                            frame_timestamp=now,
                            auto_response_triggered=anomaly_score >= 0.85,
                        )
                        db.add(anomaly_threat)
                        threats_count += 1

                        if anomaly_score >= 0.65:
                            await _publish_ws_event(
                                "vision:threats", "threat_detected",
                                {
                                    "threat_type": "scene_anomaly",
                                    "severity": anomaly_class["level"],
                                    "confidence": round(anomaly_score, 3),
                                    "description": anomaly_class["description"],
                                    "camera_name": camera.name,
                                    "camera_id": str(camera.id),
                                    "zone": camera.zone,
                                },
                                camera.tenant_id,
                            )

                    # Video action recognition (VideoMAE / optical flow fight/fall detection)
                    action_result = action_svc.push_frame(frame)
                    if action_result and action_svc.is_alert_worthy(action_result):
                        action_threat = ThreatDetection(
                            tenant_id=camera.tenant_id,
                            client_id=camera.client_id,
                            site_id=camera.site_id,
                            camera_id=camera.id,
                            threat_type=f"action:{action_result['security_category']}",
                            severity=action_result["severity"],
                            confidence=action_result["confidence"],
                            description=action_result["description"],
                            detected_objects=[{
                                "action": action_result["security_category"],
                                "raw_label": action_result["raw_kinetics_label"],
                                "detection_source": action_result["source"],
                            }],
                            zone=camera.zone,
                            frame_timestamp=now,
                            auto_response_triggered=action_result["severity"] in ("critical", "high"),
                        )
                        db.add(action_threat)
                        threats_count += 1

                        await _publish_ws_event(
                            "vision:threats", "threat_detected",
                            {
                                "threat_type": f"action:{action_result['security_category']}",
                                "severity": action_result["severity"],
                                "confidence": action_result["confidence"],
                                "description": action_result["description"],
                                "camera_name": camera.name,
                                "camera_id": str(camera.id),
                                "zone": camera.zone,
                            },
                            camera.tenant_id,
                        )

                    # Threat detection (YOLO11)
                    if camera_config["threat_detection_enabled"]:
                        threat_results = threat_svc.analyze_frame(frame, camera_config)
                        for t in threat_results:
                            threat = ThreatDetection(
                                tenant_id=camera.tenant_id,
                                client_id=camera.client_id,
                                site_id=camera.site_id,
                                camera_id=camera.id,
                                threat_type=t["threat_type"],
                                severity=t["severity"],
                                confidence=t["confidence"],
                                description=t["description"],
                                detected_objects=t.get("detected_objects"),
                                zone=camera.zone,
                                frame_timestamp=now,
                                auto_response_triggered=t["severity"] in ("critical", "high"),
                                response_actions=(
                                    [{"action": "lockdown", "status": "triggered"},
                                     {"action": "notify_security", "status": "triggered"}]
                                    if t["severity"] == "critical" else None
                                ),
                            )
                            db.add(threat)
                            threats_count += 1

                            await _publish_ws_event(
                                "vision:threats", "threat_detected",
                                {
                                    "threat_type": t["threat_type"],
                                    "severity": t["severity"],
                                    "confidence": t["confidence"],
                                    "description": t["description"],
                                    "camera_name": camera.name,
                                    "camera_id": str(camera.id),
                                    "zone": camera.zone,
                                    "detected_objects": t.get("detected_objects"),
                                },
                                camera.tenant_id,
                            )

                            if t["severity"] == "critical":
                                await _create_auto_incident(db, claims, camera, t, now)

                    if frame_count % 50 == 0:
                        await db.commit()

                    await asyncio.sleep(frame_interval)

            finally:
                cap.release()

            # Persist person tracks
            for key, track_data in active_tracks.items():
                dwell = int((track_data["last_seen"] - track_data["first_seen"]).total_seconds())
                if dwell > 10:
                    person_track = PersonTrack(
                        tenant_id=camera.tenant_id,
                        site_id=camera.site_id,
                        track_id=track_data["track_id"],
                        is_identified=False,
                        person_label=f"Unknown Person",
                        first_seen_at=track_data["first_seen"],
                        last_seen_at=track_data["last_seen"],
                        first_camera_id=track_data["camera_id"],
                        last_camera_id=camera.id,
                        dwell_time_seconds=dwell,
                        movement_path=[{
                            "camera_id": str(camera.id),
                            "zone": camera.zone,
                            "timestamp": track_data["first_seen"].isoformat(),
                            "action": "detected",
                        }],
                        threat_level="low" if dwell > 300 else "none",
                        flags=["loitering"] if dwell > 300 else None,
                    )
                    db.add(person_track)

            camera.status = "active"
            await db.commit()

            logger.info(
                "Camera %s processing complete: %d frames, %d face detections, %d threats",
                camera.name, frame_count, detections_count, threats_count,
            )

        await engine.dispose()

    try:
        _run_async(_process())
    except Exception as exc:
        logger.exception("Camera feed processing failed for %s: %s", camera_id, exc)
        raise self.retry(exc=exc, countdown=60)


async def _create_auto_incident(db, claims, camera, threat_data, timestamp):
    """Create an incident automatically from a critical threat detection."""
    from app.services.incident_service import IncidentService

    svc = IncidentService(db, claims)
    await svc.create(
        title=f"AI THREAT: {threat_data['description']}",
        description=(
            f"Automated incident from AI threat detection.\n"
            f"Camera: {camera.name}\n"
            f"Location: {camera.location_description or 'N/A'}\n"
            f"Zone: {camera.zone or 'N/A'}\n"
            f"Threat Type: {threat_data['threat_type']}\n"
            f"Confidence: {threat_data['confidence']:.1%}\n"
            f"Detected at: {timestamp.isoformat()}"
        ),
        type="ai_detection",
        severity="critical" if threat_data["severity"] == "critical" else "high",
        source="ai_vision",
        client_id=camera.client_id,
        site_id=camera.site_id,
    )


@celery_app.task(name="app.workers.tasks.start_all_camera_feeds")
def start_all_camera_feeds():
    """Periodic task: ensure all active cameras have processing tasks running."""
    async def _start():
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        from sqlalchemy import select
        from app.core.config import settings
        from app.models.vision import CameraFeed

        engine = create_async_engine(settings.DATABASE_URL)
        SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

        async with SessionFactory() as db:
            result = await db.execute(
                select(CameraFeed).where(
                    CameraFeed.status.in_(["active"]),
                    CameraFeed.ai_enabled == True,
                )
            )
            cameras = result.scalars().all()

            for camera in cameras:
                process_camera_feed.delay(str(camera.id), duration_seconds=300)
                logger.info("Queued processing for camera %s (%s)", camera.name, camera.id)

        await engine.dispose()

    _run_async(_start())
