"""m2026_09_30_face_photos — опциональное хранение фото лиц (решение клуба)
+ автоочистка шаблонов при удалении клиента.

Revision: m2026_09_30_face_photos
Revises: m2026_09_30_face_settings
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_09_30_face_photos"
down_revision = "m2026_09_30_face_settings"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text(
        "ALTER TABLE face_settings ADD COLUMN IF NOT EXISTS store_photos BOOLEAN NOT NULL DEFAULT FALSE"))
    # автоочистка шаблонов при ФИЗИЧЕСКОМ удалении клиента
    op.execute(sa.text("""
        CREATE OR REPLACE FUNCTION _face_cleanup_on_client_delete() RETURNS trigger AS $$
        BEGIN
            DELETE FROM face_templates WHERE client_id = OLD.id;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql
    """))
    op.execute(sa.text("""
        DROP TRIGGER IF EXISTS face_cleanup_on_client_delete ON clients;
        CREATE TRIGGER face_cleanup_on_client_delete
        AFTER DELETE ON clients
        FOR EACH ROW EXECUTE FUNCTION _face_cleanup_on_client_delete()
    """))


def downgrade():
    op.execute(sa.text("DROP TRIGGER IF EXISTS face_cleanup_on_client_delete ON clients"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS _face_cleanup_on_client_delete()"))
    op.execute(sa.text("ALTER TABLE face_settings DROP COLUMN IF EXISTS store_photos"))