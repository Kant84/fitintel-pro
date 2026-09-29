"""m2026_09_29_roles_ext — экранные профили для ролей RBAC (cashier/accountant/support/owner)

Revision: m2026_09_29_roles_ext
Revises: m2026_09_29_dal_tables
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_09_29_roles_ext"
down_revision = "m2026_09_29_dal_tables"
branch_labels = None
depends_on = None


def upgrade():
    # новым ролям даём все экраны видимыми — клуб потом отметит нужное в «Экраны ролей»
    op.execute(sa.text("""
        INSERT INTO ui_role_screens (role, screen_code, is_visible)
        SELECT r.role, s.code, TRUE
        FROM (VALUES ('cashier'), ('accountant'), ('support'), ('owner')) AS r(role)
        CROSS JOIN ui_screens s
        ON CONFLICT (role, screen_code) DO NOTHING
    """))


def downgrade():
    op.execute(sa.text("""
        DELETE FROM ui_role_screens
        WHERE role IN ('cashier', 'accountant', 'support', 'owner')
    """))