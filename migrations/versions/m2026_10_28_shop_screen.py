"""Register the desktop Shop screen for SuperAdmin only.

Revision ID: m2026_10_28_shop_screen
Revises: m2026_10_28_runtime_fixes
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_28_shop_screen"
down_revision = "m2026_10_28_runtime_fixes"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        INSERT INTO ui_screens (code, name, path, icon, sort_order, is_active)
        VALUES ('shop', 'Магазин', '/shop', 'shopping-bag', 56, TRUE)
        ON CONFLICT (code) DO NOTHING
    """))
    op.execute(sa.text("""
        INSERT INTO ui_role_screens (role, screen_code, is_visible)
        SELECT r.role, 'shop', r.role = 'superadmin'
        FROM (VALUES
            ('superadmin'), ('admin'), ('manager'), ('trainer'), ('reception'),
            ('cashier'), ('accountant'), ('support'), ('owner')
        ) AS r(role)
        ON CONFLICT (role, screen_code) DO NOTHING
    """))


def downgrade():
    # Не удаляем возможную ручную настройку экрана при откате версии.
    pass
