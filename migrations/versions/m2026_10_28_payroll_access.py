"""Add payroll schema and repair runtime RBAC.

Revision: m2026_10_28_payroll_access
Revises: m2026_10_28_owner_rbac
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_28_payroll_access"
down_revision = "m2026_10_28_owner_rbac"
branch_labels = None
depends_on = None

PERM_DEFS = [
    ("service.accounts.manage", "Управление service-аккаунтами", "system"),
    ("audit.view", "Просмотр аудита доступа", "audit"),
    ("system.admin", "System administration", "system"),
]


def upgrade():
    bind = op.get_bind()

    op.execute(sa.text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)"
    ))

    for ddl in (
        """CREATE TABLE IF NOT EXISTS staff_positions (
            id UUID PRIMARY KEY, code VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL, base_salary NUMERIC(12,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS staff_payroll (
            user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            position_id UUID REFERENCES staff_positions(id) ON DELETE SET NULL,
            base_salary NUMERIC(12,2),
            rate_per_hour NUMERIC(12,2) NOT NULL DEFAULT 0,
            commission_percent NUMERIC(5,2) NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS payroll_monthly (
            id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            period VARCHAR(7) NOT NULL, advance NUMERIC(12,2) NOT NULL DEFAULT 0,
            deductions NUMERIC(12,2) NOT NULL DEFAULT 0, fines NUMERIC(12,2) NOT NULL DEFAULT 0,
            bonus NUMERIC(12,2) NOT NULL DEFAULT 0, note VARCHAR(500),
            paid_amount NUMERIC(12,2) NOT NULL DEFAULT 0, paid_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now(), UNIQUE (user_id, period))""",
    ):
        op.execute(sa.text(ddl))

    op.execute(sa.text(
        "ALTER TABLE payroll_monthly ADD COLUMN IF NOT EXISTS "
        "paid_amount NUMERIC(12,2) NOT NULL DEFAULT 0"
    ))
    op.execute(sa.text(
        "ALTER TABLE payroll_monthly ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ"
    ))

    for code, name, module in PERM_DEFS:
        bind.execute(sa.text("""
            INSERT INTO permissions (id, code, name, module, created_at, updated_at)
            VALUES (gen_random_uuid(), :code, :name, :module, now(), now())
            ON CONFLICT (code) DO NOTHING
        """), {"code": code, "name": name, "module": module})

    for role in ("admin", "owner"):
        for code, _, _ in PERM_DEFS:
            bind.execute(sa.text("""
                INSERT INTO role_permissions (
                    id, role_id, permission_id, created_at, updated_at
                )
                SELECT gen_random_uuid(), r.id, p.id, now(), now()
                FROM roles r JOIN permissions p ON p.code = :code
                WHERE r.code = :role
                ON CONFLICT (role_id, permission_id) DO NOTHING
            """), {"role": role, "code": code})


def downgrade():
    # Объекты могли существовать после прежнего lazy DDL/seed.
    pass