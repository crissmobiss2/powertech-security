"""Pydantic schemas for AI Vision endpoints."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Authorized Person ──────────────────────────────────────────────────────────

class AuthorizedPersonCreate(BaseModel):
    client_id: UUID
    site_ids: list[UUID] | None = None
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    person_type: str = Field(default="employee", pattern="^(employee|contractor|visitor|vip|banned)$")
    employee_id: str | None = None
    department: str | None = None
    access_level: str = Field(default="standard", pattern="^(restricted|standard|elevated|full)$")
    access_schedule: dict | None = None
    notes: str | None = None

class AuthorizedPersonUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    person_type: str | None = None
    employee_id: str | None = None
    department: str | None = None
    access_level: str | None = None
    access_schedule: dict | None = None
    status: str | None = None
    site_ids: list[UUID] | None = None
    notes: str | None = None

class AuthorizedPersonResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    client_id: UUID
    site_ids: list[UUID] | None
    first_name: str
    last_name: str
    person_type: str
    employee_id: str | None
    department: str | None
    access_level: str
    status: str
    photo_url: str | None
    access_schedule: dict | None
    face_encoding_count: int = 0
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Camera Feed ────────────────────────────────────────────────────────────────

class CameraFeedCreate(BaseModel):
    client_id: UUID
    site_id: UUID | None = None
    asset_id: UUID | None = None
    name: str = Field(max_length=200)
    stream_url: str = Field(max_length=500)
    stream_type: str = Field(default="rtsp", pattern="^(rtsp|http|hls)$")
    location_description: str | None = None
    floor: str | None = None
    zone: str | None = None
    ai_enabled: bool = True
    face_recognition_enabled: bool = True
    threat_detection_enabled: bool = True
    person_tracking_enabled: bool = True
    processing_fps: int = Field(default=5, ge=1, le=30)
    detection_confidence_threshold: float = Field(default=0.7, ge=0.1, le=1.0)
    roi_zones: list[dict] | None = None

class CameraFeedUpdate(BaseModel):
    name: str | None = None
    stream_url: str | None = None
    location_description: str | None = None
    floor: str | None = None
    zone: str | None = None
    ai_enabled: bool | None = None
    face_recognition_enabled: bool | None = None
    threat_detection_enabled: bool | None = None
    person_tracking_enabled: bool | None = None
    processing_fps: int | None = None
    detection_confidence_threshold: float | None = None
    roi_zones: list[dict] | None = None
    status: str | None = None

class CameraFeedResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    client_id: UUID
    site_id: UUID | None
    asset_id: UUID | None
    name: str
    stream_url: str
    stream_type: str
    location_description: str | None
    floor: str | None
    zone: str | None
    ai_enabled: bool
    face_recognition_enabled: bool
    threat_detection_enabled: bool
    person_tracking_enabled: bool
    processing_fps: int
    detection_confidence_threshold: float
    roi_zones: list[dict] | None
    status: str
    last_frame_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Face Detection ─────────────────────────────────────────────────────────────

class FaceDetectionResponse(BaseModel):
    id: UUID
    camera_id: UUID
    person_id: UUID | None
    match_confidence: float | None
    is_recognized: bool
    is_authorized: bool
    person_type_detected: str | None
    person_name: str | None = None
    bbox_x: int | None
    bbox_y: int | None
    bbox_w: int | None
    bbox_h: int | None
    estimated_age: int | None = None
    age_range: str | None = None
    gender: str | None = None
    primary_emotion: str | None = None
    mood_category: str | None = None
    emotion_scores: dict | None = None
    body_language: dict | None = None
    appearance: dict | None = None
    threat_score: float | None = None
    threat_level: str | None = None
    threat_factors: list[str] | None = None
    snapshot_path: str | None
    frame_timestamp: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Threat Detection ──────────────────────────────────────────────────────────

class ThreatDetectionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    client_id: UUID
    site_id: UUID | None
    camera_id: UUID
    incident_id: UUID | None
    threat_type: str
    severity: str
    confidence: float
    status: str
    description: str
    snapshot_path: str | None
    video_clip_path: str | None
    detected_objects: list[dict] | None
    zone: str | None
    frame_timestamp: datetime
    auto_response_triggered: bool
    response_actions: list[dict] | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

class ThreatAcknowledge(BaseModel):
    status: str = Field(pattern="^(acknowledged|investigating|resolved|false_positive)$")
    notes: str | None = None


# ── Person Track ───────────────────────────────────────────────────────────────

class PersonTrackResponse(BaseModel):
    id: UUID
    site_id: UUID | None
    person_id: UUID | None
    track_id: str
    is_identified: bool
    person_label: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    first_camera_id: UUID
    last_camera_id: UUID
    dwell_time_seconds: int
    movement_path: list[dict] | None
    threat_level: str
    flags: list[str] | None
    snapshot_path: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Face Enrollment ───────────────────────────────────────────────────────────

class FaceEnrollRequest(BaseModel):
    """For enrolling a face via base64 image data."""
    image_base64: str
    is_primary: bool = False

class FaceEnrollResponse(BaseModel):
    encoding_id: UUID | None = None
    person_id: UUID
    quality_score: float | None = None
    encoding_model: str
    is_primary: bool = False
    photo_only: bool = False
    message: str | None = None

    model_config = {"from_attributes": True}


# ── Vision Stats ──────────────────────────────────────────────────────────────

class VisionDashboardStats(BaseModel):
    active_cameras: int
    total_cameras: int
    authorized_persons: int
    faces_detected_today: int
    unknown_faces_today: int
    active_threats: int
    threats_today: int
    active_tracks: int
    cameras_with_errors: int


# ── WebAuthn / Fingerprint ────────────────────────────────────────────────

class WebAuthnRegistrationOptionsRequest(BaseModel):
    user_id: UUID | None = None
    person_id: UUID | None = None

class WebAuthnRegistrationOptionsResponse(BaseModel):
    challenge: str
    rp_id: str
    rp_name: str
    user_id: str
    user_name: str
    user_display_name: str
    pub_key_cred_params: list[dict]
    authenticator_selection: dict
    timeout: int
    attestation: str

class WebAuthnRegisterRequest(BaseModel):
    credential_id: str
    public_key: str
    sign_count: int = 0
    device_type: str = "platform"
    backed_up: bool = False
    transports: list[str] | None = None
    friendly_name: str | None = None
    person_id: UUID | None = None

class WebAuthnCredentialResponse(BaseModel):
    id: UUID
    credential_id: str
    device_type: str
    friendly_name: str | None
    backed_up: bool
    transports: list[str] | None
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

class WebAuthnAuthenticateRequest(BaseModel):
    credential_id: str
    signature: str
    authenticator_data: str
    client_data_json: str

class WebAuthnAuthenticateResponse(BaseModel):
    verified: bool
    user_id: UUID | None = None
    person_id: UUID | None = None
    person_name: str | None = None


# ── Biometric Access Log ─────────────────────────────────────────────────

class BiometricAccessLogResponse(BaseModel):
    id: UUID
    person_id: UUID | None
    user_id: UUID | None
    method: str
    success: bool
    confidence: float
    person_name: str | None
    person_type: str | None
    zone: str | None
    device: str | None
    failure_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
