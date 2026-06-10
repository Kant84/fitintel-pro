"""add_subscription_lifecycle_fields

Revision ID: 40c0b026f189
Revises: 245df88b5d73
Create Date: 2026-04-16 00:18:15.561826

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40c0b026f189'
down_revision: Union[str, Sequence[str], None] = '245df88b5d73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================
    # 1. Добавляем новые поля в таблицу subscriptions
    # ==========================================================
    
    # Поля для заморозки
    op.add_column("subscriptions", sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("subscriptions", sa.Column("frozen_until", sa.Date(), nullable=True))
    op.add_column("subscriptions", sa.Column("freeze_reason", sa.String(255), nullable=True))
    
    # Поля для продления и отмены
    op.add_column("subscriptions", sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("subscriptions", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("subscriptions", sa.Column("cancellation_reason", sa.String(255), nullable=True))
    op.add_column("subscriptions", sa.Column("last_renewed_at", sa.DateTime(timezone=True), nullable=True))
    
    # ==========================================================
    # 2. Создаём таблицу subscription_events (история статусов)
    # ==========================================================
    
    op.create_table(
        "subscription_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("subscription_id", sa.UUID(), nullable=False),
        sa.Column("from_status", sa.String(50), nullable=True),
        sa.Column("to_status", sa.String(50), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Создаём индексы
    op.create_index("ix_subscription_events_subscription_id", "subscription_events", ["subscription_id"])
    op.create_index("ix_subscription_events_actor_user_id", "subscription_events", ["actor_user_id"])


def downgrade() -> None:
    # ==========================================================
    # 1. Удаляем таблицу subscription_events
    # ==========================================================
    
    op.drop_index("ix_subscription_events_actor_user_id", table_name="subscription_events")
    op.drop_index("ix_subscription_events_subscription_id", table_name="subscription_events")
    op.drop_table("subscription_events")
    
    # ==========================================================
    # 2. Удаляем добавленные поля из subscriptions
    # ==========================================================
    
    op.drop_column("subscriptions", "last_renewed_at")
    op.drop_column("subscriptions", "cancellation_reason")
    op.drop_column("subscriptions", "cancelled_at")
    op.drop_column("subscriptions", "auto_renew")
    op.drop_column("subscriptions", "freeze_reason")
    op.drop_column("subscriptions", "frozen_until")
    op.drop_column("subscriptions", "frozen_at")