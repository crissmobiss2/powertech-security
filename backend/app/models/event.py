"""Security event ingestion model. High-volume; partitioned by month in production."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class SecurityEvent(Base, TenantMixin):
    __tablename__ = "security_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    site_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True
    )
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # asset.offline, asset.online, access.denied, access.granted,
    # door.forced_open, camera.tampering, motion.detected,
    # auth.failed, auth.success, vuln.discovered, malware.detected, ...

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # nvr, access_control, edr, firewall, siem, manual, api

    source_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    # critical, high, medium, low, info

    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    normalized_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    false_positive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    # created_at is the event timestamp (partition key)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_security_events_tenant_client_created", "tenant_id", "client_id", "created_at"),
        Index("ix_security_events_asset_created", "asset_id", "created_at"),
        Index("ix_security_events_processed", "processed", "created_at"),
    )
