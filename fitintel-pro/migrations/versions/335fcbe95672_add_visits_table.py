"""add_visits_table

Revision ID: 335fcbe95672
Revises: 40c0b026f189
Create Date: 2026-04-16 22:55:01.801217

"""


from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "335fcbe95672" 
down_revision: Union[str, Sequence[str], None] = "40c0b026f189"  
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаём таблицу visits
    op.create_table(
        "visits",
        sa.Column("id", sa.UUID(), nullable=False),
        
        # Связи
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("subscription_id", sa.UUID(), nullable=True),
        sa.Column("processed_by_user_id", sa.UUID(), nullable=True),
        
        # Временные метки
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exit_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        
        # Информация о доступе
        sa.Column("access_method", sa.String(50), nullable=False, server_default="QR"),
        sa.Column("access_device_id", sa.String(255), nullable=True),
        sa.Column("access_granted", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("access_denied_reason", sa.String(255), nullable=True),
        
        # Статус и зона
        sa.Column("status", sa.String(50), nullable=False, server_default="ACTIVE"),
        sa.Column("zone", sa.String(100), nullable=True),
        
        # Дополнительно
        sa.Column("notes", sa.Text(), nullable=True),
        
        # Служебные поля
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        
        # Ограничения
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["processed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Создаём индексы
    op.create_index("ix_visits_client_id", "visits", ["client_id"])
    op.create_index("ix_visits_subscription_id", "visits", ["subscription_id"])
    op.create_index("ix_visits_entry_time", "visits", ["entry_time"])
    op.create_index("ix_visits_status", "visits", ["status"])
    op.create_index("ix_visits_access_method", "visits", ["access_method"])
    op.create_index("ix_visits_processed_by_user_id", "visits", ["processed_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_visits_processed_by_user_id", table_name="visits")
    op.drop_index("ix_visits_access_method", table_name="visits")
    op.drop_index("ix_visits_status", table_name="visits")
    op.drop_index("ix_visits_entry_time", table_name="visits")
    op.drop_index("ix_visits_subscription_id", table_name="visits")
    op.drop_index("ix_visits_client_id", table_name="visits")
    op.drop_table("visits")