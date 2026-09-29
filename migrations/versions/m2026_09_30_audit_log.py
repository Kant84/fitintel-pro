"""m2026_09_30_audit_log — журнал аудита по модели app/models/audit.py (audit_logs)
+ настройка срока хранения + экран 'История' + право audit.read.

Revision: m2026_09_30_audit_log
Revises: m2026_09_30_sales_table
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_09_30_audit_log"
down_revision = "m2026_09_30_sales_table"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            actor_user_id UUID,
            action VARCHAR NOT NULL,
            entity_type VARCHAR NOT NULL,
            entity_id UUID,
            target_user_id UUID,
            role_id UUID,
            permission_id UUID,
            status VARCHAR NOT NULL,
            message VARCHAR,
            before_data JSONB,
            after_data JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at DESC)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_audit_logs_entity ON audit_logs (entity_type, action)"))
    # срок хранения (дней; 0 = бессрочно)
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS audit_settings (
            id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            retention_days INT NOT NULL DEFAULT 365
        )
    """))
    op.execute(sa.text("INSERT INTO audit_settings (id, retention_days) VALUES (1, 365) ON CONFLICT (id) DO NOTHING"))
    # экран «История» (видимостью управляет «Экраны ролей»)
    op.execute(sa.text("""
        INSERT INTO ui_screens (code, name, path, icon, sort_order) VALUES
        ('audit', 'История', '/audit', 'history', 86)
        ON CONFLICT (code) DO NOTHING
    """))
    op.execute(sa.text("""
        INSERT INTO ui_role_screens (role, screen_code, is_visible)
        SELECT r.role, 'audit', r.role IN ('superadmin', 'admin')
        FROM (VALUES ('superadmin'), ('admin'), ('manager'), ('trainer'),
                     ('reception'), ('cashier'), ('accountant'), ('support'), ('owner')) AS r(role)
        ON CONFLICT (role, screen_code) DO NOTHING
    """))
    # право чтения аудита
    op.execute(sa.text("""
        INSERT INTO permissions (id, code, name, module, created_at, updated_at)
        VALUES (gen_random_uuid(), 'audit.read', 'Просмотр журнала аудита', 'audit', now(), now())
        ON CONFLICT (code) DO NOTHING
    """))
    op.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r JOIN permissions p ON p.code = 'audit.read'
        WHERE r.code IN ('admin', 'owner')
        ON CONFLICT (role_id, permission_id) DO NOTHING
    """))


def downgrade():
    op.execute(sa.text("DROP TABLE IF EXISTS audit_logs"))
    op.execute(sa.text("DROP TABLE IF EXISTS audit_settings"))