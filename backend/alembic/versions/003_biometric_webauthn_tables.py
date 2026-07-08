"""WebAuthn credentials and biometric access log tables.

Revision ID: 003
Revises: 002
Create Date: 2026-07-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webauthn_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("authorized_persons.id", ondelete="CASCADE"), nullable=True),
        sa.Column("credential_id", sa.String(500), nullable=False, unique=True),
        sa.Column("public_key", sa.Text, nullable=False),
        sa.Column("sign_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("device_type", sa.String(50), nullable=False, server_default="platform"),
        sa.Column("backed_up", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("transports", postgresql.JSONB, nullable=True),
        sa.Column("friendly_name", sa.String(200), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_webauthn_credentials_tenant", "webauthn_credentials", ["tenant_id"])
    op.create_index("ix_webauthn_credentials_user", "webauthn_credentials", ["user_id"])
    op.create_index("ix_webauthn_credentials_credential_id", "webauthn_credentials", ["credential_id"], unique=True)

    op.create_table(
        "biometric_access_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("authorized_persons.id"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("method", sa.String(30), nullable=False),
        sa.Column("success", sa.Boolean, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0"),
        sa.Column("person_name", sa.String(200), nullable=True),
        sa.Column("person_type", sa.String(30), nullable=True),
        sa.Column("zone", sa.String(100), nullable=True),
        sa.Column("device", sa.String(200), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("failure_reason", sa.String(200), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_biometric_access_logs_tenant", "biometric_access_logs", ["tenant_id"])
    op.create_index("ix_biometric_access_logs_created", "biometric_access_logs", ["created_at"])
    op.create_index("ix_biometric_access_logs_method", "biometric_access_logs", ["method"])


def downgrade() -> None:
    op.drop_table("biometric_access_logs")
    op.drop_table("webauthn_credentials")
