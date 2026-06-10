# migrations\versions\0098d04719ff_add_devices_table.py
"""add_devices_table

Revision ID: 0098d04719ff
Revises: 335fcbe95672
Create Date: 2026-04-16 23:21:57.184724

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0098d04719ff'
down_revision: Union[str, Sequence[str], None] = '335fcbe95672'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("device_type", sa.String(50), nullable=False),
        sa.Column("manufacturer", sa.String(100), nullable=True),
        sa.Column("protocol", sa.String(50), nullable=False, server_default="none"),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("zone", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_devices_code", "devices", ["code"], unique=True)
    op.create_index("ix_devices_device_type", "devices", ["device_type"])
    op.create_index("ix_devices_protocol", "devices", ["protocol"])
    op.create_index("ix_devices_is_active", "devices", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_devices_is_active", table_name="devices")
    op.drop_index("ix_devices_protocol", table_name="devices")
    op.drop_index("ix_devices_device_type", table_name="devices")
    op.drop_index("ix_devices_code", table_name="devices")
    op.drop_table("devices")