"""AI Vision models: authorized persons, face encodings, detections, threat events, tracking."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func  # noqa: F401
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AuthorizedPerson(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Known/authorized individuals with face data for recognition."""
    __tablename__ = "authorized_persons"

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    site_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    person_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="employee"
    )  # employee, contractor, visitor, vip, banned
    employee_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    access_level: Mapped[str] = mapped_column(String(30), nullable=False, default="standard")  # restricted, standard, elevated, full
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active, inactive, banned, expired

    photo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    # Access schedule (e.g., {"days": ["mon","tue",...], "start": "08:00", "end": "18:00"})
    access_schedule: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    face_encodings: Mapped[list["FaceEncoding"]] = relationship(back_populates="person", cascade="all, delete-orphan")


class FaceEncoding(UUIDPrimaryKeyMixin, Base):
    """Stored face encoding vectors for recognition matching."""
    __tablename__ = "face_encodings"

    person_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("authorized_persons.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    encoding_vector: Mapped[list] = mapped_column(JSONB, nullable=False)  # 128-d face encoding as JSON array
    encoding_model: Mapped[str] = mapped_column(String(50), nullable=False, default="dlib_v1")
    source_image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    person: Mapped["AuthorizedPerson"] = relationship(back_populates="face_encodings")


class CameraFeed(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Registered CCTV camera feeds for AI processing."""
    __tablename__ = "camera_feeds"

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    site_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=True)
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    stream_url: Mapped[str] = mapped_column(String(500), nullable=False)  # RTSP/HTTP stream URL
    stream_type: Mapped[str] = mapped_column(String(20), nullable=False, default="rtsp")  # rtsp, http, hls
    location_description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    floor: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    zone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # AI processing config
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    face_recognition_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    threat_detection_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    person_tracking_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    processing_fps: Mapped[int] = mapped_column(Integer, default=5)  # frames to analyze per second
    detection_confidence_threshold: Mapped[float] = mapped_column(Float, default=0.7)

    # Regions of interest (zones within the frame)
    roi_zones: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # [{"name": "entrance", "polygon": [[x,y],...], "type": "entry"}, ...]

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active, inactive, error, processing
    last_frame_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class FaceDetection(UUIDPrimaryKeyMixin, Base):
    """Individual face detection event from a camera frame."""
    __tablename__ = "face_detections"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    camera_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("camera_feeds.id"), nullable=False)
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("authorized_persons.id"), nullable=True)

    match_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0-1.0
    is_recognized: Mapped[bool] = mapped_column(Boolean, default=False)
    is_authorized: Mapped[bool] = mapped_column(Boolean, default=False)
    person_type_detected: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # employee, unknown, banned

    # Face bounding box in frame
    bbox_x: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bbox_y: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bbox_w: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bbox_h: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Person analysis data
    person_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    estimated_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    age_range: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    primary_emotion: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    mood_category: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    emotion_scores: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    body_language: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    appearance: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    threat_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threat_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    threat_factors: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    full_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    snapshot_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    frame_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ThreatDetection(UUIDPrimaryKeyMixin, Base):
    """AI-detected threat events from camera feeds."""
    __tablename__ = "threat_detections"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    site_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=True)
    camera_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("camera_feeds.id"), nullable=False)
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=True)

    threat_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # weapon_detected, aggressive_behavior, unauthorized_person, banned_person,
    # intrusion, loitering, tailgating, crowd_anomaly, perimeter_breach,
    # abandoned_object, vehicle_violation, fire_smoke, fall_detected

    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="high")  # critical, high, medium, low
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # active, acknowledged, investigating, resolved, false_positive

    description: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    video_clip_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Detection details
    detected_objects: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # [{"class": "handgun", "confidence": 0.92, "bbox": [x,y,w,h]}, ...]

    # Person involved (if face was detected)
    face_detection_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("face_detections.id"), nullable=True)

    # Location context
    zone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    frame_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Response tracking
    auto_response_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    response_actions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # [{"action": "lockdown", "status": "executed"}, {"action": "notify_police", "status": "sent"}]

    acknowledged_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WebAuthnCredential(UUIDPrimaryKeyMixin, Base):
    """Stored WebAuthn/FIDO2 credentials for biometric authentication."""
    __tablename__ = "webauthn_credentials"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("authorized_persons.id", ondelete="CASCADE"), nullable=True)

    credential_id: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    public_key: Mapped[str] = mapped_column(Text, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False, default="platform")
    backed_up: Mapped[bool] = mapped_column(Boolean, default=False)
    transports: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    friendly_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BiometricAccessLog(UUIDPrimaryKeyMixin, Base):
    """Records every biometric verification attempt (face or fingerprint)."""
    __tablename__ = "biometric_access_logs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("authorized_persons.id"), nullable=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    method: Mapped[str] = mapped_column(String(30), nullable=False)  # face, fingerprint
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    person_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    person_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    zone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    device: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PersonTrack(UUIDPrimaryKeyMixin, Base):
    """Cross-camera person tracking session."""
    __tablename__ = "person_tracks"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    site_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=True)
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("authorized_persons.id"), nullable=True)

    track_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # internal tracking ID
    is_identified: Mapped[bool] = mapped_column(Boolean, default=False)
    person_label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # name if known, "Unknown #3" if not

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_camera_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("camera_feeds.id"), nullable=False)
    last_camera_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("camera_feeds.id"), nullable=False)
    dwell_time_seconds: Mapped[int] = mapped_column(Integer, default=0)

    # Movement path: ordered list of camera sightings
    movement_path: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # [{"camera_id": "...", "zone": "lobby", "timestamp": "...", "action": "entered"}, ...]

    threat_level: Mapped[str] = mapped_column(String(20), nullable=False, default="none")  # none, low, medium, high, critical
    flags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # ["loitering", "restricted_area", "after_hours"]

    snapshot_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
