"""Encrypt existing fiscal dto_password values (C1).

Revision: m2026_10_31_fiscal_crypto
Revises: m2026_10_30_ui_fixes
"""
import json
import os

from alembic import op
import sqlalchemy as sa

revision = "m2026_10_31_fiscal_crypto"
down_revision = "m2026_10_30_ui_fixes"
branch_labels = None
depends_on = None

_PREFIX = "enc:v1:"


def upgrade():
    key = (os.environ.get("FISCAL_CRYPTO_KEY") or "").strip()
    if not key:
        # Без ключа миграция ничего не делает: запись останется в открытом
        # виде, приложение продолжит работать (passthrough-режим).
        return
    from cryptography.fernet import Fernet
    f = Fernet(key.encode())

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, settings FROM fiscal_settings")).fetchall()
    for rid, raw in rows:
        try:
            data = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
        except Exception:
            continue
        pwd = data.get("dto_password")
        if not pwd or str(pwd).startswith(_PREFIX):
            continue
        data["dto_password"] = _PREFIX + f.encrypt(str(pwd).encode()).decode()
        bind.execute(sa.text(
            "UPDATE fiscal_settings SET settings = :s, updated_at = now() WHERE id = :i"
        ), {"s": json.dumps(data, ensure_ascii=False), "i": rid})


def downgrade():
    pass
