"""Role permission profiles, platform/security roles, matrix rows.

Revision: m2026_10_29_role_profiles
Revises: m2026_10_29_document_archive
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_29_role_profiles"
down_revision = "m2026_10_29_document_archive"
branch_labels = None
depends_on = None

PROFILES = {
    "trainer": ["clients.read", "visits.read"],
    "cashier": ["clients.read", "tariffs.read", "subscriptions.read",
                "payments.read", "payments.create", "visits.read",
                "receipts.read", "receipts.send"],
    "accountant": ["clients.read", "tariffs.read", "subscriptions.read",
                   "payments.read", "payments.update", "visits.read",
                   "documents.read", "cash_desk.read"],
    "owner": ["clients.read", "clients.create", "clients.update",
              "tariffs.read", "tariffs.create", "tariffs.update",
              "subscriptions.read", "subscriptions.create", "subscriptions.update",
              "visits.read", "visits.create", "visits.update",
              "payments.read", "payments.create", "payments.update",
              "users.read", "payments.refund"],
    "support": ["clients.read", "settings.read"],
    "security": ["clients.read", "visits.read", "lockers.read"],
}

NEW_ROLES = [
    ("platform", "Платформа", "Сервисная роль платформы", True),
    ("security", "Охрана / СКУД", "Роль охраны и СКУД", False),
]

MATRIX = {
    "music": [("admin", True), ("accountant", False), ("cashier", False),
              ("manager", False), ("owner", False), ("support", False),
              ("trainer", False), ("security", False)],
    "connections": [("admin", True), ("accountant", False), ("cashier", False),
                    ("manager", False), ("owner", False), ("support", False),
                    ("trainer", False), ("security", False)],
}


def upgrade():
    bind = op.get_bind()

    for code, name, desc, is_system in NEW_ROLES:
        bind.execute(sa.text("""
            INSERT INTO roles (code, name, description, is_system, id, created_at, updated_at)
            VALUES (:code, :name, :desc, :sys, gen_random_uuid(), now(), now())
            ON CONFLICT (code) DO NOTHING
        """), {"code": code, "name": name, "desc": desc, "sys": is_system})

    bind.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r CROSS JOIN permissions p
        WHERE r.code = 'admin'
        ON CONFLICT (role_id, permission_id) DO NOTHING
    """))

    for role, codes in PROFILES.items():
        for code in codes:
            bind.execute(sa.text("""
                INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                SELECT gen_random_uuid(), r.id, p.id, now(), now()
                FROM roles r JOIN permissions p ON p.code = :code
                WHERE r.code = :role
                ON CONFLICT (role_id, permission_id) DO NOTHING
            """), {"role": role, "code": code})

    # Каталог экранов: регистрируем music (connections/credentials уже есть).
    bind.execute(sa.text("""
        INSERT INTO ui_screens (code, name)
        SELECT 'music', 'Музыка/DJ'
        WHERE NOT EXISTS (SELECT 1 FROM ui_screens WHERE code = 'music')
    """))

    for screen, rows in MATRIX.items():
        for role, visible in rows:
            bind.execute(sa.text("""
                INSERT INTO ui_role_screens (id, role, screen_code, is_visible)
                SELECT gen_random_uuid(),
                       CAST(:role AS varchar), CAST(:screen AS varchar),
                       CAST(:vis AS boolean)
                WHERE NOT EXISTS (
                    SELECT 1 FROM ui_role_screens
                    WHERE role = :role AND screen_code = :screen
                )
            """), {"role": role, "screen": screen, "vis": visible})


def downgrade():
    pass
