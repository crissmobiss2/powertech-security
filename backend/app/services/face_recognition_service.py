"""
Face recognition engine using InsightFace (ArcFace / buffalo_l).

InsightFace provides:
- RetinaFace detection
- ArcFace recognition (512-dim embeddings)
- Age + gender estimation (built-in to buffalo_l)

Replaces the old dlib/face_recognition library for significantly better accuracy.
Model downloads automatically to ~/.insightface on first run (~320 MB).
"""
import base64
import io
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import TokenClaims

logger = logging.getLogger(__name__)

# --- Lazy singletons ---------------------------------------------------------

_insightface_app = None
_cv2 = None


def _get_cv2():
    global _cv2
    if _cv2 is None:
        import cv2
        _cv2 = cv2
    return _cv2


def _get_insightface():
    """Lazy-load InsightFace buffalo_l model (ArcFace + RetinaFace + age/gender)."""
    global _insightface_app
    if _insightface_app is None:
        try:
            import insightface
            from insightface.app import FaceAnalysis
            app = FaceAnalysis(
                name="buffalo_l",
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
            )
            app.prepare(ctx_id=0, det_size=(640, 640))
            _insightface_app = app
            logger.info("InsightFace buffalo_l loaded (ArcFace + RetinaFace + age/gender)")
        except Exception as e:
            logger.error("InsightFace failed to load: %s — falling back to OpenCV Haar", e)
            _insightface_app = None
    return _insightface_app


# -----------------------------------------------------------------------------

