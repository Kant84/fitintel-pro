# tests/test_auth.py
"""Тесты аутентификации: register/login/token/refresh/me/change-password/logout.

Контракт — app/api/v1/auth.py (JSON login {"login","password"}, register -> TokenResponse 200,
token-check -> {"user", "message"}, refresh ротирует токен, logout отзывает).
"""
import uuid

import pytest


def _uniq(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class TestAuth:
    """Аутентификация и токены."""

    def test_register_success(self, client):
        login = _uniq("reguser")
        resp = client.post("/api/v1/auth/register", json={
            "login": login,
            "email": f"{login}@test.ru",
            "password": "password123",
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "refresh_token" in data

    def test_register_duplicate_login(self, client):
        login = _uniq("dupuser")
        payload = {"login": login, "password": "pass123"}
        first = client.post("/api/v1/auth/register", json=payload)
        assert first.status_code == 200, first.text
        second = client.post("/api/v1/auth/register", json=payload)
        assert second.status_code == 409

    def test_login_success_json(self, client):
        login = _uniq("loguser")
        client.post("/api/v1/auth/register", json={
            "login": login, "password": "mypass123"})
        resp = client.post("/api/v1/auth/login", json={
            "login": login, "password": "mypass123"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "access_token" in data and "refresh_token" in data

    def test_login_form_token_endpoint(self, client):
        """OAuth2-форма для Swagger: POST /auth/token (form username/password)."""
        login = _uniq("formuser")
        client.post("/api/v1/auth/register", json={
            "login": login, "password": "formpass123"})
        resp = client.post("/api/v1/auth/token", data={
            "username": login, "password": "formpass123"})
        assert resp.status_code == 200, resp.text
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "login": "no_such_user", "password": "wrong"})
        assert resp.status_code == 401

    def test_me_endpoint(self, client, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert "username" in resp.json()

    def test_me_without_token(self, client):
        assert client.get("/api/v1/auth/me").status_code == 401

    def test_token_check(self, client, auth_headers):
        resp = client.get("/api/v1/auth/token-check", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "user" in data          # актуальная схема: {"user", "message"}
        assert "message" in data

    def test_change_password_and_login_with_new(self, client):
        login = _uniq("pwuser")
        old, new = "oldpass123", "newpass456"
        client.post("/api/v1/auth/register", json={
            "login": login, "password": old})
        token = client.post("/api/v1/auth/login", json={
            "login": login, "password": old}).json()["access_token"]
        h = {"Authorization": "Bearer " + token}

        # неверный текущий -> 400
        bad = client.post("/api/v1/auth/change-password", headers=h, json={
            "current_password": "nope", "new_password": new})
        assert bad.status_code == 400

        # корректная смена -> старый пароль не пускает, новый пускает
        ok = client.post("/api/v1/auth/change-password", headers=h, json={
            "current_password": old, "new_password": new})
        assert ok.status_code == 200, ok.text
        assert client.post("/api/v1/auth/login", json={
            "login": login, "password": old}).status_code == 401
        assert client.post("/api/v1/auth/login", json={
            "login": login, "password": new}).status_code == 200

    def test_refresh_rotates_token(self, client):
        login = _uniq("refreshuser")
        r = client.post("/api/v1/auth/register", json={
            "login": login, "password": "refresh123"})
        old_refresh = r.json()["refresh_token"]

        # обмен на новую пару
        r2 = client.post("/api/v1/auth/refresh",
                         json={"refresh_token": old_refresh})
        assert r2.status_code == 200, r2.text
        new_refresh = r2.json()["refresh_token"]

        # старый refresh сгорел (ротация) — повторное использование -> 401
        r3 = client.post("/api/v1/auth/refresh",
                         json={"refresh_token": old_refresh})
        assert r3.status_code == 401
        # новый жив
        r4 = client.post("/api/v1/auth/refresh",
                         json={"refresh_token": new_refresh})
        assert r4.status_code == 200

    def test_logout_revokes_refresh(self, client):
        login = _uniq("logoutuser")
        r = client.post("/api/v1/auth/register", json={
            "login": login, "password": "logout123"})
        refresh = r.json()["refresh_token"]
        access = r.json()["access_token"]

        out = client.post("/api/v1/auth/logout",
                          headers={"Authorization": "Bearer " + access})
        assert out.status_code == 200, out.text

        # после logout refresh отозван
        r2 = client.post("/api/v1/auth/refresh",
                         json={"refresh_token": refresh})
        assert r2.status_code == 401