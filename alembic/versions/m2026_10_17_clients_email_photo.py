"""clients: photo_url column, email non-unique, normalize empty emails

Revision ID: m2026_10_17_clients_email_photo
Revises: m2026_10_01_fiscal_tables
Create Date: 2026-10-17 01:30:00
"""
from alembic import op

revision = "m2026_10_17_clients_email_photo"
down_revision = "m2026_10_01_fiscal_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS photo_url VARCHAR(500)")
    op.execute("DROP INDEX IF EXISTS ix_clients_email")
    op.execute("UPDATE clients SET email = NULL WHERE email = ''")


def downgrade():
    op.execute("UPDATE clients SET email = '' WHERE email IS NULL")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_clients_email ON clients (email)")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS photo_url")