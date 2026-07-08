import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Contract(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "contracts"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )

    reference_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    service_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # cctv_installation, access_control, cybersecurity_soc, it_support, network_security,
    # security_automation, emergency_alert, comprehensive

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    auto_renew: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    value: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PHP")
    billing_cycle: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    # monthly, quarterly, semi_annual, annual, one_time

    payment_terms_days: Mapped[int] = mapped_column(nullable=False, default=30)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # draft, active, suspended, expired, terminated

    services: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Included service modules and their configs

    sla_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    client: Mapped["Client"] = relationship("Client", back_populates="contracts")  # type: ignore[name-defined]

    __table_args__ = (
        Index("ix_contracts_tenant_client_status", "tenant_id", "client_id", "status"),
        Index("ix_contracts_end_date", "end_date"),
    )
