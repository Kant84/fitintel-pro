# tests/test_qr_max_entry.py
"""Вход по QR из MAX (B6): бот выдаёт динамический QR -> турникет пускает по правилам.

Цепочка: /max-bot/link (привязка) -> webhook "/qr" (бот выдаёт payload) ->
POST /dynamic-qr/turnstile (подпись, TTL, одноразовость, абонемент).
"""
import base64
import json
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest


@pytest.fixture
def qr_env(db_session):
    from app.models.dynamic_qr import DynamicQRCode
    db_session.query(DynamicQRCode).delete()
    db_session.commit()
    return db_session


def _mk_client(client, headers):
    phone = "+79%09d" % (uuid.uuid4().int % 10 ** 9)
    r = client.post("/api/v1/clients/", headers=headers, json={
        "first_name": "QR", "last_name": "Входов", "phone": phone})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _mk_tariff(client, headers):
    code = f"TAR_{uuid.uuid4().hex[:8]}"
    r = client.post("/api/v1/tariffs/", headers=headers, json={
        "code": code, "name": f"Тариф {code}", "price": 1000, "currency": "RUB",
        "duration_days": 30, "visit_limit": 10,
        "is_unlimited": False, "is_active": True})
    assert r.status_code == 201, r.text
    return r.json()


def _mk_subscription(client, headers, cid, tid):
    r = client.post("/api/v1/subscriptions/", headers=headers, json={
        "client_id": cid, "tariff_id": tid["id"],
        "start_date": str(date.today()), "status": "ACTIVE"})
    assert r.status_code == 201, r.text
    return r.json()


def _bind(client, headers, cid, max_uid):
    r = client.post("/api/v1/max-bot/link", headers=headers, json={
        "client_id": cid, "max_user_id": max_uid})
    assert r.status_code == 200, r.text


def _bot_qr(client, max_uid):
    r = client.post("/api/v1/max-bot/webhook", json={
        "message": {"sender": {"user_id": max_uid}, "body": {"text": "/qr"}}})
    assert r.status_code == 200, r.text
    return r.json().get("reply", "")


def _payload_from_reply(reply: str) -> str:
    for line in reply.split("\n"):
        line = line.strip()
        if line and not line.startswith(("🎟", "Покажите")):
            return line
    raise AssertionError("QR payload не найден в ответе бота: %r" % reply[:200])


def _turnstile(client, payload, device="turnstile-qr-1"):
    return client.post("/api/v1/dynamic-qr/turnstile", json={
        "qr_payload": payload, "device_id": device, "zone": "main"})


class TestMaxQrEntry:
    def test_qr_requires_binding(self, client, auth_headers, qr_env):
        reply = _bot_qr(client, "777000111")
        assert 'приложен' in reply.lower()

    def test_qr_requires_active_subscription(self, client, auth_headers, qr_env):
        cid = _mk_client(client, auth_headers)
        _bind(client, auth_headers, cid, "777000222")
        reply = _bot_qr(client, "777000222")
        assert "абонемент" in reply.lower()

    def test_qr_issued_and_turnstile_grants_entry(self, client, auth_headers, qr_env):
        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers)
        _mk_subscription(client, auth_headers, cid, tid)
        _bind(client, auth_headers, cid, "777000333")

        reply = _bot_qr(client, "777000333")
        assert "одноразовый" in reply
        payload = _payload_from_reply(reply)

        r = _turnstile(client, payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["access_granted"] is True
        assert d["turnstile_open"] is True
        assert str(d["client_id"]).replace("-", "") == cid.replace("-", "")

    def test_qr_is_one_time(self, client, auth_headers, qr_env):
        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers)
        _mk_subscription(client, auth_headers, cid, tid)
        _bind(client, auth_headers, cid, "777000444")
        payload = _payload_from_reply(_bot_qr(client, "777000444"))

        assert _turnstile(client, payload).json()["access_granted"] is True
        r2 = _turnstile(client, payload)      # повторное сканирование
        assert r2.status_code == 410
        assert "использован" in r2.json()["detail"].lower()

    def test_turnstile_rejects_tampered_signature(self, client, auth_headers, qr_env):
        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers)
        _mk_subscription(client, auth_headers, cid, tid)
        _bind(client, auth_headers, cid, "777000555")
        payload = _payload_from_reply(_bot_qr(client, "777000555"))

        raw = json.loads(base64.b64decode(payload))
        raw["client_id"] = str(uuid.uuid4())   # подмена при сохранении старой подписи
        tampered = base64.b64encode(json.dumps(raw).encode()).decode()
        r = _turnstile(client, tampered)
        assert r.status_code == 403

    def test_turnstile_rejects_expired_qr(self, client, auth_headers, qr_env):
        import hashlib
        import hmac as hmac_mod
        import time as time_mod
        from app.core.config import settings

        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers)
        _mk_subscription(client, auth_headers, cid, tid)
        _bind(client, auth_headers, cid, "777000666")

        # payload со старым timestamp (TTL 60 с, «выдан» 10 минут назад)
        secret = getattr(settings, "QR_SECRET_KEY", "fitintel-qr-secret-2026")
        ts = int(time_mod.time()) - 600
        body = {"client_id": cid, "timestamp": ts, "ttl": 60,
                "expires_at": ts + 60, "jti": uuid.uuid4().hex}
        sig = hmac_mod.new(secret.encode(),
                           json.dumps(body, sort_keys=True).encode(),
                           hashlib.sha256).hexdigest()
        body["signature"] = sig
        payload = base64.b64encode(json.dumps(body).encode()).decode()

        r = _turnstile(client, payload)
        assert r.status_code == 410
        assert "истёк" in r.json()["detail"].lower()

    def test_generate_endpoint_requires_active_subscription(self, client, auth_headers, qr_env):
        cid = _mk_client(client, auth_headers)
        r = client.post("/api/v1/dynamic-qr/generate", headers=auth_headers,
                        json={"client_id": cid, "expires_in_minutes": 5})
        assert r.status_code == 402