import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Table, Column
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.site import Site
    from app.models.incident import Incident


class Asset(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "assets"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    site_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # camera, nvr, dvr, access_panel, door_controller, biometric,
    # server, workstation, laptop, network_switch, router, firewall,
    # ups, sensor, iot_device, cloud_resource, other

    sub_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # e.g. type=camera, sub_type=dome|bullet|ptz|fisheye

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="online")
    # online, offline, degraded, maintenance, decommissioned, unknown

    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, index=True)
    mac_address: Mapped[Optional[str]] = mapped_column(String(17), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    firmware_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    purchase_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    warranty_expires: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    location_detail: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    floor: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    zone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_health_check_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    extra: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    # Flexible: camera resolution, NVR channels, server specs, etc.

    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    site: Mapped[Optional["Site"]] = relationship("Site", back_populates="assets")
    maintenance_logs: Mapped[list["AssetMaintenanceLog"]] = relationship(
        "AssetMaintenanceLog", back_populates="asset", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_assets_tenant_client", "tenant_id", "client_id"),
        Index("ix_assets_tenant_type_status", "tenant_id", "type", "status"),
        Index("ix_assets_site", "site_id"),
    )


class AssetMaintenanceLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "asset_maintenance_logs"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # preventive, corrective, emergency, inspection

    performed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    parts_used: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(nullable=True)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_maintenance_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="maintenance_logs")
