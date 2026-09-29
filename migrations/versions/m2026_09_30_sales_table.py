"""m2026_09_30_sales_table — таблица продаж (модель app/models/sale.py).
Чинит 500 при удалении пользователя (каскад ORM) и /sales/report.

Revision: m2026_09_30_sales_table
Revises: m2026_09_29_perms_ext
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_09_30_sales_table"
down_revision = "m2026_09_29_perms_ext"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS sales (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cashier_id UUID NOT NULL REFERENCES users(id),
            total_amount NUMERIC(10, 2) NOT NULL,
            payment_method VARCHAR(20) NOT NULL,
            items JSONB NOT NULL,
            discount_code VARCHAR(50),
            status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED',
            refunded_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_sales_cashier_id ON sales (cashier_id)"))


def downgrade():
    op.execute(sa.text("DROP TABLE IF EXISTS sales"))