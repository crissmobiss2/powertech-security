import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.site import Site
    from app.models.contract import Contract


class Client(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "clients"

    code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    risk_tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium"
    )
    # risk_tier: critical, high, medium, low

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # status: active, inactive, suspended, prospect

    billing_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # { street, city, province, zip, country }

    sla_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # { critical_response_hours: 1, high_response_hours: 4, medium_response_hours: 24 }

    account_manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="client")
    sites: Mapped[list["Site"]] = relationship("Site", back_populates="client")
    contracts: Mapped[list["Contract"]] = relationship("Contract", back_populates="client")

    __table_args__ = (
        Index("ix_clients_tenant_status", "tenant_id", "status"),
    )
