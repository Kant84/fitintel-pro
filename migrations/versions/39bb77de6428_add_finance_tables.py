"""add_finance_tables

Revision ID: 39bb77de6428
Revises: 74a33460bc33
Create Date: 2026-04-18 00:14:57.037386

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39bb77de6428'
down_revision: Union[str, Sequence[str], None] = '74a33460bc33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # ==========================================================
    # 1. Кошелёк клиента
    # ==========================================================
    op.create_table(
        "wallets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("frozen_balance", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wallets_client_id", "wallets", ["client_id"], unique=True)

    # ==========================================================
    # 2. Транзакции кошелька
    # ==========================================================
    op.create_table(
        "wallet_transactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("wallet_id", sa.UUID(), nullable=False),
        sa.Column("transaction_type", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_before", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", sa.String(255), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wallet_transactions_wallet_id", "wallet_transactions", ["wallet_id"])
    op.create_index("ix_wallet_transactions_transaction_type", "wallet_transactions", ["transaction_type"])
    op.create_index("ix_wallet_transactions_reference_type", "wallet_transactions", ["reference_type"])
    op.create_index("ix_wallet_transactions_reference_id", "wallet_transactions", ["reference_id"])

    # ==========================================================
    # 3. Платежи
    # ==========================================================
    op.create_table(
        "payments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("payment_method", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("external_payment_id", sa.String(255), nullable=True),
        sa.Column("payment_system", sa.String(50), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payments_client_id", "payments", ["client_id"])
    op.create_index("ix_payments_payment_method", "payments", ["payment_method"])
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_external_payment_id", "payments", ["external_payment_id"])

    # ==========================================================
    # 4. Чеки
    # ==========================================================
    op.create_table(
        "receipts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("payment_id", sa.UUID(), nullable=False),
        sa.Column("receipt_number", sa.String(50), nullable=False),
        sa.Column("receipt_type", sa.String(50), nullable=False),
        sa.Column("fiscal_sign", sa.String(255), nullable=True),
        sa.Column("fiscal_document_number", sa.Integer(), nullable=True),
        sa.Column("fiscal_document_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ofd_url", sa.Text(), nullable=True),
        sa.Column("qr_code", sa.Text(), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("customer_email", sa.String(255), nullable=True),
        sa.Column("customer_phone", sa.String(20), nullable=True),
        sa.Column("is_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_receipts_payment_id", "receipts", ["payment_id"], unique=True)
    op.create_index("ix_receipts_receipt_number", "receipts", ["receipt_number"], unique=True)
    op.create_index("ix_receipts_receipt_type", "receipts", ["receipt_type"])

    # ==========================================================
    # 5. Кассовые смены
    # ==========================================================
    op.create_table(
        "cash_desk_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_number", sa.Integer(), nullable=False),
        sa.Column("cashier_user_id", sa.UUID(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opening_balance", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("closing_balance", sa.Numeric(12, 2), nullable=True),
        sa.Column("cash_income", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("cash_outcome", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("card_income", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("expected_cash", sa.Numeric(12, 2), nullable=True),
        sa.Column("actual_cash", sa.Numeric(12, 2), nullable=True),
        sa.Column("discrepancy", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="OPEN"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cashier_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cash_desk_sessions_session_number", "cash_desk_sessions", ["session_number"])
    op.create_index("ix_cash_desk_sessions_cashier_user_id", "cash_desk_sessions", ["cashier_user_id"])
    op.create_index("ix_cash_desk_sessions_status", "cash_desk_sessions", ["status"])

    # ==========================================================
    # 6. Кассовые операции
    # ==========================================================
    op.create_table(
        "cash_operations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("operation_type", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_method", sa.String(50), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["cash_desk_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cash_operations_session_id", "cash_operations", ["session_id"])
    op.create_index("ix_cash_operations_operation_type", "cash_operations", ["operation_type"])
    op.create_index("ix_cash_operations_payment_method", "cash_operations", ["payment_method"])
    op.create_index("ix_cash_operations_reference_type", "cash_operations", ["reference_type"])
    op.create_index("ix_cash_operations_reference_id", "cash_operations", ["reference_id"])


def downgrade() -> None:
    # Удаляем таблицы в обратном порядке
    op.drop_index("ix_cash_operations_reference_id", table_name="cash_operations")
    op.drop_index("ix_cash_operations_reference_type", table_name="cash_operations")
    op.drop_index("ix_cash_operations_payment_method", table_name="cash_operations")
    op.drop_index("ix_cash_operations_operation_type", table_name="cash_operations")
    op.drop_index("ix_cash_operations_session_id", table_name="cash_operations")
    op.drop_table("cash_operations")

    op.drop_index("ix_cash_desk_sessions_status", table_name="cash_desk_sessions")
    op.drop_index("ix_cash_desk_sessions_cashier_user_id", table_name="cash_desk_sessions")
    op.drop_index("ix_cash_desk_sessions_session_number", table_name="cash_desk_sessions")
    op.drop_table("cash_desk_sessions")

    op.drop_index("ix_receipts_receipt_type", table_name="receipts")
    op.drop_index("ix_receipts_receipt_number", table_name="receipts")
    op.drop_index("ix_receipts_payment_id", table_name="receipts")
    op.drop_table("receipts")

    op.drop_index("ix_payments_external_payment_id", table_name="payments")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_payment_method", table_name="payments")
    op.drop_index("ix_payments_client_id", table_name="payments")
    op.drop_table("payments")

    op.drop_index("ix_wallet_transactions_reference_id", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_reference_type", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_transaction_type", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_wallet_id", table_name="wallet_transactions")
    op.drop_table("wallet_transactions")

    op.drop_index("ix_wallets_client_id", table_name="wallets")
    op.drop_table("wallets")