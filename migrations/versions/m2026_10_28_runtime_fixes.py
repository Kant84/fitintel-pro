"""Client soft-delete schema and music runtime tables.

Revision ID: m2026_10_28_runtime_fixes
Revises: m2026_10_27_runtime_tables
"""
from alembic import op
import sqlalchemy as sa

revision = "m2026_10_28_runtime_fixes"
down_revision = "m2026_10_27_runtime_tables"
branch_labels = None
depends_on = None


def upgrade():
    # Таблица snapshot общая для восстановления клиентов и пользователей.
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS deletion_snapshots (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            payload JSONB NOT NULL,
            deleted_at TIMESTAMPTZ DEFAULT now()
        )
    """))
    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_deletion_snapshots_entity
        ON deletion_snapshots (entity, entity_id, deleted_at DESC)
    """))

    op.execute(sa.text(
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ"
    ))
    # Восстанавливаем признак удаления у клиентов, удалённых старой реализацией.
    op.execute(sa.text("""
        WITH latest_snapshots AS (
            SELECT DISTINCT ON (entity_id) entity_id, deleted_at
            FROM deletion_snapshots
            WHERE entity = 'clients'
            ORDER BY entity_id, deleted_at DESC
        )
        UPDATE clients AS c
        SET deleted_at = COALESCE(c.deleted_at, s.deleted_at, now()),
            is_active = FALSE
        FROM latest_snapshots AS s
        WHERE c.id::text = s.entity_id
    """))
    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_clients_deleted_at
        ON clients (deleted_at)
    """))

    # Раньше эти таблицы конкурентно создавались из HTTP-запросов.
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS music_zones (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            provider_type VARCHAR(20) NOT NULL DEFAULT 'local_agent',
            provider_config JSON,
            agent_token VARCHAR(64),
            desired_state VARCHAR(10) NOT NULL DEFAULT 'stopped',
            desired_playlist_id VARCHAR(36),
            volume INTEGER NOT NULL DEFAULT 50,
            dj_state JSON,
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """))
    op.execute(sa.text(
        "ALTER TABLE music_zones ADD COLUMN IF NOT EXISTS dj_state JSON"
    ))
    op.execute(sa.text(
        "ALTER TABLE music_zones ADD COLUMN IF NOT EXISTS machine_id VARCHAR(64)"
    ))
    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_music_zones_machine
        ON music_zones(machine_id)
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS music_playlists (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description VARCHAR(255),
            tracks JSON NOT NULL DEFAULT '[]'::json,
            is_energize BOOLEAN NOT NULL DEFAULT FALSE
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS music_schedule (
            id VARCHAR(36) PRIMARY KEY,
            zone_id VARCHAR(36) NOT NULL
                REFERENCES music_zones(id) ON DELETE CASCADE,
            day_of_week INTEGER NOT NULL DEFAULT -1,
            time_from TIME NOT NULL,
            time_to TIME NOT NULL,
            playlist_id VARCHAR(36),
            volume INTEGER NOT NULL DEFAULT 50
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS music_sfx (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            path VARCHAR(255) NOT NULL,
            volume INTEGER NOT NULL DEFAULT 80,
            sort INTEGER NOT NULL DEFAULT 0
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS music_pad_events (
            id VARCHAR(36) PRIMARY KEY,
            zone_id VARCHAR(36) NOT NULL,
            sfx_id VARCHAR(36),
            status VARCHAR(10) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            acked_at TIMESTAMP
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS music_license (
            id INTEGER PRIMARY KEY DEFAULT 1,
            license_type VARCHAR(20) NOT NULL DEFAULT 'none',
            provider_name VARCHAR(100),
            contract_number VARCHAR(100),
            valid_until DATE,
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """))
    op.execute(sa.text("""
        INSERT INTO music_license (id) VALUES (1)
        ON CONFLICT (id) DO NOTHING
    """))


def downgrade():
    # Миграция может принять таблицы и колонки, созданные старым lazy DDL.
    # Не удаляем их при downgrade, чтобы не потерять уже существующие данные.
    pass
