"""SEC1: подписи, суммы и идемпотентность /bank/webhook."""
import hashlib
import hmac
import json
import uuid
from decimal import Decimal

import pytest

from app.api.v1.bank_online import _sber_checksum, _tinkoff_token
from app.models.client import Client
from app.models.payment import Payment
from app.models.wallet import Wallet


PATH = "/api/v1/bank/webhook"
TBANK_PASSWORD = "tbank-test-password"
SBER_CALLBACK_TOKEN = "sber-test-callback-token"


def _config():
    return {
        "tinkoff": {
            "terminal_key": "terminal-test",
            "password": TBANK_PASSWORD,
        },
        "sber": {
            "callback_token": SBER_CALLBACK_TOKEN,
        },
    }


@pytest.fixture
def bank_env(monkeypatch):
    monkeypatch.setattr("app.api.v1.bank_online._cfg", _config)


def _payment(db_session, status="pending", with_wallet=True):
    client = Client(
        first_name="Bank",
        last_name="Webhook",
        phone="+79" + str(uuid.uuid4().int)[:9],
    )
    db_session.add(client)
    db_session.flush()
    order_id = f"order-{uuid.uuid4().hex}"
    payment = Payment(
        client_id=client.id,
        amount=Decimal("100.00"),
        currency="RUB",
        payment_method="bank_card",
        payment_direction="incoming",
        payment_category="service",
        status=status,
        external_payment_id=f"bank:{order_id}",
        payment_system="bank:tinkoff",
    )
    db_session.add(payment)
    wallet = None
    if with_wallet:
        wallet = Wallet(
            client_id=client.id,
            balance=Decimal("50.00"),
            currency="RUB",
            frozen_balance=Decimal("0.00"),
        )
        db_session.add(wallet)
    db_session.commit()
    return payment, wallet, order_id


def _tbank_payload(order_id, status="CONFIRMED"):
    payload = {
        "TerminalKey": "terminal-test",
        "Amount": 10000,
        "OrderId": order_id,
        "PaymentId": f"payment-{order_id}",
        "Status": status,
        "Success": True,
    }
    payload["Token"] = _tinkoff_token(payload, TBANK_PASSWORD)
    return payload


def _post_tbank(client, payload):
    return client.post(
        PATH,
        content=json.dumps(payload, separators=(",", ":")).encode(),
        headers={"Content-Type": "application/json"},
    )


def _sber_payload(order_id, operation="deposited"):
    payload = {
        "amount": "10000",
        "mdOrder": f"md-{order_id}",
        "operation": operation,
        "orderNumber": order_id,
        "status": "1",
    }
    payload["checksum"] = _sber_checksum(payload, SBER_CALLBACK_TOKEN)
    return payload


def test_tbank_missing_token_rejected(
        client, db_session, bank_env):
    payment, wallet, order_id = _payment(db_session)
    payload = _tbank_payload(order_id)
    del payload["Token"]

    response = _post_tbank(client, payload)

    assert response.status_code == 401
    db_session.refresh(payment)
    db_session.refresh(wallet)
    assert payment.status == "pending"
    assert wallet.balance == Decimal("50.00")


def test_tbank_invalid_token_rejected(
        client, db_session, bank_env):
    payment, wallet, order_id = _payment(db_session)
    payload = _tbank_payload(order_id)
    payload["Token"] = "0" * 64

    response = _post_tbank(client, payload)

    assert response.status_code == 401
    db_session.refresh(payment)
    assert payment.status == "pending"


def test_tbank_missing_password_fails_closed(
        client, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.bank_online._cfg",
        lambda: {"tinkoff": {"terminal_key": "terminal-test"}},
    )
    payment, _, order_id = _payment(db_session)

    response = _post_tbank(client, _tbank_payload(order_id))

    assert response.status_code == 503
    db_session.refresh(payment)
    assert payment.status == "pending"


def test_tbank_amount_mismatch_rejected(
        client, db_session, bank_env):
    payment, wallet, order_id = _payment(db_session)
    payload = _tbank_payload(order_id)
    payload["Amount"] = 999
    payload["Token"] = _tinkoff_token(payload, TBANK_PASSWORD)

    response = _post_tbank(client, payload)

    assert response.status_code == 400
    db_session.refresh(payment)
    db_session.refresh(wallet)
    assert payment.status == "pending"
    assert wallet.balance == Decimal("50.00")


def test_tbank_success_and_replay_credit_wallet_once(
        client, db_session, bank_env):
    payment, wallet, order_id = _payment(db_session)
    payload = _tbank_payload(order_id)

    first = _post_tbank(client, payload)
    second = _post_tbank(client, payload)

    assert first.status_code == 200, first.text
    assert first.json()["duplicate"] is False
    assert second.status_code == 200, second.text
    assert second.json()["duplicate"] is True
    db_session.refresh(payment)
    db_session.refresh(wallet)
    assert payment.status == "succeeded"
    assert wallet.balance == Decimal("150.00")


def test_tbank_cancel_and_replay_do_not_credit(
        client, db_session, bank_env):
    payment, wallet, order_id = _payment(db_session)
    payload = _tbank_payload(order_id, status="CANCELED")

    first = _post_tbank(client, payload)
    second = _post_tbank(client, payload)

    assert first.status_code == 200, first.text
    assert second.json()["duplicate"] is True
    db_session.refresh(payment)
    db_session.refresh(wallet)
    assert payment.status == "canceled"
    assert wallet.balance == Decimal("50.00")


def test_tbank_refund_and_replay_debit_wallet_once(
        client, db_session, bank_env):
    payment, wallet, order_id = _payment(db_session)
    succeeded = _tbank_payload(order_id)
    refunded = _tbank_payload(order_id, status="REFUNDED")

    assert _post_tbank(client, succeeded).status_code == 200
    first = _post_tbank(client, refunded)
    second = _post_tbank(client, refunded)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json()["duplicate"] is True
    db_session.refresh(payment)
    db_session.refresh(wallet)
    assert payment.status == "refunded"
    assert wallet.balance == Decimal("50.00")


def test_sber_missing_checksum_rejected(
        client, db_session, bank_env):
    payment, wallet, order_id = _payment(db_session)
    payload = _sber_payload(order_id)
    del payload["checksum"]

    response = client.post(PATH, data=payload)

    assert response.status_code == 401
    db_session.refresh(payment)
    db_session.refresh(wallet)
    assert payment.status == "pending"
    assert wallet.balance == Decimal("50.00")


def test_sber_success_and_get_replay_credit_wallet_once(
        client, db_session, bank_env):
    payment, wallet, order_id = _payment(db_session)
    payload = _sber_payload(order_id)

    first = client.post(PATH, data=payload)
    second = client.get(PATH, params=payload)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json()["duplicate"] is True
    db_session.refresh(payment)
    db_session.refresh(wallet)
    assert payment.status == "succeeded"
    assert wallet.balance == Decimal("150.00")


def test_sber_invalid_checksum_rejected(
        client, db_session, bank_env):
    payment, _, order_id = _payment(db_session)
    payload = _sber_payload(order_id)
    payload["checksum"] = "0" * 64

    response = client.post(PATH, data=payload)

    assert response.status_code == 401
    db_session.refresh(payment)
    assert payment.status == "pending"