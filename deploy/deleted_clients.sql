-- Hide deleted clients without confusing them with ordinary inactive clients.
-- Existing trash snapshots identify clients deleted before deleted_at existed.
-- Safe to run repeatedly.

BEGIN;

ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

WITH latest_snapshots AS (
    SELECT DISTINCT ON (entity_id)
           entity_id, deleted_at
    FROM deletion_snapshots
    WHERE entity = 'clients'
    ORDER BY entity_id, deleted_at DESC
)
UPDATE clients AS c
SET deleted_at = COALESCE(c.deleted_at, s.deleted_at, now()),
    is_active = FALSE
FROM latest_snapshots AS s
WHERE c.id::text = s.entity_id;

CREATE INDEX IF NOT EXISTS idx_clients_deleted_at
    ON clients (deleted_at);

COMMIT;
