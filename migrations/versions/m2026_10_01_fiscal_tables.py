"""m2026_10_01_fiscal_tables — таблицы фискализации (E31): fiscal_settings,
fiscal_receipts, fiscal_shift. Чинит 500/502 на /fiscal/*.

Revision: m2026_10_01_fiscal_tables
Revises: m2026_09_30_connectors
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_01_fiscal_tables"
down_revision = "m2026_09_30_connectors"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS fiscal_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            driver VARCHAR(30) NOT NULL DEFAULT 'atol',
            port VARCHAR(100) NOT NULL DEFAULT 'COM3',
            settings JSONB,
            ofd_provider VARCHAR(50) DEFAULT 'ofd-ru',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS fiscal_receipts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            receipt_id VARCHAR(64) UNIQUE,
            driver VARCHAR(30) NOT NULL,
            receipt_type VARCHAR(20) NOT NULL,
            amount NUMERIC(12,2) NOT NULL DEFAULT 0,
            status VARCHAR(30) NOT NULL DEFAULT 'delivered',
            fiscal_document_number VARCHAR(32),
            fiscal_document_sign VARCHAR(64),
            original_receipt_id VARCHAR(64),
            ofd_provider VARCHAR(50),
            payload JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS fiscal_shift (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            is_open BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))


def downgrade():
    op.execute(sa.text("DROP TABLE IF EXISTS fiscal_shift"))
    op.execute(sa.text("DROP TABLE IF EXISTS fiscal_receipts"))
    op.execute(sa.text("DROP TABLE IF EXISTS fiscal_settings"))