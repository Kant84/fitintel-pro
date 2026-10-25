BEGIN;

CREATE TABLE IF NOT EXISTS deletion_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_deletion_snapshots_entity
    ON deletion_snapshots (entity, entity_id, deleted_at DESC);

CREATE OR REPLACE FUNCTION trash_snapshot() RETURNS trigger AS $$
BEGIN
    INSERT INTO deletion_snapshots (entity, entity_id, payload)
    VALUES (TG_TABLE_NAME, COALESCE(OLD.id::text, ''), row_to_json(OLD));
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    entity_table TEXT;
BEGIN
    FOREACH entity_table IN ARRAY ARRAY[
        'clients',
        'users',
        'tariffs',
        'document_templates',
        'music_zones',
        'documents',
        'subscriptions',
        'credentials',
        'bonus_rules',
        'staff_positions',
        'connectors',
        'roles',
        'music_playlists',
        'music_schedule',
        'music_sfx',
        'client_contacts',
        'client_cars'
    ]
    LOOP
        -- Some optional modules create their tables lazily. They are skipped
        -- here and will be picked up by a repeated execution of this script.
        IF to_regclass('public.' || entity_table) IS NOT NULL
           AND NOT EXISTS (
               SELECT 1
               FROM pg_trigger
               WHERE tgrelid = to_regclass('public.' || entity_table)
                 AND tgname = 'trash_snapshot_trigger'
                 AND NOT tgisdisabled
           )
        THEN
            EXECUTE format(
                'CREATE TRIGGER trash_snapshot_trigger '
                || 'BEFORE DELETE ON public.%I '
                || 'FOR EACH ROW EXECUTE FUNCTION trash_snapshot()',
                entity_table
            );
        END IF;
    END LOOP;
END;
$$;

COMMIT;

SELECT
    c.relname AS table_name,
    t.tgname AS trigger_name
FROM pg_trigger AS t
JOIN pg_class AS c ON c.oid = t.tgrelid
WHERE t.tgname = 'trash_snapshot_trigger'
  AND NOT t.tgisdisabled
ORDER BY c.relname;
