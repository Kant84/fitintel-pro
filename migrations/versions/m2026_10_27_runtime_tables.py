"""Runtime tables omitted by the clean-install baseline.

Revision ID: m2026_10_27_auth_notification_runtime
Revises: m2026_10_18_client_ext
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_27_auth_notification_runtime"
down_revision = "m2026_10_18_client_ext"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            token_hash VARCHAR(64) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            revoked BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS notification_settings (
            id INTEGER PRIMARY KEY,
            updated_at TIMESTAMP DEFAULT now(),
            email_enabled BOOLEAN DEFAULT FALSE,
            smtp_host TEXT,
            smtp_port INTEGER DEFAULT 465,
            smtp_user TEXT,
            smtp_pass TEXT,
            email_from TEXT,
            sms_enabled BOOLEAN DEFAULT FALSE,
            smsc_login TEXT,
            smsc_pass TEXT,
            smsc_sender TEXT,
            webpush_enabled BOOLEAN DEFAULT FALSE,
            vapid_public TEXT,
            vapid_private TEXT,
            vapid_sub TEXT,
            digest_time VARCHAR(5) DEFAULT '09:00'
        )
    """))

    op.execute(sa.text("""
        INSERT INTO notification_settings (id)
        VALUES (1)
        ON CONFLICT (id) DO NOTHING
    """))


def downgrade():
    op.execute(sa.text("DROP TABLE IF EXISTS notification_settings"))
    op.execute(sa.text("DROP TABLE IF EXISTS auth_refresh_tokens"))