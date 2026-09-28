"""m2026_09_28_screens_v2 — досев недостающих экранов тонкого клиента
(11 экранов: dashboard, clients, subscriptions, accounting, analytics,
commerce, export, integrations, messenger, notifications, ai_center).
Чистые установки получат их автоматически.

Revision: m2026_09_28_screens_v2
Revises: m2026_09_28_raw_tables
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_09_28_screens_v2"
down_revision = "m2026_09_28_raw_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        INSERT INTO ui_screens (code, name, path, sort_order) VALUES
         ('dashboard','Главная','/dashboard',5),
         ('clients','Клиенты','/clients',15),
         ('subscriptions','Абонементы','/subscriptions',25),
         ('accounting','Бухгалтерия','/accounting',52),
         ('analytics','Аналитика','/analytics',55),
         ('commerce','Коммерция','/commerce',75),
         ('export','Экспорт','/export',76),
         ('integrations','Интеграции','/integrations',77),
         ('messenger','MAX сообщения','/messenger',78),
         ('notifications','Уведомления','/notifications',79),
         ('ai_center','AI Центр','/ai-center',80)
        ON CONFLICT (code) DO NOTHING
    """))
    op.execute(sa.text("""
        INSERT INTO ui_role_screens (role, screen_code, is_visible)
        SELECT r.role, s.code, TRUE
        FROM (VALUES ('admin'),('manager'),('superadmin')) AS r(role)
        CROSS JOIN ui_screens s
        ON CONFLICT (role, screen_code) DO NOTHING
    """))


def downgrade():
    op.execute(sa.text("""
        DELETE FROM ui_role_screens WHERE screen_code IN
        ('dashboard','clients','subscriptions','accounting','analytics',
         'commerce','export','integrations','messenger','notifications','ai_center')
    """))
    op.execute(sa.text("""
        DELETE FROM ui_screens WHERE code IN
        ('dashboard','clients','subscriptions','accounting','analytics',
         'commerce','export','integrations','messenger','notifications','ai_center')
    """))