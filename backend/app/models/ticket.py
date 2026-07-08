import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.incident import Incident


class Ticket(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "tickets"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    site_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True
    )
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True
    )
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    type: Mapped[str] = mapped_column(String(50), nullable=False, default="support")
    # installation, maintenance, support, investigation, emergency, inspection

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    # open, assigned, in_progress, on_hold, resolved, closed, cancelled

    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    # critical, high, medium, low

    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_team: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    sla_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    checkin_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    checkout_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    client_signoff_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    client_signoff_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    labor_hours: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    parts_used: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # [{ name, qty, unit_cost, part_number }]
    cost: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    incident: Mapped[Optional["Incident"]] = relationship("Incident", back_populates="tickets")
    comments: Mapped[list["TicketComment"]] = relationship(
        "TicketComment", back_populates="ticket", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_tickets_tenant_client_status", "tenant_id", "client_id", "status"),
        Index("ix_tickets_assigned_to_status", "assigned_to", "status"),
        Index("ix_tickets_site", "site_id"),
        Index("ix_tickets_incident", "incident_id"),
        Index("ix_tickets_sla_due", "sla_due_at"),
    )


class TicketComment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ticket_comments"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attachments: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="comments")
