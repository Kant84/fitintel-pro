# tests/test_w6_wallet_bonus_booking.py
"""W6: кошелёк (test-провайдер), правила бонусов, запись на занятие и отмена."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.core.security import pwd_context
from app.models.user import User

NOW = datetime.now(timezone.utc)


@pytest.fixture
def w6env(db_session):
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS wallets (id VARCHAR(64) PRIMARY KEY,"
        " client_id VARCHAR(64), balance FLOAT DEFAULT 0, frozen_balance FLOAT DEFAULT 0,"
        " currency VARCHAR(8) DEFAULT 'RUB', created_at TIMESTAMP, updated_at TIMESTAMP)"))
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS wallet_transactions (id VARCHAR(64) PRIMARY KEY,"
        " wallet_id VARCHAR(64), client_id VARCHAR(64), amount FLOAT,"
        " transaction_type VARCHAR(30), description TEXT,"
        " balance_before FLOAT, balance_after FLOAT,"
        " created_at TIMESTAMP, updated_at TIMESTAMP)"))
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS gamification_levels (id VARCHAR(64) PRIMARY KEY,"
        " client_id VARCHAR(64), current_xp FLOAT DEFAULT 0, level INTEGER DEFAULT 1,"
        " xp_to_next INTEGER DEFAULT 100, total_visits INTEGER DEFAULT 0,"
        " total_workout_minutes INTEGER DEFAULT 0, streak_days INTEGER DEFAULT 0,"
        " max_streak_days INTEGER DEFAULT 0, last_visit_date TIMESTAMP,"
        " achievements_count INTEGER DEFAULT 0, created_at TIMESTAMP, updated_at TIMESTAMP)"))
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS bonus_rules (id UUID PRIMARY KEY,"
        " category VARCHAR(20) NOT NULL DEFAULT 'ALL', event VARCHAR(30) NOT NULL,"
        " mode VARCHAR(10) NOT NULL DEFAULT 'fix', value NUMERIC(12,2) NOT NULL DEFAULT 0,"
        " active BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ)"))
    _cols = {r[1] for r in db_session.execute(text("PRAGMA table_info(clients)"))}
    if "user_id" not in _cols:
        db_session.execute(text("ALTER TABLE clients ADD COLUMN user_id VARCHAR(64)"))
        db_session.commit()
    for t in ("wallets", "wallet_transactions", "gamification_levels", "bonus_rules"):
        db_session.execute(text("DELETE FROM %s" % t))
    db_session.commit()
    return db_session


def _user_headers(client, db, auth_headers, phone):
    if not db.query(User).filter_by(username="w6user").first():
        db.add(User(username="w6user", email="w6@t.ru",
                    password_hash=pwd_context.hash("w6pass12345"), is_active=True))
        db.commit()
    r = client.post("/api/v1/auth/login",
                    json={"login": "w6user", "password": "w6pass12345"})
    h = {"Authorization": "Bearer " + r.json()["access_token"]}
    r2 = client.post("/api/v1/clients/", headers=auth_headers,
                     json={"first_name": "W6", "last_name": "Клиент", "phone": phone})
    assert r2.status_code == 201, r2.text
    uid = str(db.query(User).filter_by(username="w6user").first().id)
    db.execute(text("UPDATE clients SET user_id=:u "
                    "WHERE replace(cast(id as varchar),'-','')=:c"),
               {"u": uid, "c": str(r2.json()["id"]).replace("-", "")})
    db.commit()
    return h


class TestWallet:
    def test_config(self, client, w6env, auth_headers):
        h = _user_headers(client, w6env, auth_headers, "+79000000101")
        r = client.get("/api/v1/miniapp/wallet/config", headers=h)
        assert r.status_code == 200
        d = r.json()
        assert d["provider"] == "test" and d["min"] == 100.0 and d["bonus_percent"] == 5.0

    def test_topup_below_min_422(self, client, w6env, auth_headers):
        h = _user_headers(client, w6env, auth_headers, "+79000000102")
        r = client.post("/api/v1/miniapp/wallet/topup", json={"amount": 50}, headers=h)
        assert r.status_code == 422

    def test_topup_credits_balance_and_bonus(self, client, w6env, auth_headers):
        h = _user_headers(client, w6env, auth_headers, "+79000000103")
        r = client.post("/api/v1/bonus-rules", headers=auth_headers,
                        json={"category": "ALL", "event": "topup", "mode": "percent", "value": 7})
        assert r.status_code == 200, r.text
        r = client.post("/api/v1/miniapp/wallet/topup", json={"amount": 100}, headers=h)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["balance"] == 100.0 and d["bonuses_added"] == 7.0
        r = client.get("/api/v1/miniapp/wallet", headers=h)
        assert r.json()["balance"] == 100.0 and r.json()["bonuses"] == 7.0

    def test_topup_accumulates(self, client, w6env, auth_headers):
        h = _user_headers(client, w6env, auth_headers, "+79000000104")
        client.post("/api/v1/bonus-rules", headers=auth_headers,
                    json={"category": "ALL", "event": "topup", "mode": "percent", "value": 7})
        r1 = client.post("/api/v1/miniapp/wallet/topup", json={"amount": 100}, headers=h)
        print("TOPUP1:", r1.status_code, r1.text[:160])
        r2 = client.post("/api/v1/miniapp/wallet/topup", json={"amount": 100}, headers=h)
        print("TOPUP2:", r2.status_code, r2.text[:160])
        rows = w6env.execute(text(
            "SELECT replace(cast(client_id as varchar),'-',''), current_xp FROM gamification_levels")).fetchall()
        print("GAMIFI ROWS:", rows)
        w = client.get("/api/v1/miniapp/wallet", headers=h)
        print("WALLET:", w.status_code, w.text[:160])
        assert r1.json()["bonuses_added"] == 7.0
        assert r2.json()["balance"] == 200.0 and r2.json()["bonuses_added"] == 7.0
        assert w.json()["balance"] == 200.0 and w.json()["bonuses"] == 14.0

    def test_category_rule_adds_to_all(self, client, w6env, auth_headers):
        h = _user_headers(client, w6env, auth_headers, "+79000000105")
        client.post("/api/v1/bonus-rules", headers=auth_headers,
                    json={"category": "ALL", "event": "topup", "mode": "percent", "value": 7})
        client.post("/api/v1/bonus-rules", headers=auth_headers,
                    json={"category": "ADULT", "event": "topup", "mode": "fix", "value": 50})
        w6env.execute(text("UPDATE clients SET client_category='ADULT' WHERE phone=:p"),
                      {"p": "+79000000105"})
        w6env.commit()
        from app.api.v1.miniapp_config import award_bonus
        cid = w6env.execute(
            text("SELECT replace(cast(id as varchar),'-','') FROM clients WHERE phone=:p"),
            {"p": "+79000000105"}).scalar()
        got = award_bonus(w6env, cid, "topup", 100)
        print("ENGINE BONUS:", got, "| cid:", cid)
        assert got == 57.0  # 7% от 100 + фикс 50 (ALL + ADULT суммируются)

    def test_bonus_rules_crud(self, client, w6env, auth_headers):
        r = client.post("/api/v1/bonus-rules", headers=auth_headers,
                        json={"category": "VIP", "event": "visit", "mode": "fix", "value": 50})
        rid = r.json()["id"]
        items = client.get("/api/v1/bonus-rules", headers=auth_headers).json()["items"]
        print("RULES:", items)
        assert any(x["id"].replace("-", "") == rid.replace("-", "") for x in items), items
        client.delete("/api/v1/bonus-rules/" + rid, headers=auth_headers)
        items = client.get("/api/v1/bonus-rules", headers=auth_headers).json()["items"]
        assert all(x["id"].replace("-", "") != rid.replace("-", "") for x in items), items


class TestBookingCancel:
    def _service(self, db):
        from app.models.service import Service
        s = Service(name="W6 Занятие", category="GROUP", price=500.0,
                    duration_minutes=45, max_capacity=1, is_active=True)
        db.add(s)
        db.commit()
        db.refresh(s)
        import json as _json
        db.execute(text("UPDATE services SET schedule=:sc "
                        "WHERE replace(cast(id as varchar),'-','')=:i"),
                   {"sc": _json.dumps({"days": [0, 1, 2, 3, 4, 5, 6],
                                       "time_slots": [{"time": "10:00", "capacity": 1}]}),
                    "i": str(s.id).replace("-", "")})
        db.commit()
        return str(s.id)

    def test_slots_create_conflict_cancel(self, client, w6env, auth_headers):
        h = _user_headers(client, w6env, auth_headers, "+79000000106")
        sid = self._service(w6env)
        day = (NOW + timedelta(days=2)).strftime("%Y-%m-%d")
        r = client.get("/api/v1/miniapp/booking/slots",
                       params={"service_id": sid, "day": day})
        assert r.status_code == 200 and r.json()["items"][0]["time"] == "10:00"
        r = client.post("/api/v1/miniapp/booking",
                        json={"service_id": sid, "day": day, "time": "10:00"}, headers=h)
        assert r.status_code == 200, r.text
        r2 = client.post("/api/v1/miniapp/booking",
                         json={"service_id": sid, "day": day, "time": "10:00"}, headers=h)
        assert r2.status_code == 409
        mine = client.get("/api/v1/miniapp/booking/my", headers=h).json()["items"]
        assert len(mine) == 1
        r = client.delete("/api/v1/miniapp/booking/" + mine[0]["id"], headers=h)
        assert r.status_code == 200
        r = client.delete("/api/v1/miniapp/booking/" + mine[0]["id"], headers=h)
        assert r.status_code == 422

    def test_cancel_window_enforced(self, client, w6env, auth_headers):
        """CANCEL_WINDOW_HOURS=24: +2ч — отказ, +30ч — отмена."""
        h = _user_headers(client, w6env, auth_headers, "+79000000107")
        sid = self._service(w6env)
        day_close = (NOW + timedelta(hours=2)).strftime("%Y-%m-%d")
        client.post("/api/v1/miniapp/booking",
                    json={"service_id": sid, "day": day_close, "time": "10:00"}, headers=h)
        bid = client.get("/api/v1/miniapp/booking/my", headers=h).json()["items"][0]["id"]
        assert client.delete("/api/v1/miniapp/booking/" + bid, headers=h).status_code == 422
        day_far = (NOW + timedelta(days=2)).strftime("%Y-%m-%d")
        client.post("/api/v1/miniapp/booking",
                    json={"service_id": sid, "day": day_far, "time": "10:00"}, headers=h)
        mine = client.get("/api/v1/miniapp/booking/my", headers=h).json()["items"]
        bid2 = [x for x in mine if x["id"] != bid][0]["id"]
        assert client.delete("/api/v1/miniapp/booking/" + bid2, headers=h).status_code == 200
