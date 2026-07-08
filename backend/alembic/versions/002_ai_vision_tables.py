"""AI Vision tables — authorized persons, face encodings, camera feeds,
face detections, threat detections, person tracks.

Revision ID: 002
Revises: 001
Create Date: 2026-07-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── authorized_persons ──────────────────────────────────────────────────
    op.create_table(
        "authorized_persons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_ids", postgresql.JSONB, nullable=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("person_type", sa.String(30), nullable=False, server_default="employee"),
        sa.Column("employee_id", sa.String(50), nullable=True),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("access_level", sa.String(30), nullable=False, server_default="standard"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("access_schedule", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_authorized_persons_tenant", "authorized_persons", ["tenant_id"])
    op.create_index("ix_authorized_persons_client", "authorized_persons", ["client_id"])
    op.create_index("ix_authorized_persons_type", "authorized_persons", ["tenant_id", "person_type"])

    # ── face_encodings ──────────────────────────────────────────────────────
    op.create_table(
        "face_encodings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encoding_vector", postgresql.JSONB, nullable=False),
        sa.Column("encoding_model", sa.String(50), nullable=False, server_default="dlib_v1"),
        sa.Column("source_image_path", sa.String(500), nullable=True),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("is_primary", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["person_id"], ["authorized_persons.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_face_encodings_tenant", "face_encodings", ["tenant_id"])
    op.create_index("ix_face_encodings_person", "face_encodings", ["person_id"])

    # ── camera_feeds ────────────────────────────────────────────────────────
    op.create_table(
        "camera_feeds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("stream_url", sa.String(500), nullable=False),
        sa.Column("stream_type", sa.String(20), nullable=False, server_default="rtsp"),
        sa.Column("location_description", sa.String(200), nullable=True),
        sa.Column("floor", sa.String(20), nullable=True),
        sa.Column("zone", sa.String(50), nullable=True),
        sa.Column("ai_enabled", sa.Boolean, server_default="true"),
        sa.Column("face_recognition_enabled", sa.Boolean, server_default="true"),
        sa.Column("threat_detection_enabled", sa.Boolean, server_default="true"),
        sa.Column("person_tracking_enabled", sa.Boolean, server_default="true"),
        sa.Column("processing_fps", sa.Integer, server_default="5"),
        sa.Column("detection_confidence_threshold", sa.Float, server_default="0.7"),
        sa.Column("roi_zones", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("last_frame_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_camera_feeds_tenant", "camera_feeds", ["tenant_id"])
    op.create_index("ix_camera_feeds_client", "camera_feeds", ["client_id"])
    op.create_index("ix_camera_feeds_status", "camera_feeds", ["tenant_id", "status"])

    # ── face_detections ─────────────────────────────────────────────────────
    op.create_table(
        "face_detections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("match_confidence", sa.Float, nullable=True),
        sa.Column("is_recognized", sa.Boolean, server_default="false"),
        sa.Column("is_authorized", sa.Boolean, server_default="false"),
        sa.Column("person_type_detected", sa.String(30), nullable=True),
        sa.Column("person_name", sa.String(200), nullable=True),
        sa.Column("bbox_x", sa.Integer, nullable=True),
        sa.Column("bbox_y", sa.Integer, nullable=True),
        sa.Column("bbox_w", sa.Integer, nullable=True),
        sa.Column("bbox_h", sa.Integer, nullable=True),
        sa.Column("estimated_age", sa.Integer, nullable=True),
        sa.Column("age_range", sa.String(20), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("primary_emotion", sa.String(30), nullable=True),
        sa.Column("mood_category", sa.String(30), nullable=True),
        sa.Column("emotion_scores", postgresql.JSONB, nullable=True),
        sa.Column("body_language", postgresql.JSONB, nullable=True),
        sa.Column("appearance", postgresql.JSONB, nullable=True),
        sa.Column("threat_score", sa.Float, nullable=True),
        sa.Column("threat_level", sa.String(20), nullable=True),
        sa.Column("threat_factors", postgresql.JSONB, nullable=True),
        sa.Column("full_analysis", postgresql.JSONB, nullable=True),
        sa.Column("snapshot_path", sa.String(500), nullable=True),
        sa.Column("frame_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["camera_id"], ["camera_feeds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["authorized_persons.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_face_detections_tenant", "face_detections", ["tenant_id"])
    op.create_index("ix_face_detections_camera", "face_detections", ["camera_id"])
    op.create_index("ix_face_detections_person", "face_detections", ["person_id"])
    op.create_index("ix_face_detections_timestamp", "face_detections", ["tenant_id", "frame_timestamp"])
    op.create_index("ix_face_detections_threat", "face_detections", ["tenant_id", "threat_level"])

    # ── threat_detections ───────────────────────────────────────────────────
    op.create_table(
        "threat_detections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("threat_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="high"),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("snapshot_path", sa.String(500), nullable=True),
        sa.Column("video_clip_path", sa.String(500), nullable=True),
        sa.Column("detected_objects", postgresql.JSONB, nullable=True),
        sa.Column("face_detection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("zone", sa.String(50), nullable=True),
        sa.Column("frame_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("auto_response_triggered", sa.Boolean, server_default="false"),
        sa.Column("response_actions", postgresql.JSONB, nullable=True),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["camera_id"], ["camera_feeds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["face_detection_id"], ["face_detections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["acknowledged_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_threat_detections_tenant", "threat_detections", ["tenant_id"])
    op.create_index("ix_threat_detections_status", "threat_detections", ["tenant_id", "status"])
    op.create_index("ix_threat_detections_severity", "threat_detections", ["tenant_id", "severity"])
    op.create_index("ix_threat_detections_camera", "threat_detections", ["camera_id"])
    op.create_index("ix_threat_detections_timestamp", "threat_detections", ["tenant_id", "frame_timestamp"])

    # ── person_tracks ───────────────────────────────────────────────────────
    op.create_table(
        "person_tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("track_id", sa.String(100), nullable=False),
        sa.Column("is_identified", sa.Boolean, server_default="false"),
        sa.Column("person_label", sa.String(200), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dwell_time_seconds", sa.Integer, server_default="0"),
        sa.Column("movement_path", postgresql.JSONB, nullable=True),
        sa.Column("threat_level", sa.String(20), nullable=False, server_default="none"),
        sa.Column("flags", postgresql.JSONB, nullable=True),
        sa.Column("snapshot_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["person_id"], ["authorized_persons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["first_camera_id"], ["camera_feeds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_camera_id"], ["camera_feeds.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_person_tracks_tenant", "person_tracks", ["tenant_id"])
    op.create_index("ix_person_tracks_track_id", "person_tracks", ["track_id"])
    op.create_index("ix_person_tracks_person", "person_tracks", ["person_id"])
    op.create_index("ix_person_tracks_threat", "person_tracks", ["tenant_id", "threat_level"])
    op.create_index("ix_person_tracks_dwell", "person_tracks", ["tenant_id", "dwell_time_seconds"])


def downgrade() -> None:
    for table in [
        "person_tracks", "threat_detections", "face_detections",
        "camera_feeds", "face_encodings", "authorized_persons",
    ]:
        op.drop_table(table)
