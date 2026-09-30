"""m2026_09_30_face_settings — настройки движка Face ID под клуб.
threshold: евклидово расстояние dlib (меньше = строже; 0.6 — дефолт dlib).
min_quality: порог резкости (Лапласиан). max_templates: лимит шаблонов на клиента.

Revision: m2026_09_30_face_settings
Revises: m2026_09_30_audit_log
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_09_30_face_settings"
down_revision = "m2026_09_30_audit_log"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS face_settings (
            id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            threshold NUMERIC(4,3) NOT NULL DEFAULT 0.600,
            min_quality NUMERIC(10,2) NOT NULL DEFAULT 40.00,
            max_templates INT NOT NULL DEFAULT 5
        )
    """))
    op.execute(sa.text(
        "INSERT INTO face_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING"))


def downgrade():
    op.execute(sa.text("DROP TABLE IF EXISTS face_settings"))