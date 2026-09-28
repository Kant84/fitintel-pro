"""m2026_09_28_raw_tables — таблицы без ORM-моделей (raw SQL роутеры)

Создаёт: accounting_entries, setup_wizard, ui_screens, ui_role_screens
+ seed ui_screens (реестр экранов тонкого клиента) и видимость для ролей.

Revision: m2026_09_28_raw_tables
Revises: e60a1_add_ml_events
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_09_28_raw_tables"
down_revision = "e60a1_add_ml_events"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS accounting_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entry_date DATE NOT NULL,
            debit_account VARCHAR(50) NOT NULL,
            credit_account VARCHAR(50) NOT NULL,
            amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
            description TEXT,
            source VARCHAR(50) DEFAULT 'manual',
            is_closing BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS setup_wizard (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            key VARCHAR(100) UNIQUE NOT NULL,
            value TEXT,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS ui_screens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code VARCHAR(64) UNIQUE NOT NULL,
            name VARCHAR(128) NOT NULL,
            path VARCHAR(255) DEFAULT '',
            icon VARCHAR(50) DEFAULT 'circle',
            sort_order INTEGER DEFAULT 100,
            is_active BOOLEAN DEFAULT TRUE
        )
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS ui_role_screens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            role VARCHAR(100) NOT NULL,
            screen_code VARCHAR(64) NOT NULL REFERENCES ui_screens(code) ON DELETE CASCADE,
            is_visible BOOLEAN DEFAULT TRUE,
            UNIQUE (role, screen_code)
        )
    """))

    # seed: реестр экранов тонкого клиента (соответствует sidebar desktop)
    op.execute(sa.text("""
        INSERT INTO ui_screens (code, name, path, icon, sort_order) VALUES
        ('tariffs',     'Тарифы',        '/tariffs',     'tag',      10),
        ('visits',      'Входы/Выходы',  '/visits',      'log-in',   20),
        ('services',    'Услуги',        '/services',    'briefcase',30),
        ('schedule',    'Расписание',    '/schedule',    'calendar', 40),
        ('payments',    'Платежи',       '/payments',    'card',     50),
        ('reports',     'Отчёты',        '/reports',     'chart',    60),
        ('documents',   'Документы',     '/documents',   'file',     70),
        ('users',       'Пользователи',  '/users',       'users',    80),
        ('roles',       'Роли и права',  '/roles',       'shield',   90),
        ('devices',     'Устройства',    '/devices',     'cpu',     100),
        ('face_id',     'Face ID',       '/face-id',     'scan',    110),
        ('license',     'Лицензия',      '/license',     'key',     120),
        ('ui_config',   'Экраны ролей',  '/ui-config',   'layout',  130),
        ('setup',       'Мастер установки', '/setup',    'tool',    140),
        ('settings',    'Настройки',     '/settings',    'gear',    150),
        ('credentials', 'Браслеты/Карты','/credentials', 'key',     160),
        ('connections', 'Подключения',   '/connections', 'link',    170)
        ON CONFLICT (code) DO NOTHING
    """))

    # видимость: admin и manager видят всё (настраивается через «Экраны ролей»)
    op.execute(sa.text("""
        INSERT INTO ui_role_screens (role, screen_code, is_visible)
        SELECT r.role, s.code, TRUE
        FROM (VALUES ('admin'), ('manager'), ('superadmin')) AS r(role)
        CROSS JOIN ui_screens s
        ON CONFLICT (role, screen_code) DO NOTHING
    """))


def downgrade():
    op.execute(sa.text("DROP TABLE IF EXISTS ui_role_screens"))
    op.execute(sa.text("DROP TABLE IF EXISTS ui_screens"))
    op.execute(sa.text("DROP TABLE IF EXISTS setup_wizard"))
    op.execute(sa.text("DROP TABLE IF EXISTS accounting_entries"))