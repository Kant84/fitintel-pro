"""Assign default working permissions to the manager role.

Revision: m2026_10_28_manager_rbac
Revises: m2026_10_28_server_admins
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_28_manager_rbac"
down_revision = "m2026_10_28_server_admins"
branch_labels = None
depends_on = None

PERM_DEFS = [
    ("clients.read", "Просмотр клиентов", "clients"),
    ("clients.create", "Создание клиентов", "clients"),
    ("clients.update", "Изменение клиентов", "clients"),
    ("tariffs.read", "Просмотр тарифов", "tariffs"),
    ("tariffs.create", "Создание тарифов", "tariffs"),
    ("tariffs.update", "Изменение тарифов", "tariffs"),
    ("subscriptions.read", "Просмотр абонементов", "subscriptions"),
    ("subscriptions.create", "Создание абонементов", "subscriptions"),
    ("subscriptions.update", "Изменение и заморозка абонементов", "subscriptions"),
    ("visits.read", "Просмотр посещений", "visits"),
    ("visits.create", "Создание посещений", "visits"),
    ("visits.update", "Завершение посещений", "visits"),
    ("payments.read", "Просмотр платежей", "payments"),
    ("payments.create", "Создание платежей", "payments"),
    ("payments.update", "Изменение платежей", "payments"),
]


def upgrade():
    bind = op.get_bind()

    for code, name, module in PERM_DEFS:
        bind.execute(sa.text("""
            INSERT INTO permissions (id, code, name, module, created_at, updated_at)
            VALUES (gen_random_uuid(), :code, :name, :module, now(), now())
            ON CONFLICT (code) DO NOTHING
        """), {"code": code, "name": name, "module": module})

    for code, _, _ in PERM_DEFS:
        bind.execute(sa.text("""
            INSERT INTO role_permissions (
                id, role_id, permission_id, created_at, updated_at
            )
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r JOIN permissions p ON p.code = :code
            WHERE r.code = 'manager'
            ON CONFLICT (role_id, permission_id) DO NOTHING
        """), {"code": code})


def downgrade():
    # Не снимаем права автоматически: после миграции их могли назначить вручную.
    pass
