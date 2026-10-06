# tests/test_email_queue.py
"""A4: очередь email — копится при выключенном SMTP, уходит при включённом,
ретраи с backoff, FAILED после max_attempts, дайджест ставит письма в очередь."""
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest


@pytest.fixture
def email_env(db_session, monkeypatch):
    from app.services.email_queue_service import EmailQueueService, ensure_email_queue
    ensure_email_queue(db_session)
    from sqlalchemy import text
    db_session.execute(text("DELETE FROM email_queue"))
    db_session.commit()

    def _set_smtp(**cfg):
        r = db_session.execute(text("SELECT config FROM notification_settings WHERE id=1"))
        row = r.first()
        import json
        cur = {}
        if row and row[0]:
            try:
                cur = json.loads(row[0])
            except Exception:
                pass
        cur.update(cfg)
        db_session.execute(text(
            "INSERT INTO notification_settings (id, config, updated_at)"
            " VALUES (1, :c, :t) ON CONFLICT (id) DO UPDATE SET config=:c"),
            {"c": json.dumps(cur, ensure_ascii=False),
             "t": datetime.now(timezone.utc).isoformat()})
        db_session.commit()

    return type("Env", (), {"db": db_session, "set_smtp": staticmethod(_set_smtp),
                            "q": EmailQueueService(db_session)})()


def _mk_client(client, headers, with_email=True):
    phone = "+79%09d" % (uuid.uuid4().int % 10 ** 9)
    payload = {"first_name": "Почта", "last_name": "Тестовая", "phone": phone}
    if with_email:
        payload["email"] = "client_%s@test.ru" % uuid.uuid4().hex[:8]
    r = client.post("/api/v1/clients/", headers=headers, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


class TestEmailQueue:
    def test_queued_when_smtp_off_then_sent_when_on(self, client, auth_headers, email_env, monkeypatch):
        """Критерий A4: без SMTP письмо копится (PENDING), после настройки — уходит (SENT)."""
        email_env.set_smtp(smtp_host="")   # SMTP выключен
        r = client.post("/api/v1/notifications/send-test", headers=auth_headers,
                        json={"email": "boss@club.ru", "message": "проверка"})
        assert r.status_code == 200, r.text

        row = email_env.db.execute(
            __import__("sqlalchemy").text(
                "SELECT status FROM email_queue WHERE recipient='boss@club.ru'")
        ).first()
        assert row and row[0] == "PENDING"

        # «включили SMTP» — доставку подменяем (боевой smtplib в тестах не нужен)
        monkeypatch.setattr(
            "app.services.email_queue_service.EmailQueueService._deliver",
            lambda self, cfg, recipient, subject, body, html_body: None)
        email_env.set_smtp(smtp_host="smtp.mail.ru", smtp_port=465,
                           smtp_user="club@mail.ru", smtp_password="app-pass",
                           smtp_ssl=True, from_email="club@mail.ru")
        res = email_env.q.process_queue()
        assert res["sent"] == 1
        row = email_env.db.execute(
            __import__("sqlalchemy").text(
                "SELECT status FROM email_queue WHERE recipient='boss@club.ru'")
        ).first()
        assert row[0] == "SENT"

    def test_retries_with_backoff_then_failed(self, client, auth_headers, email_env, monkeypatch):
        def _boom(self, cfg, recipient, subject, body, html_body):
            raise RuntimeError("SMTP unavailable")
        monkeypatch.setattr(
            "app.services.email_queue_service.EmailQueueService._deliver", _boom)

        email_env.q.enqueue("a@b.ru", "тема", "текст", max_attempts=3)
        from sqlalchemy import text
        for expected_attempt in (1, 2, 3):
            # сбрасываем next_attempt_at, чтобы не ждать backoff
            email_env.db.execute(text(
                "UPDATE email_queue SET next_attempt_at=NULL WHERE recipient='a@b.ru'"))
            email_env.db.commit()
            email_env.q.process_queue()
            row = email_env.db.execute(text(
                "SELECT status, attempts FROM email_queue WHERE recipient='a@b.ru'")).first()
            assert row.attempts == expected_attempt
        assert row.status == "FAILED"   # после max_attempts

    def test_process_endpoint_for_admin(self, client, auth_headers, email_env, monkeypatch):
        monkeypatch.setattr(
            "app.services.email_queue_service.EmailQueueService._deliver",
            lambda self, cfg, recipient, subject, body, html_body: None)
        email_env.set_smtp(smtp_host="smtp.mail.ru")
        email_env.q.enqueue("x@y.ru", "s", "b")
        r = client.post("/api/v1/notifications/email-queue/process", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["sent"] >= 1

    def test_expiring_digest_enqueues_email(self, client, auth_headers, email_env):
        c = _mk_client(client, auth_headers)
        code = f"TAR_{uuid.uuid4().hex[:8]}"
        t = client.post("/api/v1/tariffs/", headers=auth_headers, json={
            "code": code, "name": f"Тариф {code}", "price": 1000, "currency": "RUB",
            "duration_days": 30, "visit_limit": 10,
            "is_unlimited": False, "is_active": True})
        assert t.status_code == 201, t.text
        r = client.post("/api/v1/subscriptions/", headers=auth_headers, json={
            "client_id": c["id"], "tariff_id": t.json()["id"],
            "start_date": str(date.today() - timedelta(days=28)),
            "status": "ACTIVE"})
        assert r.status_code == 201, r.text

        r = client.post("/api/v1/notifications/expiring-digest?days=7",
                        headers=auth_headers)
        assert r.status_code == 200, r.text
        from sqlalchemy import text
        row = email_env.db.execute(text(
            "SELECT count(*) FROM email_queue WHERE recipient=:e"),
            {"e": c["email"]}).first()
        assert row[0] >= 1   # дайджест поставил письмо в очередь