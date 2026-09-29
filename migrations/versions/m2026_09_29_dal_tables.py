"""m2026_09_29_dal_tables — таблицы DAL (устройства и драйверы)
Чинит 500 на /dal/devices и /dal/drivers (экран «Устройства»).

Revision: m2026_09_29_dal_tables
Revises: m2026_09_28_screens_v2
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_09_29_dal_tables"
down_revision = "m2026_09_28_screens_v2"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS dal_devices (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            driver_id UUID,
            name VARCHAR(128) NOT NULL,
            device_type VARCHAR(50) DEFAULT '',
            connection_string VARCHAR(255) DEFAULT '',
            driver_package VARCHAR(100) DEFAULT '',
            status VARCHAR(30) DEFAULT 'offline',
            config JSONB DEFAULT '{}'::jsonb,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS dal_drivers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            package VARCHAR(100) UNIQUE NOT NULL,
            name VARCHAR(128) DEFAULT '',
            version VARCHAR(30) DEFAULT '1.0.0',
            is_enabled BOOLEAN DEFAULT TRUE,
            installed_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))
    # стартовый набор драйверов (соответствует справке экрана «Устройства»)
    op.execute(sa.text("""
        INSERT INTO dal_drivers (package, name, version) VALUES
         ('era-t1000',  'ЭРА T-1000/2000 (C-PRO)',      '1.0.0'),
         ('kerong',     'Kerong (KR-*, СКУД)',          '1.0.0'),
         ('acs-acr1252','ACS ACR1252U (USB RFID)',      '1.0.0'),
         ('x1',         'X1 (турникеты)',               '1.0.0'),
         ('generic',    'Generic (HTTP/MQTT/MODBUS)',   '1.0.0')
        ON CONFLICT (package) DO NOTHING
    """))


def downgrade():
    op.execute(sa.text("DROP TABLE IF EXISTS dal_devices"))
    op.execute(sa.text("DROP TABLE IF EXISTS dal_drivers"))