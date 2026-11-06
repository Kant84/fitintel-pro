-- 002_incidents.sql — статистика грубых обращений + флаг пробела знаний (07.11.2026)
CREATE TABLE IF NOT EXISTS incidents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_max_id text NOT NULL,
  club_id text,
  text text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_incidents_user ON incidents(user_max_id);
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS kb_miss boolean NOT NULL DEFAULT false;
