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


@pytest.fixture(autouse=True)
def _ensure_client_cols(db_session):
    """clients.rating и clients.parent_id для прямых проверок (свип/дети идут
    без HTTP -> ленивый ensure не отрабатывает). Только тестовая сессия."""
    cols = {r[1] for r in db_session.execute(text("PRAGMA table_info(clients)"))}
    if "rating" not in cols:
        db_session.execute(text("ALTER TABLE clients ADD COLUMN rating FLOAT DEFAULT 5.0"))
    if "parent_id" not in cols:
        db_session.execute(text("ALTER TABLE clients ADD COLUMN parent_id VARCHAR(64)"))
    db_session.commit()


def _uid(c) -> str:
    """UUID как хранится в sqlite: hex без дефисов."""
    return str(c.id).replace("-", "")


_API = {}


def _api(db):
    """(TestClient, headers) drift-proof: логин один раз на сессию тестов."""
    if "h" not in _API:
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.security import pwd_context
        from app.models.user import User
        if not db.query(User).filter_by(username="superadmin").first():
            db.add(User(username="superadmin", email="sa@t.ru",
                        password_hash=pwd_context.hash("testpass123"),
                        is_active=True, is_superuser=True))
            db.commit()
        c = TestClient(app)
        r = c.post("/api/v1/auth/login",
                   json={"login": "superadmin", "password": "testpass123"})
        _API["h"] = {"Authorization": "Bearer " + r.json()["access_token"]}
        _API["c"] = c
    return _API["c"], _API["h"]


def _mk_client(db, phone="+79000000001") -> Client:
    """Через API: сервер сам заполнит обязательные поля модели (дрейф-сейф)."""
    c, h = _api(db)
    resp = c.post("/api/v1/clients", json={"first_name": "Иван", "last_name": "Тестов",
                                           "phone": phone}, headers=h)
    assert resp.status_code in (200, 201), resp.text
    return db.query(Client).filter_by(id=resp.json()["id"]).first()


def _mk_service(db, name="Персональная тренировка", maxcap=1) -> Service:
    s = Service(name=name, category="PERSONAL_TRAINER", price=1500.0,
                duration_minutes=45, max_capacity=maxcap, is_active=True)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _mk_tariff(db, name="Безлимит", code="TEST-UNL") -> Tariff:
    import uuid as _uuid
    c, h = _api(db)
    r = c.post("/api/v1/tariffs/", headers=h, json={
        "code": f"{code}-{_uuid.uuid4().hex[:6]}", "name": name, "price": 3000,
        "currency": "RUB", "duration_days": 30, "visit_limit": 10,
        "is_unlimited": False, "is_active": True})   # зеркалим B6 (проверенный набор)
    assert r.status_code == 201, r.text
    return db.query(Tariff).filter_by(id=r.json()["id"]).first()


def _mk_subscription(db, client_id, tariff_id) -> Subscription:
    """Через API: сервер заполнит price/currency/даты из тарифа (дрейф-сейф)."""
    c, h = _api(db)
    r = c.post("/api/v1/subscriptions/", headers=h, json={
        "client_id": str(client_id), "tariff_id": str(tariff_id),
        "start_date": str(NOW.date()), "status": "ACTIVE"})
    assert r.status_code == 201, r.text
    return db.query(Subscription).filter_by(id=r.json()["id"]).first()


# ---------- параметры клуба ----------

