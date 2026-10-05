# tests/test_subscriptions.py
"""Абонементы: CRUD + жизненный цикл (freeze/unfreeze/renew/cancel/history).

Роутеры: app/api/v1/subscriptions.py + subscription_lifecycle.py.
Изоляция: уникальные коды тарифов и телефоны (SQLite общий на сессию).
"""
import uuid
from datetime import date, timedelta

import pytest


def _uniq(p: str) -> str:
    return f"{p}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def sub_env(db_session):
    """К таблицам абонементов/событий conftest.create_all уже подключён —
    здесь только чистим, чтобы тесты не зависели от порядка."""
    from sqlalchemy import text
    db_session.execute(text("DELETE FROM subscription_events"))
    db_session.execute(text("DELETE FROM subscriptions"))
    db_session.commit()
    return db_session


def _mk_client(client, headers):
    phone = "+79%09d" % (uuid.uuid4().int % 10 ** 9)
    r = client.post("/api/v1/clients/", headers=headers, json={
        "first_name": "Абонемент", "last_name": "Тестовый", "phone": phone})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _mk_tariff(client, headers, days=30, limit=10):
    code = _uniq("TAR")
    r = client.post("/api/v1/tariffs/", headers=headers, json={
        "code": code, "name": f"Тариф {code}", "description": "тест",
        "price": 3000, "currency": "RUB", "duration_days": days,
        "visit_limit": limit, "is_unlimited": False, "is_active": True})
    assert r.status_code == 201, r.text
    return r.json()


def _mk_subscription(client, headers, cid, tid, start=None):
    r = client.post("/api/v1/subscriptions/", headers=headers, json={
        "client_id": cid, "tariff_id": tid["id"],
        "start_date": str(start or date.today()),
        "status": "ACTIVE", "notes": "тест"})
    assert r.status_code == 201, r.text
    return r.json()


class TestSubscriptionCrud:
    def test_create_get_list(self, client, auth_headers, sub_env):
        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers, days=30)
        sub = _mk_subscription(client, auth_headers, cid, tid)
        assert sub["status"] == "ACTIVE"
        assert sub["end_date"] == str(date.today() + timedelta(days=30))

        r = client.get(f"/api/v1/subscriptions/{sub['id']}", headers=auth_headers)
        assert r.status_code == 200 and r.json()["id"] == sub["id"]

        r = client.get(f"/api/v1/subscriptions/client/{cid}", headers=auth_headers)
        assert r.status_code == 200 and r.json()["count"] >= 1

    def test_create_client_not_found(self, client, auth_headers, sub_env):
        tid = _mk_tariff(client, auth_headers)
        r = client.post("/api/v1/subscriptions/", headers=auth_headers, json={
            "client_id": str(uuid.uuid4()), "tariff_id": tid["id"],
            "start_date": str(date.today()), "status": "ACTIVE"})
        assert r.status_code == 404

    def test_update_patch(self, client, auth_headers, sub_env):
        """PATCH меняет статус (visits_used сервис игнорирует — см. ROADMAP, мёртвый параметр)."""
        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers)
        sub = _mk_subscription(client, auth_headers, cid, tid)
        r = client.patch(f"/api/v1/subscriptions/{sub['id']}", headers=auth_headers,
                         json={"status": "FROZEN", "notes": "через PATCH"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "FROZEN"

    def test_extend_grows_end_date(self, client, auth_headers, sub_env):
        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers, days=30)
        sub = _mk_subscription(client, auth_headers, cid, tid)
        r = client.post(f"/api/v1/subscriptions/{sub['id']}/extend?days=10",
                        headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["end_date"] == str(date.today() + timedelta(days=40))

    def test_extend_cancelled_rejected(self, client, auth_headers, sub_env):
        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers)
        sub = _mk_subscription(client, auth_headers, cid, tid)
        client.post(f"/api/v1/subscriptions/{sub['id']}/cancel", headers=auth_headers,
                    json={"reason": "USER_REQUEST"})
        r = client.post(f"/api/v1/subscriptions/{sub['id']}/extend?days=10",
                        headers=auth_headers)
        assert r.status_code == 400

    def test_delete_subscription(self, client, auth_headers, sub_env):
        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers)
        sub = _mk_subscription(client, auth_headers, cid, tid)
        r = client.delete(f"/api/v1/subscriptions/{sub['id']}", headers=auth_headers)
        assert r.status_code == 204
        assert client.get(f"/api/v1/subscriptions/{sub['id']}",
                          headers=auth_headers).status_code == 404


class TestSubscriptionLifecycle:
    def test_freeze_unfreeze_shifts_end_date(self, client, auth_headers, sub_env):
        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers, days=30)
        sub = _mk_subscription(client, auth_headers, cid, tid)
        orig_end = sub["end_date"]

        r = client.post(f"/api/v1/subscriptions/{sub['id']}/freeze",
                        headers=auth_headers,
                        json={"frozen_until": str(date.today() + timedelta(days=7)),
                              "reason": "TRAVEL", "notes": "отпуск"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "FROZEN"

        r = client.post(f"/api/v1/subscriptions/{sub['id']}/unfreeze",
                        headers=auth_headers)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "ACTIVE"
        # немедленная разморозка: фактический сдвиг 0 дней, срок не уменьшился
        assert d["end_date"] == orig_end
    def test_freeze_not_active_rejected(self, client, auth_headers, sub_env):
        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers)
        sub = _mk_subscription(client, auth_headers, cid, tid)
        client.post(f"/api/v1/subscriptions/{sub['id']}/cancel", headers=auth_headers,
                    json={"reason": "USER_REQUEST"})
        r = client.post(f"/api/v1/subscriptions/{sub['id']}/freeze",
                        headers=auth_headers,
                        json={"reason": "TRAVEL"})
        assert r.status_code == 400

    def test_cancel_makes_inactive(self, client, auth_headers, sub_env):
        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers)
        sub = _mk_subscription(client, auth_headers, cid, tid)
        r = client.post(f"/api/v1/subscriptions/{sub['id']}/cancel",
                        headers=auth_headers,
                        json={"reason": "USER_REQUEST", "notes": "отказ"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "CANCELLED"
        assert r.json()["is_active"] is False

    def test_renew_expired_subscription(self, client, auth_headers, sub_env):
        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers, days=30)
        sub = _mk_subscription(client, auth_headers, cid, tid,
                               start=date.today() - timedelta(days=60))
        r = client.post(f"/api/v1/subscriptions/{sub['id']}/renew",
                        headers=auth_headers, json={"auto_renew": False})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "ACTIVE"
        assert r.json()["end_date"] >= str(date.today() + timedelta(days=29))

    def test_history_records_lifecycle(self, client, auth_headers, sub_env):
        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers)
        sub = _mk_subscription(client, auth_headers, cid, tid)
        sid = sub["id"]
        client.post(f"/api/v1/subscriptions/{sid}/freeze", headers=auth_headers,
                    json={"reason": "TRAVEL"})
        client.post(f"/api/v1/subscriptions/{sid}/unfreeze", headers=auth_headers)
        client.post(f"/api/v1/subscriptions/{sid}/cancel", headers=auth_headers,
                    json={"reason": "USER_REQUEST"})
        r = client.get(f"/api/v1/subscriptions/{sid}/history", headers=auth_headers)
        assert r.status_code == 200, r.text
        statuses = [e["to_status"] for e in r.json()["items"]]
        assert "FROZEN" in statuses and "CANCELLED" in statuses
        assert len(statuses) >= 3   # freeze + unfreeze + cancel 