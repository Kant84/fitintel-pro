"""m2026_09_30_connectors — внешние коннекторы клубных систем (1С Фитнес, ХИТ)
Таблицы: connectors (настройки подключений), connector_sync_log (журнал синков).

Revision: m2026_09_30_connectors
Revises: m2026_09_30_analytics_defaults
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_09_30_connectors"
down_revision = "m2026_09_30_analytics_defaults"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS connectors (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(128) NOT NULL,
            type VARCHAR(30) NOT NULL,
            base_url VARCHAR(255) NOT NULL,
            auth_login VARCHAR(128),
            auth_password VARCHAR(255),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            last_sync_at TIMESTAMPTZ,
            last_status VARCHAR(20),
            last_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS connector_sync_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            connector_id UUID NOT NULL REFERENCES connectors(id) ON DELETE CASCADE,
            direction VARCHAR(10) NOT NULL DEFAULT 'in',
            entity VARCHAR(50) NOT NULL,
            records_count INT NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL,
            message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_connector_log ON connector_sync_log (connector_id, created_at DESC)"))


def downgrade():
    op.execute(sa.text("DROP TABLE IF EXISTS connector_sync_log"))
    op.execute(sa.text("DROP TABLE IF EXISTS connectors"))