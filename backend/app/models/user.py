import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.client import Client


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    role: Mapped[str] = mapped_column(String(50), nullable=False, default="soc_analyst")
    # Roles: super_admin, client_admin, security_director, soc_analyst,
    #        it_engineer, field_technician, site_supervisor, executive, auditor

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # Statuses: active, inactive, suspended, pending_activation

    permissions_override: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Null = use role defaults; list of permission strings = override

    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    client: Mapped[Optional["Client"]] = relationship(
        "Client", back_populates="users", foreign_keys="[User.client_id]"
    )
    sessions: Mapped[list["UserSession"]] = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    __table_args__ = (
        Index("ix_users_tenant_email", "tenant_id", "email", unique=True),
        Index("ix_users_tenant_role", "tenant_id", "role"),
    )


class UserSession(Base, UUIDPrimaryKeyMixin):
    """Stores refresh token hashes for revocation support."""
    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    device_info: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="sessions")

    @property
    def is_valid(self) -> bool:
        from datetime import timezone
        return self.revoked_at is None and self.expires_at > datetime.now(timezone.utc)
