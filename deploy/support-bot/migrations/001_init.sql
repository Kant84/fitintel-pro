-- 001_init.sql — схема бота поддержки (своя БД support_bot, platform не трогается)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS kb_articles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  question text NOT NULL,
  keywords text,
  answer text NOT NULL,
  category text,
  screenshots text[] NOT NULL DEFAULT '{}',
  source_file text,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_file, question)
);

CREATE TABLE IF NOT EXISTS clubs_bound (
  max_user_id text PRIMARY KEY,
  club_id text NOT NULL,
  license_key text NOT NULL,
  bound_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tickets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_max_id text NOT NULL,
  club_id text,
  subject text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'new' CHECK (status IN ('new','in_progress','waiting','closed')),
  assignee text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ticket_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticket_id uuid NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
  direction text NOT NULL CHECK (direction IN ('in','out')),
  body text NOT NULL,
  author text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bot_admins (
  max_user_id text PRIMARY KEY,
  name text NOT NULL,
  role text NOT NULL DEFAULT 'admin' CHECK (role IN ('admin','superadmin')),
  active boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS support_schedule (
  id serial PRIMARY KEY,
  admin_id text NOT NULL REFERENCES bot_admins(max_user_id) ON DELETE CASCADE,
  weekday int NOT NULL CHECK (weekday BETWEEN 0 AND 6),
  time_from time NOT NULL,
  time_to time NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_kb_fts ON kb_articles
  USING gin (to_tsvector('russian', coalesce(question,'') || ' ' || coalesce(keywords,'') || ' ' || coalesce(answer,'')));
CREATE INDEX IF NOT EXISTS idx_kb_trgm ON kb_articles USING gin (question gin_trgm_ops, keywords gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_user ON tickets(user_max_id);
CREATE INDEX IF NOT EXISTS idx_msg_ticket ON ticket_messages(ticket_id, created_at);
