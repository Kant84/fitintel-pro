# tests/test_visits.py
"""Посещения: вход/выход, anti-passback, завершение, активные, статистика.

Роутер: app/api/v1/visits.py (entry/exit/manual/complete/active/stats).
"""
import uuid
from datetime import date, datetime, timezone, datetime, timezone

import pytest


@pytest.fixture
def visits_env(db_session):
    from sqlalchemy import text
    db_session.execute(text("DELETE FROM visits"))
    db_session.commit()
    return db_session


def _mk_client(client, headers):
    phone = "+79%09d" % (uuid.uuid4().int % 10 ** 9)
    r = client.post("/api/v1/clients/", headers=headers, json={
        "first_name": "Визит", "last_name": "Тестовый", "phone": phone})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _mk_tariff(client, headers, limit=10):
    code = f"TAR_{uuid.uuid4().hex[:8]}"
    r = client.post("/api/v1/tariffs/", headers=headers, json={
        "code": code, "name": f"Тариф {code}", "price": 1000, "currency": "RUB",
        "duration_days": 30, "visit_limit": limit,
        "is_unlimited": False, "is_active": True})
    assert r.status_code == 201, r.text
    return r.json()


def _mk_subscription(client, headers, cid, tid):
    r = client.post("/api/v1/subscriptions/", headers=headers, json={
        "client_id": cid, "tariff_id": tid["id"],
        "start_date": str(date.today()), "status": "ACTIVE"})
    assert r.status_code == 201, r.text
    return r.json()


class TestVisits:
    def test_entry_requires_identifier(self, client, auth_headers, visits_env):
        r = client.post("/api/v1/visits/entry", headers=auth_headers,
                        json={"access_method": "MANUAL", "zone": "main"})
        assert r.status_code == 400

    def test_manual_visit_and_double_entry_conflict(self, client, auth_headers, visits_env):
        cid = _mk_client(client, auth_headers)
        r = client.post("/api/v1/visits/manual", headers=auth_headers, json={
            "client_id": cid,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "access_method": "MANUAL", "zone": "main"})
        assert r.status_code == 201, r.text
        assert r.json()["status"] == "ACTIVE"
        vid = r.json()["id"]

        r2 = client.post("/api/v1/visits/manual", headers=auth_headers, json={
            "client_id": cid,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "access_method": "MANUAL", "zone": "main"})
        assert r2.status_code == 409
        assert "уже" in r2.json()["detail"].lower()

        r3 = client.get(f"/api/v1/visits/{vid}", headers=auth_headers)
        assert r3.json()["status"] == "ACTIVE"

    def test_complete_visit_calculates_duration(self, client, auth_headers, visits_env):
        cid = _mk_client(client, auth_headers)
        vid = client.post("/api/v1/visits/manual", headers=auth_headers, json={
            "client_id": cid,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "access_method": "MANUAL"}).json()["id"]
        r = client.post(f"/api/v1/visits/{vid}/complete", headers=auth_headers,
                        json={"visit_id": vid})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "COMPLETED"
        assert d["exit_time"] is not None
        assert d["duration_minutes"] is not None

    def test_exit_endpoint(self, client, auth_headers, visits_env):
        cid = _mk_client(client, auth_headers)
        vid = client.post("/api/v1/visits/manual", headers=auth_headers, json={
            "client_id": cid,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "access_method": "RFID"}).json()["id"]
        r = client.post("/api/v1/visits/exit", headers=auth_headers,
                        json={"visit_id": vid})
        assert r.status_code == 200
        assert r.json()["status"] == "COMPLETED"

    def test_active_list_and_count(self, client, auth_headers, visits_env):
        cid = _mk_client(client, auth_headers)
        client.post("/api/v1/visits/manual", headers=auth_headers, json={
            "client_id": cid,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "access_method": "MANUAL"})
        r = client.get("/api/v1/visits/active", headers=auth_headers)
        assert r.status_code == 200 and r.json()["count"] >= 1
        r = client.get("/api/v1/visits/active/count", headers=auth_headers)
        assert r.status_code == 200 and r.json()["count"] >= 1

    def test_client_visits_history(self, client, auth_headers, visits_env):
        cid = _mk_client(client, auth_headers)
        client.post("/api/v1/visits/manual", headers=auth_headers, json={
            "client_id": cid,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "access_method": "QR"})
        r = client.get(f"/api/v1/visits/client/{cid}", headers=auth_headers)
        assert r.status_code == 200 and r.json()["count"] >= 1

    def test_visit_not_found(self, client, auth_headers, visits_env):
        r = client.get(f"/api/v1/visits/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code == 404

    def test_entry_with_subscription_uses_visit(self, client, auth_headers, visits_env):
        cid = _mk_client(client, auth_headers)
        tid = _mk_tariff(client, auth_headers, limit=1)
        sub = _mk_subscription(client, auth_headers, cid, tid)
        r = client.post("/api/v1/visits/entry", headers=auth_headers, json={
            "client_id": cid, "subscription_id": sub["id"],
            "access_method": "QR", "zone": "main"})
        assert r.status_code == 201, r.text
        r2 = client.get(f"/api/v1/subscriptions/{sub['id']}", headers=auth_headers)
        assert r2.json()["visits_used"] == 1
        r3 = client.post("/api/v1/visits/entry", headers=auth_headers, json={
            "client_id": cid, "subscription_id": sub["id"], "access_method": "QR"})
        assert r3.status_code in (400, 409)

    def test_stats_today(self, client, auth_headers, visits_env):
        cid = _mk_client(client, auth_headers)
        client.post("/api/v1/visits/manual", headers=auth_headers, json={
            "client_id": cid,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "access_method": "MANUAL"})
        r = client.get("/api/v1/visits/stats/today", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["total_visits"] >= 1