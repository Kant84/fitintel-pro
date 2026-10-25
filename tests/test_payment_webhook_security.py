"""SEC1: подпись и идемпотентность generic payment webhook."""
import hashlib
import hmac
import json
import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.models.client import Client
from app.models.payment import Payment
from app.services.payment_service import PaymentService


PROVIDER = "testpay"
SECRET = "test-webhook-secret"
PATH = f"/api/v1/payments/webhook/{PROVIDER}"


def _raw(payload):
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _signature(raw):
    return hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()


def _post(client, raw, signature=None):
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Payment-Signature"] = signature
    return client.post(PATH, content=raw, headers=headers)


def _payment(db_session, status="PENDING", external_id=None):
    client = Client(
        first_name="Webhook",
        last_name="Тест",
        phone="+79" + str(uuid.uuid4().int)[:9],
        email=f"webhook-{uuid.uuid4().hex[:8]}@test.ru",
    )
    db_session.add(client)
    db_session.flush()
    payment = Payment(
        client_id=client.id,
        amount=Decimal("100.00"),
        currency="RUB",
        payment_method="ONLINE",
        payment_direction="INCOMING",
        payment_category="SUBSCRIPTION",
        status=status,
        external_payment_id=external_id or f"ext-{uuid.uuid4().hex}",
        paid_at=datetime.now() if status == "COMPLETED" else None,
    )
    db_session.add(payment)
    db_session.commit()
    return payment


@pytest.fixture
def webhook_env(monkeypatch):
    monkeypatch.setenv("PAYMENT_WEBHOOK_SECRET_TESTPAY", SECRET)
    monkeypatch.setattr(
        PaymentService,
        "_create_accounting_entry",
        lambda self, payment, kind="sale": None,
    )


def _payload(payment, status, event_id=None):
    data = {
        "payment_id": payment.external_payment_id,
        "status": status,
        "amount": "100.00",
    }
    if event_id:
        data["event_id"] = event_id
    return _raw(data)


def test_missing_signature_rejected_without_mutation(
        client, db_session, webhook_env):
    payment = _payment(db_session)
    raw = _payload(payment, "succeeded")

    response = _post(client, raw)

    assert response.status_code == 401
    db_session.refresh(payment)
    assert payment.status == "PENDING"


def test_invalid_signature_rejected_without_mutation(
        client, db_session, webhook_env):
    payment = _payment(db_session)
    raw = _payload(payment, "succeeded")

    response = _post(client, raw, "0" * 64)

    assert response.status_code == 401
    db_session.refresh(payment)
    assert payment.status == "PENDING"


def test_missing_secret_fails_closed(
        client, db_session, monkeypatch):
    monkeypatch.delenv("PAYMENT_WEBHOOK_SECRET_TESTPAY", raising=False)
    payment = _payment(db_session)
    raw = _payload(payment, "succeeded")

    response = _post(client, raw, _signature(raw))

    assert response.status_code == 503
    db_session.refresh(payment)
    assert payment.status == "PENDING"


def test_signed_malformed_json_rejected(client, webhook_env):
    raw = b'{"payment_id":'

    response = _post(client, raw, _signature(raw))

    assert response.status_code == 400


def test_succeeded_processed_once_and_replay_is_duplicate(
        client, db_session, webhook_env):
    payment = _payment(db_session)
    raw = _payload(payment, "succeeded", "event-success-1")
    signature = _signature(raw)

    first = _post(client, raw, signature)
    second = _post(client, raw, signature)

    assert first.status_code == 200, first.text
    assert first.json() == {"status": "ok", "duplicate": False}
    assert second.status_code == 200, second.text
    assert second.json() == {"status": "ok", "duplicate": True}
    db_session.refresh(payment)
    assert payment.status == "COMPLETED"
    assert payment.paid_at is not None
    events = db_session.execute(text(
        "SELECT COUNT(*) FROM payment_webhook_events "
        "WHERE event_key = :key"
    ), {"key": "testpay:event:event-success-1"}).scalar()
    assert events == 1


def test_canceled_processed_once_and_replay_is_duplicate(
        client, db_session, webhook_env):
    payment = _payment(db_session)
    raw = _payload(payment, "canceled", "event-cancel-1")
    signature = _signature(raw)

    first = _post(client, raw, signature)
    second = _post(client, raw, signature)

    assert first.status_code == 200, first.text
    assert second.json()["duplicate"] is True
    db_session.refresh(payment)
    assert payment.status == "FAILED"


def test_refund_processed_once_and_replay_is_duplicate(
        client, db_session, webhook_env, monkeypatch):
    payment = _payment(db_session, status="COMPLETED")
    monkeypatch.setattr("app.api.v1.fiscal._fiscalize", lambda *a, **k: None)
    monkeypatch.setattr(
        "app.api.v1.fiscal._get_settings",
        lambda db: {"driver": "mock"},
    )
    raw = _payload(payment, "refunded", "event-refund-1")
    signature = _signature(raw)

    first = _post(client, raw, signature)
    second = _post(client, raw, signature)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json()["duplicate"] is True
    db_session.refresh(payment)
    assert payment.status == "REFUNDED"
    refunds = db_session.query(Payment).filter_by(
        payment_direction="REFUND",
    ).count()
    assert refunds == 1