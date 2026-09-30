"""m2026_09_30_analytics_defaults — DEFAULT now() для created_at в analytics_daily
Чинит 500 dashboard: 'null value in column created_at violates not-null constraint'.

Revision: m2026_09_30_analytics_defaults
Revises: m2026_09_30_analytics_unique
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_09_30_analytics_defaults"
down_revision = "m2026_09_30_analytics_unique"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text(
        "ALTER TABLE analytics_daily ALTER COLUMN created_at SET DEFAULT now()"))


def downgrade():
    op.execute(sa.text(
        "ALTER TABLE analytics_daily ALTER COLUMN created_at DROP DEFAULT"))