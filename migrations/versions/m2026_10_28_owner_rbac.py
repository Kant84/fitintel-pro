"""Assign the admin role to the license owner only.

Revision ID: m2026_10_28_owner_rbac
Revises: m2026_10_28_shop_screen
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_28_owner_rbac"
down_revision = "m2026_10_28_shop_screen"
branch_labels = None
depends_on = None


def upgrade():
    # Используем логин из активной лицензии, а не installer server-admin.
    op.execute(sa.text("""
        INSERT INTO user_roles (
            id, user_id, role_id, assigned_at, created_at, updated_at
        )
        SELECT gen_random_uuid(), u.id, r.id,
               CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM license_state AS ls
        JOIN users AS u ON lower(u.username) = lower(ls.superadmin_login)
        JOIN roles AS r ON r.code = 'admin'
        WHERE ls.id = 1
          AND u.is_active = TRUE
          AND u.is_superuser = TRUE
        ON CONFLICT (user_id, role_id) DO NOTHING
    """))


def downgrade():
    # Не снимаем роль автоматически: после миграции её могли назначить вручную.
    pass
