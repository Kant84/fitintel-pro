"""Server document archive and document RBAC.

Revision: m2026_10_29_document_archive
Revises: m2026_10_28_reports_rbac_runtime
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_29_document_archive"
down_revision = "m2026_10_28_reports_rbac_runtime"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("documents.read", "Чтение документов"),
    ("documents.create", "Создание и подписание документов"),
    ("documents.delete", "Удаление документов"),
)


def upgrade():
    bind = op.get_bind()
    for code, name in PERMISSIONS:
        bind.execute(sa.text("""
            INSERT INTO permissions (id, code, name, module, created_at, updated_at)
            VALUES (gen_random_uuid(), :code, :name, 'documents', now(), now())
            ON CONFLICT (code) DO NOTHING
        """), {"code": code, "name": name})

    for role, codes in (
        ("admin", tuple(code for code, _ in PERMISSIONS)),
        ("manager", ("documents.read", "documents.create")),
    ):
        for code in codes:
            bind.execute(sa.text("""
                INSERT INTO role_permissions (
                    id, role_id, permission_id, created_at, updated_at
                )
                SELECT gen_random_uuid(), r.id, p.id, now(), now()
                FROM roles r JOIN permissions p ON p.code = :code
                WHERE r.code = :role
                ON CONFLICT (role_id, permission_id) DO NOTHING
            """), {"code": code, "role": role})

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS document_versions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID NOT NULL
                REFERENCES documents(id) ON DELETE CASCADE,
            version INTEGER NOT NULL,
            pdf_path VARCHAR(500) NOT NULL,
            pdf_sha256 VARCHAR(64) NOT NULL,
            pdf_size BIGINT NOT NULL,
            docx_path VARCHAR(500) NOT NULL,
            docx_sha256 VARCHAR(64) NOT NULL,
            docx_size BIGINT NOT NULL,
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_document_versions_document_version
                UNIQUE (document_id, version),
            CONSTRAINT ck_document_versions_positive CHECK (version > 0),
            CONSTRAINT ck_document_versions_pdf_sha256
                CHECK (pdf_sha256 ~ '^[0-9a-f]{64}$'),
            CONSTRAINT ck_document_versions_docx_sha256
                CHECK (docx_sha256 ~ '^[0-9a-f]{64}$')
        )
    """))
    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_document_versions_document_created
        ON document_versions (document_id, version DESC, created_at DESC)
    """))


def downgrade():
    # Архивные версии и назначенные права не удаляем автоматически.
    pass
