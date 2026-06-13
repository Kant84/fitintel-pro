# tests/test_clients.py
"""Тесты CRUD клиентов"""
import pytest


class TestClients:
    """Тесты клиентской базы"""

    def test_create_client(self, client, auth_headers):
        resp = client.post("/api/v1/clients/", headers=auth_headers, json={
            "first_name": "Петр",
            "last_name": "Иванов",
            "phone": "+79001234567",
            "email": "petr@mail.ru",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["first_name"] == "Петр"
        assert "id" in data

    def test_list_clients(self, client, auth_headers):
        resp = client.get("/api/v1/clients/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_get_client(self, client, auth_headers):
        create = client.post("/api/v1/clients/", headers=auth_headers, json={
            "first_name": "Test",
            "last_name": "Client",
            "phone": "+79009998877",
        })
        client_id = create.json()["id"]
        resp = client.get(f"/api/v1/clients/{client_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["phone"] == "+79009998877"

    def test_update_client(self, client, auth_headers):
        create = client.post("/api/v1/clients/", headers=auth_headers, json={
            "first_name": "Old",
            "last_name": "Name",
            "phone": "+79001112233",
        })
        client_id = create.json()["id"]
        resp = client.patch(f"/api/v1/clients/{client_id}", headers=auth_headers, json={
            "first_name": "New",
        })
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "New"

    def test_client_phone_unique(self, client, auth_headers):
        client.post("/api/v1/clients/", headers=auth_headers, json={
            "first_name": "A",
            "last_name": "B",
            "phone": "+79000000001",
        })
        resp = client.post("/api/v1/clients/", headers=auth_headers, json={
            "first_name": "C",
            "last_name": "D",
            "phone": "+79000000001",
        })
        assert resp.status_code == 409

    def test_unauthorized_access(self, client):
        resp = client.get("/api/v1/clients/")
        assert resp.status_code == 401
