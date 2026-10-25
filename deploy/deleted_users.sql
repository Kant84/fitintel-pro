-- Deleted users are technical tombstones, not ordinary inactive employees.
-- Safe to run repeatedly.

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- Mark only accounts anonymized by the old deletion implementation.
-- Ordinary inactive users and names merely starting with "deleted_" are untouched.
UPDATE users
SET deleted_at = COALESCE(deleted_at, now()),
    is_active = FALSE
WHERE COALESCE(username, '') ~ '^deleted_[0-9a-fA-F]{8}$';

CREATE INDEX IF NOT EXISTS idx_users_deleted_at
    ON users (deleted_at);

-- UserService.delete_user writes a restorable snapshot before anonymization.
CREATE TABLE IF NOT EXISTS deletion_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_deletion_snapshots_entity
    ON deletion_snapshots (entity, entity_id, deleted_at DESC);

COMMIT;
