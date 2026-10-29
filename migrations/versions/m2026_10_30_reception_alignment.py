"""Reception role, matrix/permission alignment.

Revision: m2026_10_30_reception_alignment
Revises: m2026_10_29_role_profiles
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_30_reception_alignment"
down_revision = "m2026_10_29_role_profiles"
branch_labels = None
depends_on = None

RECEPTION_PERMS = [
    "clients.read",
    "tariffs.read",
    "subscriptions.read", "subscriptions.create", "subscriptions.update",
    "payments.read", "payments.create",
    "visits.read", "visits.create",
]

RECEPTION_SCREENS = ["dashboard", "clients", "subscriptions", "visits", "payments"]

# Экраны, видимые без соответствующего права: скрываем.
ALIGN_HIDE = [
    ("accountant", "users"), ("cashier", "users"), ("support", "users"),
    ("cashier", "documents"), ("support", "documents"),
    ("support", "subscriptions"),
    ("accountant", "setup"), ("cashier", "setup"),
    ("owner", "setup"), ("support", "setup"),
    ("accountant", "roles"), ("cashier", "roles"), ("owner", "roles"),
    ("support", "roles"), ("security", "roles"), ("reception", "roles"),
]


def upgrade():
    bind = op.get_bind()

    bind.execute(sa.text("""
        INSERT INTO roles (code, name, description, is_system, id, created_at, updated_at)
        VALUES ('reception', 'Ресепшен', 'Роль сотрудника ресепшена', false,
                gen_random_uuid(), now(), now())
        ON CONFLICT (code) DO NOTHING
    """))

    for code in RECEPTION_PERMS:
        bind.execute(sa.text("""
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r JOIN permissions p ON p.code = :code
            WHERE r.code = 'reception'
            ON CONFLICT (role_id, permission_id) DO NOTHING
        """), {"code": code})

    # owner читает документы (директор)
    bind.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r JOIN permissions p ON p.code = 'documents.read'
        WHERE r.code = 'owner'
        ON CONFLICT (role_id, permission_id) DO NOTHING
    """))

    for screen in RECEPTION_SCREENS:
        bind.execute(sa.text("""
            INSERT INTO ui_role_screens (id, role, screen_code, is_visible)
            SELECT gen_random_uuid(),
                   CAST('reception' AS varchar), CAST(:screen AS varchar),
                   CAST(true AS boolean)
            WHERE NOT EXISTS (
                SELECT 1 FROM ui_role_screens
                WHERE role = 'reception' AND screen_code = :screen
            )
        """), {"screen": screen})

    for role, screen in ALIGN_HIDE:
        bind.execute(sa.text("""
            INSERT INTO ui_role_screens (id, role, screen_code, is_visible)
            SELECT gen_random_uuid(),
                   CAST(:role AS varchar), CAST(:screen AS varchar),
                   CAST(false AS boolean)
            WHERE NOT EXISTS (
                SELECT 1 FROM ui_role_screens
                WHERE role = :role AND screen_code = :screen
            )
        """), {"role": role, "screen": screen})
        bind.execute(sa.text("""
            UPDATE ui_role_screens SET is_visible = false
            WHERE role = :role AND screen_code = :screen
        """), {"role": role, "screen": screen})


def downgrade():
    pass
