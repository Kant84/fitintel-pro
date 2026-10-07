"""Волна 5 (реальная встройка): параметры клуба, лейблы, жизненный цикл брони,
политика входа (абонемент ИЛИ оплаченное занятие), свип напоминаний.

Фикстуры conftest: client (TestClient), auth_headers (superadmin), db_session.
"""
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import text

from app.models.client import Client
from app.models.service import Service, ServiceBooking
from app.models.subscription import Subscription
from app.models.tariff import Tariff
from app.services.entry_policy import entry_reasons, can_enter
from app.services.booking_sweep import sweep as booking_sweep

NOW = datetime.now(timezone.utc)


def _mk_client(db, phone="+79000000001") -> Client:
    """Через API: сервер сам заполнит обязательные поля модели (дрейф-сейф)."""
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    from app.core.security import pwd_context
    from app.models.user import User
    sess = db
    if not sess.query(User).filter_by(username="superadmin").first():
        sess.add(User(username="superadmin", email="sa@t.ru",
                      password_hash=pwd_context.hash("testpass123"),
                      is_active=True, is_superuser=True))
        sess.commit()
    r = c.post("/api/v1/auth/login", json={"login": "superadmin", "password": "testpass123"})
    h = {"Authorization": "Bearer " + r.json()["access_token"]}
    resp = c.post("/api/v1/clients", json={"first_name": "Иван", "last_name": "Тестов",
                                           "phone": phone}, headers=h)
    assert resp.status_code in (200, 201), resp.text
    cid = resp.json()["id"]
    return sess.query(Client).filter_by(id=cid).first()


def _mk_service(db, name="Персональная тренировка", maxcap=1) -> Service:
    s = Service(name=name, category="PERSONAL_TRAINER", price=1500.0,
                duration_minutes=45, max_capacity=maxcap, is_active=True)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _mk_tariff(db, name="Безлимит", code="TEST-UNL") -> Tariff:
    t = Tariff(name=name, code=code, price=3000.0, visit_limit=None, duration_days=30,
               is_active=True)
    db.add(t); db.commit(); db.refresh(t)
    return t


def _mk_subscription(db, client_id, tariff_id) -> Subscription:
    sub = Subscription(client_id=str(client_id), tariff_id=tariff_id,
                       start_date=NOW.date(), end_date=(NOW + timedelta(days=30)).date(),
                       visits_used=0, is_unlimited=True, status="ACTIVE", is_active=True)
    db.add(sub); db.commit(); db.refresh(sub)
    return sub


# ---------- параметры клуба ----------

class TestClubParams:
    def test_defaults_present(self, client, auth_headers):
        r = client.get("/api/v1/club-params", headers=auth_headers)
        assert r.status_code == 200
        data = {i["key"]: i["value"] for i in r.json()}
        assert data["SLOT_MINUTES"] == "45"
        assert data["QR_ACCESS_WINDOW_HOURS"] == "1"
        assert data["CANCEL_WINDOW_HOURS"] == "24"

    def test_override_and_readback(self, client, auth_headers):
        r = client.put("/api/v1/club-params/CANCEL_WINDOW_HOURS",
                       json={"value": "48"}, headers=auth_headers)
        assert r.status_code == 200
        r = client.get("/api/v1/club-params", headers=auth_headers)
        data = {i["key"]: i["value"] for i in r.json()}
        assert data["CANCEL_WINDOW_HOURS"] == "48"
        # вернуть обратно для остальных тестов
        client.put("/api/v1/club-params/CANCEL_WINDOW_HOURS",
                   json={"value": "24"}, headers=auth_headers)

    def test_unknown_param_rejected(self, client, auth_headers):
        r = client.put("/api/v1/club-params/NOPE", json={"value": "1"}, headers=auth_headers)
        assert r.status_code == 404


# ---------- лейблы ----------

