"""m2026_09_29_perms_ext — право users.delete + выдача ролям

Revision: m2026_09_29_perms_ext
Revises: m2026_09_29_roles_ext
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_09_29_perms_ext"
down_revision = "m2026_09_29_roles_ext"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        INSERT INTO permissions (id, code, name, module, created_at, updated_at)
        VALUES (gen_random_uuid(), 'users.delete', 'Удаление пользователей', 'users', now(), now())
        ON CONFLICT (code) DO NOTHING
    """))
    op.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r JOIN permissions p ON p.code = 'users.delete'
        WHERE r.code IN ('admin', 'manager', 'owner')
        ON CONFLICT (role_id, permission_id) DO NOTHING
    """))


def downgrade():
    op.execute(sa.text("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code='users.delete')"))
    op.execute(sa.text("DELETE FROM permissions WHERE code='users.delete'"))