# -*- coding: utf-8 -*-
"""Клиент HTTP API 1С:Фитнес клуб (V3) для FitIntel Pro.

Авторизация двухуровневая (как в спецификации Helix-QA/API):
  1) Basic: base64(UTF-8("Пользователь:Пароль"))
  2) заголовок apikey: ключ приложения (внешней системы).
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class Fitness1CError(Exception):
    """Ошибка API 1С (error/error_message из ответа или сети)."""

    def __init__(self, code: Any, message: str, http_status: Optional[int] = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.http_status = http_status


@dataclass
class Fitness1CConfig:
    base_url: str = ""        # например http://192.168.101.182:8095/hs/api/v3
    username: str = ""        # имя для входа пользователя ИБ
    password: str = ""
    api_key: str = ""         # ключ приложения
    club_id: str = ""         # UUID клуба; если пусто — берётся первый из /clubs/
    timeout: int = 25
    verify_tls: bool = True


class Fitness1CClient:
    def __init__(self, config: Fitness1CConfig):
        self.config = config
        self._session = requests.Session()

    # ---------- транспорт ----------
    def _headers(self) -> dict:
        pair = f"{self.config.username}:{self.config.password}".encode("utf-8")
        return {
            "Authorization": "Basic " + base64.b64encode(pair).decode("ascii"),
            "apikey": self.config.api_key,
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, params: dict = None, json_body: dict = None) -> Any:
        url = self.config.base_url.rstrip("/") + path
        try:
            resp = self._session.request(
                method, url, headers=self._headers(), params=params, json=json_body,
                timeout=self.config.timeout, verify=self.config.verify_tls)
        except requests.RequestException as exc:
            raise Fitness1CError(-2, f"Сетевая ошибка: {exc}") from exc
        if resp.status_code == 401:
            raise Fitness1CError(401, "Ошибка аутентификации пользователя 1С (Basic)", 401)
        try:
            payload = resp.json()
        except ValueError as exc:
            raise Fitness1CError(-1, f"Невалидный ответ (не JSON): {resp.text[:200]}", resp.status_code) from exc
        if isinstance(payload, dict) and payload.get("result") is False:
            raise Fitness1CError(payload.get("error"), payload.get("error_message", "Ошибка API"), resp.status_code)
        resp.raise_for_status()
        return payload.get("data") if isinstance(payload, dict) and "data" in payload else payload

    # ---------- сервисные ----------
    def test_connection(self) -> dict:
        """Аналог кнопки «Тест связи». Возвращает auth_types + клубы."""
        auth_types = self._request("GET", "/auth_types")
        clubs = self._request("GET", "/clubs/") or []
        club_id = self.config.club_id or (clubs[0]["id"] if clubs else "")
        if not clubs:
            raise Fitness1CError(-3, "API ответил, но список клубов пуст (проверьте «Соответствие клубов» в 1С)")
        return {"ok": True, "auth_types": auth_types, "clubs": clubs, "club_id": club_id}

    def get_club_id(self) -> str:
        if self.config.club_id:
            return self.config.club_id
        clubs = self._request("GET", "/clubs/") or []
        if not clubs:
            raise Fitness1CError(-3, "Список клубов пуст")
        return clubs[0]["id"]

    # ---------- клиенты ----------
    def list_customers(self, changed_after: Optional[str] = None) -> list:
        params = {"club_id": self.get_club_id()}
        if changed_after:
            params["changed_after"] = changed_after
        return self._request("GET", "/customers/", params=params) or []

    def get_customer(self, customer_id: str) -> dict:
        return self._request("GET", f"/customers/{customer_id}/")

    def create_customer(self, name: str, phone: str, email: str = "",
                        birthday: str = "", sex: str = "", note: str = "") -> dict:
        body = {"name": name, "phone": phone, "club_id": self.get_club_id(),
                "email": email, "birthday": birthday, "sex": sex, "note": note}
        return self._request("POST", "/customers/", json_body=body)

    def update_customer(self, customer_id: str, **fields) -> dict:
        return self._request("PATCH", f"/customers/{customer_id}/", json_body=fields)

    def get_customer_photo(self, customer_id: str) -> bytes:
        url = self.config.base_url.rstrip("/") + f"/customers/{customer_id}/photo/"
        resp = self._session.get(url, headers=self._headers(),
                                 timeout=self.config.timeout, verify=self.config.verify_tls)
        resp.raise_for_status()
        return resp.content

    # ---------- членства ----------
    def list_memberships(self, customer_id: str) -> list:
        return self._request("GET", f"/customers/{customer_id}/memberships/",
                             params={"club_id": self.get_club_id()}) or []

    # ---------- шкафчики ----------
    def list_cabinets(self) -> list:
        return self._request("GET", "/cabinets/", params={"club_id": self.get_club_id()}) or []

    def list_club_cabinets(self) -> list:
        return self._request("GET", "/club_cabinets/", params={"club_id": self.get_club_id()}) or []

    def assign_cabinet(self, customer_id: str, cabinet_id: str) -> dict:
        return self._request("POST", f"/customers/{customer_id}/club_cabinets/",
                             json_body={"cabinet_id": cabinet_id, "club_id": self.get_club_id()})

    def release_cabinet(self, assignment_id: str) -> dict:
        return self._request("DELETE", f"/club_cabinets/{assignment_id}/")

    # ---------- персонал и расписание ----------
    def list_employees(self) -> list:
        return self._request("GET", "/employees/") or []

    def list_schedules(self, on_date: Optional[str] = None) -> list:
        params = {"club_id": self.get_club_id()}
        if on_date:
            params["date"] = on_date
        return self._request("GET", "/schedules/", params=params) or []

    # ---------- визиты (turnstile) ----------
    def set_person_state(self, person_id: str, state_id: int) -> dict:
        return self._request("POST", f"/persons/{person_id}/state/", json_body={"state_id": state_id})

    def get_person_state(self, person_id: str) -> Optional[dict]:
        return self._request("GET", f"/persons/{person_id}/state/")

    def list_visits(self, on_date: Optional[str] = None) -> list:
        params = {"club_id": self.get_club_id()}
        if on_date:
            params["date"] = on_date
        return self._request("GET", "/visits/", params=params) or []