class TestClubParams:
    def test_defaults_present(self, client, auth_headers):
        r = client.get("/api/v1/club-params", headers=auth_headers)
        assert r.status_code == 200
        data = {i["key"]: i["value"] for i in r.json()}
        assert data["SLOT_MINUTES"] == "45"
        assert data["ENTRY_WINDOW_BEFORE_HOURS"] == "1"
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
        bid = str(db_session.query(ServiceBooking).filter_by(client_id=str(c.id)).first().id)

        assert client.post(f"/api/v1/services/bookings/{bid}/confirm",
                           headers=auth_headers).status_code == 200
        assert client.post(f"/api/v1/services/bookings/{bid}/pay?price=1500",
                           headers=auth_headers).status_code == 200
        r = client.post(f"/api/v1/services/bookings/{bid}/complete", headers=auth_headers)
        assert r.status_code == 200 and r.json()["status"] == "COMPLETED"

        # рейтинг стартует с максимума 5.0 -> +0.1 упирается в кламп (остаётся 5.0)
        rating = db_session.execute(text("SELECT rating FROM clients WHERE replace(id, '-', '') = :i"),
                                    {"i": _uid(c)}).scalar()
        assert abs(rating - 5.0) < 1e-6

        # вторая бронь -> no-show: -0.5 с клампа, затем complete третьей: +0.1
        when2 = (NOW + timedelta(hours=50)).isoformat()
        client.post(f"/api/v1/services/{s.id}/book",
                    json={"client_id": str(c.id), "booking_date": when2}, headers=auth_headers)
        bid2 = str(db_session.query(ServiceBooking)
                   .filter_by(client_id=str(c.id)).order_by(ServiceBooking.booking_date.desc())
                   .first().id)
        client.post(f"/api/v1/services/bookings/{bid2}/confirm", headers=auth_headers)
        client.post(f"/api/v1/services/bookings/{bid2}/no-show", headers=auth_headers)
        rating = db_session.execute(text("SELECT rating FROM clients WHERE replace(id, '-', '') = :i"),
                                    {"i": _uid(c)}).scalar()
        assert abs(rating - 4.5) < 1e-6

        when3 = (NOW + timedelta(hours=70)).isoformat()
        client.post(f"/api/v1/services/{s.id}/book",
                    json={"client_id": str(c.id), "booking_date": when3}, headers=auth_headers)
        bid3 = str(db_session.query(ServiceBooking)
                   .filter_by(client_id=str(c.id)).order_by(ServiceBooking.booking_date.desc())
                   .first().id)
        client.post(f"/api/v1/services/bookings/{bid3}/confirm", headers=auth_headers)
        client.post(f"/api/v1/services/bookings/{bid3}/pay", headers=auth_headers)
        client.post(f"/api/v1/services/bookings/{bid3}/complete", headers=auth_headers)
        rating = db_session.execute(text("SELECT rating FROM clients WHERE replace(id, '-', '') = :i"),
                                    {"i": _uid(c)}).scalar()
        assert abs(rating - 4.6) < 1e-6  # +0.1 за завершённое занятие

    def test_no_show_drops_rating(self, client, auth_headers, db_session):
        c = _mk_client(db_session, "+79000000012")
        s = _mk_service(db_session, "Тренировка Б")
        when = (NOW + timedelta(hours=30)).isoformat()
        client.post(f"/api/v1/services/{s.id}/book",
                    json={"client_id": str(c.id), "booking_date": when},
                    headers=auth_headers)
        bid = str(db_session.query(ServiceBooking).filter_by(client_id=str(c.id)).first().id)
        client.post(f"/api/v1/services/bookings/{bid}/confirm", headers=auth_headers)
        r = client.post(f"/api/v1/services/bookings/{bid}/no-show", headers=auth_headers)
        assert r.status_code == 200
        rating = db_session.execute(text("SELECT rating FROM clients WHERE replace(id, '-', '') = :i"),
                                    {"i": _uid(c)}).scalar()
        assert abs(rating - 4.5) < 1e-6

    def test_cancel_window_from_params(self, client, auth_headers, db_session):
        """Окно отмены читается из параметров: бронь через 30 ч.
        Окно 48 ч -> отказ (осталось меньше 48 ч); окно 24 ч -> отмена проходит."""
        c = _mk_client(db_session, "+79000000013")
        s = _mk_service(db_session, "Тренировка В")
        when = (NOW + timedelta(hours=30)).isoformat()
        client.post(f"/api/v1/services/{s.id}/book",
                    json={"client_id": str(c.id), "booking_date": when},
                    headers=auth_headers)
        bid = str(db_session.query(ServiceBooking).filter_by(client_id=str(c.id)).first().id)
        try:
            client.put("/api/v1/club-params/CANCEL_WINDOW_HOURS",
                       json={"value": "48"}, headers=auth_headers)
            r = client.post(f"/api/v1/services/bookings/{bid}/cancel", headers=auth_headers)
            assert r.status_code == 400, r.text   # < 48 ч до занятия — нельзя

            client.put("/api/v1/club-params/CANCEL_WINDOW_HOURS",
                       json={"value": "24"}, headers=auth_headers)
            r = client.post(f"/api/v1/services/bookings/{bid}/cancel", headers=auth_headers)
            assert r.status_code == 200, r.text   # > 24 ч — можно
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
        bid = str(db_session.query(ServiceBooking).filter_by(client_id=str(c.id)).first().id)
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
        bid = str(db_session.query(ServiceBooking).filter_by(client_id=str(c.id)).first().id)
        client.post(f"/api/v1/services/bookings/{bid}/pay", headers=auth_headers)
        assert entry_reasons(db_session, str(c.id), at=NOW) == []
        assert not can_enter(db_session, str(c.id), at=NOW)

    def test_window_grows_with_param(self, client, auth_headers, db_session):
        """BEFORE увеличили 1 -> 6: занятие через 5 ч из «вне окна» стало «в окне»."""
        client.put("/api/v1/club-params/ENTRY_WINDOW_BEFORE_HOURS",
                   json={"value": "6"}, headers=auth_headers)
        try:
            c = _mk_client(db_session, "+79000000024")
            s = _mk_service(db_session, "Массаж 3")
            when = (NOW + timedelta(hours=5)).isoformat()
            client.post(f"/api/v1/services/{s.id}/book",
                        json={"client_id": str(c.id), "booking_date": when},
                        headers=auth_headers)
            bid = str(db_session.query(ServiceBooking).filter_by(client_id=str(c.id)).first().id)
            client.post(f"/api/v1/services/bookings/{bid}/pay", headers=auth_headers)
            assert can_enter(db_session, str(c.id), at=NOW)
        finally:
            client.put("/api/v1/club-params/ENTRY_WINDOW_BEFORE_HOURS",
                       json={"value": "1"}, headers=auth_headers)

    def test_stay_until_close(self, client, auth_headers, db_session):
        """ENTRY_STAY_UNTIL_CLOSE=true: вход вечером в день занятия разрешён
        (окно AFTER=1ч давно прошло, но «до конца дня»)."""
        client.put("/api/v1/club-params/ENTRY_STAY_UNTIL_CLOSE",
                   json={"value": "true"}, headers=auth_headers)
        try:
            c = _mk_client(db_session, "+79000000025")
            s = _mk_service(db_session, "Вечернее занятие")
            when = (NOW + timedelta(hours=2)).isoformat()
            client.post(f"/api/v1/services/{s.id}/book",
                        json={"client_id": str(c.id), "booking_date": when},
                        headers=auth_headers)
            bid = str(db_session.query(ServiceBooking).filter_by(client_id=str(c.id)).first().id)
            client.post(f"/api/v1/services/bookings/{bid}/pay", headers=auth_headers)
            # 8 часов ПОСЛЕ начала: AFTER=1ч нарушено, но until_close спасает
            assert can_enter(db_session, str(c.id), at=NOW + timedelta(hours=10))
        finally:
            client.put("/api/v1/club-params/ENTRY_STAY_UNTIL_CLOSE",
                       json={"value": "false"}, headers=auth_headers)

    def test_child_booking_grants_parent_entry(self, client, auth_headers, db_session):
        """Бронь ребёнка (CHILD, parent_id) — основание для входа РОДИТЕЛЯ."""
        parent = _mk_client(db_session, "+79000000027")
        child = Client(first_name="Пётр", last_name="Тестов",
                       phone="child:test:Пётр", client_category="CHILD")
        db_session.add(child); db_session.commit(); db_session.refresh(child)
        # parent_id — колонка вне модели (ALTER), выставляем raw-SQL
        db_session.execute(text(
            "UPDATE clients SET parent_id=:p WHERE replace(id,'-','')=:i"),
            {"p": _uid(parent), "i": _uid(child)})
        db_session.commit()
        s = _mk_service(db_session, "Детское плавание")
        when = (NOW + timedelta(minutes=30)).isoformat()
        client.post(f"/api/v1/services/{s.id}/book",
                    json={"client_id": str(child.id), "booking_date": when},
                    headers=auth_headers)
        bid = str(db_session.query(ServiceBooking).filter_by(client_id=str(child.id)).first().id)
        client.post(f"/api/v1/services/bookings/{bid}/pay", headers=auth_headers)
        reasons = entry_reasons(db_session, str(parent.id), at=NOW)
        assert any("Детское плавание" in r for r in reasons)
        assert can_enter(db_session, str(parent.id), at=NOW)

    def test_gym_access_full_day(self, client, auth_headers, db_session):
        """GYM_ACCESS (без слота): оплаченный день — вход в любое время дня."""
        c = _mk_client(db_session, "+79000000026")
        s = _mk_service(db_session, "Разовый зал")
        s.category = "GYM_ACCESS"
        db_session.commit()
        when = (NOW + timedelta(hours=1)).isoformat()
        client.post(f"/api/v1/services/{s.id}/book",
                    json={"client_id": str(c.id), "booking_date": when},
                    headers=auth_headers)
        bid = str(db_session.query(ServiceBooking).filter_by(client_id=str(c.id)).first().id)
        client.post(f"/api/v1/services/bookings/{bid}/pay", headers=auth_headers)
        # утро того же дня (задолго до «за 1 час») — пускает
        morning = NOW - timedelta(hours=6)
        assert can_enter(db_session, str(c.id), at=morning)


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
        res = booking_sweep(db_session, now=NOW + timedelta(hours=3))
        assert res["reminded"] == 1
        db_session.expire_all()
        assert db_session.get(ServiceBooking, b.id).reminded_at is not None
        # за 4 ч (< дедлайна 6 ч): авто-отмена, рейтинг не тронут
        res = booking_sweep(db_session, now=start - timedelta(hours=4))
        assert res["auto_cancelled"] == 1
        db_session.expire_all()
        b2 = db_session.get(ServiceBooking, b.id)
        assert b2.status == "AUTO_CANCELLED"
        rating = db_session.execute(text("SELECT rating FROM clients WHERE replace(id, '-', '') = :i"),
                                    {"i": _uid(c)}).scalar()
        assert rating == 5.0

    def test_confirmed_survives_deadline(self, db_session):
        c = _mk_client(db_session, "+79000000032")
        s = _mk_service(db_session, "Занятие свип 2")
        start = NOW + timedelta(hours=4)
        b = ServiceBooking(service_id=s.id, client_id=str(c.id),
                           booking_date=start, status="CONFIRMED")
        db_session.add(b); db_session.commit()
        res = booking_sweep(db_session, now=start - timedelta(hours=3))
        assert res["auto_cancelled"] == 0
        db_session.expire_all()
        assert db_session.get(ServiceBooking, b.id).status == "CONFIRMED"