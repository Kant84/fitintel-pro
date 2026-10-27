"""Create separate installer server-admin accounts.

Revision: m2026_10_28_server_admins
Revises: m2026_10_28_document_templates
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_28_server_admins"
down_revision = "m2026_10_28_document_templates"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS server_admins (
            id UUID PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            migrated_from_user_id UUID REFERENCES users(id) ON DELETE RESTRICT,
            last_login_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))


def downgrade():
    # Не удаляем административные учётные записи автоматически.
    pass