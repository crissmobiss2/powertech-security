"""Expand photo_url column to Text to support base64 thumbnails."""
from typing import Union
import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "authorized_persons",
        "photo_url",
        type_=sa.Text,
        existing_type=sa.String(500),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "authorized_persons",
        "photo_url",
        type_=sa.String(500),
        existing_type=sa.Text,
        existing_nullable=True,
    )
