# tests/test_email_queue.py
"""A4: очередь email — копится при выключенном SMTP, уходит при включённом,
ретраи с backoff, FAILED после max_attempts, дайджест ставит письмо в очередь."""
import pytest


@pytest.fixture
def email_env(db_session, monkeypatch):
    from app.services.email_queue_service import EmailQueueService, ensure_email_queue
    ensure_email_queue(db_session)
    from sqlalchemy import text
    db_session.execute(text("DELETE FROM email_queue"))
    db_session.commit()

    def _set_smtp(**cfg):
        # алиасы полей (тесты используют читаемые имена)
        if "smtp_password" in cfg:
            cfg["smtp_pass"] = cfg.pop("smtp_password")
        if "from_email" in cfg:
            cfg["email_from"] = cfg.pop("from_email")
        cfg.pop("smtp_ssl", None)   # режим определяется портом (465=SSL)
        vals = {"email_enabled": True, "smtp_host": "", "smtp_port": 465,
                "smtp_user": "", "smtp_pass": "", "email_from": ""}
        vals.update({k: v for k, v in cfg.items() if k in vals})
        cols = ", ".join(vals)
        ins = ", ".join(":%s" % k for k in vals)
        upd = ", ".join("%s=:%s" % (k, k) for k in vals)
        db_session.execute(text(
            "INSERT INTO notification_settings (id, %s) VALUES (1, %s)"
            " ON CONFLICT (id) DO UPDATE SET %s" % (cols, ins, upd)), vals)
        db_session.commit()

    return type("Env", (), {"db": db_session, "set_smtp": staticmethod(_set_smtp),
                            "q": EmailQueueService(db_session)})()


class TestEmailQueue:
    def test_queued_when_smtp_off_then_sent_when_on(self, client, auth_headers,
                                                    email_env, monkeypatch):
        """Критерий A4: без SMTP письмо копится (PENDING), после настройки — уходит (SENT)."""
        email_env.set_smtp(smtp_host="")   # SMTP выключен
        r = client.post("/api/v1/notify/test", headers=auth_headers,
                        json={"channel": "email", "to": "boss@club.ru",
                              "message": "проверка"})
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
                           from_email="club@mail.ru")
        res = email_env.q.process_queue()
        assert res["sent"] == 1
        row = email_env.db.execute(
            __import__("sqlalchemy").text(
                "SELECT status FROM email_queue WHERE recipient='boss@club.ru'")
        ).first()
        assert row[0] == "SENT"

    def test_retries_with_backoff_then_failed(self, client, auth_headers,
                                              email_env, monkeypatch):
        def _boom(self, cfg, recipient, subject, body, html_body):
            raise RuntimeError("SMTP unavailable")
        monkeypatch.setattr(
            "app.services.email_queue_service.EmailQueueService._deliver", _boom)

        # SMTP «настроен», но отправка падает -> ретраи -> FAILED
        email_env.set_smtp(smtp_host="smtp.mail.ru")
        email_env.q.enqueue("a@b.ru", "тема", "текст")
        from sqlalchemy import text
        row = None
        for expected_attempt in (1, 2, 3):
            # сбрасываем next_attempt_at, чтобы не ждать backoff
            email_env.db.execute(text(
                "UPDATE email_queue SET next_attempt_at=NULL WHERE recipient='a@b.ru'"))
            email_env.db.commit()
            email_env.q.process_queue()
            row = email_env.db.execute(text(
                "SELECT status, attempts FROM email_queue"
                " WHERE recipient='a@b.ru'")).first()
            assert row.attempts == expected_attempt
        assert row.status == "FAILED"   # после max_attempts

    def test_process_endpoint_for_admin(self, client, auth_headers, email_env,
                                        monkeypatch):
        monkeypatch.setattr(
            "app.services.email_queue_service.EmailQueueService._deliver",
            lambda self, cfg, recipient, subject, body, html_body: None)
        email_env.set_smtp(smtp_host="smtp.mail.ru")
        email_env.q.enqueue("x@y.ru", "s", "b")
        r = client.post("/api/v1/email-queue/process", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["sent"] >= 1

    def test_expiring_digest_enqueues_email(self, client, auth_headers, email_env):
        """Дайджест шлёт КЛУБУ (email_from из настроек) и ставит письмо в очередь."""
        email_env.set_smtp(email_from="club@mail.ru", smtp_user="club@mail.ru")
        r = client.post("/api/v1/notify/digest", headers=auth_headers)
        assert r.status_code == 200, r.text
        from sqlalchemy import text
        row = email_env.db.execute(text(
            "SELECT count(*) FROM email_queue WHERE recipient=:e"),
            {"e": "club@mail.ru"}).first()
        assert row[0] >= 1   # дайджест встал в очередь на адрес клуба