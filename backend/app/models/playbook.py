import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Playbook(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """
    SOAR automation playbook.

    trigger_config example (asset_offline):
      { "asset_types": ["camera"], "site_risk_levels": ["high", "critical"] }

    conditions example (CEL-like JSON):
      { "all": [{ "field": "site.risk_level", "op": "in", "value": ["high","critical"] }] }

    actions example:
      [
        { "type": "create_incident", "config": { "severity": "high", "type": "physical" } },
        { "type": "send_alert", "config": { "channels": ["sms","in_app"], "roles": ["site_supervisor","client_admin"] } },
        { "type": "create_ticket", "config": { "type": "support", "priority": "high", "assign_role": "it_engineer" } }
      ]
    """
    __tablename__ = "playbooks"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # asset_offline, asset_online, incident_created, incident_severity_change,
    # scheduled, manual, webhook, threshold, security_event

    trigger_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    conditions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    actions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    executions: Mapped[list["PlaybookExecution"]] = relationship(
        "PlaybookExecution", back_populates="playbook"
    )

    __table_args__ = (
        Index("ix_playbooks_tenant_enabled_trigger", "tenant_id", "enabled", "trigger_type"),
    )


class PlaybookExecution(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "playbook_executions"

    playbook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True
    )

    trigger_event: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    # running, completed, failed, cancelled

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps_completed: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    results: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    playbook: Mapped["Playbook"] = relationship("Playbook", back_populates="executions")

    __table_args__ = (
        Index("ix_playbook_executions_tenant", "tenant_id", "started_at"),
    )
