"""Manager schedule access and omitted warehouse/export schema.

Revision: m2026_10_28_reports_rbac_runtime
Revises: m2026_10_28_manager_rbac
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_28_reports_rbac_runtime"
down_revision = "m2026_10_28_manager_rbac"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    bind.execute(sa.text("""
        INSERT INTO permissions (id, code, name, module, created_at, updated_at)
        VALUES (gen_random_uuid(), 'trainers.read', 'Просмотр тренеров', 'trainers', now(), now())
        ON CONFLICT (code) DO NOTHING
    """))
    bind.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r JOIN permissions p ON p.code = 'trainers.read'
        WHERE r.code = 'manager'
        ON CONFLICT (role_id, permission_id) DO NOTHING
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS product_categories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            club_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            type VARCHAR(50),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT now()
        )
    """))
    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_product_categories_club_active
        ON product_categories (club_id, is_active)
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS export_jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            club_id INTEGER NOT NULL,
            user_id UUID,
            entity VARCHAR(50) NOT NULL,
            format VARCHAR(20) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            file_path VARCHAR(500),
            file_size BIGINT,
            row_count INTEGER,
            error_message TEXT,
            filters JSON,
            created_at TIMESTAMP DEFAULT now(),
            completed_at TIMESTAMP
        )
    """))
    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_export_jobs_club_created
        ON export_jobs (club_id, created_at DESC)
    """))


def downgrade():
    # Не удаляем данные и не снимаем права автоматически.
    pass
