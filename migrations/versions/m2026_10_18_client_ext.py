"""clients: tag/segment/source

Revision ID: m2026_10_18_client_ext
Revises: m2026_10_17_clients_email_photo
"""
from alembic import op

revision = "m2026_10_18_client_ext"
down_revision = "m2026_10_17_clients_email_photo"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS client_tag VARCHAR(100)")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS segment VARCHAR(100)")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS source VARCHAR(100)")


def downgrade():
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS client_tag")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS segment")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS source")