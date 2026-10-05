# tests/test_payments_fiscal.py
"""Кассовый контур E31/E33: смены, guard, балансы, возвраты, инкассация.

Покрывает тест-матрицу Блоков 1-2, 4, 7 (см. docs). Запуск:
    pytest tests/test_payments_fiscal.py -v
"""
import pytest
from sqlalchemy import text


@pytest.fixture
def admin_headers(auth_headers):
    """auth_headers уже суперпользователь (см. conftest) — bypass RBAC."""
    return auth_headers


@pytest.fixture
def fiscal_env(db_session, monkeypatch):
    """SQLite-окружение кассы: служебные таблицы + наивный _insert
    (боевой _insert ходит в information_schema, которого нет в SQLite).
    Изоляция: кассовые таблицы общие на сессию (StaticPool), поэтому
    перед каждым тестом смены/остаток сбрасываем."""
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS fiscal_shift ("
        " id TEXT PRIMARY KEY, is_open INTEGER DEFAULT 0,"
        " opened_at TIMESTAMP, closed_at TIMESTAMP,"
        " cash_total NUMERIC DEFAULT 0, card_total NUMERIC DEFAULT 0,"
        " created_at TIMESTAMP, updated_at TIMESTAMP)"))
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS fiscal_settings ("
        " id TEXT PRIMARY KEY, driver VARCHAR(50) DEFAULT 'atol',"
        " port VARCHAR(50), settings TEXT, ofd_provider VARCHAR(50),"
        " created_at TIMESTAMP, updated_at TIMESTAMP)"))    
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS fiscal_receipts ("
        " id TEXT PRIMARY KEY, receipt_id TEXT, driver VARCHAR(50),"
        " receipt_type VARCHAR(20), amount NUMERIC, status VARCHAR(20),"
        " fiscal_document_number TEXT, fiscal_document_sign TEXT,"
        " original_receipt_id TEXT, ofd_provider VARCHAR(50), payload TEXT,"
        " created_at TIMESTAMP, updated_at TIMESTAMP)"))   
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS fiscal_pending ("
        " id INTEGER PRIMARY KEY DEFAULT 1, cash NUMERIC DEFAULT 0,"
        " card NUMERIC DEFAULT 0, withdrawn_at TIMESTAMP, withdrawn_by TEXT)"))
    try:
        db_session.execute(
            text("ALTER TABLE payments ADD COLUMN completed_at TIMESTAMP"))
    except Exception:
        pass  # колонка уже есть
    db_session.commit()
    # изоляция: чистим состояние кассы перед тестом (после CREATE!)
    db_session.execute(text("DELETE FROM fiscal_shift"))
    db_session.execute(text("DELETE FROM fiscal_pending"))
    db_session.execute(text("INSERT INTO fiscal_pending (id) VALUES (1)"))
    db_session.commit()

    def naive_insert(db, table, data):
        data = {k: v for k, v in data.items() if v is not None}
        if not data:
            return
        db.execute(text("INSERT INTO %s (%s) VALUES (%s)" % (
            table, ", ".join(data), ", ".join(":" + k for k in data))), data)

    monkeypatch.setattr("app.api.v1.fiscal._insert", naive_insert)
    return db_session


