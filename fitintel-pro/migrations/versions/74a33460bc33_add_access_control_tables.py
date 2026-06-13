"""add_access_control_tables

Revision ID: 74a33460bc33
Revises: 0098d04719ff
Create Date: 2026-04-17 20:52:49.463194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74a33460bc33'
down_revision: Union[str, Sequence[str], None] = '0098d04719ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




def upgrade() -> None:
    # ==========================================================
    # 1. credentials
    # ==========================================================
    op.create_table(
        "credentials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("issued_by_user_id", sa.UUID(), nullable=True),
        sa.Column("credential_type", sa.String(50), nullable=False),
        sa.Column("credential_value", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="ACTIVE"),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("qr_version", sa.String(50), nullable=True),
        sa.Column("qr_format", sa.String(50), nullable=True, server_default="jwt"),
        sa.Column("rfid_manufacturer", sa.String(100), nullable=True),
        sa.Column("rfid_model", sa.String(100), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issued_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credentials_client_id", "credentials", ["client_id"])
    op.create_index("ix_credentials_credential_value", "credentials", ["credential_value"], unique=True)
    op.create_index("ix_credentials_credential_type", "credentials", ["credential_type"])
    op.create_index("ix_credentials_status", "credentials", ["status"])
    op.create_index("ix_credentials_valid_until", "credentials", ["valid_until"])

    # ==========================================================
    # 2. access_cache
    # ==========================================================
    op.create_table(
        "access_cache",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("credential_value", sa.String(255), nullable=False),
        sa.Column("access_granted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("client_name", sa.String(255), nullable=True),
        sa.Column("subscription_status", sa.String(50), nullable=True),
        sa.Column("visits_left", sa.Integer(), nullable=True),
        sa.Column("subscription_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cache_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_cache_credential_value", "access_cache", ["credential_value"], unique=True)
    op.create_index("ix_access_cache_valid_until", "access_cache", ["valid_until"])
    op.create_index("ix_access_cache_device_id", "access_cache", ["device_id"])

    # ==========================================================
    # 3. access_logs
    # ==========================================================
    op.create_table(
        "access_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("credential_value", sa.String(255), nullable=False),
        sa.Column("credential_type", sa.String(50), nullable=True),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("mode", sa.String(50), nullable=False, server_default="online"),
        sa.Column("cache_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("request_data", sa.JSON(), nullable=True),
        sa.Column("response_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_logs_device_id", "access_logs", ["device_id"])
    op.create_index("ix_access_logs_credential_value", "access_logs", ["credential_value"])
    op.create_index("ix_access_logs_client_id", "access_logs", ["client_id"])
    op.create_index("ix_access_logs_created_at", "access_logs", ["created_at"])
    op.create_index("ix_access_logs_decision", "access_logs", ["decision"])

    # ==========================================================
    # 4. lockers
    # ==========================================================
    op.create_table(
        "lockers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("number", sa.String(50), nullable=False),
        sa.Column("zone", sa.String(100), nullable=True),
        sa.Column("lock_type", sa.String(50), nullable=False, server_default="OFFLINE"),
        sa.Column("status", sa.String(50), nullable=False, server_default="FREE"),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("requires_privilege", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lockers_number", "lockers", ["number"], unique=True)
    op.create_index("ix_lockers_lock_type", "lockers", ["lock_type"])
    op.create_index("ix_lockers_status", "lockers", ["status"])

    # ==========================================================
    # 5. locker_sessions
    # ==========================================================
    op.create_table(
        "locker_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("locker_id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("credential_id", sa.UUID(), nullable=True),
        sa.Column("lock_type", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="ACTIVE"),
        sa.Column("info_terminal_id", sa.String(255), nullable=True),
        sa.Column("register_terminal_id", sa.String(255), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["locker_id"], ["lockers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["credential_id"], ["credentials.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_locker_sessions_locker_id", "locker_sessions", ["locker_id"])
    op.create_index("ix_locker_sessions_client_id", "locker_sessions", ["client_id"])
    op.create_index("ix_locker_sessions_lock_type", "locker_sessions", ["lock_type"])
    op.create_index("ix_locker_sessions_status", "locker_sessions", ["status"])

    # ==========================================================
    # 6. locker_privileges
    # ==========================================================
    op.create_table(
        "locker_privileges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("locker_type", sa.String(50), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("issued_by_user_id", sa.UUID(), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issued_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_locker_privileges_client_id", "locker_privileges", ["client_id"])
    op.create_index("ix_locker_privileges_locker_type", "locker_privileges", ["locker_type"])

    # ==========================================================
    # 7. external_sync_logs
    # ==========================================================
    op.create_table(
        "external_sync_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("system_type", sa.String(50), nullable=False),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("request_data", sa.JSON(), nullable=True),
        sa.Column("response_data", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_external_sync_logs_system_type", "external_sync_logs", ["system_type"])
    op.create_index("ix_external_sync_logs_status", "external_sync_logs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_external_sync_logs_status", table_name="external_sync_logs")
    op.drop_index("ix_external_sync_logs_system_type", table_name="external_sync_logs")
    op.drop_table("external_sync_logs")

    op.drop_index("ix_locker_privileges_locker_type", table_name="locker_privileges")
    op.drop_index("ix_locker_privileges_client_id", table_name="locker_privileges")
    op.drop_table("locker_privileges")

    op.drop_index("ix_locker_sessions_status", table_name="locker_sessions")
    op.drop_index("ix_locker_sessions_lock_type", table_name="locker_sessions")
    op.drop_index("ix_locker_sessions_client_id", table_name="locker_sessions")
    op.drop_index("ix_locker_sessions_locker_id", table_name="locker_sessions")
    op.drop_table("locker_sessions")

    op.drop_index("ix_lockers_status", table_name="lockers")
    op.drop_index("ix_lockers_lock_type", table_name="lockers")
    op.drop_index("ix_lockers_number", table_name="lockers")
    op.drop_table("lockers")

    op.drop_index("ix_access_logs_decision", table_name="access_logs")
    op.drop_index("ix_access_logs_created_at", table_name="access_logs")
    op.drop_index("ix_access_logs_client_id", table_name="access_logs")
    op.drop_index("ix_access_logs_credential_value", table_name="access_logs")
    op.drop_index("ix_access_logs_device_id", table_name="access_logs")
    op.drop_table("access_logs")

    op.drop_index("ix_access_cache_device_id", table_name="access_cache")
    op.drop_index("ix_access_cache_valid_until", table_name="access_cache")
    op.drop_index("ix_access_cache_credential_value", table_name="access_cache")
    op.drop_table("access_cache")

    op.drop_index("ix_credentials_valid_until", table_name="credentials")
    op.drop_index("ix_credentials_status", table_name="credentials")
    op.drop_index("ix_credentials_credential_type", table_name="credentials")
    op.drop_index("ix_credentials_credential_value", table_name="credentials")
    op.drop_index("ix_credentials_client_id", table_name="credentials")
    op.drop_table("credentials")