class TestLabels:
    def test_defaults(self, client, auth_headers):
        r = client.get("/api/v1/bot-labels", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["labels"]["TXT.MENU.QR"]

    def test_override(self, client, auth_headers):
        r = client.put("/api/v1/bot-labels/TXT.MENU.QR",
                       json={"value": "🔳 Пропуск"}, headers=auth_headers)
        assert r.status_code == 200
        from app.api.v1.club_params import get_label
        assert get_label("TXT.MENU.QR") == "🔳 Пропуск"


# ---------- жизненный цикл брони ----------

class TestBookingLifecycle:
    def test_book_confirm_pay_complete(self, client, auth_headers, db_session):
        c = _mk_client(db_session, "+79000000011")
        s = _mk_service(db_session, "Тренировка А")
        when = (NOW + timedelta(hours=30)).isoformat()
        r = client.post(f"/api/v1/services/{s.id}/book",
                        json={"client_id": str(c.id), "booking_date": when},
                        headers=auth_headers)
        assert r.status_code == 201, r.text
        bid = str(db_session.query(ServiceBooking).first().id)

        assert client.post(f"/api/v1/services/bookings/{bid}/confirm",
                           headers=auth_headers).status_code == 200
        assert client.post(f"/api/v1/services/bookings/{bid}/pay?price=1500",
                           headers=auth_headers).status_code == 200
        r = client.post(f"/api/v1/services/bookings/{bid}/complete", headers=auth_headers)
        assert r.status_code == 200 and r.json()["status"] == "COMPLETED"

        rating = db_session.execute(text("SELECT rating FROM clients WHERE id=:i"),
                                    {"i": str(c.id)}).scalar()
        assert abs(rating - 5.1) < 1e-6  # +0.1 за завершённое занятие

    def test_no_show_drops_rating(self, client, auth_headers, db_session):
        c = _mk_client(db_session, "+79000000012")
        s = _mk_service(db_session, "Тренировка Б")
        when = (NOW + timedelta(hours=30)).isoformat()
        client.post(f"/api/v1/services/{s.id}/book",
                    json={"client_id": str(c.id), "booking_date": when},
                    headers=auth_headers)
        bid = str(db_session.query(ServiceBooking).first().id)
        client.post(f"/api/v1/services/bookings/{bid}/confirm", headers=auth_headers)
        r = client.post(f"/api/v1/services/bookings/{bid}/no-show", headers=auth_headers)
        assert r.status_code == 200
        rating = db_session.execute(text("SELECT rating FROM clients WHERE id=:i"),
                                    {"i": str(c.id)}).scalar()
        assert abs(rating - 4.5) < 1e-6

    def test_cancel_window_from_params(self, client, auth_headers, db_session):
        client.put("/api/v1/club-params/CANCEL_WINDOW_HOURS",
                   json={"value": "48"}, headers=auth_headers)
        try:
            c = _mk_client(db_session, "+79000000013")
            s = _mk_service(db_session, "Тренировка В")
            when = (NOW + timedelta(hours=30)).isoformat()
            client.post(f"/api/v1/services/{s.id}/book",
                        json={"client_id": str(c.id), "booking_date": when},
                        headers=auth_headers)
            bid = str(db_session.query(ServiceBooking).first().id)
            # за 30 ч до занятия: при окне 24 ч отказало бы, при 48 — пускает
            r = client.post(f"/api/v1/services/bookings/{bid}/cancel", headers=auth_headers)
            assert r.status_code == 200, r.text
        finally:
            client.put("/api/v1/club-params/CANCEL_WINDOW_HOURS",
                       json={"value": "24"}, headers=auth_headers)


# ---------- политика входа ----------

class TestEntryPolicy:
    def test_subscription_is_reason(self, db_session):
        c = _mk_client(db_session, "+79000000021")
        t = _mk_tariff(db_session)
        _mk_subscription(db_session, c.id, t.id)
        reasons = entry_reasons(db_session, str(c.id), at=NOW)
        assert reasons and "Абонемент" in reasons[0]

    def test_paid_booking_in_window_is_reason(self, client, auth_headers, db_session):
        c = _mk_client(db_session, "+79000000022")
        s = _mk_service(db_session, "Массаж")
        when = (NOW + timedelta(minutes=30)).isoformat()
        client.post(f"/api/v1/services/{s.id}/book",
                    json={"client_id": str(c.id), "booking_date": when},
                    headers=auth_headers)
        bid = str(db_session.query(ServiceBooking).first().id)
        client.post(f"/api/v1/services/bookings/{bid}/pay", headers=auth_headers)
        reasons = entry_reasons(db_session, str(c.id), at=NOW)
        assert any("Массаж" in r for r in reasons)
        assert can_enter(db_session, str(c.id), at=NOW)

    def test_outside_window_not_a_reason(self, client, auth_headers, db_session):
        c = _mk_client(db_session, "+79000000023")
        s = _mk_service(db_session, "Массаж 2")
        when = (NOW + timedelta(hours=5)).isoformat()
        client.post(f"/api/v1/services/{s.id}/book",
                    json={"client_id": str(c.id), "booking_date": when},
                    headers=auth_headers)
        bid = str(db_session.query(ServiceBooking).first().id)
        client.post(f"/api/v1/services/bookings/{bid}/pay", headers=auth_headers)
        assert entry_reasons(db_session, str(c.id), at=NOW) == []
        assert not can_enter(db_session, str(c.id), at=NOW)

    def test_window_grows_with_param(self, client, auth_headers, db_session):
        client.put("/api/v1/club-params/QR_ACCESS_WINDOW_HOURS",
                   json={"value": "6"}, headers=auth_headers)
        try:
            c = _mk_client(db_session, "+79000000024")
            s = _mk_service(db_session, "Массаж 3")
            when = (NOW + timedelta(hours=5)).isoformat()
            client.post(f"/api/v1/services/{s.id}/book",
                        json={"client_id": str(c.id), "booking_date": when},
                        headers=auth_headers)
            bid = str(db_session.query(ServiceBooking).first().id)
            client.post(f"/api/v1/services/bookings/{bid}/pay", headers=auth_headers)
            assert can_enter(db_session, str(c.id), at=NOW)
        finally:
            client.put("/api/v1/club-params/QR_ACCESS_WINDOW_HOURS",
                       json={"value": "1"}, headers=auth_headers)


# ---------- свип ----------

class TestSweep:
    def test_remind_then_auto_cancel(self, client, auth_headers, db_session):
        c = _mk_client(db_session, "+79000000031")
        s = _mk_service(db_session, "Занятие свип")
        start = NOW + timedelta(hours=20)
        b = ServiceBooking(service_id=s.id, client_id=str(c.id),
                           booking_date=start, status="BOOKED")
        db_session.add(b); db_session.commit()
        # за 20 ч: напоминание (окно 24 ч)
        res = booking_sweep(now=NOW + timedelta(hours=3))
        assert res["reminded"] == 1
        db_session.expire_all()
        assert db_session.get(ServiceBooking, b.id).reminded_at is not None
        # за 4 ч (< дедлайна 6 ч): авто-отмена, рейтинг не тронут
        res = booking_sweep(now=start - timedelta(hours=4))
        assert res["auto_cancelled"] == 1
        db_session.expire_all()
        b2 = db_session.get(ServiceBooking, b.id)
        assert b2.status == "AUTO_CANCELLED"
        rating = db_session.execute(text("SELECT rating FROM clients WHERE id=:i"),
                                    {"i": str(c.id)}).scalar()
        assert rating == 5.0

    def test_confirmed_survives_deadline(self, db_session):
        c = _mk_client(db_session, "+79000000032")
        s = _mk_service(db_session, "Занятие свип 2")
        start = NOW + timedelta(hours=4)
        b = ServiceBooking(service_id=s.id, client_id=str(c.id),
                           booking_date=start, status="CONFIRMED")
        db_session.add(b); db_session.commit()
        res = booking_sweep(now=start - timedelta(hours=3))
        assert res["auto_cancelled"] == 0
        db_session.expire_all()
        assert db_session.get(ServiceBooking, b.id).status == "CONFIRMED"