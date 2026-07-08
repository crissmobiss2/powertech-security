import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.incident import Incident


class Alert(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "alerts"

    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    # critical, high, medium, low, info

    type: Mapped[str] = mapped_column(String(30), nullable=False, default="security")
    # security, operational, emergency, test

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    # draft, sending, sent, partial_failure, failed

    channels: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # ["sms", "email", "push", "in_app", "whatsapp", "telegram"]

    # Delivery tracking aggregates
    total_recipients: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    acknowledged_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    incident: Mapped[Optional["Incident"]] = relationship("Incident", back_populates="alerts")
    recipients: Mapped[list["AlertRecipient"]] = relationship(
        "AlertRecipient", back_populates="alert", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_alerts_tenant_status", "tenant_id", "status"),
        Index("ix_alerts_incident", "incident_id"),
        Index("ix_alerts_created_at", "created_at"),
    )


class AlertRecipient(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "alert_recipients"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    # sms, email, push, in_app, whatsapp, telegram, voice

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    # queued, sent, delivered, read, acknowledged, failed

    external_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    alert: Mapped["Alert"] = relationship("Alert", back_populates="recipients")

    __table_args__ = (
        Index("ix_alert_recipients_alert", "alert_id"),
        Index("ix_alert_recipients_user_status", "user_id", "status"),
    )
