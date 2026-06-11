# tests/test_auth.py
"""Тесты аутентификации и авторизации"""
import pytest


class TestAuth:
    """Тесты JWT + регистрация + логин"""

    def test_register(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "email": "new@mail.ru",
            "password": "password123",
            "first_name": "Иван",
            "last_name": "Петров",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["username"] == "newuser"

    def test_register_duplicate_username(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "dupuser",
            "email": "dup1@mail.ru",
            "password": "pass123",
            "first_name": "A",
            "last_name": "B",
        })
        resp = client.post("/api/v1/auth/register", json={
            "username": "dupuser",
            "email": "dup2@mail.ru",
            "password": "pass123",
            "first_name": "C",
            "last_name": "D",
        })
        assert resp.status_code == 409

    def test_login_success(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "loguser",
            "email": "log@mail.ru",
            "password": "mypass123",
            "first_name": "Test",
            "last_name": "Test",
        })
        resp = client.post("/api/v1/auth/token", data={
            "username": "loguser",
            "password": "mypass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        resp = client.post("/api/v1/auth/token", data={
            "username": "nonexistent",
            "password": "wrong",
        })
        assert resp.status_code in (401, 404)

    def test_me_endpoint(self, client, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "username" in data

    def test_me_without_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_token_check(self, client, auth_headers):
        resp = client.get("/api/v1/auth/token-check", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
