"""Банки: ролевой экран, маскирование и сохранение структурированной конфигурации."""
import json
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import text

import conftest
from app.api.dependencies import get_current_active_user, get_current_user
from app.api.v1 import server_settings as settings
from app.main import app


PATH = "/api/v1/server-settings/bank-config"


@pytest.fixture
def bank_settings_env(monkeypatch):
    monkeypatch.setattr(settings, "engine", conftest.engine)
    with conftest.engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS server_settings (key VARCHAR(255) PRIMARY KEY, value TEXT, updated_at TIMESTAMP)"))
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS ui_screens ("
            "id VARCHAR(36), code VARCHAR(64) PRIMARY KEY, name VARCHAR(128), "
            "path VARCHAR(255), icon VARCHAR(50), sort_order INTEGER, is_active BOOLEAN)"
        ))
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS ui_role_screens ("
            "id VARCHAR(36), role VARCHAR(100), screen_code VARCHAR(64), "
            "is_visible BOOLEAN, UNIQUE(role, screen_code))"
        ))
        connection.execute(text("DELETE FROM ui_role_screens"))
        connection.execute(text("DELETE FROM ui_screens"))
        connection.execute(text("DELETE FROM server_settings WHERE key='BANK_CONFIG'"))
    user = SimpleNamespace(
        id=uuid.uuid4(), username="superadmin", is_superuser=True,
        is_active=True, roles=[],
    )
    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_current_user, None)
    with conftest.engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS server_settings (key VARCHAR(255) PRIMARY KEY, value TEXT, updated_at TIMESTAMP)"))
        connection.execute(text("DELETE FROM server_settings WHERE key='BANK_CONFIG'"))


def _raw_config():
    with conftest.engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS server_settings (key VARCHAR(255) PRIMARY KEY, value TEXT, updated_at TIMESTAMP)"))
        raw = connection.execute(text(
            "SELECT value FROM server_settings WHERE key='BANK_CONFIG'"
        )).scalar()
    return json.loads(raw)


def test_bank_screen_registered_with_safe_role_defaults(client, bank_settings_env):
    response = client.get("/api/v1/ui-config/screens")

    assert response.status_code == 200
    bank = next(row for row in response.json()["screens"] if row["code"] == "banks")
    assert bank["name"] == "Банки"
    with conftest.engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS server_settings (key VARCHAR(255) PRIMARY KEY, value TEXT, updated_at TIMESTAMP)"))
        rows = connection.execute(text(
            "SELECT role, is_visible FROM ui_role_screens WHERE screen_code='banks'"
        )).fetchall()
    visibility = {role: bool(visible) for role, visible in rows}
    assert visibility["superadmin"] is True
    assert visibility["admin"] is True
    assert visibility["manager"] is False
    assert visibility["cashier"] is False


def test_save_and_read_never_returns_secrets(client, bank_settings_env):
    payload = {
        "active": "tinkoff",
        "providers": {
            "tinkoff": {
                "terminal_key": "terminal-demo",
                "password": "very-secret-password",
                "notification_url": "https://club.example.ru/api/v1/bank/webhook",
            }
        },
    }
    saved = client.put(PATH, json=payload)
    assert saved.status_code == 200, saved.text

    response = client.get(PATH)
    assert response.status_code == 200
    assert "very-secret-password" not in response.text
    fields = response.json()["providers"]["tinkoff"]["fields"]
    assert fields["password"] == {"secret": True, "is_set": True, "value": ""}
    assert fields["terminal_key"]["value"] == "terminal-demo"
    assert response.json()["providers"]["vtb"]["supported"] is False
    assert response.json()["providers"]["alfa"]["supported"] is False
    assert response.json()["providers"]["psb"]["supported"] is False

    generic = client.get("/api/v1/server-settings")
    assert generic.status_code == 200
    assert "very-secret-password" not in generic.text
    bank_row = next(row for row in generic.json() if row["key"] == "BANK_CONFIG")
    assert bank_row["value"] == "••••••"


def test_empty_secret_is_preserved_and_none_clears_it(client, bank_settings_env):
    initial = {
        "active": "",
        "providers": {"tinkoff": {
            "terminal_key": "terminal-demo",
            "password": "keep-this-secret",
            "notification_url": "https://club.example.ru/api/v1/bank/webhook",
        }},
    }
    assert client.put(PATH, json=initial).status_code == 200

    preserved = client.put(PATH, json={
        "active": "",
        "providers": {"tinkoff": {"password": "", "terminal_key": "new-terminal"}},
    })
    assert preserved.status_code == 200
    assert _raw_config()["tinkoff"]["password"] == "keep-this-secret"
    assert _raw_config()["tinkoff"]["terminal_key"] == "new-terminal"

    cleared = client.put(PATH, json={
        "active": "",
        "providers": {"tinkoff": {"password": None}},
    })
    assert cleared.status_code == 200
    assert "password" not in _raw_config()["tinkoff"]


def test_unsupported_bank_cannot_be_activated(client, bank_settings_env):
    response = client.put(PATH, json={"active": "vtb", "providers": {}})

    assert response.status_code == 422
    with conftest.engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS server_settings (key VARCHAR(255) PRIMARY KEY, value TEXT, updated_at TIMESTAMP)"))
        assert connection.execute(text(
            "SELECT 1 FROM server_settings WHERE key='BANK_CONFIG'"
        )).first() is None


def test_active_bank_requires_all_security_fields(client, bank_settings_env):
    response = client.put(PATH, json={
        "active": "sber",
        "providers": {"sber": {
            "mode": "json", "merchant_id": "club-api", "token": "api-secret",
            "return_url": "https://club.example.ru/pay/return",
        }},
    })

    assert response.status_code == 422
    assert "callback_token" in response.text


def test_role_screen_is_enforced_by_bank_settings_api(client, bank_settings_env):
    bank_settings_env.username = "manager-user"
    bank_settings_env.is_superuser = False
    bank_settings_env.roles = [SimpleNamespace(code="manager")]

    assert client.get(PATH).status_code == 403
    with conftest.engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS server_settings (key VARCHAR(255) PRIMARY KEY, value TEXT, updated_at TIMESTAMP)"))
        connection.execute(text(
            "UPDATE ui_role_screens SET is_visible=TRUE "
            "WHERE role='manager' AND screen_code='banks'"
        ))
    assert client.get(PATH).status_code == 200


def test_urls_require_https_and_raw_json_editor_is_closed(client, bank_settings_env):
    response = client.put(PATH, json={
        "active": "",
        "providers": {"tinkoff": {"notification_url": "http://192.168.1.10/webhook"}},
    })
    assert response.status_code == 422

    raw = client.put("/api/v1/server-settings", json={
        "key": "BANK_CONFIG", "value": '{"active":"tinkoff"}',
    })
    assert raw.status_code == 400
