"""Fix tariffs screen active flag, hide tariffs from support.

Revision: m2026_10_30_ui_fixes
Revises: m2026_10_30_reception_alignment
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_30_ui_fixes"
down_revision = "m2026_10_30_reception_alignment"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    bind.execute(sa.text(
        "UPDATE ui_screens SET is_active = true WHERE code = 'tariffs'"))
    bind.execute(sa.text("""
        INSERT INTO ui_role_screens (id, role, screen_code, is_visible)
        SELECT gen_random_uuid(),
               CAST('support' AS varchar), CAST('tariffs' AS varchar),
               CAST(false AS boolean)
        WHERE NOT EXISTS (
            SELECT 1 FROM ui_role_screens
            WHERE role = 'support' AND screen_code = 'tariffs'
        )
    """))
    bind.execute(sa.text("""
        UPDATE ui_role_screens SET is_visible = false
        WHERE role = 'support' AND screen_code = 'tariffs'
    """))


def downgrade():
    pass
