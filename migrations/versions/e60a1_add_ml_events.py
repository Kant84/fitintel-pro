"""E60: add ml_events table (canonical schema, safe for existing DBs)

Revision ID: e60a1_add_ml_events
Revises: 3084bd1d536e
"""
from alembic import op

revision = "e60a1_add_ml_events"
down_revision = "3084bd1d536e"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS ml_events (
            id UUID PRIMARY KEY,
            event_type VARCHAR(64) NOT NULL,
            payload JSONB DEFAULT '{}'::jsonb,
            client_id VARCHAR(64),
            user_id VARCHAR(64),
            session_id VARCHAR(64),
            source VARCHAR(32) DEFAULT 'api',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_ml_events_type ON ml_events (event_type, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ml_events_user ON ml_events (user_id, created_at)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS ml_events")