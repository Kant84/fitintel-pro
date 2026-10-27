"""Create media files and append-only access audit schema.

Revision: m2026_10_28_media_audit
Revises: m2026_10_28_payroll_access
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_28_media_audit"
down_revision = "m2026_10_28_payroll_access"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS media_files (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 't-1',
            owner_type TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            photo_type TEXT NOT NULL DEFAULT 'document',
            orig_name TEXT,
            mime TEXT,
            size BIGINT,
            sha256 TEXT,
            dek_enc TEXT,
            dek_nonce TEXT,
            file_nonce TEXT,
            key_version INTEGER DEFAULT 1,
            path TEXT,
            legacy_path TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            archived_at TIMESTAMP
        )
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_media_owner
        ON media_files (tenant_id, owner_type, owner_id)
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS media_access_log (
            id BIGSERIAL PRIMARY KEY,
            file_id TEXT,
            user_id TEXT,
            user_role TEXT,
            session_id TEXT,
            owner_id TEXT,
            action TEXT,
            result TEXT,
            ip TEXT,
            user_agent TEXT,
            reason TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    op.execute(sa.text("""
        CREATE OR REPLACE FUNCTION media_log_immutable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION
                'media_access_log is append-only: % not allowed', TG_OP;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
    """))

    op.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'media_log_no_update'
            ) THEN
                CREATE TRIGGER media_log_no_update
                BEFORE UPDATE OR DELETE ON media_access_log
                FOR EACH ROW
                EXECUTE FUNCTION media_log_immutable();
            END IF;
        END
        $$
    """))


def downgrade():
    # Таблицы могли существовать после прежнего lazy DDL.
    pass