import os

migration_content = '''\"\"\"add_analytics_daily

Revision ID: 1ab62d1deaab
Revises: 
Create Date: 2026-06-20 19:48:00

\"\"\"
from alembic import op
import sqlalchemy as sa

revision = '1ab62d1deaab'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'analytics_daily',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('club_id', sa.Integer(), sa.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('metric', sa.String(20), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('value', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('forecast', sa.Numeric(12, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('club_id', 'metric', 'date', name='uix_daily_metric')
    )
    
    op.create_index('ix_analytics_daily_date', 'analytics_daily', ['date'])
    op.create_index('ix_analytics_daily_metric', 'analytics_daily', ['metric'])
    op.create_index('ix_analytics_daily_club_id', 'analytics_daily', ['club_id'])
    
    op.execute(\"\"\"
    CREATE OR REPLACE FUNCTION recalc_analytics_daily(p_club_id INT, p_date DATE)
    RETURNS VOID AS write_migration.py
    BEGIN
        INSERT INTO analytics_daily (club_id, metric, date, value)
        SELECT p_club_id, 'attendance', p_date, COUNT(*)
        FROM visits WHERE club_id = p_club_id AND DATE(check_in_at) = p_date
        ON CONFLICT (club_id, metric, date) DO UPDATE SET value = EXCLUDED.value;

        INSERT INTO analytics_daily (club_id, metric, date, value)
        SELECT p_club_id, 'revenue', p_date, COALESCE(SUM(amount), 0)
        FROM payments WHERE club_id = p_club_id AND DATE(created_at) = p_date AND status = 'completed'
        ON CONFLICT (club_id, metric, date) DO UPDATE SET value = EXCLUDED.value;

        INSERT INTO analytics_daily (club_id, metric, date, value)
        SELECT p_club_id, 'new_clients', p_date, COUNT(*)
        FROM users WHERE club_id = p_club_id AND DATE(created_at) = p_date
        ON CONFLICT (club_id, metric, date) DO UPDATE SET value = EXCLUDED.value;

        INSERT INTO analytics_daily (club_id, metric, date, value)
        SELECT p_club_id, 'churn_risk', p_date, COUNT(DISTINCT u.id)
        FROM users u
        JOIN subscriptions s ON s.user_id = u.id AND s.status = 'active'
        WHERE u.club_id = p_club_id
          AND NOT EXISTS (
              SELECT 1 FROM visits v 
              WHERE v.user_id = u.id AND v.check_in_at >= p_date - INTERVAL '14 days'
          )
        ON CONFLICT (club_id, metric, date) DO UPDATE SET value = EXCLUDED.value;
    END;
    write_migration.py LANGUAGE plpgsql;
    \"\"\")\n\n\ndef downgrade():\n    op.execute(\"DROP FUNCTION IF EXISTS recalc_analytics_daily(INT, DATE)\")\n    op.drop_index('ix_analytics_daily_club_id', table_name='analytics_daily')\n    op.drop_index('ix_analytics_daily_metric', table_name='analytics_daily')\n    op.drop_index('ix_analytics_daily_date', table_name='analytics_daily')\n    op.drop_table('analytics_daily')\n'''

path = 'migrations/versions/1ab62d1deaab_add_analytics_daily.py'
with open(path, 'w', encoding='utf-8') as f:
    f.write(migration_content)
print(f'Migration written: {path}')
