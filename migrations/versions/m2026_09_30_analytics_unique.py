"""m2026_09_30_analytics_unique — уникальный ключ для upsert метрик аналитики
Чинит 500 на /analytics/dashboard и /analytics/recalc
('there is no unique or exclusion constraint matching the ON CONFLICT').

Revision: m2026_09_30_analytics_unique
Revises: m2026_09_30_face_photos
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_09_30_analytics_unique"
down_revision = "m2026_09_30_face_photos"
branch_labels = None
depends_on = None

TABLE = "daily_metrics"   # если запрос показал другое имя — впишите сюда


def upgrade():
    # защита от дублей, которые помешают создать约束
    op.execute(sa.text(f"""
        DELETE FROM {TABLE} a USING {TABLE} b
        WHERE a.ctid < b.ctid
          AND a.club_id = b.club_id AND a.metric = b.metric AND a.date = b.date
    """))
    op.execute(sa.text(f"""
        ALTER TABLE {TABLE}
        ADD CONSTRAINT uq_{TABLE}_club_metric_date UNIQUE (club_id, metric, date)
    """))


def downgrade():
    op.execute(sa.text(f"ALTER TABLE {TABLE} DROP CONSTRAINT IF EXISTS uq_{TABLE}_club_metric_date"))