def _mk_client(client, headers, _attempt=0):
    import random
    phone = "+79%09d" % random.randint(0, 999999999)   # только цифры, 11 знаков
    r = client.post("/api/v1/clients/", headers=headers, json={
        "first_name": "Касса", "last_name": "Тестовая", "phone": phone})
    if r.status_code == 409 and _attempt < 5:          # редкое совпадение — повторим
        return _mk_client(client, headers, _attempt + 1)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _mk_payment(client, headers, amount, method="CASH", direction="INCOMING"):
    cid = _mk_client(client, headers)
    r = client.post("/api/v1/payments/", headers=headers, json={
        "client_id": cid, "amount": amount, "payment_method": method,
        "payment_direction": direction, "payment_category": "TEST"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestShiftLifecycle:
    """Блок 1: жизненный цикл смены."""

    def test_open_shift(self, client, admin_headers, fiscal_env):
        r = client.post("/api/v1/fiscal/open-shift", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["is_open"] is True

    def test_double_open_rejected(self, client, admin_headers, fiscal_env):
        client.post("/api/v1/fiscal/open-shift", headers=admin_headers)
        r = client.post("/api/v1/fiscal/open-shift", headers=admin_headers)
        assert r.status_code == 400
        assert "уже открыта" in r.json()["detail"]

    def test_close_without_open(self, client, admin_headers, fiscal_env):
        r = client.post("/api/v1/fiscal/close-shift", headers=admin_headers)
        assert r.status_code == 400

    def test_x_report_requires_open_shift(self, client, admin_headers, fiscal_env):
        r = client.post("/api/v1/fiscal/x-report", headers=admin_headers)
        assert r.status_code == 400

    def test_shift_state_balances(self, client, admin_headers, fiscal_env):
        client.post("/api/v1/fiscal/open-shift", headers=admin_headers)
        r = client.get("/api/v1/fiscal/shift", headers=admin_headers)
        d = r.json()
        assert d["is_open"] is True
        assert d["cash_total"] == 0.0 and d["card_total"] == 0.0


class TestPaymentLifecycle:
    """Блоки 2/3/7: деньги, guard, возвраты, сверка."""

    def test_confirm_requires_open_shift(self, client, admin_headers, fiscal_env):
        pid = _mk_payment(client, admin_headers, 100)
        r = client.post(f"/api/v1/payments/{pid}/complete", headers=admin_headers)
        assert r.status_code == 400
        assert "Смена закрыта" in r.json()["detail"]
        # платёж остался «Ожидает» — повтор возможен
        r2 = client.get(f"/api/v1/payments/{pid}", headers=admin_headers)
        assert r2.json()["status"] == "PENDING"

    def test_cash_flow_separate_from_card(self, client, admin_headers, fiscal_env):
        client.post("/api/v1/fiscal/open-shift", headers=admin_headers)
        p1 = _mk_payment(client, admin_headers, 1000, "CASH")
        p2 = _mk_payment(client, admin_headers, 2000, "CARD")
        p3 = _mk_payment(client, admin_headers, 300, "CASH", "OUTGOING")
        for p in (p1, p2, p3):
            r = client.post(f"/api/v1/payments/{p}/complete", headers=admin_headers)
            assert r.status_code == 200, r.text
        d = client.get("/api/v1/fiscal/shift", headers=admin_headers).json()
        assert d["cash_total"] == 700.0     # 1000 - 300
        assert d["card_total"] == 2000.0    # раздельный учёт, не суммируются

    def test_pending_not_in_balance_and_full_refund_zero_effect(
            self, client, admin_headers, fiscal_env):
        client.post("/api/v1/fiscal/open-shift", headers=admin_headers)
        pid = _mk_payment(client, admin_headers, 100)
        client.post(f"/api/v1/payments/{pid}/complete", headers=admin_headers)
        r = client.post(f"/api/v1/payments/{pid}/refund",
                        headers=admin_headers,
                        json={"reason": "тест полного возврата"})
        assert r.status_code == 200, r.text
        d = client.get("/api/v1/fiscal/shift", headers=admin_headers).json()
        assert d["cash_total"] == 0.0   # +100 (COMPLETED) исчлючён (REFUNDED),
                                        # платёж-возврат direction=REFUND исключён

    def test_refund_exceeds_amount_rejected(self, client, admin_headers, fiscal_env):
        client.post("/api/v1/fiscal/open-shift", headers=admin_headers)
        pid = _mk_payment(client, admin_headers, 200, "CARD")
        client.post(f"/api/v1/payments/{pid}/complete", headers=admin_headers)
        r = client.post(f"/api/v1/payments/{pid}/refund",
                        headers=admin_headers,
                        json={"amount": 99999, "reason": "граница"})
        assert r.status_code == 400
        assert "не может превышать" in r.json()["detail"]

    def test_close_shift_transfers_to_pending(self, client, admin_headers, fiscal_env):
        client.post("/api/v1/fiscal/open-shift", headers=admin_headers)
        pid = _mk_payment(client, admin_headers, 250)
        client.post(f"/api/v1/payments/{pid}/complete", headers=admin_headers)
        r = client.post("/api/v1/fiscal/close-shift", headers=admin_headers)
        d = r.json()
        assert r.status_code == 200
        assert d["cash_total"] == 250.0          # Z-отчёт
        assert d["prev_cash"] == 250.0           # ушло в «не снятый» остаток
        s = client.get("/api/v1/fiscal/shift", headers=admin_headers).json()
        assert s["is_open"] is False

    def test_cash_withdrawal_resets_pending(self, client, admin_headers, fiscal_env):
        client.post("/api/v1/fiscal/open-shift", headers=admin_headers)
        pid = _mk_payment(client, admin_headers, 250)
        client.post(f"/api/v1/payments/{pid}/complete", headers=admin_headers)
        client.post("/api/v1/fiscal/close-shift", headers=admin_headers)
        r = client.post("/api/v1/fiscal/cash-withdrawal", headers=admin_headers)
        d = r.json()
        assert r.status_code == 200
        assert d["withdrawn_cash"] == 250.0
        s = client.get("/api/v1/fiscal/shift", headers=admin_headers).json()
        assert s["prev_cash"] == 0.0