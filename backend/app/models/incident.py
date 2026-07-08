import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.ticket import Ticket


class Incident(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "incidents"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    site_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True
    )
    parent_incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    # critical, high, medium, low, info

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="new")
    # new, acknowledged, investigating, in_progress, resolved, closed, false_positive

    type: Mapped[str] = mapped_column(String(30), nullable=False, default="operational")
    # physical, cyber, combined, operational

    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    # manual, automated, integration, alert

    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    escalated_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    sla_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    resolution_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    timeline: Mapped[list["IncidentTimeline"]] = relationship(
        "IncidentTimeline", back_populates="incident", cascade="all, delete-orphan",
        order_by="IncidentTimeline.created_at"
    )
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="incident")
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="incident")

    __table_args__ = (
        Index("ix_incidents_tenant_client_status", "tenant_id", "client_id", "status"),
        Index("ix_incidents_tenant_severity_status", "tenant_id", "severity", "status"),
        Index("ix_incidents_assigned_to", "assigned_to"),
        Index("ix_incidents_created_at", "created_at"),
        Index("ix_incidents_sla_due_at", "sla_due_at"),
    )


class IncidentTimeline(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "incident_timeline"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # created, status_changed, severity_changed, assigned, escalated, commented,
    # alert_sent, ticket_created, playbook_executed, evidence_added, closed

    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="timeline")

    __table_args__ = (
        Index("ix_incident_timeline_incident_created", "incident_id", "created_at"),
    )
