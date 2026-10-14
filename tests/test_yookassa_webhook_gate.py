# tests/test_yookassa_webhook_gate.py
"""ЮKassa webhook: врата безопасности (HMAC-подпись, антидубль) — без зачисления."""
import hashlib, hmac, json, uuid
from datetime import datetime, timezone

from sqlalchemy import text


def _body(eid="w5-gate-1"):
    return {"event": "payment.succeeded",
            "object": {"id": eid, "status": "succeeded",
                       "amount": {"value": "100.00", "currency": "RUB"},
                       "metadata": {"wallet_topup": "1", "client_id": "x", "bonus_percent": "7"}}}


def _sig(raw: bytes, key: str = "test-webhook-secret") -> str:
    return hmac.new(key.encode(), raw, hashlib.sha256).hexdigest()


class TestWebhookGate:
    def test_bad_signature_rejected(self, client):
        raw = json.dumps(_body(), separators=(",", ":")).encode()
        r = client.post("/api/v1/yookassa/webhook", content=raw,
                        headers={"X-YooKassa-Signature": "deadbeef",
                                 "Content-Type": "application/json"})
        assert r.status_code == 403

    def test_duplicate_event_idempotent(self, client, db_session):
        raw = json.dumps(_body("w5-dup-1"), separators=(",", ":")).encode()
        db_session.execute(text(
            "INSERT INTO yookassa_webhook_events (id, event_key, event_type, payload, created_at, updated_at) "
            "VALUES (:i, :k, :t, :p, :c, :u)"),
            {"i": str(uuid.uuid4()), "k": "payment.succeeded:w5-dup-1",
             "t": "payment.succeeded", "p": raw.decode(),
             "c": datetime.now(timezone.utc), "u": datetime.now(timezone.utc)})
        db_session.commit()
        r = client.post("/api/v1/yookassa/webhook", content=raw,
                        headers={"X-YooKassa-Signature": _sig(raw),
                                 "Content-Type": "application/json"})
        assert r.status_code == 200