class FaceRecognitionService:
    """
    InsightFace-powered face enrollment and real-time recognition.

    Encoding: 512-dim ArcFace embedding, cosine similarity matching.
    Accuracy: ~99.77% on LFW benchmark (vs ~99.38% for dlib).
    """

    COSINE_THRESHOLD = 0.35   # cosine distance; lower = stricter (0.0 = identical)
    MIN_DET_SCORE = 0.5       # RetinaFace detection confidence minimum
    ENCODING_MODEL = "insightface_buffalo_l_arcface"

    def __init__(self, db: AsyncSession, claims: TokenClaims):
        self.db = db
        self.claims = claims

    async def enroll_face(
        self,
        person_id: UUID,
        image_base64: str,
        is_primary: bool = False,
    ) -> dict:
        """Generate ArcFace embedding from an image and store it for a person."""
        from app.models.vision import AuthorizedPerson, FaceEncoding

        person_result = await self.db.execute(
            select(AuthorizedPerson).where(
                AuthorizedPerson.id == person_id,
                AuthorizedPerson.tenant_id == self.claims.tenant_id,
            )
        )
        person = person_result.scalar_one_or_none()
        if not person:
            raise ValueError("Person not found")

        image = self._decode_image(image_base64)

        fa = _get_insightface()
        if fa is None:
            raise RuntimeError("InsightFace not available — cannot enroll face")

        faces = fa.get(image)
        if not faces:
            raise ValueError("No face detected in image")
        if len(faces) > 1:
            raise ValueError(
                f"Multiple faces detected ({len(faces)}). Provide exactly one face."
            )

        face = faces[0]
        embedding = face.normed_embedding.tolist()  # 512-dim L2-normalized ArcFace
        quality = self._assess_quality(image, face)

        if is_primary:
            existing = await self.db.execute(
                select(FaceEncoding).where(
                    FaceEncoding.person_id == person_id,
                    FaceEncoding.is_primary == True,
                )
            )
            for enc in existing.scalars().all():
                enc.is_primary = False

        face_enc = FaceEncoding(
            person_id=person_id,
            tenant_id=self.claims.tenant_id,
            encoding_vector=embedding,
            encoding_model=self.ENCODING_MODEL,
            quality_score=quality,
            is_primary=is_primary,
        )
        self.db.add(face_enc)
        await self.db.flush()
        await self.db.refresh(face_enc)

        return {
            "encoding_id": face_enc.id,
            "person_id": person_id,
            "quality_score": quality,
            "encoding_model": self.ENCODING_MODEL,
            "is_primary": is_primary,
            "det_score": float(face.det_score),
            "estimated_age": int(face.age) if hasattr(face, "age") else None,
            "gender": "male" if face.gender == 1 else "female" if hasattr(face, "gender") else None,
        }

    def _decode_image(self, image_base64: str) -> np.ndarray:
        cv2 = _get_cv2()
        image_data = base64.b64decode(image_base64)
        image_array = np.frombuffer(image_data, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Invalid image data")
        return image

    def _assess_quality(self, image: np.ndarray, face) -> float:
        """Quality score 0–1 from detection confidence, face size, and sharpness."""
        cv2 = _get_cv2()

        det_score = float(face.det_score)

        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox
        face_w = max(x2 - x1, 1)
        face_h = max(y2 - y1, 1)
        face_crop = image[max(0, y1):y2, max(0, x1):x2]

        size_score = min((face_w * face_h) / (200 * 200), 1.0)

        if face_crop.size > 0:
            gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
            blur_score = min(cv2.Laplacian(gray, cv2.CV_64F).var() / 500.0, 1.0)
        else:
            blur_score = 0.0

        return round(det_score * 0.4 + size_score * 0.3 + blur_score * 0.3, 3)

    async def load_encodings_for_tenant(
        self,
    ) -> tuple[list[np.ndarray], list[dict]]:
        """Load all ArcFace embeddings for active persons in the tenant."""
        from app.models.vision import AuthorizedPerson, FaceEncoding

        result = await self.db.execute(
            select(FaceEncoding, AuthorizedPerson)
            .join(AuthorizedPerson, FaceEncoding.person_id == AuthorizedPerson.id)
            .where(
                FaceEncoding.tenant_id == self.claims.tenant_id,
                AuthorizedPerson.status == "active",
            )
        )
        rows = result.all()

        encodings, metadata = [], []
        for encoding, person in rows:
            encodings.append(np.array(encoding.encoding_vector, dtype=np.float32))
            metadata.append({
                "person_id": str(person.id),
                "name": f"{person.first_name} {person.last_name}",
                "person_type": person.person_type,
                "access_level": person.access_level,
                "employee_id": person.employee_id,
                "department": person.department,
                "site_ids": person.site_ids,
            })

        return encodings, metadata

    def identify_faces_in_frame(
        self,
        frame: np.ndarray,
        known_encodings: list[np.ndarray],
        known_metadata: list[dict],
    ) -> list[dict]:
        """
        Detect and identify all faces in a frame using InsightFace ArcFace.
        Returns list of detections with bbox, identity, age, gender, confidence.
        """
        fa = _get_insightface()
        if fa is None:
            return self._fallback_opencv_detect(frame)

        faces = fa.get(frame)
        results = []

        for face in faces:
            if face.det_score < self.MIN_DET_SCORE:
                continue

            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox

            detection = {
                "bbox": {"x": int(x1), "y": int(y1), "w": int(x2 - x1), "h": int(y2 - y1)},
                "is_recognized": False,
                "is_authorized": False,
                "person_id": None,
                "person_name": None,
                "person_type": None,
                "confidence": 0.0,
                "access_level": None,
                "det_score": float(face.det_score),
                "estimated_age": int(face.age) if hasattr(face, "age") and face.age is not None else None,
                "gender": ("male" if face.gender == 1 else "female") if hasattr(face, "gender") and face.gender is not None else None,
                "encoding": face.normed_embedding.tolist(),
            }

            if known_encodings and face.normed_embedding is not None:
                embedding = face.normed_embedding
                # Cosine distances: 1 - (A·B) for L2-normalized vectors
                sims = np.dot(known_encodings, embedding)
                dists = 1.0 - sims
                best_idx = int(np.argmin(dists))
                best_dist = float(dists[best_idx])

                if best_dist < self.COSINE_THRESHOLD:
                    meta = known_metadata[best_idx]
                    detection.update({
                        "is_recognized": True,
                        "is_authorized": meta["person_type"] != "banned",
                        "person_id": meta["person_id"],
                        "person_name": meta["name"],
                        "person_type": meta["person_type"],
                        "confidence": round(float(sims[best_idx]), 3),
                        "access_level": meta["access_level"],
                    })

            results.append(detection)

        return results

    def _fallback_opencv_detect(self, frame: np.ndarray) -> list[dict]:
        """Fallback Haar-cascade detection when InsightFace is unavailable."""
        cv2 = _get_cv2()
        try:
            cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, 1.1, 4, minSize=(40, 40))
            return [
                {
                    "bbox": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
                    "is_recognized": False,
                    "is_authorized": False,
                    "person_id": None,
                    "person_name": None,
                    "person_type": "unknown",
                    "confidence": 0.0,
                    "access_level": None,
                    "det_score": 0.5,
                    "estimated_age": None,
                    "gender": None,
                    "encoding": [],
                }
                for (x, y, w, h) in faces
            ]
        except Exception:
            return []


