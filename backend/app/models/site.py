import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.asset import Asset


class Site(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sites"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)

    address: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # { street, city, province, zip, country }

    latitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(nullable=True)

    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    # risk_level: critical, high, medium, low

    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Manila")

    type: Mapped[str] = mapped_column(String(50), nullable=False, default="office")
    # type: office, datacenter, warehouse, retail, industrial, residential, government, other

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    floor_plans: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # [{ floor: "1F", url: "...", uploaded_at: "..." }]

    emergency_contacts: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # [{ name: "...", role: "...", phone: "...", email: "..." }]

    notes: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="sites")
    assets: Mapped[list["Asset"]] = relationship("Asset", back_populates="site")

    __table_args__ = (
        Index("ix_sites_tenant_client", "tenant_id", "client_id"),
        Index("ix_sites_tenant_risk", "tenant_id", "risk_level"),
    )