# --- Threat / Object Detection -----------------------------------------------

class ThreatDetectionService:
    """YOLO11-powered threat and anomaly detection."""

    WEAPON_CLASSES = {"handgun", "rifle", "knife", "bat", "hammer", "scissors"}
    BEHAVIOR_THRESHOLDS = {
        "loitering_seconds": 300,
        "crowd_size_alert": 15,
    }

    def __init__(self, db: AsyncSession, claims: TokenClaims):
        self.db = db
        self.claims = claims
        self._yolo_model = None

    def _get_yolo(self):
        """Lazy-load YOLO11 nano model."""
        if self._yolo_model is None:
            try:
                from ultralytics import YOLO
            except ImportError:
                logger.warning("ultralytics not installed — YOLO threat detection unavailable")
                return None
            try:
                self._yolo_model = YOLO("yolo11n.pt")
                logger.info("YOLO11n loaded")
            except Exception:
                self._yolo_model = YOLO("yolov8n.pt")
                logger.warning("YOLO11 unavailable, using YOLOv8n fallback")
        return self._yolo_model

    def analyze_frame(self, frame: np.ndarray, camera_config: dict) -> list[dict]:
        """Run YOLO11 object detection for weapons, crowds, abandoned objects."""
        threats = []
        conf_threshold = camera_config.get("detection_confidence_threshold", 0.6)

        model = self._get_yolo()
        if model is None:
            return []
        results = model(frame, verbose=False, conf=conf_threshold)

        person_count = 0
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]

                if class_name == "person":
                    person_count += 1

                if class_name in self.WEAPON_CLASSES:
                    threats.append({
                        "threat_type": "weapon_detected",
                        "severity": "critical",
                        "confidence": round(confidence, 3),
                        "description": f"Weapon detected: {class_name} ({confidence:.0%} confidence)",
                        "detected_objects": [{
                            "class": class_name,
                            "confidence": round(confidence, 3),
                            "bbox": [x1, y1, x2 - x1, y2 - y1],
                        }],
                    })

        if person_count >= self.BEHAVIOR_THRESHOLDS["crowd_size_alert"]:
            threats.append({
                "threat_type": "crowd_anomaly",
                "severity": "medium",
                "confidence": 0.85,
                "description": f"Crowd anomaly: {person_count} people detected simultaneously",
                "detected_objects": [{"class": "crowd", "count": person_count}],
            })

        return threats

    def analyze_person_behavior(
        self,
        track: dict,
        dwell_time: int,
        zone_type: str | None,
    ) -> list[dict]:
        threats = []

        if dwell_time > self.BEHAVIOR_THRESHOLDS["loitering_seconds"]:
            threats.append({
                "threat_type": "loitering",
                "severity": "low",
                "confidence": min(dwell_time / 600.0, 0.95),
                "description": f"Person loitering for {dwell_time // 60} min",
            })

        if zone_type == "restricted" and not track.get("is_authorized"):
            threats.append({
                "threat_type": "intrusion",
                "severity": "high",
                "confidence": 0.9,
                "description": "Unauthorized access to restricted zone",
            })

        if zone_type == "secured" and track.get("after_hours"):
            threats.append({
                "threat_type": "after_hours_presence",
                "severity": "medium",
                "confidence": 0.85,
                "description": "After-hours presence in secured area",
            })

        return threats
